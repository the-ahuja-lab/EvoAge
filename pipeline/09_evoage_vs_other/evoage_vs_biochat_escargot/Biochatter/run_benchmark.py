"""Run the EvoAge-vs-BioChatter question set through BioChatter and save results.

Reads ../questions.json, asks each question, and records the generated Cypher,
the rows returned, the prose answer, latency and error state. Writes both a CSV
(for scoring) and a Markdown file (for reading).

Results are flushed after every question, so a long run can be inspected while
still in progress and resumed if interrupted.

Usage:
    python run_benchmark.py                 # all 37 questions
    python run_benchmark.py --tier 1        # one tier
    python run_benchmark.py --tier 4 5      # several tiers
    python run_benchmark.py --ids 31 32     # specific questions
    python run_benchmark.py --resume        # skip questions already in the CSV
"""

import argparse
import csv
import json
import os
import re
import time
import traceback

import evoage_biochatter as E

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = os.path.join(HERE, "..", "questions.json")
RESULTS_DIR = os.path.join(HERE, "results")
CSV_PATH = os.path.join(RESULTS_DIR, "biochatter_results.csv")
MD_PATH = os.path.join(RESULTS_DIR, "biochatter_results.md")

FIELDS = ["id", "tier", "question", "cypher", "n_rows", "answer", "seconds", "error"]


def load_questions(args) -> list[dict]:
    with open(QUESTIONS) as f:
        questions = json.load(f)
    if args.tier:
        questions = [q for q in questions if q["tier"] in args.tier]
    if args.ids:
        questions = [q for q in questions if q["id"] in args.ids]
    return questions


def already_done() -> set[int]:
    if not os.path.exists(CSV_PATH):
        return set()
    with open(CSV_PATH) as f:
        return {int(row["id"]) for row in csv.DictReader(f) if row.get("id")}


def ask(agent, question: str, k: int) -> dict:
    """Run one question, capturing the Cypher and rows rather than printing."""
    documents = agent.get_query_results(question, k=k)
    if not documents:
        return {"cypher": "", "n_rows": 0, "answer": "", "error": "no documents returned"}

    cypher = documents[0].metadata.get("cypher_query", "")
    content = documents[0].page_content
    # DatabaseAgent signals "ran fine but matched nothing" with this phrasing.
    empty = content.startswith("I didn't find any result")

    conversation = E.conversation_factory()
    conversation.append_system_message(
        "You are answering a biomedical question using results retrieved from "
        "the EvoAge cross-species aging knowledge graph. Answer concisely and "
        "only from the provided results. If the results are empty, say so.",
    )
    answer, _, _ = conversation.query(f"Question: {question}\n\nRetrieved:\n{content}")

    # page_content embeds the retrieved rows as a JSON array; parse it back out
    # rather than guessing from the prose.
    n_rows = 0
    if not empty:
        match = re.search(r"(\[.*\])\. The query used is:", content, re.DOTALL)
        if match:
            try:
                n_rows = len(json.loads(match.group(1)))
            except json.JSONDecodeError:
                n_rows = -1  # rows returned, but unparseable

    return {"cypher": cypher, "n_rows": n_rows, "answer": answer, "error": ""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", nargs="*", type=int, help="only these tiers")
    parser.add_argument("--ids", nargs="*", type=int, help="only these question ids")
    parser.add_argument("--k", type=int, default=10, help="rows to keep per question")
    parser.add_argument("--resume", action="store_true", help="skip ids already in the CSV")
    args = parser.parse_args()

    questions = load_questions(args)
    skip = already_done() if args.resume else set()
    questions = [q for q in questions if q["id"] not in skip]
    if not questions:
        print("nothing to run")
        return

    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"BioChatter benchmark | {len(questions)} questions | model={E.MODEL_NAME}")
    agent = E.build_agent()

    new_csv = not os.path.exists(CSV_PATH)
    csv_file = open(CSV_PATH, "a", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    if new_csv:
        writer.writeheader()
    md_file = open(MD_PATH, "a")
    if new_csv:
        md_file.write("# BioChatter results\n")

    for i, item in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] tier {item['tier']} Q{item['id']}: {item['q'][:70]}")
        started = time.time()
        try:
            result = ask(agent, item["q"], args.k)
        except Exception as exc:  # noqa: BLE001 -- one bad question must not end the run
            result = {"cypher": "", "n_rows": 0, "answer": "", "error": f"{type(exc).__name__}: {exc}"}
            traceback.print_exc()
        elapsed = round(time.time() - started, 1)

        row = {
            "id": item["id"],
            "tier": item["tier"],
            "question": item["q"],
            "cypher": result["cypher"],
            "n_rows": result["n_rows"],
            "answer": result["answer"],
            "seconds": elapsed,
            "error": result["error"],
        }
        writer.writerow(row)
        csv_file.flush()

        md_file.write(
            f"\n## Q{item['id']} (tier {item['tier']}) — {elapsed}s\n\n"
            f"**{item['q']}**\n\n"
            f"```cypher\n{result['cypher'] or '(none generated)'}\n```\n\n"
            f"rows: {result['n_rows']}"
            + (f" | error: {result['error']}" if result["error"] else "")
            + f"\n\n{result['answer']}\n",
        )
        md_file.flush()

        status = result["error"] or f"{result['n_rows']} rows"
        print(f"    -> {status} in {elapsed}s")

    csv_file.close()
    md_file.close()
    print(f"\nwrote {CSV_PATH}\nwrote {MD_PATH}")


if __name__ == "__main__":
    main()
