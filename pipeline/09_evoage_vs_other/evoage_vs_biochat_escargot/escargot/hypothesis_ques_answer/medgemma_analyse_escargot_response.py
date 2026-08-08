"""Judge Escargot's hypothesis answers with the locally hosted MedGemma model.

Counterpart to the BioChatter judge, producing the same `Medgemma_verdict`
column on the same five-level ladder:

    strong_support | support | partial_support | weak_support | no_support

The rubric
----------
JUDGE_PROMPT below is the verbatim rubric both systems are graded by. It is
written out in full here, rather than imported, so that this file can be read
and published on its own as the complete record of how Escargot was judged.

The prompt names no system and states that the judge is not told which tool
produced the output it is reading, so applying it to Escargot introduces no
asymmetry.

Because the identical rubric must also grade BioChatter for the comparison to
mean anything, this file checks its copy against the BioChatter judge's copy at
startup and refuses to run if the two have drifted apart. Edit one, and you must
edit the other. See `check_prompt_matches_shared_judge` below.

Only the rubric is duplicated. The client, payload builder and run loop are
still imported from the BioChatter judge, since those are plumbing rather than
scoring criteria, and duplicating them would create real drift risk without
making the grading any more transparent.

Usage:
    python medgemma_analyse_escargot_response.py
    python medgemma_analyse_escargot_response.py --limit 5
    python medgemma_analyse_escargot_response.py --resume

    # second, independent judge for inter-judge agreement
    python medgemma_analyse_escargot_response.py \\
        --input escargot_hypothesis_results_medgemma.csv \\
        --output escargot_hypothesis_results_2judges.csv \\
        --base-url https://opencode.ai/zen/go/v1 \\
        --model deepseek-v4-flash \\
        --verdict-col Deepseek_verdict
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVOAGE_VS_OTHERS = os.path.dirname(os.path.dirname(HERE))
SHARED_JUDGE = os.path.join(
    EVOAGE_VS_OTHERS, "Biochatter", "hypothesis_ques_answer",
    "medgemma_analyse_biochatter_response.py",
)

DEFAULT_INPUT = os.path.join(HERE, "escargot_hypothesis_results.csv")
DEFAULT_OUTPUT = os.path.join(HERE, "escargot_hypothesis_results_medgemma.csv")


# =============================================================================
# PROMPT  -- verdict ladder mirrored from EvoAge's JUDGE_PROMPT
#
# Identical to the rubric in medgemma_analyse_biochatter_response.py. Both
# systems are graded by this exact text; see the module docstring.
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


def load_shared_judge():
    """Load the BioChatter judge module by path for its client and run loop."""
    if not os.path.exists(SHARED_JUDGE):
        raise SystemExit(
            f"shared judge not found at {SHARED_JUDGE}\n"
            "It provides the MedGemma client and run loop, and holds the second "
            "copy of the rubric this file is checked against."
        )
    spec = importlib.util.spec_from_file_location("shared_judge", SHARED_JUDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_prompt_matches_shared_judge(judge) -> None:
    """Refuse to run if the two copies of the rubric have diverged.

    Both systems must be scored on one scale for the comparison to be valid. A
    silent divergence would not crash anything -- it would just quietly produce
    two incomparable verdict columns, which is the worst possible failure here.
    So it is made loud instead.
    """
    theirs = getattr(judge, "JUDGE_PROMPT", None)
    if theirs is None:
        raise SystemExit(
            f"{os.path.basename(SHARED_JUDGE)} no longer defines JUDGE_PROMPT, so "
            "the two rubrics cannot be checked against each other."
        )
    if theirs != JUDGE_PROMPT:
        raise SystemExit(
            "RUBRIC MISMATCH -- refusing to run.\n\n"
            f"  this file      : {os.path.abspath(__file__)}\n"
            f"  BioChatter judge: {SHARED_JUDGE}\n\n"
            "Their JUDGE_PROMPT texts differ, so Escargot and BioChatter would be "
            "graded on different scales and the comparison would be invalid.\n"
            "Reconcile the two copies (they must be identical), then rerun."
        )


def main() -> None:
    judge = load_shared_judge()
    check_prompt_matches_shared_judge(judge)

    # This file's copy of the rubric is the one that gets used.
    judge.JUDGE_PROMPT = JUDGE_PROMPT

    # Point the shared runner at Escargot's results unless told otherwise.
    if not any(a.startswith("--input") for a in sys.argv[1:]):
        sys.argv += ["--input", DEFAULT_INPUT]
    if not any(a.startswith("--output") for a in sys.argv[1:]):
        sys.argv += ["--output", DEFAULT_OUTPUT]

    print("judging Escargot results with the rubric defined in this file")
    print(f"  (verified identical to {SHARED_JUDGE})\n")
    judge.main()


if __name__ == "__main__":
    main()
