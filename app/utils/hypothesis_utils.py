from typing import Any, Dict, List, Tuple, Optional
import re, os, io
import json, uuid
from pathlib import Path
from textwrap import dedent
import numpy as np

def build_hypothesis_system_prompt(hypothesis: str) -> str:
    """
    Returns a formatted system prompt that embeds the provided hypothesis.
    """
    prompt = f"""
    You are an AI assistant tasked with analyzing scientific data. I will provide you with a JSON file containing the results from a knowledge graph model experiment. The purpose of this experiment was to test the following scientific hypothesis:

    Hypothesis: "{hypothesis}"

    Please review the provided JSON file, Strict, You need to evaluate all the triples in json file(went for prediction), and prepare a comprehensive summary of the findings. Your summary must be structured to directly evaluate whether the data supports, partially supports or refuses this hypothesis. Refusal of hypothesis will only come when no. of 4_inKG_true_REJECT is >(greater than) 2_inKG_false_ACCEPT.

    Your response should include:
    - Always give info of these "terms": [used in hypothesis],"entityUnionCount":,"tripleCount":,"categoryCounts": {"1_inKG_true_ACCEPT","2_inKG_false_ACCEPT","3_inKG_false_REJECT","4_inKG_true_REJECT","total_rows"}
    - A direct conclusion at the beginning, stating whether the KG model's results support the hypothesis, this should be based on all the triples  in json file.
    - A high-level statistical overview of the experiment, ** Strict** including the total number of predictions, exactly present in JSON, Not in vector chunk. 
        the number of accepted novel predictions in whole JSON(2_inKG_false_ACCEPT), and the number of confirmed known relationships in whole JSON(1_inKG_true_ACCEPT) and rejected ground truth(4_inKG_true_REJECT)
    - No change in numbers and values which are in JSON file.
    - Don't directly evaluate no. of accepted Vs rejected count and give results, It should be based on 1_inKG_true_ACCEPT,2_inKG_false_ACCEPT,4_inKG_true_REJECT
    - A detailed breakdown of key thematic findings that connect the core concepts of the hypothesis (for example: Spermine, Hyperkinesis, Oxidative Stress, Neurotransmitters, and the Central Nervous System).
    - Quantitative evidence for each key finding. You must substantiate your claims by citing specific examples (atleast 10-15) of predicted relationships (triples) and their corresponding prediction scores from the JSON file. Please note that scores closer to zero indicate higher confidence.
    - also consider 2-3 external validation points for the asked hypothesis.
    - A concluding paragraph summarizing the overall implications of these findings for future research.
    Please adopt a formal, analytical tone suitable for a scientific report.

    For Example: I am attaching the desired results for this hypothesis: "Spermine, a polyamine involved in cellular metabolism and neuroprotection, may influence the development or severity of Hyperkinesis through its modulation of neurotransmitter signaling and oxidative stress pathways in the central nervous system."
    Desired sample output:
        Based on the knowledge graph analysis, the results provide strong computational support for the hypothesis. The model successfully identified numerous novel, plausible connections that link Spermine, Hyperkinesis, neurotransmitter signaling, and oxidative stress within the central nervous system.

        Out of 3,577 relationships tested between 104 unique biological entities, the model accepted 642 as plausible. Of these, 592 are novel predictions not previously recorded in the knowledge graph, forming a cohesive network of evidence that directly supports the proposed mechanisms.
        The Big Picture: Statistical Overview 📊
        The model's performance highlights its ability to both validate existing knowledge and generate new, data-driven hypotheses:
        Novel Discoveries (Accepted): 592 new relationships were predicted as highly plausible.
        Confirmed Knowledge (Accepted): 50 known relationships were correctly identified with very strong scores, validating the model's accuracy.
        Rejected Triples: 2,935 potential relationships (both novel and known) were correctly filtered out as unlikely, demonstrating the model's high selectivity.
        Key Thematic Findings with Quantitative Support 🔬
        The accepted predictions reveal strong thematic connections, with scores closer to zero indicating higher confidence in the predicted relationship.
        1. Direct Links Between Spermine Metabolism, Oxidative Stress, and Hyperkinesis
        The model established direct connections between the core components of the hypothesis with strong quantitative backing:
        Hyperkinesis ↔ Oxidative Stress Genes: Hyperkinesis was newly associated with several key oxidative stress genes with high confidence scores:
        Hyperkinesis ↔ OXSR1 (oxidative stress responsive kinase 1), score: -0.0316
        Hyperkinesis ↔ OSGIN2 (oxidative stress induced growth inhibitor 2), score: -0.0335
        Hyperkinesis ↔ OSGIN1 (oxidative stress induced growth inhibitor 1), score: -0.0404
        Spermine Metabolism ↔ Hyperkinesis: A direct link was predicted between spermine metabolism genes and the disease state:
        SMOX (spermine oxidase) ↔ Hyperkinesis, score: -0.0675
        Spermine Metabolism ↔ Oxidative Stress: A highly significant novel gene-gene link was predicted between SMOX and OXSR1 with a score of -0.0074, suggesting a direct molecular interplay.

        2. The Role of Neurotransmitter Signaling 🧠
        The analysis strengthens the hypothesis by quantitatively connecting both spermine and oxidative stress to neurotransmitter functions:
        Spermine Metabolism → Neurotransmitter Function: Genes like SMS (spermine synthase) and SMOX were newly linked to key neurotransmitter processes with strong scores:
        SMS ↔ neurotransmitter secretion, score: -0.0245
        SMOX ↔ neurotransmitter transport, score: -0.0304
        Oxidative Stress ↔ Neurotransmitter Pathways: The model predicted robust links between key oxidative stress genes and specific neurotransmitter systems:
        Glutamate Neurotransmitter Release Cycle ↔ OXSR1, score: -0.0301
        Dopamine Neurotransmitter Release Cycle ↔ OSGIN1, score: -0.0385
        3. Validation in the Central Nervous System 🔗
        The anatomical context of the hypothesis was validated with exceptionally strong scores for known relationships and supported by novel predictions:
        Confirmed Links: Foundational links between key genes and the central nervous system were confirmed with high confidence, including SAT1 (score: -0.0057) and OSGIN1 (score: -0.0077).

        Novel Link: A new relationship was predicted between Hyperkinesis and the central nervous system (score: -0.1178), computationally placing the disease within the correct anatomical context.

        Conclusion
        The knowledge graph model's results strongly corroborate the hypothesis by building a dense, interconnected network of evidence. The 592 novel predictions, backed by strong confidence scores, provide a quantitative foundation for the proposed mechanisms. The findings highlight a clear pathway where spermine metabolism and oxidative stress are intertwined with neurotransmitter signaling in the CNS, offering a compelling, data-driven rationale for further experimental research into the molecular basis of Hyperkinesis.

    """
    return dedent(prompt).strip()

# ================
# GEMINI UTILITY
# ================

def _strip_code_fences(s: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` fences if present.
    """
    s = s.strip()
    # ```json\n...\n```  OR  ```\n...\n```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, flags=re.IGNORECASE)
    return m.group(1).strip() if m else s

def _try_parse_json(s: str) -> Optional[Any]:
    """
    Try to parse s as JSON after trimming common wrappers.
    Only returns a value if it cleanly parses.
    """
    if not s:
        return None
    s1 = _strip_code_fences(s).strip()
    # Quick sanity: must look like JSON
    if not (s1.startswith("{") or s1.startswith("[")):
        return None
    try:
        return json.loads(s1)
    except Exception:
        return None

def genai_response_to_payload(resp) -> Dict[str, Any]:
    """
    Convert a google-genai GenerateContentResponse into a dict:
    {
      "response": <dict | {"text": "..."}>,
      "meta": {...}
    }
    """
    # 1) Extract text (works even if AFC/tools were present but still produced text)
    text = (getattr(resp, "text", None) or "").strip()

    # 2) Try to parse JSON from the text
    parsed = _try_parse_json(text)

    # 3) Extract metadata safely
    finish_reason = None
    if getattr(resp, "candidates", None):
        try:
            finish_reason = getattr(resp.candidates[0], "finish_reason", None)
        except Exception:
            pass

    # usage_metadata appears on the top-level response in google-genai
    usage = {}
    um = getattr(resp, "usage_metadata", None)
    if um:
        usage = {
            "prompt_token_count": getattr(um, "prompt_token_count", None),
            "candidates_token_count": getattr(um, "candidates_token_count", None),
            "total_token_count": getattr(um, "total_token_count", None),
        }

    payload: Dict[str, Any] = {
        "response": parsed if parsed is not None else {"text": text},
        "meta": {
            "finish_reason": finish_reason,
            "usage": usage,
            "model_version": getattr(resp, "model_version", None),
        },
    }
    return payload

# ================
# Save JSON
# ================
def _json_default(o):
    """Fallback for non-serializable objects (e.g., sets, numpy types)."""
    try:
        if isinstance(o, (np.integer, np.floating)):
            return o.item()
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
    except Exception:
        pass
    if isinstance(o, set):
        return sorted(o)
    return str(o)

def save_response_obj(response_obj, folder: str | os.PathLike, filename: str = "response_obj.json") -> Path:
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)

    out_path = folder_path / filename
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    # Pretty + UTF-8, robust fallback for odd types
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(response_obj, f, ensure_ascii=False, indent=2, default=_json_default)

    # Atomic replace
    os.replace(tmp_path, out_path)
    return out_path

__all__ = [
    # Export the original underscored names if you want them importable too
    "save_response_obj",
    "genai_response_to_payload"
]