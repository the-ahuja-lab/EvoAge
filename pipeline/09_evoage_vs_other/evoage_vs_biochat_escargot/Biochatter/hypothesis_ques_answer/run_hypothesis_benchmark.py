"""Run the hypothesis statements from Hypothesis_Questions_to_answer.csv through BioChatter.

Each row's `Right Hypothesis` is submitted to BioChatter, which generates Cypher
against the EvoAge graph, runs it, and phrases an answer. The output CSV keeps
every original column and appends the same five columns used in the earlier
benchmark:

    cypher, n_rows, answer, seconds, error

Note on interpretation: these are hypothesis *statements*, not retrieval
questions. BioChatter is retrieval-only -- it has no scoring and no accept/reject
verdict -- so `n_rows = 0` is the expected outcome whenever a hypothesis asserts
a relationship absent from the graph. That is a result, not a failure of the run.

Usage:
    python run_hypothesis_benchmark.py                # all rows
    python run_hypothesis_benchmark.py --limit 5      # first 5 (smoke test)
    python run_hypothesis_benchmark.py --resume       # continue after interruption
    python run_hypothesis_benchmark.py --column "Inverse Hypothesis"
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import traceback

# The BioChatter wiring lives one directory up.
HERE = os.path.dirname(os.path.abspath(__file__))
BIOCHATTER_DIR = os.path.dirname(HERE)
sys.path.insert(0, BIOCHATTER_DIR)

import evoage_biochatter as E  # noqa: E402

INPUT_CSV = os.path.join(
    os.path.dirname(BIOCHATTER_DIR), "Hypothesis_Questions_to_answer.csv"
)
OUTPUT_CSV = os.path.join(HERE, "biochatter_hypothesis_results.csv")
OUTPUT_MD = os.path.join(HERE, "biochatter_hypothesis_results.md")

EXTRA_FIELDS = ["cypher", "n_rows", "answer", "seconds", "error"]

SUMMARY_PROMPT = (
    "You are assessing a biological hypothesis using results retrieved from the "
    "EvoAge cross-species aging knowledge graph. State only what the retrieved "
    "results support. If the results are empty, say plainly that the knowledge "
    "graph contains no supporting evidence, and do not speculate."
)


# When the graph returns nothing there is no evidence to summarise, so the LLM
# is never asked. Otherwise it answers from its own training data and produces
# confident biology that looks like KG support but is not.
NO_EVIDENCE = (
    "NO EVIDENCE IN KNOWLEDGE GRAPH - the query returned 0 rows. "
    "No model-generated answer was produced, to avoid presenting the LLM's "
    "prior knowledge as knowledge-graph evidence."
)


def ask(agent, question: str, k: int) -> dict:
    """Run one hypothesis, returning the Cypher, row count and phrased answer."""
    documents = agent.get_query_results(question, k=k)
    if not documents:
        return {"cypher": "", "n_rows": 0, "answer": NO_EVIDENCE,
                "error": "no documents returned"}

    cypher = documents[0].metadata.get("cypher_query", "")
    content = documents[0].page_content
    empty = content.startswith("I didn't find any result")

    n_rows = 0
    if not empty:
        match = re.search(r"(\[.*\])\. The query used is:", content, re.DOTALL)
        if match:
            try:
                n_rows = len(json.loads(match.group(1)))
            except json.JSONDecodeError:
                n_rows = -1  # rows returned but unparseable

    # Zero rows -> no LLM call at all. Deterministic, and cheaper.
    if n_rows == 0:
        return {"cypher": cypher, "n_rows": 0, "answer": NO_EVIDENCE, "error": ""}

    conversation = E.conversation_factory()
    conversation.append_system_message(SUMMARY_PROMPT)
    answer, _, _ = conversation.query(
        f"Hypothesis: {question}\n\nRetrieved from the knowledge graph:\n{content}"
    )

    return {"cypher": cypher, "n_rows": n_rows, "answer": answer, "error": ""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--column", default="Right Hypothesis",
                        help="which CSV column holds the statement to submit")
    parser.add_argument("--limit", type=int, help="only process the first N rows")
    parser.add_argument("--k", type=int, default=10, help="rows to keep per query")
    parser.add_argument("--resume", action="store_true",
                        help="skip rows already present in the output CSV")
    args = parser.parse_args()

    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        original_fields = list(reader.fieldnames or [])
        rows = list(reader)

    if args.column not in original_fields:
        raise SystemExit(
            f"column {args.column!r} not found. Available: {original_fields}"
        )

    # Rows are written in input order, so a plain count is enough to resume.
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
    print(f"BioChatter hypothesis run | {len(pending)} rows | column={args.column!r} "
          f"| model={E.MODEL_NAME}")
    agent = E.build_agent()

    new_file = done == 0 or not os.path.exists(OUTPUT_CSV)
    mode = "w" if new_file else "a"
    csv_file = open(OUTPUT_CSV, mode, newline="")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    if new_file:
        writer.writeheader()
    md_file = open(OUTPUT_MD, "w" if new_file else "a")
    if new_file:
        md_file.write("# BioChatter on hypothesis statements (EvoAge graph)\n")

    empty_count = 0
    try:
        for i, row in enumerate(pending, start=done + 1):
            statement = (row.get(args.column) or "").strip()
            title = (row.get("Title") or "")[:60]
            print(f"\n[{i}/{done + len(pending)}] {title}")

            if not statement:
                result = {"cypher": "", "n_rows": 0, "answer": "",
                          "error": f"empty {args.column}"}
                elapsed = 0.0
            else:
                started = time.time()
                try:
                    result = ask(agent, statement, args.k)
                except Exception as exc:  # noqa: BLE001 -- one bad row must not end the run
                    result = {"cypher": "", "n_rows": 0, "answer": "",
                              "error": f"{type(exc).__name__}: {exc}"}
                    traceback.print_exc()
                elapsed = round(time.time() - started, 1)

            if result["n_rows"] == 0 and not result["error"]:
                empty_count += 1

            out = dict(row)
            out.update({
                "cypher": result["cypher"],
                "n_rows": result["n_rows"],
                "answer": result["answer"],
                "seconds": elapsed,
                "error": result["error"],
            })
            writer.writerow(out)
            csv_file.flush()

            md_file.write(
                f"\n## {i}. {row.get('Title', '')}\n\n"
                f"**Hypothesis:** {statement}\n\n"
                f"```cypher\n{result['cypher'] or '(none generated)'}\n```\n\n"
                f"rows: {result['n_rows']}"
                + (f" | error: {result['error']}" if result["error"] else "")
                + f"\n\n{result['answer']}\n"
            )
            md_file.flush()

            print(f"    -> {result['error'] or str(result['n_rows']) + ' rows'} in {elapsed}s")
    finally:
        csv_file.close()
        md_file.close()

    print(f"\nwrote {OUTPUT_CSV}\nwrote {OUTPUT_MD}")
    print(f"rows with no KG evidence: {empty_count}/{len(pending)}")


if __name__ == "__main__":
    main()