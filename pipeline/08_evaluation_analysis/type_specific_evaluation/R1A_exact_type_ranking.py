#!/usr/bin/env python3
"""
A_type_compatible_ranking.py -- Part A: exact, FILTERED, TYPE-COMPATIBLE full ranking
for a DGL-KE RESCAL model, with overall and per-relation reports.

For every test triple (h, r, t) and each side:
  tail prediction: rank t among ALL entities whose type occurs as a tail of r
  head prediction: rank h among ALL entities whose type occurs as a head of r
  Filtered: every other known-true answer for the same (h, r) / (r, t) in
  train+valid+test is removed from the candidates; the target itself stays.
  Ties get the average rank. RESCAL score: s(h,r,t) = h^T M_r t.

Method notes (exactness is preserved):
  * queries sharing (h, r) [or (r, t)] are scored once (deduplication)
  * ranks via a histogram of binary-searched candidate scores (O(C log K))
  * filtering by subtracting the known-true entities' counts, not by masking
  * fp32 with TF32 disabled; score ties compared with a small relative band

Outputs
  <rank_dir>/ranks_eval_{rel}_{tail|head}.npy   float32 rank per test triple
  <rank_dir>/pools_{rel}.json                   head/tail pool sizes
  <out_dir>/table1_overall.csv                  micro (tail/head/both) + macro
  <out_dir>/table2_per_relation.csv             one row per relation
  <out_dir>/results.json, run_metadata.json     everything + provenance

Example
  python R1A_exact_type_ranking.py --data_path DATA --model_path MODEL \
      --work WORK --rank_dir WORK/full_ranks_eval --out_dir WORK/full_report \
      --gpus 0,1 --resume 2>&1 | tee full_rank.log
  (add --report_only to rebuild the tables from existing rank files)
"""


import argparse, csv, glob, itertools, json, os, platform, sys, time
import numpy as np

UNSET = -1
KS = (1, 3, 10, 100, 1000)


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ============================================================ input / caching
def _read_txt_triples(path):
    import pandas as pd
    df = pd.read_csv(path, sep='\t', header=None, usecols=[0, 1, 2], names=['h', 'r', 't'],
                     dtype=np.int64, engine='c', quoting=3)
    return np.ascontiguousarray(df.values.astype(np.int32))


def load_split(data_path, stem, cache_dir, allow_pt=True):
    """(n,3) int32 array of a split; parse cached as <cache_dir>/<stem>.npy.
    Prefers the .pt tensor when its first 1000 rows agree with the .txt."""
    cache = os.path.join(cache_dir, stem + '.npy')
    if os.path.exists(cache):
        x = np.load(cache, mmap_mode='r')
        log(f"  {stem}: {len(x):,} triples (cached)")
        return np.asarray(x)
    txt, pt = os.path.join(data_path, stem + '.txt'), os.path.join(data_path, stem + '.pt')
    t0, x = time.time(), None
    if allow_pt and os.path.exists(pt):
        import torch
        head = None
        if os.path.exists(txt):
            with open(txt) as fh:
                head = np.array([[int(v) for v in l.split('\t')[:3]]
                                 for l in itertools.islice(fh, 1000)], dtype=np.int64)
        y = torch.load(pt, map_location='cpu')          # no weights_only: old torch
        y = y.numpy() if hasattr(y, 'numpy') else np.asarray(y)
        if head is None or (len(y) >= 1000 and np.array_equal(y[:1000].astype(np.int64), head)):
            x = np.ascontiguousarray(y.astype(np.int32))
            log(f"  {stem}: {len(x):,} triples from .pt in {time.time()-t0:.1f}s")
        else:
            log(f"  {stem}: .pt disagrees with .txt -> parsing text")
        del y
    if x is None:
        x = _read_txt_triples(txt)
        log(f"  {stem}: {len(x):,} triples from .txt in {time.time()-t0:.1f}s")
    np.save(cache, x)
    return x


def load_types(path, cache_dir):
    """entity id -> int16 type code (cached), plus type names."""
    cc, cn = os.path.join(cache_dir, 'type_code.npy'), os.path.join(cache_dir, 'type_names.txt')
    if os.path.exists(cc) and os.path.exists(cn):
        return np.load(cc), open(cn).read().split('\n')
    import pandas as pd
    t0 = time.time()
    df = pd.read_csv(path, sep='\t', header=None, usecols=[0, 2], names=['id', 'ty'],
                     dtype={0: np.int64, 2: 'category'}, engine='c', quoting=3)
    ids = df['id'].values
    names = list(df['ty'].cat.categories)
    arr = np.full(int(ids.max()) + 1, UNSET, dtype=np.int16)
    arr[ids] = df['ty'].cat.codes.values.astype(np.int16)
    np.save(cc, arr)
    open(cn, 'w').write('\n'.join(names))
    log(f"  types: {len(arr):,} entities, {len(names)} types in {time.time()-t0:.1f}s")
    return arr, names


def prepare(a):
    """One-off: per relation write all_{r}.npy (train+valid+test (h,t) = filter set)
    and test_{r}.npy. A PREPARED marker makes this a no-op on reruns."""
    done = os.path.join(a.work, 'PREPARED')
    if os.path.exists(done) and not a.force_prepare:
        log("prepare: reusing per-relation cache")
        return json.load(open(done))
    log("prepare: loading splits")
    splits = {n: load_split(a.data_path, n, a.work, not a.no_pt)
              for n in (a.train, a.valid, a.test)}
    test = splits[a.test]
    allX = np.concatenate([splits[n] for n in (a.train, a.valid, a.test)], axis=0)
    for n in list(splits):
        if n != a.test:
            del splits[n]
    meta = {'num_test': int(len(test)), 'rel': {}}
    for tag, X in (('all', allX), ('test', test)):
        t0 = time.time()
        R = X[:, 1].astype(np.int32)
        order = np.argsort(R, kind='stable')
        bnd = np.searchsorted(R[order], np.arange(int(R.max()) + 2))
        for r in range(len(bnd) - 1):
            s, e = bnd[r], bnd[r + 1]
            if e <= s:
                continue
            np.save(os.path.join(a.work, f'{tag}_{r}.npy'),
                    np.ascontiguousarray(X[order[s:e]][:, [0, 2]]))
            meta['rel'].setdefault(str(r), {})[tag] = int(e - s)
        log(f"  {tag}: {len(X):,} triples grouped in {time.time()-t0:.1f}s")
        del R, order
    del allX
    json.dump(meta, open(done, 'w'))
    return meta


# ================================================================== ranking
def _csr_from_pairs(keys, vals, nkeys):
    """CSR of DISTINCT (key, val) pairs. Dedup is required: filter counts are
    subtracted, so a pair listed twice would be removed twice."""
    code = np.unique(keys.astype(np.int64) * np.int64(nkeys) + vals.astype(np.int64))
    k, v = code // nkeys, (code % nkeys).astype(np.int64)
    indptr = np.zeros(nkeys + 1, dtype=np.int64)
    np.cumsum(np.bincount(k, minlength=nkeys), out=indptr[1:])
    return indptr, v


def _batches(sizes_a, sizes_b, budget_a, budget_b, max_b):
    """Group queries (descending cost) into padded batches with bounded waste."""
    order = np.argsort(-(np.maximum(sizes_a, sizes_b)), kind='stable')
    cur, ma, mb = [], 0, 0
    for q in order:
        na, nb = max(ma, sizes_a[q]), max(mb, sizes_b[q])
        if cur and ((len(cur) + 1) * na > budget_a or (len(cur) + 1) * nb > budget_b
                    or len(cur) + 1 > max_b):
            yield np.array(cur), ma, mb
            cur, ma, mb = [q], sizes_a[q], sizes_b[q]
        else:
            cur.append(q); ma, mb = na, nb
    if cur:
        yield np.array(cur), ma, mb


def rank_side(torch, dev, ent_t, Mr_eff, qent, tent, filt_indptr, filt_vals,
              pool_t, tile, ties, eps=1e-6, cand_rows=4_000_000):
    """Exact filtered ranks of every target within its query's candidate pool.
    qent/tent: query/target entity per test triple; pool_t: candidate ids (device)."""
    n = len(qent)
    uq, inv = np.unique(qent, return_inverse=True)
    Q = len(uq)
    gorder = np.argsort(inv, kind='stable')
    gcnt = np.bincount(inv, minlength=Q)
    gptr = np.zeros(Q + 1, dtype=np.int64)
    np.cumsum(gcnt, out=gptr[1:])
    tg = tent[gorder]
    fcnt = (filt_indptr[uq + 1] - filt_indptr[uq]).astype(np.int64)
    C = pool_t.numel()
    ranks = np.empty(n, dtype=np.float64)

    for qb, K, F in _batches(gcnt, fcnt, 4 << 20, 4 << 20, 8192):
        B = len(qb)
        proj = ent_t.index_select(0, torch.as_tensor(uq[qb], dtype=torch.long, device=dev)) @ Mr_eff

        # target scores -> per-query sorted thresholds (+inf padded)
        th = torch.full((B, K), float('inf'), device=dev, dtype=ent_t.dtype)
        rows, cols, tids, dest = [], [], [], []
        for i, q in enumerate(qb):
            k = int(gcnt[q])
            rows.append(np.full(k, i, np.int64)); cols.append(np.arange(k, dtype=np.int64))
            tids.append(tg[gptr[q]:gptr[q] + k]); dest.append(gorder[gptr[q]:gptr[q] + k])
        rows, cols = np.concatenate(rows), np.concatenate(cols)
        tids, dest = np.concatenate(tids), np.concatenate(dest)
        rt, ct = torch.as_tensor(rows, device=dev), torch.as_tensor(cols, device=dev)
        tvec = ent_t.index_select(0, torch.as_tensor(tids.astype(np.int64), dtype=torch.long, device=dev))
        th[rt, ct] = (proj[rt] * tvec).sum(1)
        th_sorted, th_perm = torch.sort(th, dim=1)
        # the target score comes from 3 kernels that can differ in the last bit;
        # compare within a tolerance band so the target cancels in the subtraction
        band = eps * (th_sorted.abs().clamp(max=1e30) + 1.0)
        th_hi, th_lo = th_sorted + band, th_sorted - band
        gtH = torch.zeros(B, K + 2, dtype=torch.int32, device=dev)
        geH = torch.zeros(B, K + 2, dtype=torch.int32, device=dev)

        def accumulate(scores, gH, eH):
            sc = scores.contiguous()
            one = torch.ones_like(sc, dtype=torch.int32)
            gH.scatter_add_(1, torch.searchsorted(th_hi, sc), one)
            if ties:
                eH.scatter_add_(1, torch.searchsorted(th_lo, sc, right=True), one)

        # (a) the full type-compatible candidate pool, streamed in tiles
        step = max(1, min(tile // max(B, 1), cand_rows))
        for c0 in range(0, C, step):
            cand = ent_t.index_select(0, pool_t[c0:c0 + step])
            accumulate(proj @ cand.T, gtH, geH)
            del cand

        # (b) known-true entities (train+valid+test), subtracted -> filtered setting
        if F > 0:
            fpad = np.zeros((B, F), dtype=np.int64)
            fmask = np.zeros((B, F), dtype=bool)
            for i, q in enumerate(qb):
                s0, s1 = filt_indptr[uq[q]], filt_indptr[uq[q] + 1]
                fpad[i, :s1 - s0] = filt_vals[s0:s1]; fmask[i, :s1 - s0] = True
            fpad_t, fmask_t = torch.as_tensor(fpad, device=dev), torch.as_tensor(fmask, device=dev)
            fstep = max(1, min(tile // max(B, 1), cand_rows // max(B, 1)))
            gtF = torch.zeros(B, K + 2, dtype=torch.int32, device=dev)
            geF = torch.zeros(B, K + 2, dtype=torch.int32, device=dev)
            for f0 in range(0, F, fstep):
                ids = fpad_t[:, f0:f0 + fstep]
                emb = ent_t.index_select(0, ids.reshape(-1)).reshape(B, ids.shape[1], -1)
                sc = torch.einsum('bd,bfd->bf', proj, emb)
                sc = torch.where(fmask_t[:, f0:f0 + fstep], sc, torch.full_like(sc, -float('inf')))
                accumulate(sc, gtF, geF)
            gtH -= gtF
            geH -= geF

        def suffix(H):
            return torch.flip(torch.cumsum(torch.flip(H, [1]), 1), [1])[:, 1:K + 1]

        gt = suffix(gtH).double()
        if ties:
            eq = (suffix(geH) - suffix(gtH)).double()   # tied with target, excluding itself
            rk = gt + eq / 2.0 + 1.0                    # average rank
        else:
            rk = gt + 1.0
        rk = rk.clamp(min=1.0)    # last-bit disagreement can give -1 in ~7e-8 of cases

        inv_perm = torch.empty_like(th_perm)
        inv_perm.scatter_(1, th_perm, torch.arange(K, device=dev).expand(B, K))
        rk = rk.gather(1, inv_perm)
        ranks[dest] = rk[rt, ct].cpu().numpy()
        del gtH, geH, th, th_sorted, proj
    return ranks


# ================================================================== workers
def rank_path(a, r, side):
    return os.path.join(a.rank_dir, f'ranks_eval_{r}_{side}.npy')


def pool_path(a, r):
    return os.path.join(a.rank_dir, f'pools_{r}.json')


def relation_done(a, r, n_expected):
    for side in ('tail', 'head'):
        f = rank_path(a, r, side)
        try:
            if not os.path.exists(f) or len(np.load(f, mmap_mode='r')) != n_expected:
                return False
        except Exception:
            return False
    return os.path.exists(pool_path(a, r))


def worker(gpu, tasks, a, ret):
    try:
        _worker(gpu, tasks, a)
        ret.put({'ok': gpu})
    except BaseException:
        import traceback
        traceback.print_exc()
        ret.put({'__error__': f'gpu{gpu}: ' + traceback.format_exc()})


def _worker(gpu, tasks, a):
    import torch
    torch.backends.cuda.matmul.allow_tf32 = a.tf32      # TF32 off: exact to ~+/-2 ranks
    torch.backends.cudnn.allow_tf32 = a.tf32
    dev = f'cuda:{gpu}'
    torch.cuda.set_device(dev)

    tarr = np.load(os.path.join(a.work, 'type_code.npy'))
    num_ent = len(tarr)
    tsize = np.bincount(tarr[tarr >= 0].astype(np.int64))

    t0 = time.time()
    ent_np = np.load(a.entity_npy)      # sequential read (mmap measured ~7 MB/s here)
    log(f"[gpu{gpu}] entity table {ent_np.shape} read in {time.time()-t0:.1f}s")
    ent_t = torch.empty(ent_np.shape, dtype=torch.float32, device=dev)
    for i in range(0, len(ent_np), 2_000_000):
        ent_t[i:i + 2_000_000] = torch.from_numpy(ent_np[i:i + 2_000_000]).to(dev)
    del ent_np
    rel_np = np.load(a.relation_npy)
    d = a.hidden_dim
    assert ent_t.shape[1] == d and rel_np.shape[1] == d * d, \
        f"--hidden_dim {d} does not match model: ent {ent_t.shape}, rel {rel_np.shape}"

    pool_cache = {}
    for r in tasks:
        t0 = time.time()
        allht = np.load(os.path.join(a.work, f'all_{r}.npy'))
        testht = np.load(os.path.join(a.work, f'test_{r}.npy'))
        if a.sample and len(testht) > a.sample:
            sel = np.random.default_rng(a.seed).choice(len(testht), a.sample, replace=False)
            testht = testht[np.sort(sel)]
        if a.resume and relation_done(a, r, len(testht)):
            log(f"[gpu{gpu}] rel {r:>3} already complete -- skipping")
            continue

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

        Mr = torch.from_numpy(rel_np[r].reshape(d, d).copy()).to(dev)
        for side in ('tail', 'head'):
            if side == 'tail':
                keys, vals, Mr_eff, pool = allht[:, 0], allht[:, 1], Mr, pools['tail']
                qe, te, tys = testht[:, 0], testht[:, 1], ttypes
            else:
                keys, vals, Mr_eff, pool = allht[:, 1], allht[:, 0], Mr.T.contiguous(), pools['head']
                qe, te, tys = testht[:, 1], testht[:, 0], htypes
            indptr, fv = _csr_from_pairs(keys.astype(np.int64), vals, num_ent)
            assert np.isin(tarr[fv], np.array(tys, dtype=np.int16)).all(), \
                f"rel {r} {side}: a known-true entity lies outside the candidate pool"
            rk = rank_side(torch, dev, ent_t, Mr_eff, qe.astype(np.int64), te.astype(np.int64),
                           indptr, fv, pool, a.tile, not a.no_ties, a.rank_eps, a.cand_rows)
            np.save(rank_path(a, r, side), rk.astype(np.float32))
            del indptr, fv
        json.dump({'pool_head': int(pools['head'].numel()), 'pool_tail': int(pools['tail'].numel()),
                   'n_test': int(len(testht)),
                   'head_types': [int(x) for x in htypes], 'tail_types': [int(x) for x in ttypes]},
                  open(pool_path(a, r), 'w'))
        log(f"[gpu{gpu}] rel {r:>3} n={len(testht):>11,} "
            f"pool h/t={pools['head'].numel():>10,}/{pools['tail'].numel():<10,} {time.time()-t0:7.1f}s")


# =================================================================== report
def rand_mrr(C):
    """Expected reciprocal rank of a uniformly random position among C candidates."""
    C = float(C)
    if C <= 1:
        return 1.0
    return (np.log(C) + 0.5772156649 + 1 / (2 * C) - 1 / (12 * C * C)) / C


def side_sums(rk):
    rk = np.asarray(rk, dtype=np.float64)
    return np.array([len(rk), (1 / rk).sum(), rk.sum()] + [(rk <= k).sum() for k in KS])


def sums_to_metrics(v):
    n = v[0]
    m = {'n': int(n), 'MRR': v[1] / n, 'MR': v[2] / n}
    m.update({f'H@{k}': c / n for k, c in zip(KS, v[3:])})
    return m


def report(a, names, rels):
    os.makedirs(a.out_dir, exist_ok=True)
    tot = {'tail': np.zeros(3 + len(KS)), 'head': np.zeros(3 + len(KS))}
    rnd_mrr = {'tail': 0.0, 'head': 0.0}
    rnd_h = {'tail': np.zeros(len(KS)), 'head': np.zeros(len(KS))}
    rows = []
    for r in rels:
        if not os.path.exists(pool_path(a, r)):
            log(f"rel {r}: no pool file, skipped"); continue
        pj = json.load(open(pool_path(a, r)))
        per = np.zeros(3 + len(KS)); rm, rh, n_all = 0.0, np.zeros(len(KS)), 0
        side_m = {}
        for side in ('tail', 'head'):
            f = rank_path(a, r, side)
            if not os.path.exists(f):
                continue
            rk = np.load(f)
            C = pj['pool_' + side]
            st = side_sums(rk)
            tot[side] += st; per += st
            rr = rand_mrr(C); rhk = np.array([min(k, C) / C for k in KS])
            rnd_mrr[side] += rr * len(rk); rnd_h[side] += rhk * len(rk)
            rm += rr * len(rk); rh += rhk * len(rk); n_all += len(rk)
            side_m[side] = sums_to_metrics(st)
        if not n_all:
            continue
        m = sums_to_metrics(per); rmrr = rm / n_all
        row = {'rel': r, 'relation': names.get(r, '?'), 'n_test_triples': pj['n_test'],
               'pool_head': pj['pool_head'], 'pool_tail': pj['pool_tail'],
               'MRR': m['MRR'], **{f'H@{k}': m[f'H@{k}'] for k in KS}, 'MR': m['MR'],
               'MRR_tail': side_m.get('tail', {}).get('MRR', float('nan')),
               'MRR_head': side_m.get('head', {}).get('MRR', float('nan')),
               'random_MRR': rmrr, 'enrichment_MRR': m['MRR'] / rmrr,
               'random_H@1': rh[KS.index(1)] / n_all,
               'random_H@3': rh[KS.index(3)] / n_all,
               'random_H@10': rh[KS.index(10)] / n_all,
               'enrichment_H@10': m['H@10'] / (rh[KS.index(10)] / n_all),
               'random_H@100': rh[KS.index(100)] / n_all,
               'enrichment_H@100': m['H@100'] / (rh[KS.index(100)] / n_all)}
        rows.append(row)
    if not rows:
        sys.exit("no rank files found -- nothing to report")

    t1 = []
    for name, v, rm_, rh_ in (
            ('micro_tail', tot['tail'], rnd_mrr['tail'], rnd_h['tail']),
            ('micro_head', tot['head'], rnd_mrr['head'], rnd_h['head']),
            ('micro_both', tot['tail'] + tot['head'], rnd_mrr['tail'] + rnd_mrr['head'],
             rnd_h['tail'] + rnd_h['head'])):
        m = sums_to_metrics(v); rmrr = rm_ / v[0]
        t1.append({'view': name, 'n': m['n'], 'MRR': m['MRR'],
                   **{f'H@{k}': m[f'H@{k}'] for k in KS}, 'MR': m['MR'],
                   'random_MRR': rmrr, 'enrichment_MRR': m['MRR'] / rmrr,
                   'random_H@1': rh_[KS.index(1)] / v[0],
                   'random_H@3': rh_[KS.index(3)] / v[0],
                   'random_H@10': rh_[KS.index(10)] / v[0],
                   'random_H@100': rh_[KS.index(100)] / v[0]})
    mean = lambda k: float(np.mean([x[k] for x in rows]))
    t1.append({'view': 'macro_over_relations', 'n': len(rows), 'MRR': mean('MRR'),
               **{f'H@{k}': mean(f'H@{k}') for k in KS}, 'MR': mean('MR'),
               'random_MRR': mean('random_MRR'), 'enrichment_MRR': mean('enrichment_MRR'),
               'random_H@1': mean('random_H@1'), 'random_H@3': mean('random_H@3'),
               'random_H@10': mean('random_H@10'), 'random_H@100': mean('random_H@100')})
    rows.sort(key=lambda x: -x['n_test_triples'])

    def write(path, rs):
        with open(path, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rs[0].keys()))
            w.writeheader(); w.writerows(rs)
    write(os.path.join(a.out_dir, 'table1_overall.csv'), t1)
    write(os.path.join(a.out_dir, 'table2_per_relation.csv'), rows)
    json.dump({'overall': t1, 'per_relation': rows},
              open(os.path.join(a.out_dir, 'results.json'), 'w'), indent=2)

    W = 118
    print('\n' + '=' * W + '\nTABLE 1  overall, filtered, full type-compatible ranking\n' + '=' * W)
    print(f"{'view':<22}{'n':>13}{'MRR':>10}{'H@1':>8}{'H@3':>8}{'H@10':>8}{'H@100':>8}"
          f"{'H@1000':>8}{'MR':>12}{'rand MRR':>11}{'enrich':>9}")
    for r_ in t1:
        print(f"{r_['view']:<22}{r_['n']:>13,}{r_['MRR']:>10.5f}{r_['H@1']:>8.4f}{r_['H@3']:>8.4f}"
              f"{r_['H@10']:>8.4f}{r_['H@100']:>8.4f}{r_['H@1000']:>8.4f}{r_['MR']:>12,.0f}"
              f"{r_['random_MRR']:>11.5f}{r_['enrichment_MRR']:>8.1f}x")
    print('\n' + '=' * W + '\nTABLE 2  per relation\n' + '=' * W)
    print(f"{'rel':>4} {'relation':<44}{'n':>11}{'poolH':>10}{'poolT':>10}{'MRR':>9}{'H@10':>8}"
          f"{'H@100':>8}{'rand MRR':>10}{'enrich':>9}")
    for x in rows:
        print(f"{x['rel']:>4} {x['relation'][:43]:<44}{x['n_test_triples']:>11,}{x['pool_head']:>10,}"
              f"{x['pool_tail']:>10,}{x['MRR']:>9.5f}{x['H@10']:>8.4f}{x['H@100']:>8.4f}"
              f"{x['random_MRR']:>10.6f}{x['enrichment_MRR']:>8.1f}x")
    log(f"wrote tables to {a.out_dir}")


def write_metadata(a):
    meta = {'args': vars(a), 'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'python': sys.version.split()[0], 'platform': platform.platform(),
            'numpy': np.__version__, 'files': {}}
    try:
        import torch
        meta['torch'] = torch.__version__
        meta['cuda'] = torch.version.cuda
        meta['gpus'] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    except Exception:
        pass
    for k, f in (('train', a.train), ('valid', a.valid), ('test', a.test)):
        for ext in ('.txt', '.pt'):
            p = os.path.join(a.data_path, f + ext)
            if os.path.exists(p):
                meta['files'][f + ext] = os.path.getsize(p)
    for p in (a.entity_npy, a.relation_npy):
        meta['files'][os.path.basename(p)] = os.path.getsize(p)
    os.makedirs(a.out_dir, exist_ok=True)
    json.dump(meta, open(os.path.join(a.out_dir, 'run_metadata.json'), 'w'), indent=2, default=str)


# ===================================================================== main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data_path', required=True)
    p.add_argument('--model_path', required=True)
    p.add_argument('--work', required=True, help='parsed cache (all_*.npy, test_*.npy, type_code.npy)')
    p.add_argument('--rank_dir', default=None, help='rank .npy files (default: <work>/full_ranks_eval)')
    p.add_argument('--out_dir', default=None, help='tables/metadata (default: <work>/full_report)')
    p.add_argument('--train', default='EvoAge_121_12M_KG_train_90')
    p.add_argument('--valid', default='EvoAge_121_12M_KG_valid_10')
    p.add_argument('--test', default='EvoAge_1to1_KG_test_10_shared')
    p.add_argument('--typed_dict', default='entities_final_Ntype_updated.dict')
    p.add_argument('--relations', default='relation_final.dict')
    p.add_argument('--hidden_dim', type=int, default=64)
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--gpu_weights', default=None, help='relative GPU speed, e.g. "64,83"')
    p.add_argument('--tile', type=int, default=1 << 26, help='max elements per score tile')
    p.add_argument('--cand_rows', type=int, default=4_000_000, help='max candidate rows per gather')
    p.add_argument('--sample', type=int, default=0, help='max test triples per relation (0 = all)')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--tf32', action='store_true', help='faster, ~46-rank drift')
    p.add_argument('--no_ties', action='store_true', help='optimistic instead of average rank')
    p.add_argument('--rank_eps', type=float, default=1e-6)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--no_pt', action='store_true')
    p.add_argument('--force_prepare', action='store_true')
    p.add_argument('--only_rel', default=None, help='comma-separated relation ids (debug)')
    p.add_argument('--report_only', action='store_true', help='skip ranking; rebuild tables')
    a = p.parse_args()

    a.rank_dir = a.rank_dir or os.path.join(a.work, 'full_ranks_eval')
    a.out_dir = a.out_dir or os.path.join(a.work, 'full_report')
    for d in (a.work, a.rank_dir, a.out_dir):
        os.makedirs(d, exist_ok=True)
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
    write_metadata(a)

    if not a.report_only:
        tarr = np.load(os.path.join(a.work, 'type_code.npy'))
        tsize = np.bincount(tarr[tarr >= 0].astype(np.int64))
        cost = {}
        for r in rels:           # ordering heuristic only: (#distinct queries) x (pool size)
            allht = np.load(os.path.join(a.work, f'all_{r}.npy'), mmap_mode='r')
            sub = np.asarray(allht[::max(1, len(allht) // 200_000)])
            ht, tt = np.unique(tarr[sub[:, 0]]), np.unique(tarr[sub[:, 1]])
            test = np.load(os.path.join(a.work, f'test_{r}.npy'), mmap_mode='r')
            cost[r] = (len(np.unique(test[:, 0])) * int(tsize[tt].sum())
                       + len(np.unique(test[:, 1])) * int(tsize[ht].sum()))
        order = sorted(rels, key=lambda r: -cost[r])
        log(f"planned {len(order)} relations, ~{sum(cost.values())/1e12:.1f} Tpairs")

        gpus = [int(g) for g in a.gpus.split(',')]
        w = [float(x) for x in a.gpu_weights.split(',')] if a.gpu_weights else [1.0] * len(gpus)
        assert len(w) == len(gpus), "--gpu_weights must match --gpus"
        load, shards = [0.0] * len(gpus), [[] for _ in gpus]
        for r in order:                      # longest-processing-time first
            i = min(range(len(gpus)), key=lambda j: load[j])
            shards[i].append(r); load[i] += cost[r] / w[i]
        for g, sh, l in zip(gpus, shards, load):
            log(f"  gpu{g}: {len(sh)} relations, {l/1e12:.2f} Tpairs (weighted)")

        import torch.multiprocessing as mp
        ctx = mp.get_context('spawn')
        ret = ctx.Queue()
        procs = [ctx.Process(target=worker, args=(g, s, a, ret)) for g, s in zip(gpus, shards)]
        t0 = time.time()
        for pr in procs:
            pr.start()
        got = [ret.get() for _ in procs]
        for pr in procs:
            pr.join()
        errs = [g['__error__'] for g in got if '__error__' in g]
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            sys.exit(f"{len(errs)} worker(s) failed; finished relations are saved -- rerun with --resume")
        log(f"ranking finished in {time.time()-t0:.1f}s")

    report(a, names, rels)


if __name__ == '__main__':
    main()
