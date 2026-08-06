#!/usr/bin/env python3
import os
import sys
import re
import json
import glob
import argparse
import itertools
import threading
import pandas as pd
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_args():
    parser = argparse.ArgumentParser(description="Consolidated Answer Resolution Script for KG Evaluation")
    parser.add_argument("--input", required=True, help="Input CSV file path (e.g., judge_results_4_2.csv)")
    parser.add_argument("--output", required=True, help="Output CSV file path (e.g., judge_results_4_2_resolved.csv)")
    parser.add_argument("--type", default="edge", choices=["edge", "node", "all"], help="Filter by target type (edge, node, or all)")
    parser.add_argument("--endpoints", nargs="+", default=["http://127.0.0.1:40000/v1"], help="SGLang judge API endpoint(s)")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel workers for LLM judging")
    parser.add_argument("--save-every", type=int, default=100, help="Save progress every N resolved rows")
    return parser.parse_args()

# =====================================================
# FAST PARSER
# =====================================================
POSITIVE_WORDS = {
    "true", "yes", "yeah", "yep", "yup", "correct", "right", "affirmative", "indeed", "certainly", "absolutely",
}

NEGATIVE_WORDS = {
    "false", "no", "nope", "nah", "incorrect", "wrong", "negative", "never",
}

def parse_answer(text):
    if pd.isna(text):
        return None
    text = str(text).strip()
    if not text:
        return None
    text_lower = text.lower()

    # Common starts of answers
    positive_starts = [
        "yes", "yeah", "yep", "yup", "true", "correct", "indeed", "certainly", "absolutely",
        "the answer is yes", "there is evidence", "evidence suggests",
    ]
    negative_starts = [
        "no", "nope", "nah", "false", "incorrect", "wrong", "negative",
        "the answer is no", "there is no evidence", "no evidence",
    ]

    for p in positive_starts:
        if text_lower.startswith(p):
            return "TRUE"
    for n in negative_starts:
        if text_lower.startswith(n):
            return "FALSE"

    # First-word logic
    cleaned = re.sub(r"^[^a-zA-Z]+", "", text_lower)
    if not cleaned:
        return None
    first_word = cleaned.split()[0]
    if first_word in POSITIVE_WORDS:
        return "TRUE"
    if first_word in NEGATIVE_WORDS:
        return "FALSE"

    return None

# =====================================================
# LLM JUDGE
# =====================================================
def judge_answer(client_getter, question, answer):
    prompt = f"""Question:
{question}

Model Answer:
{answer}

Classify the answer.

Output exactly one token:

TRUE  -> if the answer supports the statement.
FALSE -> if the answer rejects the statement.
OTHER -> if the answer is uncertain, ambiguous, or does not answer the question.

Output only TRUE, FALSE, or OTHER.
"""
    for _ in range(2):  # retry once
        try:
            client = client_getter()
            response = client.chat.completions.create(
                model="default",
                temperature=0,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            raw_result = response.choices[0].message.content.strip()
            result = raw_result.upper().split()[0]
            if result in ("TRUE", "FALSE", "OTHER"):
                return result, raw_result
            return "OTHER", raw_result
        except Exception as e:
            print(f"Judge Error: {e}")
            return "OTHER", f"ERROR: {e}"
    return "OTHER", "Max retries reached"

def main():
    args = parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input path '{args.input}' does not exist.")
        sys.exit(1)

    # Compile JSONL directory or load CSV
    if os.path.isdir(args.input):
        print(f"Input is a directory. Compiling JSONL files from '{args.input}'...")
        jsonl_files = glob.glob(os.path.join(args.input, "**", "*.jsonl"), recursive=True)
        if not jsonl_files:
            # Check flat dir
            jsonl_files = glob.glob(os.path.join(args.input, "*.jsonl"))
            
        if not jsonl_files:
            print(f"Error: No JSONL files found in directory '{args.input}'.")
            sys.exit(1)
            
        print(f"Found {len(jsonl_files)} JSONL file(s). Loading...")
        records = []
        for file_path in jsonl_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))
            except Exception as e:
                print(f"Warning: Failed to read {file_path}: {e}")
                
        df = pd.DataFrame(records)
        print(f"Successfully compiled {len(df):,} records.")
    else:
        print(f"Loading data from CSV file '{args.input}'...")
        df = pd.read_csv(args.input)

    # Clean columns
    df.columns = [c.strip() for c in df.columns]

    # Filter by type
    if args.type != "all":
        if "type" in df.columns:
            df = df[df["type"].astype(str).str.lower() == args.type.lower()].copy()
            print(f"Filtered to type '{args.type}'. Remaining rows: {len(df):,}")
        else:
            print(f"Warning: 'type' column not found. Skipping type filter.")

    if len(df) == 0:
        print("No rows to process after filtering.")
        sys.exit(0)

    # Clean data & remove duplicates by question
    if "question" in df.columns:
        df["question"] = df["question"].astype(str).str.strip()
        original_rows = len(df)
        df = df.drop_duplicates(subset=["question"]).reset_index(drop=True)
        print(f"Removed {original_rows - len(df):,} duplicate questions. Remaining rows: {len(df):,}")
    else:
        print("Warning: 'question' column not found in input.")

    if "model_answer" in df.columns:
        df["model_answer"] = df["model_answer"].astype(str).str.strip()
    elif "answer" in df.columns:
        df["model_answer"] = df["answer"].astype(str).str.strip()
        print("Renamed 'answer' column to 'model_answer' for compatibility.")
    else:
        print("Error: Neither 'model_answer' nor 'answer' column found.")
        sys.exit(1)

    # Initialize OpenAI clients
    clients = [
        OpenAI(api_key="EMPTY", base_url=url, timeout=30)
        for url in args.endpoints
    ]
    client_cycle = itertools.cycle(clients)
    client_lock = threading.Lock()

    def get_client():
        with client_lock:
            return next(client_cycle)

    resolved_answers = [None] * len(df)
    resolution_method = [""] * len(df)
    judge_raw_response = [None] * len(df)

    needs_judge = []

    # First Pass: Local fast rule-based parser
    print("Running local fast parser (Pass 1)...")
    for idx, row in df.iterrows():
        parsed = parse_answer(row["model_answer"])
        if parsed is not None:
            resolved_answers[idx] = parsed
            resolution_method[idx] = "parser"
        else:
            needs_judge.append((idx, str(row.get("question", "")), str(row["model_answer"])))

    print(f"Parser resolved: {sum(x == 'parser' for x in resolution_method):,} rows.")
    print(f"Need LLM judge for {len(needs_judge):,} rows.")

    # Second Pass: Parallel LLM judging
    if needs_judge:
        print(f"Running LLM judge (Pass 2) with {args.workers} workers...")
        completed = 0
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(judge_answer, get_client, q, a): idx
                for idx, q, a in needs_judge
            }
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Judging"):
                idx = futures[future]
                try:
                    label, raw_resp = future.result()
                except Exception as e:
                    label, raw_resp = "OTHER", f"ERROR: {e}"
                
                resolved_answers[idx] = label
                resolution_method[idx] = "llm_judge"
                judge_raw_response[idx] = raw_resp
                
                completed += 1
                if completed % args.save_every == 0:
                    df["resolved_answer"] = resolved_answers
                    df["resolution_method"] = resolution_method
                    df["judge_raw_response"] = judge_raw_response
                    df.to_csv(args.output, index=False)

    # Save final results
    df["resolved_answer"] = resolved_answers
    df["resolution_method"] = resolution_method
    df["judge_raw_response"] = judge_raw_response
    df.to_csv(args.output, index=False)

    print("\nSummary:")
    print(f"Total rows: {len(df):,}")
    print(f"Parser resolved: {sum(x == 'parser' for x in resolution_method):,}")
    print(f"LLM judged: {sum(x == 'llm_judge' for x in resolution_method):,}")
    print(f"Saved: {args.output}")

if __name__ == "__main__":
    main()
