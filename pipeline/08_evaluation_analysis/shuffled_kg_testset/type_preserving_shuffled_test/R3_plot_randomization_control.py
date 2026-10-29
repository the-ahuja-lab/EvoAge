#!/usr/bin/env python3
"""
Plot the randomization-test radar (MRR, Hits@1/3/10): real (red) vs mean of the
type-preserving shuffled sets (blue, faint individual seeds), empirical p-values in the footer,
plus cumulative Hits@k (real vs null mean +/- SD vs random). Saves PNG + PDF + radar_summary.csv.
p = (1 + #(null >= real)) / (n_null + 1)   (one-sided; minimum attainable = 1/(n_null+1))
"""
import argparse, os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

p = argparse.ArgumentParser()
p.add_argument('--results_dir', required=True,
               help='results_K* directory produced by R2')
p.add_argument('--out_dir', default=None)
a = p.parse_args()
out = a.out_dir or a.results_dir
S = pd.read_csv(os.path.join(a.results_dir, 'per_seed_summary.csv'))
Cm = pd.read_csv(os.path.join(a.results_dir, 'cumulative_hits.csv'))
real = S[S.tag == 'real'].iloc[0]; null = S[S.tag != 'real']; nn = len(null)
M = [('MRR', 'MRR'), ('H@1', 'Hits@1'), ('H@3', 'Hits@3'), ('H@10', 'Hits@10')]

rows = []
for col, lab in M:
    pv = (1 + (null[col] >= real[col]).sum()) / (nn + 1)
    rows.append({'metric': lab, 'real': real[col], 'null_mean': null[col].mean(), 'null_sd': null[col].std(ddof=1),
                 'null_min': null[col].min(), 'null_max': null[col].max(),
                 'random': real['random_MRR' if col == 'MRR' else 'random_' + col],
                 'p_empirical': pv, 'n_null': nn})
pd.DataFrame(rows).to_csv(os.path.join(out, 'radar_summary.csv'), index=False)

# ---- radar
ang = np.linspace(0, 2 * np.pi, len(M), endpoint=False).tolist(); ang += ang[:1]
fig = plt.figure(figsize=(7.5, 8)); ax = plt.subplot(111, polar=True)
ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
ax.set_xticks(ang[:-1]); ax.set_xticklabels([l for _, l in M], fontsize=12)
ax.set_ylim(0, 1.24); ax.set_yticks([0.24, 0.49, 0.74, 0.99, 1.24])
ax.set_yticklabels(['0.24', '0.49', '0.74', '0.99', '1.24'], fontsize=8); ax.grid(alpha=.4)
vals = lambda r_: [r_[c] for c, _ in M] + [r_[M[0][0]]]
for _, r_ in null.iterrows():
    ax.plot(ang, vals(r_), color='tab:blue', alpha=.10, lw=.8)
nm = [null[c].mean() for c, _ in M]; nm += nm[:1]
ax.plot(ang, nm, color='tab:blue', lw=2.2, label=f'Randomized, type-preserving (mean of {nn})')
ax.fill(ang, nm, color='tab:blue', alpha=.15)
ax.plot(ang, vals(real), color='tab:red', lw=2.2, label='EvoAge test data')
ax.fill(ang, vals(real), color='tab:red', alpha=.15)
ax.set_title('Randomization Test', fontsize=15, pad=22)
ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.12), fontsize=9)
ptxt = '   '.join(f"{r_['metric']}: p={r_['p_empirical']:.3f}" for r_ in rows)
fig.text(0.5, 0.03, f"Empirical one-sided p (n={nn}; min attainable {1/(nn+1):.3f}):  {ptxt}",
         ha='center', fontsize=9)
fig.subplots_adjust(bottom=0.1, right=0.8)
for ext in ('png', 'pdf'):
    fig.savefig(os.path.join(out, f'radar.{ext}'), dpi=220)
plt.close(fig)

# ---- cumulative hits@k
piv = Cm[Cm.tag.str.startswith('shuffle')].pivot(index='k', columns='tag', values='hits')
rl = Cm[Cm.tag == 'real'].set_index('k').hits; rd = Cm[Cm.tag == 'random'].set_index('k').hits
fig, ax = plt.subplots(figsize=(7, 5))
mu, sd = piv.mean(1), piv.std(1, ddof=1)
ax.plot(rl.index, rl.values, 'o-', color='tab:red', label='EvoAge test data')
ax.plot(mu.index, mu.values, 's-', color='tab:blue', label=f'Randomized, type-preserving (mean ± SD, n={piv.shape[1]})')
ax.fill_between(mu.index, mu - sd, mu + sd, color='tab:blue', alpha=.25)
if len(rd):
    ax.plot(rd.index, rd.values, 'k--', label='random expectation')
ax.set_xlabel('k'); ax.set_ylabel('Hits@k'); ax.set_ylim(0, 1.02); ax.grid(alpha=.3); ax.legend(fontsize=8)
ax.set_title('Cumulative Hits@k')
fig.tight_layout()
for ext in ('png', 'pdf'):
    fig.savefig(os.path.join(out, f'cumulative_hits.{ext}'), dpi=220)
print(pd.DataFrame(rows).round(4).to_string(index=False))
print('wrote', out)
