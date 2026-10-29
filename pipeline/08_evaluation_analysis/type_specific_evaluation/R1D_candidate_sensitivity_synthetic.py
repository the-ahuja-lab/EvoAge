#!/usr/bin/env python3
"""
Filtered, type-constrained sampled-negative evaluation for DGL-KE RESCAL on a
synthetic typed knowledge graph, plus a type-preserving randomized control.

For every test triple and each side (head / tail), the positive is ranked against
--num_neg (default 16) negatives drawn uniformly from the type-compatible candidate
pool of that relation, rejecting any draw that is a known-true triple
(train+valid+test). Rank = 1 + #(neg > pos) + 0.5 * #(neg == pos).

Controls (--control_type):
  pool    (default) fake triples draw head and tail uniformly from the FULL
          type-compatible head/tail pools of the relation; verified not in
          train+valid+test. Same n as the test set. Works for every relation.
  shuffle heads and tails permuted within the relation (degree-preserving),
          repaired against known triples, with a full-pool fallback.

RESCAL: s(h, r, t) = h^T M_r t,  M_r = relation_emb[r].reshape(d, d)
"""

import argparse, csv, json, os, subprocess, sys, time
import numpy as np

NUM_TYPES_UNSET = -1


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def human(n):
    return f"{n:,}"


# --------------------------------------------------------------------- input
def _read_txt_triples(path):
    import pandas as pd
    df = pd.read_csv(path, sep='\t', header=None, usecols=[0, 1, 2],
                     names=['h', 'r', 't'], dtype=np.int64, engine='c', quoting=3)
    return np.ascontiguousarray(df.values.astype(np.int32))


def load_split(data_path, stem, cache_dir, allow_pt=True):
    cache = os.path.join(cache_dir, stem + '.npy')
    if os.path.exists(cache):
        x = np.load(cache, mmap_mode='r')
        log(f"  {stem}: {human(len(x))} triples (cached)")
        return np.asarray(x)

    txt, pt = os.path.join(data_path, stem + '.txt'), os.path.join(data_path, stem + '.pt')
    t0 = time.time()
    x = None
    if allow_pt and os.path.exists(pt):
        import torch
        import itertools
        head = None
        if os.path.exists(txt):
            with open(txt) as fh:
                head = np.array([[int(v) for v in l.split('\t')[:3]]
                                 for l in itertools.islice(fh, 1000)], dtype=np.int64)
        y = torch.load(pt, map_location='cpu')
        y = y.numpy()
        if head is None or (len(y) >= 1000 and np.array_equal(y[:1000].astype(np.int64), head)):
            x = np.ascontiguousarray(y.astype(np.int32))
            log(f"  {stem}: {human(len(x))} triples from .pt in {time.time()-t0:.1f}s")
        else:
            log(f"  {stem}: .pt disagrees with .txt -- falling back to text parse")
        del y
    if x is None:
        x = _read_txt_triples(txt)
        log(f"  {stem}: {human(len(x))} triples from .txt in {time.time()-t0:.1f}s")
    np.save(cache, x)
    return x


def load_types(path, cache_dir):
    cc, cn = os.path.join(cache_dir, 'type_code.npy'), os.path.join(cache_dir, 'type_names.txt')
    if os.path.exists(cc) and os.path.exists(cn):
        return np.load(cc), open(cn).read().split('\n')
    import pandas as pd
    t0 = time.time()
    df = pd.read_csv(path, sep='\t', header=None, usecols=[0, 2], names=['id', 'ty'],
                     dtype={0: np.int64, 2: 'category'}, engine='c', quoting=3)
    ids = df['id'].values
    codes = df['ty'].cat.codes.values.astype(np.int16)
    names = list(df['ty'].cat.categories)
    arr = np.full(int(ids.max()) + 1, NUM_TYPES_UNSET, dtype=np.int16)
    arr[ids] = codes
    np.save(cc, arr)
    open(cn, 'w').write('\n'.join(names))
    log(f"  types: {human(len(arr))} entities, {len(names)} types in {time.time()-t0:.1f}s")
    return arr, names


# ------------------------------------------------------------------- prepare
def prepare(a):
    os.makedirs(a.work, exist_ok=True)
    done = os.path.join(a.work, 'PREPARED')
    if os.path.exists(done) and not a.force_prepare:
        log("prepare: reusing existing per-relation cache")
        return json.load(open(done))

    log("prepare: loading splits")
    splits = {n: load_split(a.data_path, n, a.work, not a.no_pt)
              for n in (a.train, a.valid, a.test)}
    test = splits[a.test]

    log("prepare: grouping all splits by relation")
    allX = np.concatenate([splits[n] for n in (a.train, a.valid, a.test)], axis=0)
    for n in list(splits):
        if n != a.test:
            del splits[n]
    meta = {'num_test': int(len(test)), 'rel': {}}

    for tag, X in (('all', allX), ('test', test)):
        t0 = time.time()
        R = X[:, 1].astype(np.int32)
        order = np.argsort(R, kind='stable')
        Rs = R[order]
        bnd = np.searchsorted(Rs, np.arange(int(Rs.max()) + 2))
        for r in range(len(bnd) - 1):
            s, e = bnd[r], bnd[r + 1]
            if e <= s:
                continue
            idx = order[s:e]
            np.save(os.path.join(a.work, f'{tag}_{r}.npy'),
                    np.ascontiguousarray(X[idx][:, [0, 2]]))
            meta['rel'].setdefault(str(r), {})[tag] = int(e - s)
        log(f"  {tag}: grouped {human(len(X))} triples into "
            f"{sum(1 for v in meta['rel'].values() if tag in v)} relations "
            f"in {time.time()-t0:.1f}s")
        del R, order, Rs
    del allX
    json.dump(meta, open(done, 'w'))
    return meta


# ----------------------------------------------------------------- controls
def within_relation_derangement(n, rng):
    if n == 1:
        return np.zeros(1, dtype=np.int64)
    p = rng.permutation(n)
    fx = np.flatnonzero(p == np.arange(n))
    while fx.size:
        if fx.size == 1:
            i = int(fx[0])
            j = int(rng.integers(n - 1))
            j += (j >= i)
            p[i], p[j] = p[j], p[i]
        else:
            p[fx] = p[np.roll(fx, 1)]
        fx = np.flatnonzero(p == np.arange(n))
    return p


def _is_known(known, num_ent, x):
    """True for rows of x (h, t) that are in the known-true code set."""
    code = x[:, 0].astype(np.int64) * np.int64(num_ent) + x[:, 1].astype(np.int64)
    i = np.minimum(np.searchsorted(known, code), len(known) - 1)
    return known[i] == code


def make_control_pool(n, seed, r, known, num_ent, head_pool, tail_pool, max_rounds=200):
    """Full-pool control: n fake (h, t) pairs, head ~ uniform(head_pool),
    tail ~ uniform(tail_pool), verified absent from train+valid+test.

    known: sorted unique int64 codes h*num_ent+t of every known-true (h, t) for r.
    Returns (control array (n, 2) int32, (n_real_first_draw, n_real_after_repair)).
    """
    rng = np.random.default_rng(seed * 100003 + r)
    out = np.empty((n, 2), dtype=np.int32)
    out[:, 0] = head_pool[rng.integers(len(head_pool), size=n)]
    out[:, 1] = tail_pool[rng.integers(len(tail_pool), size=n)]
    bad = np.flatnonzero(_is_known(known, num_ent, out))
    n_first = bad.size
    for _ in range(max_rounds):
        if not bad.size:
            break
        out[bad, 0] = head_pool[rng.integers(len(head_pool), size=bad.size)]
        out[bad, 1] = tail_pool[rng.integers(len(tail_pool), size=bad.size)]
        bad = bad[_is_known(known, num_ent, out[bad])]
    return out, (n_first, int(bad.size))


def make_control_shuffle(ht, seed, r, known, num_ent, tail_pool_fn=None, max_rounds=100):
    """Degree-preserving control: permute heads and tails within the relation,
    redraw collisions from the relation's test tails, then (fallback) from the
    full tail pool."""
    rng = np.random.default_rng(seed * 100003 + r)
    n = len(ht)
    if n < 2:
        return ht.copy(), (0, 0)
    out = np.empty_like(ht)
    out[:, 0] = ht[within_relation_derangement(n, rng), 0]
    out[:, 1] = ht[within_relation_derangement(n, rng), 1]

    bad = np.flatnonzero(_is_known(known, num_ent, out))
    n_first = bad.size
    for _ in range(max_rounds):
        if not bad.size:
            break
        out[bad, 1] = ht[rng.integers(n, size=bad.size), 1]
        bad = bad[_is_known(known, num_ent, out[bad])]
    if bad.size and tail_pool_fn is not None:
        pool = tail_pool_fn()
        for _ in range(max_rounds):
            if not bad.size:
                break
            out[bad, 1] = pool[rng.integers(len(pool), size=bad.size)]
            bad = bad[_is_known(known, num_ent, out[bad])]
    return out, (n_first, int(bad.size))


# ------------------------------------------------------------------ ranking
def rank_sampled(torch, dev, ent_t, Mr_eff, qent, tent, fcodes_t, pool_t, num_ent,
                 K, ties, chunk, gen, max_rounds=50):
    """Rank each target against K filtered, type-compatible sampled negatives.

    qent/tent: (n,) query / target entity per test triple.
    fcodes_t:  sorted unique int64 codes query*num_ent+val of ALL known-true pairs
               (on device) -- used to reject negatives that are known triples.
    Returns float64 ranks in [1, K+1].
    """
    n = len(qent)
    C = pool_t.numel()
    nf = fcodes_t.numel()
    ranks = np.empty(n, dtype=np.float64)
    ar = torch.arange(K, device=dev)[None, :]
    S = 2 * K

    for s in range(0, n, chunk):
        q = torch.as_tensor(qent[s:s + chunk], dtype=torch.long, device=dev)
        t = torch.as_tensor(tent[s:s + chunk], dtype=torch.long, device=dev)
        B = q.numel()
        proj = ent_t.index_select(0, q) @ Mr_eff
        pos = (proj * ent_t.index_select(0, t)).sum(1)

        neg = torch.zeros(B, K, dtype=torch.long, device=dev)
        cnt = torch.zeros(B, dtype=torch.long, device=dev)
        qbase = q * num_ent
        for _ in range(max_rounds):
            if bool((cnt >= K).all()):
                break
            cand = pool_t[torch.randint(C, (B, S), device=dev, generator=gen)]
            code = qbase[:, None] + cand
            idx = torch.searchsorted(fcodes_t, code).clamp_(max=nf - 1)
            valid = fcodes_t[idx] != code            # not a known-true triple
            cs = valid.cumsum(1) + cnt[:, None]
            take = valid & (cs <= K)
            rows, cols = take.nonzero(as_tuple=True)
            neg[rows, cs[rows, cols] - 1] = cand[rows, cols]
            cnt = torch.clamp(cnt + valid.sum(1), max=K)
        nv = ar < cnt[:, None]                       # rows w/ tiny pools may have < K

        emb = ent_t.index_select(0, neg.reshape(-1)).reshape(B, K, -1)
        ns = torch.einsum('bd,bkd->bk', proj, emb)
        gt = ((ns > pos[:, None]) & nv).sum(1).double()
        rk = gt + 1.0
        if ties:
            eq = ((ns == pos[:, None]) & nv).sum(1).double()
            rk = rk + eq / 2.0
        ranks[s:s + B] = rk.cpu().numpy()
        del emb, ns, neg, proj
    return ranks


# ------------------------------------------------------------------ metrics
def metrics(rk):
    rk = np.asarray(rk, dtype=np.float64)
    return dict(n=int(len(rk)), MRR=float((1 / rk).mean()), MR=float(rk.mean()),
                H1=float((rk <= 1).mean()), H3=float((rk <= 3).mean()),
                H10=float((rk <= 10).mean()))


def show(tag, per_rel, names):
    allr = {}
    for side in ('tail', 'head'):
        v = [per_rel[r][side] for r in per_rel if side in per_rel[r]]
        allr[side] = np.concatenate(v) if v else np.zeros(0)
    allr['both'] = np.concatenate([allr['tail'], allr['head']])

    print(f"\n{'='*104}\n{tag}\n{'='*104}")
    print(f"{'rel':>4} {'relation':<46}{'n':>11}{'pool':>10}{'MRR':>8}{'H@1':>8}{'H@3':>8}{'H@10':>8}{'MR':>10}")
    macro = []
    for r in sorted(per_rel, key=lambda x: -len(per_rel[x].get('tail', []))):
        rk = np.concatenate([per_rel[r][s] for s in ('tail', 'head') if s in per_rel[r]])
        m = metrics(rk); macro.append(m)
        print(f"{r:>4} {names.get(r,'?'):<46}{m['n']:>11,}{per_rel[r].get('pool',0):>10,}"
              f"{m['MRR']:>8.4f}{m['H1']:>8.4f}{m['H3']:>8.4f}{m['H10']:>8.4f}{m['MR']:>10,.2f}")
    print('-' * 104)
    for name in ('tail', 'head', 'both'):
        m = metrics(allr[name])
        print(f"{'MICRO ' + name:<51}{m['n']:>11,}{'':>10}"
              f"{m['MRR']:>8.4f}{m['H1']:>8.4f}{m['H3']:>8.4f}{m['H10']:>8.4f}{m['MR']:>10,.2f}")
    if macro:
        print(f"{'MACRO (mean over relations)':<51}{len(macro):>11,}{'':>10}"
              f"{np.mean([m['MRR'] for m in macro]):>8.4f}"
              f"{np.mean([m['H1'] for m in macro]):>8.4f}"
              f"{np.mean([m['H3'] for m in macro]):>8.4f}"
              f"{np.mean([m['H10'] for m in macro]):>8.4f}"
              f"{np.mean([m['MR'] for m in macro]):>10,.2f}")
    return {'micro': {k: metrics(allr[k]) for k in allr},
            'macro': {k: float(np.mean([m[k] for m in macro])) for k in
                      ('MRR', 'H1', 'H3', 'H10', 'MR')} if macro else {}}


def rank_file(a, m, r, side):
    return os.path.join(a.work, f'ranks_neg{a.num_neg}_{m}_{r}_{side}.npy')


def _relation_done(a, r, modes, n_test):
    for m in modes:
        for side in ('tail', 'head'):
            f = rank_file(a, m, r, side)
            if not os.path.exists(f):
                return False
            try:
                if len(np.load(f, mmap_mode='r')) != n_test:
                    return False
            except Exception:
                return False
    return True


# ------------------------------------------------------------------- worker
def worker(gpu, tasks, a, ret):
    try:
        _worker(gpu, tasks, a, ret)
    except BaseException:
        import traceback
        traceback.print_exc()
        ret.put({'__error__': f'gpu{gpu}: ' + traceback.format_exc()})


def _worker(gpu, tasks, a, ret):
    import torch
    torch.backends.cuda.matmul.allow_tf32 = a.tf32
    torch.backends.cudnn.allow_tf32 = a.tf32
    dev = f'cuda:{gpu}'
    torch.cuda.set_device(dev)

    tarr = np.load(os.path.join(a.work, 'type_code.npy'))
    num_ent = len(tarr)
    tsize = np.bincount(tarr[tarr >= 0].astype(np.int64))
    t_stage = time.time()
    ent_np = np.load(a.entity_npy)
    log(f"[gpu{gpu}] read entity table {ent_np.shape} in {time.time()-t_stage:.1f}s, staging")
    ent_t = torch.empty(ent_np.shape, dtype=torch.float32, device=dev)
    CH = 2_000_000
    for i in range(0, len(ent_np), CH):
        ent_t[i:i + CH] = torch.from_numpy(ent_np[i:i + CH]).to(dev)
    del ent_np
    rel_np = np.load(a.relation_npy)
    d = a.hidden_dim
    assert ent_t.shape[1] == d and rel_np.shape[1] == d * d

    pool_cache = {}
    out = {}
    for r, modes in tasks:
        t0 = time.time()
        allht = np.load(os.path.join(a.work, f'all_{r}.npy'))
        testht0 = np.load(os.path.join(a.work, f'test_{r}.npy'))
        if a.resume and _relation_done(a, r, modes, len(testht0)):
            ht = np.unique(tarr[allht[:, 0]]); tt = np.unique(tarr[allht[:, 1]])
            res = {'pool_tail': int(tsize[tt].sum()), 'pool_head': int(tsize[ht].sum())}
            for m in modes:
                out[(r, m)] = res
            log(f"[gpu{gpu}] rel {r:>3} already complete -- skipping")
            continue
        if a.sample and len(testht0) > a.sample:
            sel = np.random.default_rng(a.seed).choice(len(testht0), a.sample, replace=False)
            testht0 = testht0[np.sort(sel)]

        htypes = tuple(sorted(set(np.unique(tarr[allht[:, 0]]).tolist())))
        ttypes = tuple(sorted(set(np.unique(tarr[allht[:, 1]]).tolist())))
        pools = {}
        for key, tys in (('head', htypes), ('tail', ttypes)):
            if tys not in pool_cache:
                if len(pool_cache) > 2:
                    pool_cache.clear(); torch.cuda.empty_cache()
                ids = np.flatnonzero(np.isin(tarr, np.array(tys, dtype=np.int16)))
                pool_cache[tys] = torch.as_tensor(ids.astype(np.int64), device=dev)
            pools[key] = pool_cache[tys]

        known_ht = np.unique(allht[:, 0].astype(np.int64) * np.int64(num_ent)
                             + allht[:, 1].astype(np.int64))
        variants = {}
        for m in modes:
            if m == 'control':
                if a.control_type == 'pool':
                    ctrl, (n_first, n_left) = make_control_pool(
                        len(testht0), a.seed, r, known_ht, num_ent,
                        pools['head'].cpu().numpy(), pools['tail'].cpu().numpy())
                else:
                    ctrl, (n_first, n_left) = make_control_shuffle(
                        testht0, a.seed, r, known_ht, num_ent,
                        tail_pool_fn=lambda: pools['tail'].cpu().numpy())
                log(f"[gpu{gpu}] rel {r:>3} control({a.control_type}): {n_first:,} of "
                    f"{len(ctrl):,} first-draw triples were real, {n_left:,} still real after repair")
                variants[m] = ctrl
            else:
                variants[m] = testht0
        del known_ht

        Mr = torch.from_numpy(rel_np[r].reshape(d, d).copy()).to(dev)
        res = {'pool_tail': int(pools['tail'].numel()), 'pool_head': int(pools['head'].numel())}
        for side in ('tail', 'head'):
            if side == 'tail':
                keys, vals, Mr_eff, pool = allht[:, 0], allht[:, 1], Mr, pools['tail']
            else:
                keys, vals, Mr_eff, pool = allht[:, 1], allht[:, 0], Mr.T.contiguous(), pools['head']
            # sorted unique codes of all known-true (query, target) pairs
            fcodes = np.unique(keys.astype(np.int64) * np.int64(num_ent) + vals.astype(np.int64))
            fcodes_t = torch.as_tensor(fcodes, device=dev)
            del fcodes
            for m, tht in variants.items():
                qe = tht[:, 0] if side == 'tail' else tht[:, 1]
                te = tht[:, 1] if side == 'tail' else tht[:, 0]
                gen = torch.Generator(device=dev)
                gen.manual_seed(a.seed * 1000003 + r * 7 + (0 if side == 'tail' else 1)
                                + (0 if m == 'eval' else 500000))
                rk = rank_sampled(torch, dev, ent_t, Mr_eff, qe.astype(np.int64),
                                  te.astype(np.int64), fcodes_t, pool, num_ent,
                                  a.num_neg, not a.no_ties, a.chunk, gen)
                np.save(rank_file(a, m, r, side), rk.astype(np.float32))
            del fcodes_t
        for m in modes:
            out[(r, m)] = res
        log(f"[gpu{gpu}] rel {r:>3} n={len(testht0):>10,} "
            f"pool h/t={pools['head'].numel():>9,}/{pools['tail'].numel():<9,} "
            f"modes={','.join(modes)} {time.time()-t0:7.1f}s")
    ret.put(out)


# --------------------------------------------------------------------- main
def eval_main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data_path', required=True)
    p.add_argument('--train', default='EvoAge_121_12M_KG_train_90')
    p.add_argument('--valid', default='EvoAge_121_12M_KG_valid_10')
    p.add_argument('--test', default='EvoAge_1to1_KG_test_10_shared')
    p.add_argument('--typed_dict', default='entities_final_Ntype_updated.dict')
    p.add_argument('--relations', default='relation_final.dict')
    p.add_argument('--model_path', required=True)
    p.add_argument('--hidden_dim', type=int, default=64)
    p.add_argument('--work', required=True, help='scratch dir for the parsed cache')
    p.add_argument('--out', default=None, help='write metrics JSON here')
    p.add_argument('--mode', choices=['eval', 'control', 'both'], default='both')
    p.add_argument('--control_type', choices=['pool', 'shuffle'], default='pool',
                   help='pool: uniform draws from full type-compatible pools (all relations); '
                        'shuffle: degree-preserving within-relation shuffle')
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--gpu_weights', default=None, help='relative GPU throughput, e.g. "64,83"')
    p.add_argument('--num_neg', type=int, default=16,
                   help='sampled type-compatible negatives per test triple per side')
    p.add_argument('--chunk', type=int, default=200_000,
                   help='test triples processed per GPU batch (memory cap)')
    p.add_argument('--sample', type=int, default=0,
                   help='evaluate at most this many test triples per relation (0 = all)')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--tf32', action='store_true')
    p.add_argument('--no_ties', action='store_true', help='optimistic instead of average rank')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--no_pt', action='store_true')
    p.add_argument('--force_prepare', action='store_true')
    p.add_argument('--only_rel', default=None, help='comma-separated relations (debug)')
    a = p.parse_args()

    os.makedirs(a.work, exist_ok=True)
    import glob
    a.entity_npy = sorted(glob.glob(os.path.join(a.model_path, '*entity.npy')), key=len)[0]
    a.relation_npy = sorted(glob.glob(os.path.join(a.model_path, '*relation.npy')), key=len)[0]

    load_types(os.path.join(a.data_path, a.typed_dict), a.work)
    meta = prepare(a)

    names = {}
    for line in open(os.path.join(a.data_path, a.relations)):
        i, n = line.rstrip('\n').split('\t')[:2]
        names[int(i)] = n

    rels = sorted(int(r) for r, v in meta['rel'].items() if 'test' in v)
    if a.only_rel:
        keep = {int(x) for x in a.only_rel.split(',')}
        rels = [r for r in rels if r in keep]
    modes = ['eval', 'control'] if a.mode == 'both' else [a.mode]

    # cost ~ number of test triples (work is linear in n, independent of pool size)
    cost = {}
    for r in rels:
        n = meta['rel'][str(r)]['test']
        cost[r] = min(n, a.sample) if a.sample else n
    tasks = sorted([(r, modes) for r in rels], key=lambda x: -cost[x[0]])
    log(f"planned {len(tasks)} tasks over {len(rels)} relations; "
        f"{sum(cost[r] for r in rels)*len(modes)*2:,} sampled-rank problems "
        f"x {a.num_neg} negatives; control_type={a.control_type}")

    import torch.multiprocessing as mp
    ctx = mp.get_context('spawn')
    gpus = [int(g) for g in a.gpus.split(',')]
    w = [float(x) for x in a.gpu_weights.split(',')] if a.gpu_weights else [1.0] * len(gpus)
    assert len(w) == len(gpus), "--gpu_weights must match --gpus"
    load = [0.0] * len(gpus)
    shards = [[] for _ in gpus]
    for t in tasks:
        i = min(range(len(gpus)), key=lambda j: load[j])
        shards[i].append(t); load[i] += cost[t[0]] / w[i]
    for g, sh, l in zip(gpus, shards, load):
        log(f"  gpu{g}: {len(sh)} relations, {l:,.0f} weighted triples")
    ret = ctx.Queue()
    procs = [ctx.Process(target=worker, args=(g, s, a, ret)) for g, s in zip(gpus, shards)]
    t0 = time.time()
    for pr in procs:
        pr.start()
    got = [ret.get() for _ in procs]
    for pr in procs:
        pr.join()
    errs = [g['__error__'] for g in got if isinstance(g, dict) and '__error__' in g]
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        sys.exit(f"[typed_eval] {len(errs)} worker(s) failed; "
                 f"completed relations are on disk -- rerun with --resume")
    log(f"ranking finished in {time.time()-t0:.1f}s")

    ctl_title = (f'RANDOMIZED CONTROL (full-pool uniform head/tail, verified not real; '
                 f'{a.num_neg} sampled negatives)' if a.control_type == 'pool' else
                 f'RANDOMIZED CONTROL (within-relation shuffle, verified not real; '
                 f'{a.num_neg} sampled negatives)')
    results = {}
    for mode in modes:
        per_rel = {}
        for r in rels:
            e = {}
            for side in ('tail', 'head'):
                f = rank_file(a, mode, r, side)
                if os.path.exists(f):
                    e[side] = np.load(f)
            if e:
                for g in got:
                    if isinstance(g, dict) and g.get((r, mode)):
                        e['pool'] = g[(r, mode)]['pool_tail']
                per_rel[r] = e
        if per_rel:
            results[mode] = show(
                f'EVAL   ({a.num_neg} sampled type-compatible negatives, filtered)' if mode == 'eval'
                else ctl_title, per_rel, names)
    if a.out:
        json.dump(results, open(a.out, 'w'), indent=2)
        log(f"wrote {a.out}")


def _rand_mrr(k):
    n = k + 1
    return sum(1.0 / i for i in range(1, n + 1)) / n


def _rand_h(k, h):
    return min(h, k + 1) / (k + 1)


def sweep_main():
    """Run every requested K and aggregate all outputs in one R1 directory."""
    here = os.path.dirname(os.path.abspath(__file__))
    base = os.path.dirname(here)
    p = argparse.ArgumentParser(
        description='Standalone type-constrained RESCAL evaluation sweep')
    p.add_argument('--data_path', default=os.path.join(base, 'StructuredSimKG'))
    p.add_argument('--model_path', default=os.path.join(
        base, 'training', 'model_output', 'Rescal', 'RESCAL_simulated_0'))
    p.add_argument('--output', default=os.path.join(here, 'R1'))
    p.add_argument('--python', dest='eval_python', default=None,
                   help='Python containing PyTorch; auto-detects dglke_env')
    p.add_argument('--ks', default='16,32,64,128,256,512,1024')
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--gpu_weights', default=None)
    p.add_argument('--control_type', choices=['shuffle', 'pool'], default='shuffle')
    p.add_argument('--base_chunk', type=int, default=200_000)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--tf32', action='store_true')
    p.add_argument('--force_prepare', action='store_true')
    p.add_argument('--skip_run', action='store_true')
    a = p.parse_args()

    data_path = os.path.abspath(a.data_path)
    model_path = os.path.abspath(a.model_path)
    output = os.path.abspath(a.output)
    os.makedirs(output, exist_ok=True)
    if not os.path.isdir(data_path):
        p.error(f'dataset directory does not exist: {data_path}')
    if not os.path.isdir(model_path):
        p.error(f'model directory does not exist: {model_path}')

    ks = [int(x) for x in a.ks.split(',') if x.strip()]
    if not ks or any(k <= 0 for k in ks):
        p.error('--ks must contain positive comma-separated integers')

    eval_python = a.eval_python or sys.executable
    if not os.path.isfile(eval_python):
        p.error(f'evaluation Python does not exist: {eval_python}')

    print('K values:', ', '.join(map(str, ks)), flush=True)
    print('Data:', data_path, flush=True)
    print('Model:', model_path, flush=True)
    print('Evaluation Python:', eval_python, flush=True)
    print('All outputs:', output, flush=True)

    if not a.skip_run:
        for k in ks:
            chunk = max(1_000, a.base_chunk * 16 // k)
            result_file = os.path.join(output, f'results_neg{k}.json')
            cmd = [
                eval_python, os.path.abspath(__file__), '--internal-eval',
                '--data_path', data_path,
                '--model_path', model_path,
                '--work', output,
                '--out', result_file,
                '--train', 'SimKG_train',
                '--valid', 'SimKG_valid',
                '--test', 'SimKG_test',
                '--typed_dict', 'entities_typed.dict',
                '--relations', 'relations.dict',
                '--num_neg', str(k),
                '--chunk', str(chunk),
                '--control_type', a.control_type,
                '--gpus', a.gpus,
                '--seed', str(a.seed),
                '--resume',
            ]
            if a.gpu_weights:
                cmd.extend(['--gpu_weights', a.gpu_weights])
            if a.tf32:
                cmd.append('--tf32')
            if a.force_prepare and k == ks[0]:
                cmd.append('--force_prepare')
            print(f'\n===== K={k}, chunk={chunk} =====', flush=True)
            subprocess.run(cmd, check=True, cwd=here)

    rows = []
    for k in ks:
        path = os.path.join(output, f'results_neg{k}.json')
        if not os.path.exists(path):
            continue
        with open(path) as fh:
            result = json.load(fh)
        row = {'K': k, 'rand_MRR': _rand_mrr(k),
               'rand_H1': _rand_h(k, 1), 'rand_H10': _rand_h(k, 10)}
        for mode in ('eval', 'control'):
            if mode not in result:
                continue
            micro = result[mode]['micro']['both']
            for metric in ('MRR', 'H1', 'H3', 'H10', 'MR'):
                row[f'{mode}_micro_{metric}'] = micro[metric]
            for metric in ('MRR', 'H1', 'H3', 'H10', 'MR'):
                row[f'{mode}_macro_{metric}'] = result[mode]['macro'][metric]
        if 'control_micro_MRR' in row:
            row['gap_micro_MRR'] = row['eval_micro_MRR'] - row['control_micro_MRR']
            row['gap_macro_MRR'] = row['eval_macro_MRR'] - row['control_macro_MRR']
        rows.append(row)

    if not rows:
        raise SystemExit('No result JSON files were produced')
    fields = sorted({key for row in rows for key in row},
                    key=lambda key: (key != 'K', key))
    summary = os.path.join(output, 'sweep_summary.csv')
    with open(summary, 'w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print('\n' + '=' * 104)
    print(f"{'K':>6} {'eval MRR':>12} {'control MRR':>14} {'gap':>12} "
          f"{'random MRR':>12} {'eval H@10':>12} {'ctrl H@10':>12}")
    for row in rows:
        print(f"{row['K']:>6} {row.get('eval_micro_MRR', float('nan')):>12.5f} "
              f"{row.get('control_micro_MRR', float('nan')):>14.5f} "
              f"{row.get('gap_micro_MRR', float('nan')):>12.5f} "
              f"{row['rand_MRR']:>12.5f} "
              f"{row.get('eval_micro_H10', float('nan')):>12.5f} "
              f"{row.get('control_micro_H10', float('nan')):>12.5f}")
    print('=' * 104)
    print('Summary:', summary)

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        x = [row['K'] for row in rows]
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        for ax, metric, title in zip(
                axes, ('MRR', 'H10', 'H1'), ('MRR', 'Hits@10', 'Hits@1')):
            ax.plot(x, [row[f'eval_micro_{metric}'] for row in rows],
                    'o-', label='True test triples')
            ax.plot(x, [row[f'control_micro_{metric}'] for row in rows],
                    's--', label='Shuffled control')
            if metric == 'MRR':
                ax.plot(x, [row['rand_MRR'] for row in rows], 'k:',
                        label='Random-ranking baseline')
            elif metric == 'H10':
                ax.plot(x, [row['rand_H10'] for row in rows], 'k:',
                        label='Random-ranking baseline')
            elif metric == 'H1':
                ax.plot(x, [row['rand_H1'] for row in rows], 'k:',
                        label='Random-ranking baseline')
            ax.set_xscale('log', base=2)
            ax.set_xticks(x)
            ax.set_xticklabels(x)
            ax.set_xlabel('sampled negatives K')
            ax.set_title(title)
            ax.grid(alpha=.3)
            ax.legend()
        fig.tight_layout()
        plot = os.path.join(output, 'sweep_plot.png')
        fig.savefig(plot, dpi=200)
        plt.close(fig)
        print('Plot:', plot)
    except Exception as exc:
        print(f'Plot skipped: {exc}')


def main():
    if '--internal-eval' in sys.argv:
        sys.argv.remove('--internal-eval')
        eval_main()
    else:
        sweep_main()


if __name__ == '__main__':
    main()
