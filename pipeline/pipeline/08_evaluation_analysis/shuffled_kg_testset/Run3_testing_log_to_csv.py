####################################################
## convert log to 
####################################################

import re
import pandas as pd

LOG_FILE = '/storage/Arushi/090526_EvoAge/kg_formation/training_3/Shuffled_EvoAge_testing/Store_House/shuffled_test_sets/rescal_eval_all_shuffles.log'

with open(LOG_FILE, 'r') as f:
    log_text = f.read()

# Split on the SHUFFLE_ID start markers
shuffle_blocks = re.split(r'===== SHUFFLE_ID: (\d+) \| SEED: (\d+) \| START:.*?=====', log_text)

records = []
for i in range(1, len(shuffle_blocks), 3):
    shuffle_id = int(shuffle_blocks[i])
    seed = int(shuffle_blocks[i + 1])
    block_text = shuffle_blocks[i + 2]

    mrr_match    = re.search(r'Test average MRR:\s*([\d.eE+-]+)', block_text)
    mr_match     = re.search(r'Test average MR:\s*([\d.eE+-]+)', block_text)
    hits1_match  = re.search(r'Test average HITS@1:\s*([\d.eE+-]+)', block_text)
    hits3_match  = re.search(r'Test average HITS@3:\s*([\d.eE+-]+)', block_text)
    hits10_match = re.search(r'Test average HITS@10:\s*([\d.eE+-]+)', block_text)
    time_match   = re.search(r'Test takes\s*([\d.eE+-]+)\s*seconds', block_text)

    records.append({
        'shuffle_id': shuffle_id,
        'seed': seed,
        'MRR': float(mrr_match.group(1)) if mrr_match else None,
        'MR': float(mr_match.group(1)) if mr_match else None,
        'HITS@1': float(hits1_match.group(1)) if hits1_match else None,
        'HITS@3': float(hits3_match.group(1)) if hits3_match else None,
        'HITS@10': float(hits10_match.group(1)) if hits10_match else None,
        'eval_time_sec': float(time_match.group(1)) if time_match else None,
        'parsed_ok': all([mrr_match, mr_match, hits1_match, hits3_match, hits10_match])
    })

results_df = pd.DataFrame(records).sort_values('shuffle_id').reset_index(drop=True)

failed = results_df[~results_df['parsed_ok']]
if len(failed) > 0:
    print(f"WARNING: {len(failed)} shuffle(s) incomplete/failed to parse:")
    print(failed[['shuffle_id', 'seed']])

# print(results_df)
results_df
out_path = '/storage/Arushi/090526_EvoAge/kg_formation/training_3/Shuffled_EvoAge_testing/Store_House/shuffled_test_sets/rescal_shuffled_metrics.csv'
results_df.to_csv(out_path, index=False)
print(f"\nSaved to: {out_path}")

print("\nSummary across shuffles (null-hypothesis baseline distribution):")
print(results_df[['MRR', 'MR', 'HITS@1', 'HITS@3', 'HITS@10']].describe())
