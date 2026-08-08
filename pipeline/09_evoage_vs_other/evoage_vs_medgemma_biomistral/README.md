# EvoAge vs MedGemma vs BioMistral vs Aging_BioMistral_finetuned

Evaluates three biomedical language models on the same 101 right/inverse
hypothesis pairs used throughout the EvoAge benchmark, answering from their own
parametric knowledge rather than from retrieved graph evidence.

| Directory | Model | Notes |
|---|---|---|
| `medgemma/` | MedGemma-27B | Biomedical language model, as published |
| `BioMistral/` | BioMistral-7B | Biomedical language model, as published |
| `BioMistralFinetuned/` | **Aging_BioMistral_finetuned** | BioMistral-7B after AgingKG-guided adaptation (config `biomistral_lora_sft_optimized4.yaml`; see `pipeline/10_llm_fintunning/`) |

---

## The prompts are identical across all three models

Every model directory contains a **byte-identical** `run_hypothesis.py` — the
same prompts, the same two-step sequence, the same parsing. Only the served
model differs. This is what makes the three sets of verdicts comparable; if the
prompt varied by model, the comparison would not mean anything.

If you edit the prompt, edit it in all three copies.

Each hypothesis is evaluated in two steps:

1. **Verdict** — the model places the hypothesis on the five-level ladder
   `no_support → weak_support → partial_support → support → strong_support`
   and replies with the verdict alone. It is told to judge from established
   biomedical knowledge, and to pick the lower level when uncertain.
2. **Explanation** — the verdict is appended to the conversation and the model
   is asked to justify it in two or three sentences.

Both the verdict and the explanation are recorded for every hypothesis, for the
right hypothesis and its inverse, so each verdict can be audited rather than
taken on trust.

---

## Input

`All_Hypothesis_fixed_with_ent.csv` — 101 rows:

```
Title, PMID, Journal, Published, DOI, Right Hypothesis, Inverse Hypothesis
```

Each row is one publication, giving the literature-supported hypothesis and its
logically inverted counterpart. Both are evaluated.

---

## Running it

```bash
./run_all.sh            # all three models, in sequence
```

or one at a time:

```bash
cd medgemma && ./run.sh
```

Each `run.sh` launches an SGLang server for its model, waits for the endpoint to
come up, runs the evaluation, and shuts the server down again on exit.

### Configuration

Paths default to the machine this study ran on; override with environment
variables:

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_PATH` | the study's local model directory | Your copy of the model weights |
| `SGLANG_PYTHON` | `python` from the active conda env | Interpreter with SGLang installed |
| `CONDA_SH` | `$HOME/miniconda3/etc/profile.d/conda.sh` | conda bootstrap script |
| `CONDA_ENV` | `vllm3` | conda environment to activate |
| `PORT` | `50000` | Port for the local SGLang server |

```bash
MODEL_PATH=/path/to/medgemma-27b ./run.sh
```

The script exits with a clear message if `MODEL_PATH` does not exist, rather
than failing deeper inside the server launch.

---

## Output

Each directory writes `All_Hypothesis_evaluated.csv` next to its own `run.sh` —
the input columns plus:

```
Right_Hypothesis_Verdict, Right_Hypothesis_Explanation,
Inverse_Hypothesis_Verdict, Inverse_Hypothesis_Explanation
```

Server logs go to `<model>/logs/` and are not tracked.

---

## Note

No knowledge graph evidence is supplied to these models — answering from
parametric knowledge is the capability under test here. This is the difference
from the KG-grounded comparison in `../evoage_vs_biochat_escargot/`, where every
system queries the EvoAge graph and is graded on the evidence it returns.
