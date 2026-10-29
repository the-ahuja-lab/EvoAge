#!/usr/bin/env python3
"""
Generate full-size, relation-wise, type-preserving shuffled copies of the
EvoAge test set.


See README.md for usage.

"""
import argparse, csv, json, os, platform, sys, time
import numpy as np
import pandas as pd
from tqdm import tqdm

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--data', required=True, help='directory containing KG splits and dictionaries')
ap.add_argument('--train', default='EvoAge_121_12M_KG_train_90.txt')
ap.add_argument('--valid', default='EvoAge_121_12M_KG_valid_10.txt')
ap.add_argument('--test', default='EvoAge_1to1_KG_test_10_shared.txt')
ap.add_argument('--ent_dict', default='entities_final_Ntype_updated.dict')
ap.add_argument('--rel_dict', default='relation_final.dict')
ap.add_argument('--type_col', type=int, default=2)
ap.add_argument('--source', choices=['cache', 'txt'], default='cache')
ap.add_argument('--work', default=None,
                help='Part A cache (used when --source cache)')
ap.add_argument('--out', required=True, help='output directory for shuffled sets and metadata')
ap.add_argument('--n_seeds', type=int, default=30)
ap.add_argument('--seed0', type=int, default=0)
ap.add_argument('--seed', type=int, default=0, help='seed of the optional --cap subsample')
ap.add_argument('--cap', type=int, default=0, help='max test rows per relation (0 = full test set)')
ap.add_argument('--rounds', type=int, default=100, help='repair rounds (first half stage 1, rest stage 2)')
ap.add_argument('--chunk', type=int, default=2_000_000)
ap.add_argument('--only_rel', default=None, help='comma list (smoke tests)')
ap.add_argument('--no_npz', action='store_true', help='skip .npz copies (saves ~1 GB per seed)')
ap.add_argument('--delete_pieces', action='store_true')
a = ap.parse_args()
if a.source == 'cache' and not a.work:
    ap.error('--work is required when --source cache')

P = lambda *x: os.path.join(a.out, *x)
D = lambda name: os.path.join(a.data, name)
for d in (a.out, P('known'), P('pieces')):
    os.makedirs(d, exist_ok=True)
seeds = list(range(a.seed0, a.seed0 + a.n_seeds))
only = {int(x) for x in a.only_rel.split(',')} if a.only_rel else None


# ------------------------------------------------------------------ dictionaries
def load_dict(path, type_col=None):
    use = [0] if type_col is None else [0, type_col]
    dt = {0: np.int64} if type_col is None else {0: np.int64, type_col: 'category'}
    df = pd.read_csv(path, sep='\t', header=None, usecols=use, dtype=dt,
                     keep_default_na=False, quoting=3, engine='c')
    df = df.sort_values(0).reset_index(drop=True)
    if not np.array_equal(df[0].to_numpy(), np.arange(len(df))):
        raise ValueError(f'IDs in {path} must be consecutive from 0')
    return df


edf, rdf = load_dict(D(a.ent_dict), a.type_col), load_dict(D(a.rel_dict))
E, R = len(edf), len(rdf)
etype = edf[a.type_col].cat.codes.to_numpy().astype(np.int32)
if (etype < 0).any():
    raise ValueError('some entities have no type')
del edf, rdf
encode = lambda h, t: h.astype(np.int64) * np.int64(E) + t.astype(np.int64)


def is_known(codes, known):
    if len(known) == 0:
        return np.zeros(len(codes), dtype=bool)
    pos = np.searchsorted(known, codes)
    return (pos < len(known)) & (known[np.minimum(pos, len(known) - 1)] == codes)


def read_triples(path):
    for ch in pd.read_csv(path, sep='\t', header=None, dtype=np.int64, usecols=[0, 1, 2],
                          chunksize=a.chunk, quoting=3, engine='c'):
        h, r, t = ch[0].to_numpy(), ch[1].to_numpy(), ch[2].to_numpy()
        ok = (h >= 0) & (h < E) & (r >= 0) & (r < R) & (t >= 0) & (t < E)
        if not ok.all():
            raise ValueError(f'{path}: {(~ok).sum():,} triples have out-of-range ids')
        yield h, r, t


# ------------------------------------------------------------------ step 1: real test + known pairs
def cap_rows(n, r):
    if a.cap and n > a.cap:
        return np.sort(np.random.default_rng([a.seed, r]).choice(n, a.cap, replace=False))
    return None


def build_inputs():
    real_f, known_done, meta_f = P('real.npz'), P('known', 'KNOWN_DONE'), P('real_meta.json')
    if os.path.exists(real_f) and os.path.exists(known_done):
        m = json.load(open(meta_f))
        if (m['cap'], m['source'], m['only']) != (a.cap, a.source, a.only_rel):
            sys.exit(f'existing inputs were built with {m}; use a fresh --out directory')
        print('inputs already built -- reusing'); return
    Hs, Rs, Ts = [], [], []
    if a.source == 'cache':
        rels = [r for r in range(R) if os.path.exists(os.path.join(a.work, f'test_{r}.npy'))
                and (only is None or r in only)]
        for r in tqdm(rels, desc='real test + known (cache)'):
            te = np.load(os.path.join(a.work, f'test_{r}.npy'))
            sel = cap_rows(len(te), r)
            te = te[sel] if sel is not None else te
            Hs.append(te[:, 0].astype(np.int32)); Ts.append(te[:, 1].astype(np.int32))
            Rs.append(np.full(len(te), r, np.int32))
            al = np.load(os.path.join(a.work, f'all_{r}.npy'))
            np.save(P('known', f'rel{r}.npy'), np.unique(encode(al[:, 0], al[:, 1])))
        H, Rr, T = np.concatenate(Hs), np.concatenate(Rs), np.concatenate(Ts)
    else:
        h_, r_, t_ = [], [], []
        for h, r, t in tqdm(read_triples(D(a.test)), desc='read full test'):
            h_.append(h.astype(np.int32)); r_.append(r.astype(np.int32)); t_.append(t.astype(np.int32))
        H, Rr, T = np.concatenate(h_), np.concatenate(r_), np.concatenate(t_)
        order = np.argsort(Rr, kind='stable'); H, Rr, T = H[order], Rr[order], T[order]
        off = np.r_[0, np.cumsum(np.bincount(Rr, minlength=R))]
        keep = np.ones(len(H), bool)
        for r in range(R):
            n = off[r + 1] - off[r]
            if n and (only is None or r in only):
                sel = cap_rows(n, r)
                if sel is not None:
                    m = np.zeros(n, bool); m[sel] = True; keep[off[r]:off[r + 1]] = m
            elif n:
                keep[off[r]:off[r + 1]] = False
        H, Rr, T = H[keep], Rr[keep], T[keep]
        raw = {r: P('known', f'rel{r}.raw') for r in range(R)}
        for f in raw.values():
            if os.path.exists(f): os.remove(f)
        for fn in (a.train, a.valid, a.test):
            for h, r, t in tqdm(read_triples(D(fn)), desc=f'index {fn}'):
                o = np.argsort(r, kind='stable'); rs = r[o]
                b = np.r_[0, np.flatnonzero(np.diff(rs)) + 1, len(rs)]
                for lo, hi in zip(b[:-1], b[1:]):
                    rid = int(rs[lo])
                    with open(raw[rid], 'ab') as fh:
                        encode(h[o[lo:hi]], t[o[lo:hi]]).tofile(fh)
        for r in tqdm(range(R), desc='finalize known'):
            if os.path.exists(raw[r]):
                np.save(P('known', f'rel{r}.npy'), np.unique(np.fromfile(raw[r], dtype=np.int64)))
                os.remove(raw[r])
    np.savez(real_f, h=H, r=Rr, t=T)
    json.dump({'cap': a.cap, 'source': a.source, 'only': a.only_rel, 'n': int(len(H))}, open(meta_f, 'w'))
    open(known_done, 'w').write('ok')
    print(f'real test rows: {len(H):,}')


# ------------------------------------------------------------------ step 2: shuffle one relation / seed
def strat_shuffle(x, strata, rng):
    out = x.copy()
    for idx in strata:
        if len(idx) > 1:
            out[idx] = x[idx[rng.permutation(len(idx))]]
    return out


def redraw(out, pos, types_at, src, rng):
    for ty in np.unique(types_at[pos]):
        sel = pos[types_at[pos] == ty]
        s = src[ty]
        out[sel] = s[rng.integers(0, len(s), len(sel))]


def make_ctx(Hr, Tr):
    th, tt = etype[Hr], etype[Tr]
    uh, ut = np.unique(th), np.unique(tt)
    return {'th': th, 'tt': tt,
            'h_strata': [np.flatnonzero(th == ty) for ty in uh],
            't_strata': [np.flatnonzero(tt == ty) for ty in ut],
            'h_obs': {ty: Hr[th == ty] for ty in uh}, 't_obs': {ty: Tr[tt == ty] for ty in ut},
            'h_pool': None, 't_pool': None, 'uh': uh, 'ut': ut}


def shuffle_one(Hr, Tr, known, c, seed, rid):
    rng = np.random.default_rng(np.random.SeedSequence([seed, rid, 12345]))
    sh, st = strat_shuffle(Hr, c['h_strata'], rng), strat_shuffle(Tr, c['t_strata'], rng)
    bad = np.flatnonzero(is_known(encode(sh, st), known)); first = int(bad.size)
    for att in range(a.rounds):
        if not bad.size:
            break
        ch = rng.random(len(bad)) < 0.5
        if att < a.rounds // 2:
            redraw(sh, bad[ch], c['th'], c['h_obs'], rng); redraw(st, bad[~ch], c['tt'], c['t_obs'], rng)
        else:
            if c['h_pool'] is None:
                c['h_pool'] = {ty: np.flatnonzero(etype == ty).astype(np.int32) for ty in c['uh']}
                c['t_pool'] = {ty: np.flatnonzero(etype == ty).astype(np.int32) for ty in c['ut']}
            redraw(sh, bad[ch], c['th'], c['h_pool'], rng); redraw(st, bad[~ch], c['tt'], c['t_pool'], rng)
        bad = bad[is_known(encode(sh[bad], st[bad]), known)]
    still = int(is_known(encode(sh, st), known).sum())            # full verification
    tviol = int((etype[sh] != c['th']).sum() + (etype[st] != c['tt']).sum())
    if still or tviol:
        raise RuntimeError(f'relation {rid} seed {seed}: {still} known and {tviol} type-invalid rows remain '
                           f'(increase --rounds or inspect this relation)')
    changed = float(np.mean((sh != Hr) | (st != Tr)))
    return np.column_stack([sh, st]).astype(np.int32), \
        {'seed': seed, 'rel': rid, 'n': int(len(Hr)), 'first_real': first, 'still_real': still,
         'type_violations': tviol, 'frac_rows_changed': changed}


# ------------------------------------------------------------------ main
build_inputs()
z = np.load(P('real.npz'))
H, Rr, T = z['h'], z['r'], z['t']
N = len(H)
counts = np.bincount(Rr, minlength=R)
off = np.r_[0, np.cumsum(counts)]
rels = [r for r in range(R) if counts[r] > 0]
piece = lambda s, r: P('pieces', f'seed{s:02d}', f'rel{r}.npy')
pjson = lambda s, r: P('pieces', f'seed{s:02d}', f'rel{r}.json')
for s in seeds:
    os.makedirs(P('pieces', f'seed{s:02d}'), exist_ok=True)

type_rows = []
for r in tqdm(rels, desc='shuffle relations'):
    todo = [s for s in seeds if not (os.path.exists(piece(s, r)) and os.path.exists(pjson(s, r)))]
    Hr, Tr = H[off[r]:off[r + 1]], T[off[r]:off[r + 1]]
    c = make_ctx(Hr, Tr)
    type_rows.append({'rel': r, 'n': len(Hr), 'n_head_types': len(c['uh']), 'n_tail_types': len(c['ut'])})
    if not todo:
        continue
    known = np.load(P('known', f'rel{r}.npy'))
    if not is_known(encode(Hr, Tr), known).all():
        raise RuntimeError(f'relation {r}: some real test triples are missing from the known set '
                           f'(source/cache mismatch)')
    for s in todo:
        out, st = shuffle_one(Hr, Tr, known, c, s, r)
        np.save(piece(s, r), out); json.dump(st, open(pjson(s, r), 'w'))
    del known, c
with open(P('relation_types.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['rel', 'n', 'n_head_types', 'n_tail_types']); w.writeheader(); w.writerows(type_rows)

# ---- assemble per-seed full files
for s in tqdm(seeds, desc='assemble seeds'):
    tag = f'shuffle_seed{s:02d}'
    if os.path.exists(P(tag + '.DONE')):
        continue
    mh = np.lib.format.open_memmap(P(tag + '_h.npy.tmp'), mode='w+', dtype=np.int32, shape=(N,))
    mt = np.lib.format.open_memmap(P(tag + '_t.npy.tmp'), mode='w+', dtype=np.int32, shape=(N,))
    for r in rels:
        x = np.load(piece(s, r))
        if len(x) != off[r + 1] - off[r]:
            raise RuntimeError(f'seed {s} rel {r}: row count mismatch')
        mh[off[r]:off[r + 1]] = x[:, 0]; mt[off[r]:off[r + 1]] = x[:, 1]
    mh.flush(); mt.flush(); del mh, mt
    os.replace(P(tag + '_h.npy.tmp'), P(tag + '_h.npy')); os.replace(P(tag + '_t.npy.tmp'), P(tag + '_t.npy'))
    if not a.no_npz:
        np.savez(P(tag + '.npz'), h=np.load(P(tag + '_h.npy')), t=np.load(P(tag + '_t.npy')))
    open(P(tag + '.DONE'), 'w').write('ok')
if a.delete_pieces:
    import shutil; shutil.rmtree(P('pieces'), ignore_errors=True)

# ---- summary
rows = [json.load(open(pjson(s, r))) for s in seeds for r in rels if os.path.exists(pjson(s, r))]
with open(P('shuffle_summary.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['seed', 'rel', 'n', 'first_real', 'still_real', 'type_violations',
                                       'frac_rows_changed']); w.writeheader(); w.writerows(rows)
clean = all(r_['still_real'] == 0 and r_['type_violations'] == 0 for r_ in rows) and len(rows) == len(seeds) * len(rels)
print(f"\n{'seed':>5}{'rows':>14}{'first_real':>14}{'still_real':>12}{'type_viol':>11}{'changed':>9}")
for s in seeds:
    rs = [r_ for r_ in rows if r_['seed'] == s]
    if rs:
        n = sum(r_['n'] for r_ in rs)
        print(f"{s:>5}{n:>14,}{sum(r_['first_real'] for r_ in rs):>14,}{sum(r_['still_real'] for r_ in rs):>12,}"
              f"{sum(r_['type_violations'] for r_ in rs):>11,}{sum(r_['frac_rows_changed'] * r_['n'] for r_ in rs) / n:>9.4f}")
multi = [t for t in type_rows if t['n_head_types'] > 1 or t['n_tail_types'] > 1]
json.dump({'args': vars(a), 'seeds': seeds, 'n_test_rows': int(N), 'n_relations': len(rels),
           'relation_counts': {int(r): int(counts[r]) for r in rels},
           'multi_type_relations': [t['rel'] for t in multi], 'all_clean': bool(clean),
           'completed_at': time.strftime('%F %T'), 'numpy': np.__version__, 'pandas': pd.__version__,
           'python': platform.python_version()}, open(P('d1_metadata.json'), 'w'), indent=2)
print(f'multi-type relations (stratified shuffle mattered): {[t["rel"] for t in multi]}')
print(f'ALL CLEAN: {len(seeds)} sets x {N:,} rows, no known triples, no type violations' if clean
      else 'WARNING: not clean or incomplete')
sys.exit(0 if clean else 1)
