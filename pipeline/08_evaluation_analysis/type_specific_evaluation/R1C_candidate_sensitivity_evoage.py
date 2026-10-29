#!/usr/bin/env python3
"""
C_sampled_k_analysis.py -- sampled type-compatible candidate sensitivity study (K sweep)
for a DGL-KE RESCAL model, with type-preserving randomized controls. No plotting.

For every test triple and each side (tail / head):
  * candidate pool = all entities whose type occurs on that side of the relation
  * SAMPLED mode (2K <= pool size): K DISTINCT candidates drawn uniformly at random
    from the pool, excluding (a) every known-true answer for the same (h,r) / (r,t)
    in train+valid+test and (b) the target itself.
  * FULL-POOL mode (2K > pool size): all pool entities except known-true answers and
    the target are used (so the candidate count = pool size - positives).
  * rank = 1 + #(cand score > target) + 0.5 * #(cand score == target)
Controls ('control'): heads and tails permuted WITHIN each relation (relation-specific
entity types preserved by construction), repaired so that no fake triple is a known
triple in train+valid+test, then ranked with the identical protocol.
Same test subset (--sample, --seed) for every K and for eval/control.

RESCAL: s(h, r, t) = h^T M_r t,  M_r = relation_emb[r].reshape(d, d)

Outputs
  <rank_dir>/ranks_neg{K}_{eval|control}_{rel}_{tail|head}.npy   float32 ranks
  <rank_dir>/cand_{rel}.json                                     mean candidate counts
  <out_dir>/C_summary_overall.csv, C_summary_per_relation.csv, C_results.json
  <out_dir>/run_metadata.json  (versions, args, sampling description)

See README.md for a portable command-line example.

"""
import argparse, csv, glob, itertools, json, os, platform, sys, time
import numpy as np

UNSET = -1
SAMPLING_TEXT = (
    "Candidates are drawn uniformly at random, without replacement, from the "
    "type-compatible pool of the relation side (all entities whose type occurs as head "
    "or tail of that relation), excluding every known-true answer for the query in "
    "train+valid+test and the target. If 2K exceeds the pool size, all non-positive "
    "pool entities are used instead (candidate count = pool size - positives). "
    "Average rank is used for ties.")


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ============================================================ input / cache
def _read_txt(path):
    import pandas as pd
    df = pd.read_csv(path, sep='\t', header=None, usecols=[0, 1, 2], names=['h', 'r', 't'],
                     dtype=np.int64, engine='c', quoting=3)
    return np.ascontiguousarray(df.values.astype(np.int32))


def load_split(data_path, stem, cache_dir, allow_pt=True):
    cache = os.path.join(cache_dir, stem + '.npy')
    if os.path.exists(cache):
        return np.asarray(np.load(cache, mmap_mode='r'))
    txt, pt = os.path.join(data_path, stem + '.txt'), os.path.join(data_path, stem + '.pt')
    x = None
    if allow_pt and os.path.exists(pt):
        import torch
        head = None
        if os.path.exists(txt):
            with open(txt) as fh:
                head = np.array([[int(v) for v in l.split('\t')[:3]]
                                 for l in itertools.islice(fh, 1000)], dtype=np.int64)
        y = torch.load(pt, map_location='cpu')
        y = y.numpy() if hasattr(y, 'numpy') else np.asarray(y)
        if head is None or (len(y) >= 1000 and np.array_equal(y[:1000].astype(np.int64), head)):
            x = np.ascontiguousarray(y.astype(np.int32))
        del y
    if x is None:
        x = _read_txt(txt)
    log(f"  {stem}: {len(x):,} triples parsed")
    np.save(cache, x)
    return x


def load_types(path, cache_dir):
    cc, cn = os.path.join(cache_dir, 'type_code.npy'), os.path.join(cache_dir, 'type_names.txt')
    if os.path.exists(cc):
        return
    import pandas as pd
    df = pd.read_csv(path, sep='\t', header=None, usecols=[0, 2], names=['id', 'ty'],
                     dtype={0: np.int64, 2: 'category'}, engine='c', quoting=3)
    ids = df['id'].values
    arr = np.full(int(ids.max()) + 1, UNSET, dtype=np.int16)
    arr[ids] = df['ty'].cat.codes.values.astype(np.int16)
    np.save(cc, arr)
    open(cn, 'w').write('\n'.join(df['ty'].cat.categories))


def prepare(a):
    """Per relation: all_{r}.npy (train+valid+test (h,t) = filter set), test_{r}.npy."""
    done = os.path.join(a.work, 'PREPARED')
    if os.path.exists(done) and not a.force_prepare:
        return json.load(open(done))
    log("prepare: loading splits")
    sp = {n: load_split(a.data_path, n, a.work, not a.no_pt) for n in (a.train, a.valid, a.test)}
    test = sp[a.test]
    allX = np.concatenate([sp[n] for n in (a.train, a.valid, a.test)], axis=0)
    meta = {'num_test': int(len(test)), 'rel': {}}
    for tag, X in (('all', allX), ('test', test)):
        R = X[:, 1].astype(np.int32)
        order = np.argsort(R, kind='stable')
        bnd = np.searchsorted(R[order], np.arange(int(R.max()) + 2))
        for r in range(len(bnd) - 1):
            s, e = bnd[r], bnd[r + 1]
            if e > s:
                np.save(os.path.join(a.work, f'{tag}_{r}.npy'),
                        np.ascontiguousarray(X[order[s:e]][:, [0, 2]]))
                meta['rel'].setdefault(str(r), {})[tag] = int(e - s)
    json.dump(meta, open(done, 'w'))
    return meta


# ============================================================ control
def derangement(n, rng):
    if n == 1:
        return np.zeros(1, dtype=np.int64)
    p = rng.permutation(n)
    fx = np.flatnonzero(p == np.arange(n))
    while fx.size:
        if fx.size == 1:
            i = int(fx[0]); j = int(rng.integers(n - 1)); j += (j >= i)
            p[i], p[j] = p[j], p[i]
        else:
            p[fx] = p[np.roll(fx, 1)]
        fx = np.flatnonzero(p == np.arange(n))
    return p


def is_known(known, num_ent, x):
    code = x[:, 0].astype(np.int64) * np.int64(num_ent) + x[:, 1].astype(np.int64)
    i = np.minimum(np.searchsorted(known, code), len(known) - 1)
    return known[i] == code


def make_shuffle(ht, seed, r, known, num_ent, tail_pool, rounds=100):
    """Within-relation head/tail permutation (types preserved), repaired against known
    triples: redraw tails from the relation's own test tails, then from the full tail pool."""
    rng = np.random.default_rng(seed * 100003 + r + 7)
    n = len(ht)
    if n < 2:
        return ht.copy(), (0, 0)
    out = np.empty_like(ht)
    out[:, 0] = ht[derangement(n, rng), 0]
    out[:, 1] = ht[derangement(n, rng), 1]
    bad = np.flatnonzero(is_known(known, num_ent, out)); first = bad.size
    for src in (ht[:, 1], tail_pool):
        for _ in range(rounds):
            if not bad.size:
                break
            out[bad, 1] = src[rng.integers(len(src), size=bad.size)]
            bad = bad[is_known(known, num_ent, out[bad])]
    return out, (first, int(bad.size))


# ============================================================ ranking
def rank_candidates(torch, dev, ent_t, Mr_eff, qent, tent, fcodes_t, pool_t, num_ent,
                    K, chunk, gen, tile, max_rounds=6):
    """Ranks of each target among filtered type-compatible candidates.
    Returns (ranks float64, mean candidate count, used_full_pool)."""
    n, C, nf, d = len(qent), pool_t.numel(), fcodes_t.numel(), ent_t.shape[1]
    full = 2 * K > C
    ranks = np.empty(n, dtype=np.float64)
    ncand_sum = 0.0
    if full:
        poolemb = ent_t.index_select(0, pool_t)
        chunk = max(1, min(chunk, tile // max(C, 1)))
    S = 3 * K

    for s in range(0, n, chunk):
        q = torch.as_tensor(qent[s:s + chunk], dtype=torch.long, device=dev)
        t = torch.as_tensor(tent[s:s + chunk], dtype=torch.long, device=dev)
        B = q.numel()
        proj = ent_t.index_select(0, q) @ Mr_eff
        pos = (proj * ent_t.index_select(0, t)).sum(1)
        qbase = q * num_ent

        if full:
            code = qbase[:, None] + pool_t[None, :]
            idx = torch.searchsorted(fcodes_t, code).clamp_(max=nf - 1)
            valid = (fcodes_t[idx] != code) & (pool_t[None, :] != t[:, None])
            sc = proj @ poolemb.T
        else:
            buf = torch.empty(B, 0, dtype=torch.long, device=dev)
            for _ in range(max_rounds):
                new = pool_t[torch.randint(C, (B, S), device=dev, generator=gen)]
                sb, _ = torch.sort(torch.cat([buf, new], 1), dim=1)
                dup = torch.zeros_like(sb, dtype=torch.bool)
                dup[:, 1:] = sb[:, 1:] == sb[:, :-1]
                code = qbase[:, None] + sb
                idx = torch.searchsorted(fcodes_t, code).clamp_(max=nf - 1)
                valid = ~dup & (fcodes_t[idx] != code) & (sb != t[:, None])
                if bool((valid.sum(1) >= K).all()):
                    break
                buf = sb
            # pick K of the valid candidates uniformly at random
            rk_ = torch.rand(sb.shape, device=dev, generator=gen)
            rk_[~valid] = 2.0
            sel = rk_.topk(K, dim=1, largest=False).indices
            cand = sb.gather(1, sel)
            valid = valid.gather(1, sel)
            emb = ent_t.index_select(0, cand.reshape(-1)).reshape(B, K, d)
            sc = torch.einsum('bd,bkd->bk', proj, emb)
            del emb, cand, sb, rk_

        gt = ((sc > pos[:, None]) & valid).sum(1).double()
        eq = ((sc == pos[:, None]) & valid).sum(1).double()
        ranks[s:s + B] = (1.0 + gt + 0.5 * eq).cpu().numpy()
        ncand_sum += float(valid.sum().item())
        del sc, valid, proj
    return ranks, ncand_sum / max(n, 1), full


# ============================================================ worker
def rpath(a, K, m, r, side):
    return os.path.join(a.rank_dir, f'ranks_neg{K}_{m}_{r}_{side}.npy')


def file_ok(f, n):
    try:
        return os.path.exists(f) and len(np.load(f, mmap_mode='r')) == n
    except Exception:
        return False


def worker(gpu, tasks, a, ret):
    try:
        _worker(gpu, tasks, a); ret.put({'ok': gpu})
    except BaseException:
        import traceback; traceback.print_exc()
        ret.put({'__error__': f'gpu{gpu}: ' + traceback.format_exc()})


def _worker(gpu, tasks, a):
    import torch
    torch.backends.cuda.matmul.allow_tf32 = a.tf32
    dev = f'cuda:{gpu}'; torch.cuda.set_device(dev)
    Ks = [int(k) for k in a.ks.split(',')]
    modes = a.modes.split(',')
    tarr = np.load(os.path.join(a.work, 'type_code.npy')); num_ent = len(tarr)

    e = np.load(a.entity_npy)
    ent_t = torch.empty(e.shape, dtype=torch.float32, device=dev)
    for i in range(0, len(e), 2_000_000):
        ent_t[i:i + 2_000_000] = torch.from_numpy(e[i:i + 2_000_000]).to(dev)
    del e
    rel_np = np.load(a.relation_npy); d = a.hidden_dim
    assert ent_t.shape[1] == d and rel_np.shape[1] == d * d, "hidden_dim mismatch"
    log(f"[gpu{gpu}] model loaded")

    pool_cache = {}
    for r in tasks:
        t0 = time.time()
        allht = np.load(os.path.join(a.work, f'all_{r}.npy'))
        test = np.load(os.path.join(a.work, f'test_{r}.npy'))
        if a.sample and len(test) > a.sample:      # fixed subset: same for every K and mode
            test = test[np.sort(np.random.default_rng(a.seed).choice(len(test), a.sample, replace=False))]
        n = len(test)
        cj = os.path.join(a.rank_dir, f'cand_{r}.json')
        info = json.load(open(cj)) if (a.resume and os.path.exists(cj)) else {'cand': {}}
        if a.resume and os.path.exists(cj) and all(
                file_ok(rpath(a, K, m, r, s), n) for K in Ks for m in modes for s in ('tail', 'head')):
            log(f"[gpu{gpu}] rel {r:>3} complete -- skipping"); continue

        htypes = tuple(np.unique(tarr[allht[:, 0]]).tolist())
        ttypes = tuple(np.unique(tarr[allht[:, 1]]).tolist())
        pools = {}
        for key, tys in (('head', htypes), ('tail', ttypes)):
            if tys not in pool_cache:
                if len(pool_cache) > 2:
                    pool_cache.clear(); torch.cuda.empty_cache()
                ids = np.flatnonzero(np.isin(tarr, np.array(tys, dtype=np.int16)))
                pool_cache[tys] = torch.as_tensor(ids.astype(np.int64), device=dev)
            pools[key] = pool_cache[tys]

        variants = {'eval': test}
        if 'control' in modes:
            known = np.unique(allht[:, 0].astype(np.int64) * np.int64(num_ent) + allht[:, 1].astype(np.int64))
            ctrl, (first, left) = make_shuffle(test, a.seed, r, known, num_ent, pools['tail'].cpu().numpy())
            variants['control'] = ctrl
            info['control_fakes_real_first'] = int(first); info['control_fakes_real_after_repair'] = int(left)
            log(f"[gpu{gpu}] rel {r:>3} control: {first:,} of {n:,} shuffled triples were real, "
                f"{left:,} remain after repair")
            del known
        info.update({'n_test': int(n), 'pool_head': int(pools['head'].numel()),
                     'pool_tail': int(pools['tail'].numel())})

        Mr = torch.from_numpy(rel_np[r].reshape(d, d).copy()).to(dev)
        for side in ('tail', 'head'):
            if side == 'tail':
                keys, vals, Meff, pool = allht[:, 0], allht[:, 1], Mr, pools['tail']
            else:
                keys, vals, Meff, pool = allht[:, 1], allht[:, 0], Mr.T.contiguous(), pools['head']
            fcodes_t = torch.as_tensor(
                np.unique(keys.astype(np.int64) * np.int64(num_ent) + vals.astype(np.int64)), device=dev)
            C = pool.numel()
            for K in Ks:
                chunk = int(max(64, min(a.chunk, a.gather_budget // (min(K, C) * d))))
                for m in modes:
                    f = rpath(a, K, m, r, side)
                    if a.resume and file_ok(f, n):
                        continue
                    v = variants[m]
                    qe = (v[:, 0] if side == 'tail' else v[:, 1]).astype(np.int64)
                    te = (v[:, 1] if side == 'tail' else v[:, 0]).astype(np.int64)
                    gen = torch.Generator(device=dev)
                    gen.manual_seed(a.seed * 1000003 + r * 131 + K * 7 + (0 if side == 'tail' else 1)
                                    + (0 if m == 'eval' else 500000))
                    rk, mc, full = rank_candidates(torch, dev, ent_t, Meff, qe, te, fcodes_t, pool,
                                                   num_ent, K, chunk, gen, a.tile)
                    np.save(f, rk.astype(np.float32))
                    info['cand'][f'{K}|{m}|{side}'] = {'mean_candidates': mc, 'full_pool': bool(full)}
            del fcodes_t
        json.dump(info, open(cj, 'w'))
        log(f"[gpu{gpu}] rel {r:>3} n={n:>10,} pool h/t={pools['head'].numel():,}/{pools['tail'].numel():,} "
            f"{time.time()-t0:7.1f}s")


# ============================================================ report
KS_H = (1, 3, 10)


def rand_mrr(N):
    """Expected reciprocal rank of a uniformly random position among N candidates (N = cand + 1)."""
    N = float(max(N, 1.0))
    return 1.0 if N <= 1 else (np.log(N) + 0.5772156649 + 1 / (2 * N) - 1 / (12 * N * N)) / N


def sums(rk):
    rk = np.asarray(rk, dtype=np.float64)
    return np.array([len(rk), (1 / rk).sum(), rk.sum()] + [(rk <= k).sum() for k in KS_H])


def report(a, names, rels):
    os.makedirs(a.out_dir, exist_ok=True)
    Ks = [int(k) for k in a.ks.split(',')]
    modes = a.modes.split(',')
    per_rel, overall = [], []
    for K in Ks:
        for m in modes:
            tot = {'tail': np.zeros(6), 'head': np.zeros(6)}
            rnd, cand, nrow = 0.0, 0.0, 0
            rel_mrr = []
            for r in rels:
                cj = os.path.join(a.rank_dir, f'cand_{r}.json')
                if not os.path.exists(cj):
                    continue
                info = json.load(open(cj))
                per, rr_sum, c_sum, n_all = np.zeros(6), 0.0, 0.0, 0
                for side in ('tail', 'head'):
                    f = rpath(a, K, m, r, side)
                    ci = info['cand'].get(f'{K}|{m}|{side}')
                    if not os.path.exists(f) or ci is None:
                        continue
                    st = sums(np.load(f))
                    tot[side] += st; per += st
                    rr_sum += rand_mrr(ci['mean_candidates'] + 1) * st[0]
                    c_sum += ci['mean_candidates'] * st[0]; n_all += st[0]
                if not n_all:
                    continue
                mrr = per[1] / per[0]
                per_rel.append({'rel': r, 'relation': names.get(r, '?'), 'K': K, 'mode': m,
                                'n_test_triples': int(per[0] // 2), 'MRR': mrr,
                                'H@1': per[3] / per[0], 'H@3': per[4] / per[0], 'H@10': per[5] / per[0],
                                'MR': per[2] / per[0], 'mean_candidates': c_sum / n_all,
                                'random_MRR': rr_sum / n_all, 'enrichment_MRR': mrr / (rr_sum / n_all)})
                rel_mrr.append(mrr); rnd += rr_sum; cand += c_sum; nrow += n_all
            if not nrow:
                continue
            both = tot['tail'] + tot['head']
            row = {'K': K, 'mode': m, 'n_rows_both_sides': int(both[0]),
                   'micro_MRR': both[1] / both[0], 'micro_H@1': both[3] / both[0],
                   'micro_H@3': both[4] / both[0], 'micro_H@10': both[5] / both[0],
                   'micro_MR': both[2] / both[0],
                   'micro_tail_MRR': tot['tail'][1] / max(tot['tail'][0], 1),
                   'micro_head_MRR': tot['head'][1] / max(tot['head'][0], 1),
                   'macro_MRR': float(np.mean(rel_mrr)), 'median_MRR': float(np.median(rel_mrr)),
                   'micro_random_MRR': rnd / nrow, 'micro_enrichment': (both[1] / both[0]) / (rnd / nrow),
                   'micro_mean_candidates': cand / nrow, 'n_relations': len(rel_mrr)}
            overall.append(row)

    def write(p, rs):
        with open(p, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rs[0])); w.writeheader(); w.writerows(rs)
    if not overall:
        sys.exit("no rank files found -- nothing to report")
    write(os.path.join(a.out_dir, 'C_summary_overall.csv'), overall)
    write(os.path.join(a.out_dir, 'C_summary_per_relation.csv'), per_rel)
    json.dump({'overall': overall, 'per_relation': per_rel},
              open(os.path.join(a.out_dir, 'C_results.json'), 'w'), indent=2)
    print('\n' + '=' * 112 + '\nOVERALL (micro over test triples, both sides; macro over relations)\n' + '=' * 112)
    print(f"{'K':>6} {'mode':<8}{'micro MRR':>10}{'H@1':>8}{'H@10':>8}{'macro MRR':>11}{'median':>9}"
          f"{'rand MRR':>10}{'enrich':>8}{'cands':>10}")
    for r_ in overall:
        print(f"{r_['K']:>6} {r_['mode']:<8}{r_['micro_MRR']:>10.4f}{r_['micro_H@1']:>8.4f}{r_['micro_H@10']:>8.4f}"
              f"{r_['macro_MRR']:>11.4f}{r_['median_MRR']:>9.4f}{r_['micro_random_MRR']:>10.4f}"
              f"{r_['micro_enrichment']:>7.1f}x{r_['micro_mean_candidates']:>10.0f}")
    log(f"wrote tables to {a.out_dir}")


def write_metadata(a):
    meta = {'args': vars(a), 'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'sampling_method': SAMPLING_TEXT,
            'python': sys.version.split()[0], 'platform': platform.platform(), 'numpy': np.__version__}
    try:
        import torch
        meta.update({'torch': torch.__version__, 'cuda': torch.version.cuda,
                     'gpus': [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]})
    except Exception:
        pass
    os.makedirs(a.out_dir, exist_ok=True)
    json.dump(meta, open(os.path.join(a.out_dir, 'run_metadata.json'), 'w'), indent=2, default=str)


# ============================================================ main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data_path', required=True)
    p.add_argument('--model_path', required=True)
    p.add_argument('--work', required=True, help='cache dir (all_*.npy, test_*.npy, type_code.npy, PREPARED)')
    p.add_argument('--rank_dir', default=None, help='default <out_dir>/ranks')
    p.add_argument('--out_dir', default=None, help='default <work>/results')
    p.add_argument('--train', default='EvoAge_121_12M_KG_train_90')
    p.add_argument('--valid', default='EvoAge_121_12M_KG_valid_10')
    p.add_argument('--test', default='EvoAge_1to1_KG_test_10_shared')
    p.add_argument('--typed_dict', default='entities_final_Ntype_updated.dict')
    p.add_argument('--relations', default='relation_final.dict')
    p.add_argument('--hidden_dim', type=int, default=64)
    p.add_argument('--ks', default='16,32,64,128,256,512,1024')
    p.add_argument('--modes', default='eval,control', help='eval and/or control')
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--sample', type=int, default=0, help='max test triples per relation (0 = all); fixed subset')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--chunk', type=int, default=200_000, help='max queries per GPU batch')
    p.add_argument('--gather_budget', type=int, default=200_000_000, help='max elements in a (B,K,d) gather')
    p.add_argument('--tile', type=int, default=1 << 26)
    p.add_argument('--tf32', action='store_true')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--no_pt', action='store_true')
    p.add_argument('--force_prepare', action='store_true')
    p.add_argument('--only_rel', default=None)
    p.add_argument('--report_only', action='store_true')
    a = p.parse_args()

    a.out_dir = a.out_dir or os.path.join(a.work, 'results')
    a.rank_dir = a.rank_dir or os.path.join(a.out_dir, 'ranks')
    for d in (a.work, a.rank_dir, a.out_dir):
        os.makedirs(d, exist_ok=True)
    a.entity_npy = sorted(glob.glob(os.path.join(a.model_path, '*entity.npy')), key=len)[0]
    a.relation_npy = sorted(glob.glob(os.path.join(a.model_path, '*relation.npy')), key=len)[0]

    load_types(os.path.join(a.data_path, a.typed_dict), a.work)
    meta = prepare(a)
    names = {}
    for l in open(os.path.join(a.data_path, a.relations)):
        i, n = l.rstrip('\n').split('\t')[:2]; names[int(i)] = n
    rels = sorted(int(r) for r, v in meta['rel'].items() if 'test' in v)
    if a.only_rel:
        keep = {int(x) for x in a.only_rel.split(',')}; rels = [r for r in rels if r in keep]
    write_metadata(a)

    if not a.report_only:
        cost = {r: min(meta['rel'][str(r)]['test'], a.sample) if a.sample else meta['rel'][str(r)]['test']
                for r in rels}
        gpus = [int(g) for g in a.gpus.split(',')]
        load, shards = [0.0] * len(gpus), [[] for _ in gpus]
        for r in sorted(rels, key=lambda r: -cost[r]):
            i = min(range(len(gpus)), key=lambda j: load[j]); shards[i].append(r); load[i] += cost[r]
        log(f"{len(rels)} relations, K = {a.ks}, modes = {a.modes}, sample = {a.sample or 'all'}")
        import torch.multiprocessing as mp
        ctx = mp.get_context('spawn'); ret = ctx.Queue()
        procs = [ctx.Process(target=worker, args=(g, s, a, ret)) for g, s in zip(gpus, shards)]
        t0 = time.time()
        for pr in procs: pr.start()
        got = [ret.get() for _ in procs]
        for pr in procs: pr.join()
        errs = [g['__error__'] for g in got if '__error__' in g]
        if errs:
            for e in errs: print(e, file=sys.stderr)
            sys.exit("worker failed; finished work is saved -- rerun with --resume")
        log(f"ranking finished in {time.time()-t0:.1f}s")
    report(a, names, rels)


if __name__ == '__main__':
    main()
