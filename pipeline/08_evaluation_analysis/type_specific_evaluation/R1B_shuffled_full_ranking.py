#!/usr/bin/env python3
"""
R1B_null_models.py -- Part B: type-preserving randomized controls, ranked with the SAME
exact filtered type-compatible engine as Part A.

modes (--modes, comma list; default shuffle):
  shuffle  heads and tails permuted WITHIN each relation (relation-specific entity types
           preserved by construction), then repaired so that no fake triple is a known
           triple in train+valid+test (fallback: redraw tail from the full tail pool)
  pool     (optional) head~U(head pool), tail~U(tail pool), verified not in train+valid+test

Controls are built from the (optionally sampled) test triples: --ctrl_sample per relation
(0 = all test triples, identical protocol to Part A).

Outputs
  <rank_dir>/ranks_{ctrlshuffle|ctrlpool}_{rel}_{tail|head}.npy
  <out_dir>/B_table1_overall.csv, B_table2_per_relation.csv, B_results.json

See README.md for a portable command-line example.
"""
import argparse, csv, glob, importlib.util, json, os, sys, time
import numpy as np

TAG = {'pool': 'ctrlpool', 'shuffle': 'ctrlshuffle'}
KS = (1, 3, 10, 100, 1000)


def log(*x):
    print(f"[{time.strftime('%H:%M:%S')}]", *x, flush=True)


def load_engine(path):
    spec = importlib.util.spec_from_file_location('engineA', path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------ null models
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


def make_pool(n, seed, r, known, num_ent, hp, tp, rounds=200):
    rng = np.random.default_rng(seed * 100003 + r)
    out = np.empty((n, 2), dtype=np.int32)
    out[:, 0] = hp[rng.integers(len(hp), size=n)]
    out[:, 1] = tp[rng.integers(len(tp), size=n)]
    bad = np.flatnonzero(is_known(known, num_ent, out)); first = bad.size
    for _ in range(rounds):
        if not bad.size: break
        out[bad, 0] = hp[rng.integers(len(hp), size=bad.size)]
        out[bad, 1] = tp[rng.integers(len(tp), size=bad.size)]
        bad = bad[is_known(known, num_ent, out[bad])]
    return out, (first, int(bad.size))


def make_shuffle(ht, seed, r, known, num_ent, tp, rounds=100):
    rng = np.random.default_rng(seed * 100003 + r + 7)
    n = len(ht)
    if n < 2:
        return ht.copy(), (0, 0)
    out = np.empty_like(ht)
    out[:, 0] = ht[derangement(n, rng), 0]
    out[:, 1] = ht[derangement(n, rng), 1]
    bad = np.flatnonzero(is_known(known, num_ent, out)); first = bad.size
    for src in (ht[:, 1], tp):                    # own test tails first, then full pool
        for _ in range(rounds):
            if not bad.size: break
            out[bad, 1] = src[rng.integers(len(src), size=bad.size)]
            bad = bad[is_known(known, num_ent, out[bad])]
    return out, (first, int(bad.size))


# ------------------------------------------------------------ paths / worker
def rpath(a, mode, r, side):
    return os.path.join(a.rank_dir, f'ranks_{TAG[mode]}_{r}_{side}.npy')


def n_target(a, n_full):
    return min(n_full, a.ctrl_sample) if a.ctrl_sample else n_full


def mode_done(a, mode, r, n_full):
    for side in ('tail', 'head'):
        f = rpath(a, mode, r, side)
        try:
            if not os.path.exists(f) or len(np.load(f, mmap_mode='r')) != n_target(a, n_full):
                return False
        except Exception:
            return False
    return True


def worker(gpu, tasks, a, ret):
    try:
        _worker(gpu, tasks, a); ret.put({'ok': gpu})
    except BaseException:
        import traceback; traceback.print_exc()
        ret.put({'__error__': f'gpu{gpu}: ' + traceback.format_exc()})


def _worker(gpu, tasks, a):
    import torch
    eng = load_engine(a.engine)
    torch.backends.cuda.matmul.allow_tf32 = False
    dev = f'cuda:{gpu}'; torch.cuda.set_device(dev)
    modes = a.modes.split(',')
    tarr = np.load(os.path.join(a.work, 'type_code.npy')); num_ent = len(tarr)

    e = np.load(a.entity_npy)
    ent_t = torch.empty(e.shape, dtype=torch.float32, device=dev)
    for i in range(0, len(e), 2_000_000):
        ent_t[i:i + 2_000_000] = torch.from_numpy(e[i:i + 2_000_000]).to(dev)
    del e
    rel_np = np.load(a.relation_npy); d = a.hidden_dim
    assert ent_t.shape[1] == d and rel_np.shape[1] == d * d

    pool_cache = {}
    for r in tasks:
        t0 = time.time()
        allht = np.load(os.path.join(a.work, f'all_{r}.npy'))
        test = np.load(os.path.join(a.work, f'test_{r}.npy'))
        todo = [m for m in modes if not (a.resume and mode_done(a, m, r, len(test)))]
        if not todo:
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

        known = np.unique(allht[:, 0].astype(np.int64) * np.int64(num_ent) + allht[:, 1].astype(np.int64))
        tht = test
        sz = n_target(a, len(test))
        if sz < len(test):
            tht = test[np.sort(np.random.default_rng(a.seed).choice(len(test), sz, replace=False))]
        variants = {}
        for m in todo:
            if m == 'pool':
                v, info = make_pool(len(tht), a.seed, r, known, num_ent,
                                    pools['head'].cpu().numpy(), pools['tail'].cpu().numpy())
            else:
                v, info = make_shuffle(tht, a.seed, r, known, num_ent, pools['tail'].cpu().numpy())
            variants[m] = v
            log(f"[gpu{gpu}] rel {r:>3} {m}: {info[0]:,} first-draw fakes were real, "
                f"{info[1]:,} remain after repair")
        del known

        Mr = torch.from_numpy(rel_np[r].reshape(d, d).copy()).to(dev)
        for side in ('tail', 'head'):
            if side == 'tail':
                keys, vals, pool, Meff = allht[:, 0], allht[:, 1], pools['tail'], Mr
            else:
                keys, vals, pool, Meff = allht[:, 1], allht[:, 0], pools['head'], Mr.T.contiguous()
            indptr, fv = eng._csr_from_pairs(keys.astype(np.int64), vals, num_ent)
            for m, v in variants.items():
                qe = (v[:, 0] if side == 'tail' else v[:, 1]).astype(np.int64)
                te = (v[:, 1] if side == 'tail' else v[:, 0]).astype(np.int64)
                rk = eng.rank_side(torch, dev, ent_t, Meff, qe, te, indptr, fv, pool,
                                   a.tile, True, a.rank_eps, a.cand_rows)
                # a fake target is not in the filter set, so the engine counts it as tied
                # with itself; remove that self-tie (0.5 under average rank)
                rk = np.maximum(rk - 0.5, 1.0)
                np.save(rpath(a, m, r, side), rk.astype(np.float32))
            del indptr, fv
        log(f"[gpu{gpu}] rel {r:>3} modes={','.join(todo)} {time.time()-t0:7.1f}s")


# ------------------------------------------------------------ report
def sums(rk):
    rk = np.asarray(rk, dtype=np.float64)
    return np.array([len(rk), (1 / rk).sum()] + [(rk <= k).sum() for k in KS])


def fin(v):
    return {'n': int(v[0]), 'MRR': v[1] / v[0], **{f'H@{k}': c / v[0] for k, c in zip(KS, v[2:])}}


def report(a, names, rels, eng):
    os.makedirs(a.out_dir, exist_ok=True)
    modes = ['eval'] + a.modes.split(',')
    tot = {m: np.zeros(2 + len(KS)) for m in modes}
    rnd = {m: 0.0 for m in modes}
    rows = []
    for r in rels:
        pf = os.path.join(a.eval_rank_dir, f'pools_{r}.json')
        if not os.path.exists(pf):
            continue
        pj = json.load(open(pf))
        row = {'rel': r, 'relation': names.get(r, '?'), 'n_test': pj['n_test']}
        for m in modes:
            per, rr_sum, n = np.zeros(2 + len(KS)), 0.0, 0
            for side in ('tail', 'head'):
                f = (os.path.join(a.eval_rank_dir, f'ranks_eval_{r}_{side}.npy') if m == 'eval'
                     else rpath(a, m, r, side))
                if not os.path.exists(f):
                    continue
                rk = np.load(f)
                per += sums(rk); rr_sum += eng.rand_mrr(pj['pool_' + side]) * len(rk); n += len(rk)
            if n:
                f_ = fin(per)
                row[f'MRR_{m}'] = f_['MRR']; row[f'H@1_{m}'] = f_['H@1']
                row[f'H@3_{m}'] = f_['H@3']; row[f'H@10_{m}'] = f_['H@10']
                row[f'H@100_{m}'] = f_['H@100']; row[f'n_{m}'] = n // 2
                row[f'random_MRR_{m}'] = rr_sum / n
                tot[m] += per; rnd[m] += rr_sum
                if m == 'eval':
                    row['random_MRR'] = rr_sum / n
        rows.append(row)
    if not rows:
        sys.exit("nothing to report")

    t1 = []
    for m in modes:
        if tot[m][0] == 0:
            continue
        f_ = fin(tot[m]); rm = rnd[m] / tot[m][0]
        vals = [x[f'MRR_{m}'] for x in rows if f'MRR_{m}' in x]
        t1.append({'method': m, 'n_triples_both_sides': f_['n'], 'micro_MRR': f_['MRR'],
                   'micro_H@1': f_['H@1'], 'micro_H@3': f_['H@3'],
                   'micro_H@10': f_['H@10'], 'micro_H@100': f_['H@100'],
                   'macro_MRR': float(np.mean(vals)), 'macro_median_MRR': float(np.median(vals)),
                   'micro_random_MRR': rm, 'micro_enrichment': f_['MRR'] / rm})
    rows.sort(key=lambda x: -x['n_test'])

    def write(p, rs):
        keys = list(rs[0])
        for r_ in rs:
            for k in r_:
                if k not in keys: keys.append(k)
        with open(p, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rs)
    write(os.path.join(a.out_dir, 'B_table1_overall.csv'), t1)
    write(os.path.join(a.out_dir, 'B_table2_per_relation.csv'), rows)
    json.dump({'overall': t1, 'per_relation': rows}, open(os.path.join(a.out_dir, 'B_results.json'), 'w'), indent=2)

    print('\nTABLE B1  overall')
    print(f"{'method':<10}{'n':>14}{'micro MRR':>11}{'H@10':>8}{'H@100':>8}{'macro MRR':>11}{'median':>10}{'rand MRR':>10}{'enrich':>8}")
    for x in t1:
        print(f"{x['method']:<10}{x['n_triples_both_sides']:>14,}{x['micro_MRR']:>11.5f}{x['micro_H@10']:>8.4f}"
              f"{x['micro_H@100']:>8.4f}{x['macro_MRR']:>11.5f}{x['macro_median_MRR']:>10.5f}"
              f"{x['micro_random_MRR']:>10.5f}{x['micro_enrichment']:>7.1f}x")
    g = lambda x, k: x.get(k, float('nan'))
    cm = [m for m in a.modes.split(',')]
    print('\nTABLE B2  per relation (MRR)')
    print(f"{'rel':>4} {'relation':<40}{'n':>11}{'eval':>10}" + ''.join(f"{m:>10}" for m in cm) + f"{'random':>11}")
    for x in rows:
        print(f"{x['rel']:>4} {x['relation'][:39]:<40}{x['n_test']:>11,}{g(x,'MRR_eval'):>10.5f}"
              + ''.join(f"{g(x, 'MRR_' + m):>10.5f}" for m in cm) + f"{g(x,'random_MRR'):>11.6f}")
    log(f"wrote tables to {a.out_dir}")


# ------------------------------------------------------------ main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--engine', required=True, help='path to the Part A script')
    p.add_argument('--data_path', required=True)
    p.add_argument('--model_path', required=True)
    p.add_argument('--work', required=True, help='Part A cache dir (all_*.npy, test_*.npy, type_code.npy, PREPARED)')
    p.add_argument('--eval_rank_dir', required=True, help='Part A rank dir (ranks_eval_*, pools_*.json)')
    p.add_argument('--rank_dir', default=None)
    p.add_argument('--out_dir', default=None)
    p.add_argument('--relations', default='relation_final.dict')
    p.add_argument('--modes', default='shuffle', help='shuffle (default) and/or pool')
    p.add_argument('--hidden_dim', type=int, default=64)
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--ctrl_sample', type=int, default=0, help='test triples/relation for controls (0 = all)')
    p.add_argument('--tile', type=int, default=1 << 26)
    p.add_argument('--cand_rows', type=int, default=4_000_000)
    p.add_argument('--rank_eps', type=float, default=1e-6)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--only_rel', default=None)
    p.add_argument('--report_only', action='store_true')
    a = p.parse_args()
    a.rank_dir = a.rank_dir or os.path.join(a.work, 'B_ranks')
    a.out_dir = a.out_dir or os.path.join(a.work, 'B_report')
    for d in (a.rank_dir, a.out_dir):
        os.makedirs(d, exist_ok=True)
    a.entity_npy = sorted(glob.glob(os.path.join(a.model_path, '*entity.npy')), key=len)[0]
    a.relation_npy = sorted(glob.glob(os.path.join(a.model_path, '*relation.npy')), key=len)[0]

    meta = json.load(open(os.path.join(a.work, 'PREPARED')))
    names = {}
    for l in open(os.path.join(a.data_path, a.relations)):
        i, n = l.rstrip('\n').split('\t')[:2]; names[int(i)] = n
    rels = sorted(int(r) for r, v in meta['rel'].items() if 'test' in v)
    if a.only_rel:
        keep = {int(x) for x in a.only_rel.split(',')}; rels = [r for r in rels if r in keep]
    eng = load_engine(a.engine)

    if not a.report_only:
        cost = {r: meta['rel'][str(r)]['test'] for r in rels}
        gpus = [int(g) for g in a.gpus.split(',')]
        load, shards = [0.0] * len(gpus), [[] for _ in gpus]
        for r in sorted(rels, key=lambda r: -cost[r]):
            i = min(range(len(gpus)), key=lambda j: load[j]); shards[i].append(r); load[i] += cost[r]
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
            sys.exit("worker failed; rerun with --resume")
        log(f"ranking finished in {time.time()-t0:.1f}s")
    report(a, names, rels, eng)


if __name__ == '__main__':
    main()
