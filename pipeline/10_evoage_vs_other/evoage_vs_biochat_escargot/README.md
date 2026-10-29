# EvoAge vs BioChatter vs Escargot — benchmark code

Everything needed to reproduce the three-way comparison: run both published
baselines against the EvoAge knowledge graph, grade all outputs with the same
MedGemma judge, and produce the verdict counts and figures.

The comparison holds the knowledge graph, the language model and the question
set constant, so that the reasoning framework is the only variable.

---

## Layout

```
evoage_vs_others/
├── .env.example                     # credentials template -- copy to Biochatter/.env
│
├── Biochatter/                      # BioChatter baseline
│   ├── evoage_biochatter.py         #   adapter: connector subclass + prompt context
│   ├── generate_schema_info.py      #   introspects the live graph -> BioCypher-style schema
│   ├── schema_info.yaml             #   the generated schema actually used
│   ├── run_benchmark.py             #   general question runner
│   ├── results/                     #   its output
│   ├── SETUP_STEPS.md · README.md   #   install + adaptation notes
│   └── hypothesis_ques_answer/
│       ├── run_hypothesis_benchmark.py            # the 101 hypotheses
│       ├── medgemma_analyse_biochatter_response.py# JUDGE -- defines the rubric
│       └── biochatter_hypothesis_results*.csv     # raw + judged
│
├── escargot/                        # Escargot baseline
│   ├── escargot/                    #   vendored upstream, UNMODIFIED (see UPSTREAM.md)
│   ├── evoage/                      #   our adaptation: deepseek_lm.py, ask_evoage.py
│   ├── alzkb_sanity/                #   sanity check on the graph Escargot ships against
│   ├── ESCARGOT_CHANGES_DOCUMENTATION.md
│   └── hypothesis_ques_answer/
│       ├── run_hypothesis_benchmark.py
│       ├── medgemma_analyse_escargot_response.py  # JUDGE -- same rubric, divergence-guarded
│       └── escargot_hypothesis_results*.csv
│
├── evoage_results/                  # EvoAge's own verdicts on the same 101 hypotheses
└── analysis/                        # DOI join, verdict counts, figures
```

---

## Setup

```bash
cp .env.example Biochatter/.env      # fill in Neo4j credentials
pip install biochatter==0.14.2 neo4j openai pandas matplotlib python-dotenv langchain-openai
```

Both baselines read that single `.env`. Escargot's subclasses pick it up via
`DEEPSEEK_ENV`, so there is one copy of the credentials, not two.

Two services must be reachable:

| Service | Default | Used for |
|---|---|---|
| EvoAge Neo4j | from `.env` | the shared knowledge graph (read-only) |
| MedGemma-27B | `http://localhost:30001/v1` | the judge; override with `MEDGEMMA_BASE_URL` |

---

## Running it

```bash
# 1. baselines answer the 101 hypotheses against the EvoAge graph
python Biochatter/hypothesis_ques_answer/run_hypothesis_benchmark.py
python escargot/hypothesis_ques_answer/run_hypothesis_benchmark.py

# 2. grade both with the blinded MedGemma judge
python Biochatter/hypothesis_ques_answer/medgemma_analyse_biochatter_response.py
python escargot/hypothesis_ques_answer/medgemma_analyse_escargot_response.py

# 3. join on DOI, count verdicts, draw figures
python analysis/verdict_analysis_complete.py
```

Useful flags on the judges: `--limit N` (short run), `--resume` (skip rows
already graded), `--model` / `--verdict-col` (grade with a second, independent
model and write a parallel column, for inter-judge agreement).

---

## The rubric

Both baselines are graded by one system-neutral prompt on a five-level ladder:

```
no_support → weak_support → partial_support → support → strong_support
```

It is defined as `JUDGE_PROMPT` in
`Biochatter/hypothesis_ques_answer/medgemma_analyse_biochatter_response.py`.
The Escargot judge carries a byte-identical copy and **refuses to run** if the
two have drifted apart, so grading both systems on one scale is enforced by the
code rather than asserted. The prompt names no system, and the judge is never
told which system produced the output it is reading.

Zero-evidence is handled deterministically: when a query returns no rows, the
verdict is set to `no_support` in code rather than asked of the model, because a
model shown an empty result set will often fall back on its training knowledge
and award support anyway.

---

## Notes

- **The baselines were not modified.** `escargot/escargot/` is the published
  framework at commit `936a005`, untouched; all adaptation lives in
  `escargot/evoage/` as subclasses. For BioChatter this was verified by
  checksum against the PyPI distribution manifest. Every adaptation exists to
  let a baseline produce a working query where it otherwise could not, so all of
  them raise baseline performance rather than lower it.
- **Credentials are not included.** `.env` was deliberately excluded from this
  export; use `.env.example`.
- Two paths still default to an EvoAge backend `.env`
  (`Biochatter/evoage_biochatter.py`, `generate_schema_info.py`); both are
  overridable with `EVOAGE_ENV=` and are only a fallback when the local `.env`
  omits a value.
- All baseline runs are read-only. Nothing here writes to the EvoAge graph.
