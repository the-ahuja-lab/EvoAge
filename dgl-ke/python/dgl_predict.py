import subprocess
import json
import os
import uuid
import sys
import csv
sys.stdout.reconfigure(encoding='utf-8')

def dgl_predict(head: str, relation: str, topk: int = 10) -> list:
    # Set paths
    model_path = "../../RotatE_wikimedia_5"
    data_path = "../.."
    entity_dict = f"{data_path}/entities.dict"
    relation_dict = f"{data_path}/relations.dict"

    # Unique filenames
    head_file = f"temp_head_{uuid.uuid4().hex}.list"
    rel_file = f"temp_rel_{uuid.uuid4().hex}.list"
    output_file = f"temp_predict_output_{uuid.uuid4().hex}.tsv"

    # Write head and relation to temp .list files
    with open(head_file, 'w', encoding='utf-8') as f:
        f.write(f"{head}\n")
    with open(rel_file, 'w', encoding='utf-8') as f:
        f.write(f"{relation}\n")

    # Build the command
    cmd = [
        "dglke_predict",
        "--model_path", model_path,
        "--format", "h_r_*",
        "--data_files", head_file, rel_file,
        "--raw_data",
        "--entity_mfile", entity_dict,
        "--rel_mfile", relation_dict,
        "--exec_mode", "all",
        "--topK", str(topk),
        "--score_func", "logsigmoid",
        "--gpu", "0",
        "--output", output_file,
    ]

    try:
        subprocess.run(cmd, check=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Prediction failed:\n{e.stderr or e.stdout}") from e

    # Read results (TSV format)
    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Expected output file not found: {output_file}")

    results = []
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            results.append({
                "head": row["head"],
                "rel": row["rel"],
                "tail": row["tail"],
                "score": float(row["score"]),
            })

    # Clean up temp files
    os.remove(head_file)
    os.remove(rel_file)
    os.remove(output_file)

    return results

# Example call
results = dgl_predict("breast cancer", "Disease_Anatomy", topk=10)
print("First")
print(json.dumps(results, indent=2))
# results = dgl_predict("abroma agusta", "MedicinalPlant_Disease", topk=10)
# print("Second")
# print(json.dumps(results, indent=2))
# print("Third")
# results = dgl_predict("abroma agusta", "MedicinalPlant_PhytoChemical", topk=10)
# print(json.dumps(results, indent=2))