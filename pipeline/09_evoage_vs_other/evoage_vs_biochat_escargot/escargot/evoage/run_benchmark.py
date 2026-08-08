"""Run the comparison question set through Escargot on the EvoAge graph.

Cypher and row counts are captured by wrapping the graph client's execute()
rather than by parsing logs, so the numbers reflect what actually ran. When
Escargot issues several queries for one question (it branches its graph of
thoughts) every statement is recorded, separated by ' ;; ', and n_rows is the
total across them.

Usage:
    python run_benchmark.py                 # all 37 questions
    python run_benchmark.py --tier 1
    python run_benchmark.py --tier 4 5
    python run_benchmark.py --ids 31 32
    python run_benchmark.py --resume        # skip ids already in the CSV
"""

import argparse
import csv
import json
import os
import time
import traceback

from ask_evoage import build_escargot, clean_cypher

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = os.path.abspath(os.path.join(HERE, "..", "..", "questions.json"))
RESULTS_DIR = os.path.join(HERE, "results")
CSV_PATH = os.path.join(RESULTS_DIR, "escargot_results.csv")
MD_PATH = os.path.join(RESULTS_DIR, "escargot_results.md")

FIELDS = ["id", "tier", "question", "cypher", "n_rows", "answer", "seconds", "error"]


class QueryRecorder:
    """Records the Cypher Escargot actually sends to Neo4j.

    Wraps the gqlalchemy client's execute_and_fetch rather than
    Neo4jClient.execute: the latter's `statement` argument is a step descriptor
    (e.g. "DISEASE"), while the real generated Cypher is the cleaned LLM
    response handed to execute_and_fetch.

    Only statements that parse and return rows are useful for scoring, but
    failures are recorded too so a wrong query is visible rather than blank.
    """

    def __init__(self, graph_client):
        self.graph_client = graph_client
        self._client = graph_client.client
        self._original = self._client.execute_and_fetch
        self.queries: list[str] = []
        self.row_count = 0
        self._client.execute_and_fetch = self._execute_and_fetch

    def _execute_and_fetch(self, query, *args, **kwargs):
        statement = clean_cypher(str(query))
        try:
            rows = list(self._original(query, *args, **kwargs))
        except Exception:
            self.queries.append(f"[FAILED] {statement}")
            raise
        if statement not in [q.replace("[FAILED] ", "") for q in self.queries]:
            self.queries.append(statement)
        self.row_count += len(rows)
        return rows

    def reset(self):
        self.queries = []
        self.row_count = 0

    def restore(self):
        self._client.execute_and_fetch = self._original


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", nargs="*", type=int)
    parser.add_argument("--ids", nargs="*", type=int)
    parser.add_argument("--timeout", type=int, default=300,
                        help="per-question timeout in seconds (Escargot defaults to 120)")
    parser.add_argument("--memory", default="evoage",
                        help="Chroma collection name; keep separate from the AlzKB sanity run")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    questions = load_questions(args)
    skip = already_done() if args.resume else set()
    questions = [q for q in questions if q["id"] not in skip]
    if not questions:
        print("nothing to run")
        return

    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f"Escargot benchmark | {len(questions)} questions | timeout={args.timeout}s")
    escargot = build_escargot()
    recorder = QueryRecorder(escargot.graph_client)

    new_csv = not os.path.exists(CSV_PATH)
    csv_file = open(CSV_PATH, "a", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
    if new_csv:
        writer.writeheader()
    md_file = open(MD_PATH, "a")
    if new_csv:
        md_file.write("# Escargot results (EvoAge graph, deepseek-v4-flash)\n")

    try:
        for i, item in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] tier {item['tier']} Q{item['id']}: {item['q'][:70]}")
            recorder.reset()
            started = time.time()
            answer, error = "", ""
            try:
                answer = escargot.ask(
                    item["q"], debug_level=0, answer_type="natural",
                    timeout=args.timeout,
                    # Dedicated collection: the AlzKB sanity run wrote into
                    # "default", and those summaries leaked AlzKB concepts
                    # (BodyPart, "overexpresses") into EvoAge answers.
                    memory_name=args.memory,
                )
                if isinstance(answer, list):
                    answer = json.dumps(answer)
                answer = str(answer)
                # Escargot returns its timeout message as a normal string.
                if answer.startswith("Timeout occurred"):
                    error = answer
            except Exception as exc:  # noqa: BLE001 -- one bad question must not end the run
                error = f"{type(exc).__name__}: {exc}"
                traceback.print_exc()
            elapsed = round(time.time() - started, 1)

            row = {
                "id": item["id"],
                "tier": item["tier"],
                "question": item["q"],
                "cypher": " ;; ".join(recorder.queries),
                "n_rows": recorder.row_count,
                "answer": answer,
                "seconds": elapsed,
                "error": error,
            }
            writer.writerow(row)
            csv_file.flush()

            md_file.write(
                f"\n## Q{item['id']} (tier {item['tier']}) — {elapsed}s\n\n"
                f"**{item['q']}**\n\n"
                f"```cypher\n{row['cypher'] or '(none captured)'}\n```\n\n"
                f"rows: {row['n_rows']}"
                + (f" | error: {error}" if error else "")
                + f"\n\n{answer}\n",
            )
            md_file.flush()

            print(f"    -> {error or str(row['n_rows']) + ' rows'} in {elapsed}s")
    finally:
        recorder.restore()
        csv_file.close()
        md_file.close()

    print(f"\nwrote {CSV_PATH}\nwrote {MD_PATH}")


if __name__ == "__main__":
    main()
