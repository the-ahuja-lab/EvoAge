"""Run the hypothesis statements from Hypothesis_Questions_to_answer.csv through Escargot.

Escargot queries the same EvoAge Neo4j and uses the deepseek-v4-flash
model, so the framework is the only thing that differs between the two runs.

Usage:
    python run_hypothesis_benchmark.py                # all rows
    python run_hypothesis_benchmark.py --limit 3      # smoke test
    python run_hypothesis_benchmark.py --resume       # continue after interruption
    python run_hypothesis_benchmark.py --column "Inverse Hypothesis"
"""

import argparse
import csv
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ESCARGOT_DIR = os.path.dirname(HERE)
EVOAGE_DIR = os.path.join(ESCARGOT_DIR, "evoage")
sys.path.insert(0, EVOAGE_DIR)

from ask_evoage import build_escargot  # noqa: E402
from run_benchmark import QueryRecorder  # noqa: E402

INPUT_CSV = os.path.join(
    os.path.dirname(ESCARGOT_DIR), "Hypothesis_Questions_to_answer.csv"
)
OUTPUT_CSV = os.path.join(HERE, "escargot_hypothesis_results.csv")
OUTPUT_MD = os.path.join(HERE, "escargot_hypothesis_results.md")

EXTRA_FIELDS = ["cypher", "n_rows", "answer", "seconds", "error"]

# Escargot phrases its answer inside its own framework, so unlike the BioChatter
# runner the LLM call cannot be skipped. Instead the text is replaced whenever
# the graph returned nothing: with 0 rows, anything the model says is its own
# training knowledge, not evidence from the knowledge graph. The suppressed text
# is still written to the .md file so it can be inspected.
NO_EVIDENCE = (
    "NO EVIDENCE IN KNOWLEDGE GRAPH - the query returned 0 rows. "
    "Escargot's generated answer was suppressed, to avoid presenting the LLM's "
    "prior knowledge as knowledge-graph evidence. See the .md file for the "
    "suppressed text."
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--column", default="Right Hypothesis",
                        help="which CSV column holds the statement to submit")
    parser.add_argument("--limit", type=int, help="only process the first N rows")
    parser.add_argument("--timeout", type=int, default=1200,
                        help=(
                            "per-hypothesis timeout in seconds. Deliberately generous: "
                            "at 300s, 37%% of hypotheses were cut off while completions "
                            "had a median of 208s, so the cutoff was truncating the "
                            "distribution rather than measuring capability. Latency is "
                            "recorded per row and should be reported as a result."
                        ))
    parser.add_argument("--memory", default="evoage_hypothesis",
                        help="Chroma collection; kept separate from other runs")
    parser.add_argument("--resume", action="store_true",
                        help="skip rows already present in the output CSV")
    args = parser.parse_args()

    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        original_fields = list(reader.fieldnames or [])
        rows = list(reader)

    if args.column not in original_fields:
        raise SystemExit(f"column {args.column!r} not found. Available: {original_fields}")

    # Rows are written in input order, so a count is enough to resume.
    done = 0
    if args.resume and os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, newline="") as f:
            done = sum(1 for _ in csv.DictReader(f))
        print(f"resuming: {done} rows already written")

    pending = rows[done:]
    if args.limit:
        pending = pending[: args.limit]
    if not pending:
        print("nothing to run")
        return

    fieldnames = original_fields + EXTRA_FIELDS
    print(f"Escargot hypothesis run | {len(pending)} rows | column={args.column!r}")
    escargot = build_escargot()
    recorder = QueryRecorder(escargot.graph_client)

    new_file = done == 0 or not os.path.exists(OUTPUT_CSV)
    csv_file = open(OUTPUT_CSV, "w" if new_file else "a", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    if new_file:
        writer.writeheader()
    md_file = open(OUTPUT_MD, "w" if new_file else "a")
    if new_file:
        md_file.write("# Escargot on hypothesis statements (EvoAge graph)\n")

    empty_count = 0
    try:
        for i, row in enumerate(pending, start=done + 1):
            statement = (row.get(args.column) or "").strip()
            print(f"\n[{i}/{done + len(pending)}] {(row.get('Title') or '')[:60]}")

            recorder.reset()
            answer, error, elapsed = "", "", 0.0

            if not statement:
                error = f"empty {args.column}"
            else:
                started = time.time()
                try:
                    answer = escargot.ask(
                        statement, debug_level=0, answer_type="natural",
                        timeout=args.timeout, memory_name=args.memory,
                    )
                    if isinstance(answer, list):
                        answer = json.dumps(answer)
                    answer = str(answer)
                    # Escargot returns its timeout message as an ordinary string.
                    if answer.startswith("Timeout occurred"):
                        error = answer
                except Exception as exc:  # noqa: BLE001 -- one bad row must not end the run
                    error = f"{type(exc).__name__}: {exc}"
                    traceback.print_exc()
                elapsed = round(time.time() - started, 1)

            suppressed = ""
            if recorder.row_count == 0 and not error:
                empty_count += 1
                # Nothing came back from the graph, so the generated text cannot
                # be evidence. Keep it in the .md, not in the results column.
                suppressed, answer = answer, NO_EVIDENCE

            out = dict(row)
            out.update({
                "cypher": " ;; ".join(recorder.queries),
                "n_rows": recorder.row_count,
                "answer": answer,
                "seconds": elapsed,
                "error": error,
            })
            writer.writerow(out)
            csv_file.flush()

            md_file.write(
                f"\n## {i}. {row.get('Title', '')}\n\n"
                f"**Hypothesis:** {statement}\n\n"
                f"```cypher\n{out['cypher'] or '(none captured)'}\n```\n\n"
                f"rows: {out['n_rows']}"
                + (f" | error: {error}" if error else "")
                + f"\n\n{answer}\n"
                + (
                    "\n<details><summary>Suppressed model output (not KG evidence)"
                    f"</summary>\n\n{suppressed}\n\n</details>\n"
                    if suppressed else ""
                )
            )
            md_file.flush()

            print(f"    -> {error or str(out['n_rows']) + ' rows'} in {elapsed}s")
    finally:
        recorder.restore()
        csv_file.close()
        md_file.close()

    print(f"\nwrote {OUTPUT_CSV}\nwrote {OUTPUT_MD}")
    print(f"rows with no KG evidence: {empty_count}/{len(pending)}")


if __name__ == "__main__":
    main()