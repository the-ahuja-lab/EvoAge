"""Judge BioChatter's hypothesis answers with the locally hosted MedGemma model.

Takes the hypothesis and the answer BioChatter produced, shows both to MedGemma,
and asks for a single verdict on the same ladder EvoAge's own judge uses:

    strong_support | support | partial_support | weak_support | no_support

The verdict is written back as a new column, `Medgemma_verdict`, alongside a
short `Medgemma_reason` so every verdict can be audited rather than taken on
trust.

Why this exists
---------------
BioChatter returns prose. Prose cannot be scored. To compare BioChatter against
EvoAge on the same 101 hypotheses we need both systems' outputs on one scale, so
the same judge model that grades EvoAge's evidence also grades BioChatter's
answers. Using the identical verdict ladder is what makes the two columns
comparable.

Rubric provenance and neutrality
--------------------------------
The verdict ladder, the sceptical posture, the essential-link test and the
specificity test follow EvoAge's own judge, so that both systems are graded on
one scale. The wording, however, is deliberately SYSTEM-NEUTRAL: it names no
system, and the judge is not told which tool produced the output it is reading.
EvoAge's CURATED-vs-PREDICTED tiering is also removed, since it presupposes a
predictive component that retrieval-only systems do not have; the ladder is
restated purely in terms of what evidence was returned. The identical prompt
can therefore be applied to any system's output without advantaging any of
them, and should be published verbatim alongside the results.

Zero-evidence rule
------------------
When BioChatter's query returned no rows there is, by definition, no evidence,
and the verdict is no_support. This is enforced in code rather than trusted to
the model, because a language model shown an empty result will often reason from
its own training knowledge and award support anyway. Disable with --judge-empty
if you want the model's unconstrained opinion recorded instead.

Usage:
    python medgemma_analyse_biochatter_response.py
    python medgemma_analyse_biochatter_response.py --limit 5
    python medgemma_analyse_biochatter_response.py --resume
    python medgemma_analyse_biochatter_response.py --input other_results.csv
"""

import argparse
import csv
import json
import os
import re
import sys
import time

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(HERE, "biochatter_hypothesis_results.csv")
DEFAULT_OUTPUT = os.path.join(HERE, "biochatter_hypothesis_results_medgemma.csv")

MEDGEMMA_BASE_URL = os.environ.get("MEDGEMMA_BASE_URL", "http://localhost:30001/v1")
MEDGEMMA_API_KEY = os.environ.get("MEDGEMMA_API_KEY", "EMPTY")

VERDICTS = [
    "strong_support",
    "support",
    "partial_support",
    "weak_support",
    "no_support",
]

NEW_FIELDS = ["Medgemma_verdict", "Medgemma_reason"]


# =============================================================================
# PROMPT  -- verdict ladder mirrored from EvoAge's JUDGE_PROMPT
# =============================================================================

JUDGE_PROMPT = """You are an expert scientific reviewer evaluating whether a biological
hypothesis is supported by evidence. Your default posture is skeptical: a
hypothesis earns a verdict, it is not granted one for being coherent or well
written.

You will be shown a biological hypothesis, together with the output of an
automated system that was asked to find evidence for it in a curated
cross-species aging knowledge graph. The output includes the database query the
system ran, how many rows that query returned, and the answer the system wrote.

You are not told which system produced this output, and it does not matter.
Judge only the evidence presented.

## What decides the verdict
- The VERDICT is decided by the RETURNED EVIDENCE ONLY -- what the knowledge
  graph actually yielded. You may NOT create, assume, or repair a link the
  evidence does not contain.
- You MAY use your own biological knowledge to INTERPRET what the evidence
  shows. Interpretation may clarify what evidence means; it may NEVER substitute for
  missing evidence, and it may NEVER raise a verdict on its own. If removing
  your outside knowledge would lower the verdict, the verdict is too high.
- A fluent, confident answer that is not backed by returned evidence is worth
  NOTHING. Judge the evidence, not the writing.

## Essential links
A link is "essential" if the hypothesis's central claim cannot hold without it --
typically the link between the two central entities, and the link to the final
outcome or phenotype. An essential link with ZERO returned evidence, or with
evidence pointing the OPPOSITE way, caps the verdict regardless of anything else.

## The specificity test (apply BEFORE choosing a verdict)
For the central claim, ask: "If the named compound or gene were replaced with an
arbitrary, unrelated one of the same type, would this same evidence still
appear?" Generic edges that any entity of that type would also have carry almost
no evidential weight for THIS entity. Say so in your reason if this applies.

## Verdict levels (use exactly one)

strong_support
Every essential link is directly evidenced by returned knowledge-graph rows
pointing the same way as the hypothesis, no essential link is opposing or at zero
evidence, and the central mechanistic link between the two core entities is
itself present in the returned evidence.

support
Essential links point the same direction and the central claim has real
grounding in the returned evidence, but at least one essential link is missing,
indirect, or only weakly evidenced. Name the link that needs confirmatory work.

partial_support
Essential links are mostly consistent with the hypothesis but MORE THAN ONE is
missing, indirect or ambiguous, and grounding is sparse. The story is plausible
but rests largely on gaps.

weak_support
Directionally consistent but THIN: only peripheral or generic evidence was
returned, the central mechanistic link is not directly evidenced, and what was
returned would plausibly appear for an arbitrary entity of the same type.

no_support
At least one essential link has ZERO returned evidence, OR the returned
evidence OPPOSES the hypothesis, with nothing offsetting it. An empty result set
is always no_support.

## Decision procedure (follow in order)
1. Identify the essential links in the hypothesis.
2. Is any essential link at zero evidence, or opposed by the evidence?
   -> no_support. Stop.
3. Is the central mechanistic link directly evidenced by returned rows?
   If NO -> the ceiling is weak_support (peripheral/generic evidence only) or
   partial_support (several links sparsely evidenced); strong_support is
   unavailable.
4. Otherwise choose between support and strong_support on whether EVERY
   essential link is evidenced.

## Output format
Respond with valid JSON only. No preamble, no markdown fences, no explanation
outside the JSON.

{"verdict": "<one of: strong_support, support, partial_support, weak_support, no_support>",
 "reason": "<two or three sentences: which essential links were evidenced, which were not, and what capped the verdict>"}
"""


# =============================================================================
# MedGemma client
# =============================================================================

def resolve_model(client) -> str:
    """Ask the server which model it serves.

    The endpoint reports its model as a filesystem path rather than a friendly
    name, so hardcoding "medgemma-27b-local" would fail.
    """
    override = os.environ.get("MEDGEMMA_MODEL")
    if override:
        return override
    try:
        served = [m.id for m in client.models.list().data]
        if served:
            return served[0]
    except Exception as exc:  # noqa: BLE001
        print(f"warning: could not list models ({exc}); falling back", file=sys.stderr)
    return "medgemma-27b-local"


def extract_json_payload(text: str) -> str:
    """Strip reasoning tags and markdown fences, then isolate the JSON object."""
    s = (text or "").strip()
    s = re.sub(r"<think>[\s\S]*?</think>", "", s, flags=re.IGNORECASE).strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if fenced:
        s = fenced.group(1).strip()
    if s.startswith("{") or s.startswith("["):
        return s
    match = re.search(r"(\{[\s\S]*\})", s)
    return match.group(1).strip() if match else s


def judge_one(client, model: str, payload: str, retries: int = 3) -> dict:
    """Send one hypothesis/answer pair to MedGemma and parse its verdict."""
    last_error = ""
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": JUDGE_PROMPT},
                    {"role": "user", "content": payload},
                ],
                temperature=0.0,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            message = response.choices[0].message
            raw = (
                getattr(message, "content", None)
                or getattr(message, "reasoning_content", None)
                or ""
            )
            parsed = json.loads(extract_json_payload(raw))
            verdict = str(parsed.get("verdict", "")).strip().lower()
            if verdict not in VERDICTS:
                last_error = f"invalid verdict {verdict!r}"
                continue
            return {"verdict": verdict, "reason": str(parsed.get("reason", "")).strip()}
        except json.JSONDecodeError as exc:
            last_error = f"unparseable JSON: {exc}"
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(2)
    return {"verdict": "", "reason": f"JUDGE FAILED: {last_error}"}


def build_payload(row: dict, hypothesis_col: str, answer_col: str) -> str:
    """Assemble what the judge sees. n_rows is included deliberately: the judge
    must know whether the answer rests on retrieved rows or on nothing."""
    return (
        f"HYPOTHESIS:\n{(row.get(hypothesis_col) or '').strip()}\n\n"
        f"DATABASE QUERY THAT WAS RUN:\n{(row.get('cypher') or '(none generated)').strip()}\n\n"
        f"NUMBER OF ROWS THE KNOWLEDGE GRAPH RETURNED: {row.get('n_rows', '0')}\n\n"
        f"ANSWER THAT WAS PRODUCED:\n{(row.get(answer_col) or '').strip()}\n"
    )


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help=("judge model id; defaults to whatever the "
                                         "endpoint serves. Use a second, independent "
                                         "model to check judge agreement."))
    parser.add_argument("--base-url", default=MEDGEMMA_BASE_URL,
                        help="OpenAI-compatible endpoint for the judge model")
    parser.add_argument("--verdict-col", default="Medgemma_verdict",
                        help="name of the verdict column, so two judges can coexist")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="results CSV to judge")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="CSV to write")
    parser.add_argument("--hypothesis-col", default="Right Hypothesis")
    parser.add_argument("--answer-col", default="answer")
    parser.add_argument("--limit", type=int, help="judge only the first N rows")
    parser.add_argument("--resume", action="store_true",
                        help="skip rows already present in the output CSV")
    parser.add_argument("--judge-empty", action="store_true",
                        help=("also send zero-evidence rows to the model instead of "
                              "assigning no_support directly. Records the model's "
                              "unconstrained opinion; not recommended for reporting."))
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise SystemExit(f"input not found: {args.input}")

    with open(args.input, newline="") as f:
        reader = csv.DictReader(f)
        original_fields = list(reader.fieldnames or [])
        rows = list(reader)

    for required in (args.hypothesis_col, args.answer_col):
        if required not in original_fields:
            raise SystemExit(f"column {required!r} not found. Available: {original_fields}")

    done = 0
    if args.resume and os.path.exists(args.output):
        with open(args.output, newline="") as f:
            done = sum(1 for _ in csv.DictReader(f))
        print(f"resuming: {done} rows already judged")

    pending = rows[done:]
    if args.limit:
        pending = pending[: args.limit]
    if not pending:
        print("nothing to judge")
        return

    client = OpenAI(base_url=args.base_url, api_key=MEDGEMMA_API_KEY)
    model = args.model or resolve_model(client)
    print(f"MedGemma judge | {len(pending)} rows | model={model}")

    reason_col = f"{args.verdict_col}_reason"
    new_fields = [args.verdict_col, reason_col]
    fieldnames = original_fields + [f for f in new_fields if f not in original_fields]
    new_file = done == 0 or not os.path.exists(args.output)
    out_file = open(args.output, "w" if new_file else "a", newline="")
    writer = csv.DictWriter(out_file, fieldnames=fieldnames)
    if new_file:
        writer.writeheader()

    tally: dict[str, int] = {}
    try:
        for i, row in enumerate(pending, start=done + 1):
            try:
                n_rows = int(str(row.get("n_rows", "0")).strip() or 0)
            except ValueError:
                n_rows = 0

            started = time.time()
            if n_rows <= 0 and not args.judge_empty:
                # Enforced, not asked. A model shown an empty result will often
                # answer from its own training knowledge and award support.
                result = {
                    "verdict": "no_support",
                    "reason": ("Knowledge graph returned 0 rows: no retrieved evidence "
                               "exists for any essential link. Assigned directly, "
                               "without consulting the model."),
                }
            else:
                result = judge_one(client, model,
                                   build_payload(row, args.hypothesis_col, args.answer_col))
                # Safety net: if the model awards support on an empty result set,
                # the evidence contradicts it.
                if n_rows <= 0 and result["verdict"] not in ("", "no_support"):
                    result["reason"] = (
                        f"[overridden from {result['verdict']}: 0 rows retrieved] "
                        + result["reason"]
                    )
                    result["verdict"] = "no_support"
            elapsed = round(time.time() - started, 1)

            tally[result["verdict"] or "FAILED"] = tally.get(result["verdict"] or "FAILED", 0) + 1

            out = dict(row)
            out[args.verdict_col] = result["verdict"]
            out[reason_col] = result["reason"]
            writer.writerow(out)
            out_file.flush()

            print(f"[{i}/{done + len(pending)}] {(row.get('Title') or '')[:52]:<52} "
                  f"-> {result['verdict'] or 'FAILED':<15} ({n_rows} rows, {elapsed}s)")
    finally:
        out_file.close()

    print(f"\nwrote {args.output}")
    print("verdict distribution:")
    for verdict in VERDICTS + ["FAILED"]:
        if tally.get(verdict):
            print(f"   {verdict:<16} {tally[verdict]}")


if __name__ == "__main__":
    main()