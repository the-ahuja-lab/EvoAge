import re
import pandas as pd
from pathlib import Path

LOGDIR = Path("./eval_logs")

# tag -> (Graph, Ortholog, Split)
ROW_MAP = {
    "EvoAge_1to1":        ("EvoAge",     "1-to-1",  "Testing"),
    "Aging_1to1":         ("Aging",      "1-to-1",  "Testing"),
    "Biomedical_1to1":    ("Biomedical", "1-to-1",  "Testing"),
    "EvoAge_121_12M":     ("EvoAge",     "121_12M", "Testing"),
    "Aging_121_12M":      ("Aging",      "121_12M", "Testing"),
    "Biomedical_121_12M": ("Biomedical", "121_12M", "Testing"),
}

# Desired final row order
ROW_ORDER = [
    "EvoAge_1to1", "Aging_1to1", "Biomedical_1to1",
    "EvoAge_121_12M", "Aging_121_12M", "Biomedical_121_12M",
]

# dglke_eval prints lines like:
# [Test] average MRR: 0.8741
# [Test] average MR: 12.34
# [Test] average HITS@1: 0.6123
# [Test] average HITS@3: 0.8012
# [Test] average HITS@10: 0.9971
# Adjust the regex prefix if your dglke version prints differently.
METRIC_PATTERNS = {
    "MRR":   re.compile(r"MRR[:\s]+([0-9.]+)", re.IGNORECASE),
    "MR":    re.compile(r"\bMR[:\s]+([0-9.]+)", re.IGNORECASE),
    "Hit@1": re.compile(r"HITS@1[:\s]+([0-9.]+)", re.IGNORECASE),
    "Hit@3": re.compile(r"HITS@3[:\s]+([0-9.]+)", re.IGNORECASE),
    "Hit@10":re.compile(r"HITS@10[:\s]+([0-9.]+)", re.IGNORECASE),
}

def parse_log(path: Path) -> dict:
    text = path.read_text(errors="ignore")
    result = {}
    for metric, pattern in METRIC_PATTERNS.items():
        matches = pattern.findall(text)
        result[metric] = float(matches[-1]) if matches else None  # last match = final test result
    return result

rows = []
for tag in ROW_ORDER:
    log_path = LOGDIR / f"{tag}.log"
    graph, ortholog, split = ROW_MAP[tag]
    if not log_path.exists():
        rows.append({"Graph": graph, "Ortholog": ortholog, "Split": split, "Model Type": "RESCAL",
                     "Hit@1": None, "Hit@3": None, "Hit@10": None, "MR": None, "MRR": None})
        print(f"WARNING: missing log for {tag}")
        continue
    metrics = parse_log(log_path)
    rows.append({
        "Graph": graph, "Ortholog": ortholog, "Split": split, "Model Type": "RESCAL",
        "Hit@1": metrics["Hit@1"], "Hit@3": metrics["Hit@3"], "Hit@10": metrics["Hit@10"],
        "MR": metrics["MR"], "MRR": metrics["MRR"],
    })

df = pd.DataFrame(rows, columns=["Graph", "Ortholog", "Split", "Model Type", "Hit@1", "Hit@3", "Hit@10", "MR", "MRR"])
print(df.to_string(index=False))
df.to_csv("rescal_testing_summary.csv", index=False)