#!/usr/bin/env python3
"""
Score the real test set and type-preserving shuffled sets
(from D1) with the SAME sampled type-compatible protocol as Part C (imports its engine):
K distinct candidates per query, head and tail prediction, known positives (train+valid+test)
and the target excluded, average rank for ties, full-pool fallback if 2K > pool size.

Resumable: <out_dir>/scored/K{K}/{tag}/rel{r}.npz is skipped if present (--force to redo).
Outputs in <out_dir>/results_K{K}/: per_seed_summary.csv, cumulative_hits.csv,
 per_relation_all.csv, d2_metadata.json

See README.md for usage.
"""
import argparse, csv, glob, importlib.util, json, os, platform, sys, time
import numpy as np
from tqdm import tqdm

HERE = os.path.dirname(os.path.abspath(__file__))


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def tags_of(a):
    return ['real'] + [f'shuffle_seed{s:02d}' for s in range(a.seed0, a.seed0 + a.n_seeds)]


def res_path(a, tag, r):
    return os.path.join(a.out_dir, 'scored', f'K{a.K}', tag, f'rel{r}.npz')


_REAL = {}
def real_arrays(a):
    if not _REAL:
        z = np.load(os.path.join(a.d1_dir, 'real.npz'))
        _REAL['h'], _REAL['t'] = z['h'], z['t']
        _REAL['off'] = np.r_[0, np.cumsum(np.bincount(z['r']))]
    return _REAL


def available(a, tag):
    if tag == 'real':
        return os.path.exists(os.path.join(a.d1_dir, 'real.npz'))
    return os.path.exists(os.path.join(a.d1_dir, tag + '.DONE'))


def load_pairs(a, tag, r):
    R_ = real_arrays(a); x, y = R_['off'][r], R_['off'][r + 1]
    if tag == 'real':
        h, t = R_['h'][x:y], R_['t'][x:y]
    else:
        h = np.load(os.path.join(a.d1_dir, f'{tag}_h.npy'), mmap_mode='r')[x:y]
        t = np.load(os.path.join(a.d1_dir, f'{tag}_t.npy'), mmap_mode='r')[x:y]
    return np.column_stack([h, t]).astype(np.int64)


def worker(gpu, rels, a, ret):
    try:
        _worker(gpu, rels, a); ret.put({'ok': gpu})
    except BaseException:
        import traceback; traceback.print_exc()
        ret.put({'__error__': f'gpu{gpu}: ' + traceback.format_exc()})


def _worker(gpu, rels, a):
    import torch
    cm = load_mod(a.c_script, 'cmod')
    torch.backends.cuda.matmul.allow_tf32 = False
    dev = f'cuda:{gpu}'; torch.cuda.set_device(dev)
    tarr = np.load(os.path.join(a.work, 'type_code.npy')); num_ent = len(tarr)
    e = np.load(a.entity_npy)
    ent_t = torch.empty(e.shape, dtype=torch.float32, device=dev)
    for i in range(0, len(e), 2_000_000):
        ent_t[i:i + 2_000_000] = torch.from_numpy(e[i:i + 2_000_000]).to(dev)
    del e
    rel_np = np.load(a.relation_npy); d = a.hidden_dim; K = a.K
    assert ent_t.shape[1] == d and rel_np.shape[1] == d * d, 'hidden_dim mismatch'
    tags = [t for t in tags_of(a) if available(a, t)]
    pool_cache = {}
    for r in tqdm(rels, desc=f'gpu{gpu}', position=gpu):
        todo = [t for t in tags if a.force or not os.path.exists(res_path(a, t, r))]
        if not todo:
            continue
        allht = np.load(os.path.join(a.work, f'all_{r}.npy'))
        htypes = tuple(np.unique(tarr[allht[:, 0]]).tolist()); ttypes = tuple(np.unique(tarr[allht[:, 1]]).tolist())
        pools = {}
        for key, tys in (('head', htypes), ('tail', ttypes)):
            if tys not in pool_cache:
                if len(pool_cache) > 2:
                    pool_cache.clear(); torch.cuda.empty_cache()
                ids = np.flatnonzero(np.isin(tarr, np.array(tys, dtype=np.int16)))
                pool_cache[tys] = torch.as_tensor(ids.astype(np.int64), device=dev)
            pools[key] = pool_cache[tys]
        Mr = torch.from_numpy(rel_np[r].reshape(d, d).copy()).to(dev)
        acc = {t: {'n': np.zeros(2), 'rr': np.zeros(2), 'cand': np.zeros(2), 'cum': np.zeros((2, K))}
               for t in todo}
        for si, side in enumerate(('tail', 'head')):
            if side == 'tail':
                keys, vals, Meff, pool = allht[:, 0], allht[:, 1], Mr, pools['tail']
            else:
                keys, vals, Meff, pool = allht[:, 1], allht[:, 0], Mr.T.contiguous(), pools['head']
            fcodes_t = torch.as_tensor(
                np.unique(keys.astype(np.int64) * np.int64(num_ent) + vals.astype(np.int64)), device=dev)
            C_ = pool.numel()
            chunk = int(max(64, min(a.chunk, a.gather_budget // (min(K, C_) * d))))
            for t in todo:                                   # one set in RAM at a time
                v = load_pairs(a, t, r)
                qe = v[:, 0] if side == 'tail' else v[:, 1]
                te = v[:, 1] if side == 'tail' else v[:, 0]
                gen = torch.Generator(device=dev)
                tag_idx = 0 if t == 'real' else int(t[-2:]) + 1
                gen.manual_seed(a.seed * 1000003 + r * 131 + K * 7 + si + 7919 * tag_idx)
                rk, mc, _ = cm.rank_candidates(torch, dev, ent_t, Meff, qe, te, fcodes_t, pool, num_ent,
                                               K, chunk, gen, a.tile)
                idx = np.clip(np.ceil(rk).astype(np.int64), 1, K + 1)
                cnt = np.bincount(idx, minlength=K + 2)
                A = acc[t]
                A['n'][si] = len(rk); A['rr'][si] = (1.0 / rk).sum(); A['cand'][si] = mc
                A['cum'][si] = np.cumsum(cnt[1:K + 1])
                del v, qe, te
            del fcodes_t
        for t in todo:
            os.makedirs(os.path.dirname(res_path(a, t, r)), exist_ok=True)
            np.savez(res_path(a, t, r), **acc[t])
        del allht


def hk(cum, k, K, n):
    return float(n) if k >= K + 1 else float(cum[k - 1])


def aggregate(a, rels, names, cm):
    K = a.K; ks = np.arange(1, K + 1)
    out = os.path.join(a.out_dir, f'results_K{K}'); os.makedirs(out, exist_ok=True)
    seed_rows, rel_rows, cum_rows = [], [], []
    rand_cum_real = None
    for tag in tags_of(a):
        n_tot, rr_tot, cum_tot = 0.0, 0.0, np.zeros(K)
        rand_rr, rand_cum, cand_w, rel_mrr, miss = 0.0, np.zeros(K), 0.0, [], 0
        for r in rels:
            f = res_path(a, tag, r)
            if not os.path.exists(f):
                miss += 1; continue
            z = np.load(f)
            n = z['n']; cum = z['cum'].sum(0); nn = n.sum()
            rr_ = sum(cm.rand_mrr(z['cand'][i] + 1) * n[i] for i in range(2))
            rc = sum(n[i] * np.minimum(ks, z['cand'][i] + 1) / (z['cand'][i] + 1) for i in range(2))
            mrr = z['rr'].sum() / nn
            rel_rows.append({'tag': tag, 'rel': r, 'relation': names.get(r, '?'), 'n': int(nn), 'MRR': mrr,
                             'H@1': hk(cum, 1, K, nn) / nn, 'H@3': hk(cum, 3, K, nn) / nn,
                             'H@10': hk(cum, 10, K, nn) / nn,
                             'mean_candidates': float((z['cand'] * n).sum() / nn), 'random_MRR': rr_ / nn})
            n_tot += nn; rr_tot += z['rr'].sum(); cum_tot += cum; rand_rr += rr_; rand_cum += rc
            cand_w += (z['cand'] * n).sum(); rel_mrr.append(mrr)
        if miss or not n_tot:
            print(f'WARNING: {tag} incomplete ({miss} relations missing) -- excluded'); continue
        row = {'tag': tag, 'n': int(n_tot), 'MRR': rr_tot / n_tot, 'macro_MRR': float(np.mean(rel_mrr)),
               'mean_candidates': cand_w / n_tot, 'random_MRR': rand_rr / n_tot}
        for k in (1, 3, 10):
            row[f'H@{k}'] = hk(cum_tot, k, K, n_tot) / n_tot
            row[f'random_H@{k}'] = (rand_cum[min(k, K) - 1] / n_tot) if k <= K else 1.0
        seed_rows.append(row)
        for k in ks:
            cum_rows.append({'tag': tag, 'k': int(k), 'hits': cum_tot[k - 1] / n_tot})
        if tag == 'real':
            rand_cum_real = rand_cum / n_tot
    if rand_cum_real is not None:
        for k in ks:
            cum_rows.append({'tag': 'random', 'k': int(k), 'hits': float(rand_cum_real[k - 1])})

    def write(fn, rs):
        if rs:
            with open(os.path.join(out, fn), 'w', newline='') as fh:
                w = csv.DictWriter(fh, fieldnames=list(rs[0])); w.writeheader(); w.writerows(rs)
    write('per_seed_summary.csv', seed_rows); write('cumulative_hits.csv', cum_rows)
    write('per_relation_all.csv', rel_rows)
    json.dump({'args': vars(a), 'tags_scored': [r_['tag'] for r_ in seed_rows], 'time': time.strftime('%F %T'),
               'numpy': np.__version__, 'python': platform.python_version(),
               'sampling': 'K distinct type-compatible candidates per query, known positives+target excluded, '
                           'average rank, full-pool fallback if 2K > pool'},
              open(os.path.join(out, 'd2_metadata.json'), 'w'), indent=2, default=str)
    print(f"\n{'tag':<18}{'n':>13}{'MRR':>9}{'H@1':>8}{'H@3':>8}{'H@10':>8}{'macroMRR':>10}{'randMRR':>9}")
    for r_ in seed_rows:
        if r_['tag'] in ('real', f'shuffle_seed{a.seed0:02d}'):
            print(f"{r_['tag']:<18}{r_['n']:>13,}{r_['MRR']:>9.4f}{r_['H@1']:>8.4f}{r_['H@3']:>8.4f}"
                  f"{r_['H@10']:>8.4f}{r_['macro_MRR']:>10.4f}{r_['random_MRR']:>9.4f}")
    nulls = [r_ for r_ in seed_rows if r_['tag'] != 'real']
    if nulls:
        print(f"null mean over {len(nulls)} sets: MRR {np.mean([x['MRR'] for x in nulls]):.4f}  "
              f"H@10 {np.mean([x['H@10'] for x in nulls]):.4f}")
    print('wrote', out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--c_script', default=os.path.join(HERE, 'sampled_ranking_engine.py'),
                   help='sampled type-compatible ranking engine')
    p.add_argument('--work', required=True,
                   help='Part A cache: all_{r}.npy, type_code.npy')
    p.add_argument('--d1_dir', required=True, help='output directory produced by R1')
    p.add_argument('--out_dir', required=True, help='directory for scored ranks and summaries')
    p.add_argument('--data_path', required=True)
    p.add_argument('--model_path', required=True)
    p.add_argument('--relations', default='relation_final.dict')
    p.add_argument('--K', type=int, default=16)
    p.add_argument('--n_seeds', type=int, default=30)
    p.add_argument('--seed0', type=int, default=0)
    p.add_argument('--seed', type=int, default=0, help='candidate-sampling seed')
    p.add_argument('--hidden_dim', type=int, default=64)
    p.add_argument('--gpus', default='0,1')
    p.add_argument('--chunk', type=int, default=200_000)
    p.add_argument('--gather_budget', type=int, default=200_000_000)
    p.add_argument('--tile', type=int, default=1 << 26)
    p.add_argument('--only_rel', default=None)
    p.add_argument('--force', action='store_true')
    p.add_argument('--aggregate_only', action='store_true')
    a = p.parse_args()
    a.entity_npy = sorted(glob.glob(os.path.join(a.model_path, '*entity.npy')), key=len)[0]
    a.relation_npy = sorted(glob.glob(os.path.join(a.model_path, '*relation.npy')), key=len)[0]

    names = {}
    for l in open(os.path.join(a.data_path, a.relations)):
        i, n = l.rstrip('\n').split('\t')[:2]; names[int(i)] = n
    R_ = real_arrays(a)
    rels = [int(r) for r in np.flatnonzero(np.diff(R_['off']))]
    if a.only_rel:
        keep = {int(x) for x in a.only_rel.split(',')}; rels = [r for r in rels if r in keep]
    if not rels:
        sys.exit('no D1 output found -- run D1 first')
    miss = [t for t in tags_of(a) if not available(a, t)]
    if miss:
        print(f'WARNING: {len(miss)} sets not available from D1 (no .DONE): {miss[:3]}...')
    cm = load_mod(a.c_script, 'cmod')

    if not a.aggregate_only:
        sizes = {r: int(R_['off'][r + 1] - R_['off'][r]) for r in rels}
        gpus = [int(g) for g in a.gpus.split(',')]
        load, shards = [0.0] * len(gpus), [[] for _ in gpus]
        for r in sorted(rels, key=lambda r: -sizes[r]):
            i = min(range(len(gpus)), key=lambda j: load[j]); shards[i].append(r); load[i] += sizes[r]
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
            sys.exit('worker failed; rerun (finished work is skipped)')
        print(f'scoring finished in {time.time() - t0:.0f}s')
    aggregate(a, rels, names, cm)


if __name__ == '__main__':
    main()
