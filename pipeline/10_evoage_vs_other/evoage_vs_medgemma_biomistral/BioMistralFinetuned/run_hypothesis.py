import os
import re
import argparse
import pandas as pd
from openai import OpenAI

# ==========================================================
# Command Line Argument Parsing
# ==========================================================
parser = argparse.ArgumentParser(description="Evaluate hypotheses using local LLM server.")
parser.add_argument(
    "--output-dir", 
    type=str, 
    default=".", 
    help="Target directory to save the output CSV file."
)
parser.add_argument(
    "--server-url", 
    type=str, 
    default="http://127.0.0.1:50000/v1", 
    help="Base URL for OpenAI compatible SGLang server."
)
args = parser.parse_args()

# Ensure output directory exists
os.makedirs(args.output_dir, exist_ok=True)

# ==========================================================
# Load Data & Setup Prompts
# ==========================================================
input_file = "../All_Hypothesis_fixed_with_ent.csv"

# Load hypotheses dataset
if not os.path.exists(input_file):
    # Search in parent directories if executing from subfolder
    if os.path.exists(os.path.join("..", input_file)):
        input_file = os.path.join("..", input_file)
    elif os.path.exists(os.path.join("..", "..", input_file)):
        input_file = os.path.join("..", "..", input_file)
    else:
        raise FileNotFoundError(f"Could not find input file '{input_file}'.")

# Read CSV using pandas. Column names are stripped because a few carry a
# trailing space in the source file (e.g. "Journal ").
df = pd.read_csv(input_file)
df.columns = df.columns.str.strip()

VERDICTS = ["strong_support", "support", "partial_support", "weak_support", "no_support"]

# Step 1: Prompt asking for Verdict only
PROMPT_1_TEMPLATE = """You are a Chief Scientific Reviewer evaluating a biological hypothesis. Evaluate the hypothesis using only established biomedical knowledge -- known mechanisms, pathways, gene/protein function, and documented findings.

## Verdict Criteria
* strong_support: the hypothesis describes a mechanism that is
  well-established and widely documented -- the kind of relationship you
  would find stated plainly in a textbook or a well-replicated body of
  literature - and nothing you know of contradicts it.
* support: the mechanism is documented in the literature and you are
  confident it is real, but it is not textbook-level canonical -- it rests
  on a specific study or a modest body of work rather than a
  well-replicated consensus, and nothing you know of contradicts it.
* partial_support: the hypothesis is broadly consistent with known biology
  and has real grounding, but part of the proposed mechanism is not
  directly confirmed -- it rests on a reasonable extrapolation, an indirect
  finding, or a step that hasn't been directly studied.
* weak_support: the hypothesis is plausible and nothing contradicts it, but
  there is little or no specific documented evidence for it -- your
  reasoning is mostly generic biological plausibility rather than a
  documented finding.
* no_support: established knowledge directly contradicts the hypothesis, or
  you are not aware of any plausible biological basis for what it proposes.
If unsure between two levels, pick the lower one.

HYPOTHESIS TO EVALUATE: {hypothesis_text}

Reply with ONLY one of the verdicts listed above.
VERDICT:"""

# Step 2: Prompt asking for Explanation
PROMPT_2_TEXT = "Now provide a concise 2 to 3 sentence scientific explanation justifying your verdict based on known mechanisms, pathways, or evidence."

client = OpenAI(api_key="EMPTY", base_url=args.server_url)

# Helper function to run the 2-step evaluation pipeline for a single hypothesis text
def evaluate_hypothesis(hypothesis_text, idx, tag=""):
    if pd.isna(hypothesis_text) or not str(hypothesis_text).strip():
        return "N/A", "N/A"

    # --- STEP 1: Ask for Verdict ---
    prompt1 = PROMPT_1_TEMPLATE.format(hypothesis_text=hypothesis_text)
    messages = [{"role": "user", "content": prompt1}]

    try:
        response1 = client.chat.completions.create(
            model="default",
            messages=messages,
            temperature=0,
            max_tokens=20
        )
        raw_verdict = response1.choices[0].message.content.strip()
    except Exception as e:
        print(f"[{idx}/{len(df)}] Error during Step 1 API call ({tag}): {e}")
        raw_verdict = "ERROR"

    # Clean/extract verdict string
    verdict_match = re.search(r"(strong_support|support|partial_support|weak_support|no_support)", raw_verdict, re.IGNORECASE)
    extracted_verdict = verdict_match.group(1).lower() if verdict_match else raw_verdict

    # --- STEP 2: Ask for Explanation ---
    messages.append({"role": "assistant", "content": raw_verdict})
    messages.append({"role": "user", "content": PROMPT_2_TEXT})

    try:
        response2 = client.chat.completions.create(
            model="default",
            messages=messages,
            temperature=0,
            max_tokens=300
        )
        explanation = response2.choices[0].message.content.strip()
    except Exception as e:
        print(f"[{idx}/{len(df)}] Error during Step 2 API call ({tag}): {e}")
        explanation = "ERROR"

    print(f"[{idx}/{len(df)}] {tag} Verdict: {extracted_verdict} | Text: {str(hypothesis_text)[:35]}...")
    return extracted_verdict, explanation


# ==========================================================
# Execution Loop
# ==========================================================
right_verdicts = []
right_explanations = []
inverse_verdicts = []
inverse_explanations = []

print(f"Starting evaluation of {len(df)} rows (Right & Inverse Hypotheses)...")

for idx, row in df.iterrows():
    # Evaluate Right Hypothesis
    r_verdict, r_exp = evaluate_hypothesis(row.get("Right Hypothesis"), idx + 1, tag="Right")
    right_verdicts.append(r_verdict)
    right_explanations.append(r_exp)

    # Evaluate Inverse Hypothesis
    i_verdict, i_exp = evaluate_hypothesis(row.get("Inverse Hypothesis"), idx + 1, tag="Inverse")
    inverse_verdicts.append(i_verdict)
    inverse_explanations.append(i_exp)

# Append new evaluation columns to the original DataFrame
df["Right_Hypothesis_Verdict"] = right_verdicts
df["Right_Hypothesis_Explanation"] = right_explanations
df["Inverse_Hypothesis_Verdict"] = inverse_verdicts
df["Inverse_Hypothesis_Explanation"] = inverse_explanations

# Ensure Title, PMID, Journal, Published, DOI exist without throwing KeyErrors if name casing varies
expected_meta_cols = ["Title", "PMID", "Journal", "Published", "DOI"]
missing_cols = [c for c in expected_meta_cols if c not in df.columns]
if missing_cols:
    print(f"Note: The following metadata columns were not found in input CSV: {missing_cols}")

# ==========================================================
# Save Output
# ==========================================================
output_filepath = os.path.join(args.output_dir, "All_Hypothesis_evaluated.csv")

df.to_csv(output_filepath, index=False)
print(f"\nSuccessfully saved results with all metadata columns to: {output_filepath}")