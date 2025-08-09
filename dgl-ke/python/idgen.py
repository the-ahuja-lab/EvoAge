import pandas as pd
import os

data_dir = '../data/wikimedia'
output_dir = data_dir  # can be different if you want

# Read all files
def load_data(file):
    return pd.read_csv(os.path.join(data_dir, file), sep='\t', header=None, names=['head', 'rel', 'tail'])

train = load_data('train.tsv')
valid = load_data('valid.tsv')
test = load_data('test.tsv')

# Combine all for unique entity/relation extraction
all_data = pd.concat([train, valid, test])

# Generate entity and relation vocabularies
entities = pd.Series(pd.concat([all_data['head'], all_data['tail']]).unique()).sort_values().reset_index(drop=True)
relations = pd.Series(all_data['rel'].unique()).sort_values().reset_index(drop=True)

# Create dictionaries
entity2id = {e: i for i, e in enumerate(entities)}
relation2id = {r: i for i, r in enumerate(relations)}

# Save to .dict files
entities.to_csv(os.path.join(output_dir, 'entities.dict'), sep='\t', index=False, header=False)
relations.to_csv(os.path.join(output_dir, 'relations.dict'), sep='\t', index=False, header=False)

# Function to convert a file to ID format
def convert_to_ids(df):
    df['head'] = df['head'].map(entity2id)
    df['rel'] = df['rel'].map(relation2id)
    df['tail'] = df['tail'].map(entity2id)
    return df

# Convert and save
convert_to_ids(train).to_csv(os.path.join(output_dir, 'train.txt'), sep='\t', index=False, header=False)
convert_to_ids(valid).to_csv(os.path.join(output_dir, 'valid.txt'), sep='\t', index=False, header=False)
convert_to_ids(test).to_csv(os.path.join(output_dir, 'test.txt'), sep='\t', index=False, header=False)

print("✅ Preprocessing complete. Files generated:")
print("- entities.dict")
print("- relations.dict")
print("- train.txt / valid.txt / test.txt")
