import logging
import os
import re
import requests
from typing import Annotated, List, Tuple
from typing import List, Dict, Any
from typing_extensions import Annotated

from dotenv import load_dotenv
from kani import AIParam, ai_function
from kani_utils.base_kanis import StreamlitKani
import streamlit as st
# Load environment variables from .env file
load_dotenv()
API_BASE_URL = os.getenv(
    "API_BASE_URL", "http://localhost:8000"
)  # Default to localhost if not set


class HypoEvoKgAgent(StreamlitKani):
    """
    A **strict** EvoAge agent that:
    - never fabricates entity IDs or types (always resolves via /search_biological_entities),
    - validates relations against allowed schemas, and
    - refuses to call prediction/rank endpoints if inputs are invalid or mismatched.
    - predict function will always return results along with the score
    -
    """
    def __init__(self, *args, **kwargs):
        kwargs["system_prompt"] = """
    You are the EvoAge Assistant, an AI chatbot designed to answer queries about the EvoAge knowledge graph and to run hypothesis testing. EvoAge contains information on entities such as Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species and PlantExtract.

    Each entity in EvoAge has a unique "model_id" which is a unique identifier for that entity and will be used for prediction queries.
    When giving details about an entity, or its subgraph, never output the "model_id" as it is an internal identifier.

    Relationships in EvoAge:

    Anatomy-related Relationships
    ANATOMY_GENE: Between Anatomy and Gene
    ANATOMY_ANATOMY: Between Anatomy and Anatomy

    Biological Process-related Relationships
    BIOLOGICALPROCESS_CHEMICALENTITY: Between BiologicalProcess and ChemicalEntity
    BIOLOGICALPROCESS_GENE: Between BiologicalProcess and Gene
    BIOLOGICALPROCESS_BIOLOGICALPROCESS: Between BiologicalProcess and BiologicalProcess

    Cellular Component-related Relationships
    CELLULARCOMPONENT_CHEMICALENTITY: Between CellularComponent and ChemicalEntity
    CELLULARCOMPONENT_GENE: Between CellularComponent and Gene
    CELLULARCOMPONENT_CELLULARCOMPONENT: Between CellularComponent and CellularComponent

    ChemicalEntity-related Relationships
    CHEMICALENTITY_DISEASE: Between ChemicalEntity and Disease
    CHEMICALENTITY_CHEMICALENTITY: Between ChemicalEntity and ChemicalEntity
    CHEMICALENTITY_GENE: Between ChemicalEntity and Gene
    CHEMICALENTITY_PROTEIN: Between ChemicalEntity and Protein
    CHEMICALENTITY_PATHWAY: Between ChemicalEntity and Pathway
    CHEMICALENTITY_BIOLOGICALPROCESS: Between ChemicalEntity and BiologicalProcess
    CHEMICALENTITY_INHIBITS_BIOLOGICALPROCESS: Between ChemicalEntity that Inhibits BiologicalProcess
    CHEMICALENTITY_PROMOTES_BIOLOGICALPROCESS: Between ChemicalEntity that Promotes BiologicalProcess
    CHEMICALENTITY_MUTATION: Between ChemicalEntity and Mutation
    CHEMICALENTITY_TISSUE: Between ChemicalEntity and Tissue

    Disease-related Relationships
    DISEASE_DISEASE: Between Disease and Disease
    DISEASE_CHEMICALENTITY: Between Disease and ChemicalEntity
    DISEASE_GENE: Between Disease and Gene
    DISEASE_PHENOTYPE: Between Disease and Phenotype
    DISEASE_PROTEIN: Between Disease and Protein
    DISEASE_ANATOMY: Between Disease and Anatomy
    DISEASE_MUTATION: Between Disease and Mutation

    Gene-related Relationships
    GENE_DISEASE: Between Gene and Disease
    GENE_CHEMICALENTITY: Between Gene and ChemicalEntity
    GENE_GENE: Between Gene and Gene
    GENE_PHENOTYPE: Between Gene and Phenotype
    GENE_PROTEIN: Between Gene and Protein
    GENE_TISSUE: Between Gene and Tissue
    GENE_ANATOMY: Between Gene and Anatomy
    GENE_BIOLOGICALPROCESS: Between Gene and BiologicalProcess
    GENE_CELLULARCOMPONENT: Between Gene and CellularComponents
    GENE_PATHWAY: Between Gene and Pathway
    GENE_MOLECULARFUNCTION: Between Gene and MolecularFunction
    GENE_INHIBITS_BIOLOGICALPROCESS: Between Gene that Inhibits BiologicalProcess
    GENE_NOEFFECT_BIOLOGICALPROCESS: Between Gene that Does Not Affect BiologicalProcess
    GENE_PROMOTES_BIOLOGICALPROCESS: Between Gene that Promotes BiologicalProcess

    Molecular Function-related Relationships
    MOLECULARFUNCTION_MOLECULARFUNCTION: Between MolecularFunction and MolecularFunction
    MOLECULARFUNCTION_CHEMICALENTITY: Between MolecularFunction and ChemicalEntity
    MOLECULARFUNCTION_BIOLOGICALPROCESS: Between MolecularFunction and BiologicalProcess

    Mutation-related Relationships
    MUTATION_PROTEIN: Between Mutation and Protein
    MUTATION_GENE: Between Mutation and Gene
    MUTATION_DISEASE: Between Mutation and Disease

    Pathway-related Relationships
    PATHWAY_GENE: Between Pathway and Gene
    PATHWAY_PATHWAY: Between Pathway and Pathway

    PMID-related Relationships
    PMID_CHEMICALENTITY: Between PMID and ChemicalEntity
    PMID_DISEASE: Between PMID and Disease
    PMID_PROTEIN: Between PMID and Protein
    PMID_CELLULARCOMPONENT: Between PMID and CellularComponent

    Phenotype-related Relationships
    PHENOTYPE_PHENOTYPE: Between Phenotype and Phenotype
    PHENOTYPE_CHEMICALENTITY: Between Phenotype and ChemicalEntity
    PHENOTYPE_GENE: Between Phenotype and Gene
    PHENOTYPE_DISEASE: Between Phenotype and Disease

    PlantExtract-related Relationships
    PLANTEXTRACT_CHEMICALENTITY: Between PlantExtract and ChemicalEntity
    PLANTEXTRACT_DISEASE: Between PlantExtract and Disease

    Protein-related Relationships
    PROTEIN_DISEASE: Between Protein and Disease
    PROTEIN_CHEMICALENTITY: Between Protein and ChemicalEntity
    PROTEIN_GENE: Between Protein and Gene
    PROTEIN_PROTEIN: Between Protein and Protein
    PROTEIN_TISSUE: Between Protein and Tissue
    PROTEIN_PHENOTYPE: Between Protein and Phenotype
    PROTEIN_MOLECULARFUNCTION: Between Protein and MolecularFunction
    PROTEIN_PATHWAY: Between Protein and Pathway
    PROTEIN_BIOLOGICALPROCESS: Between Protein and BiologicalProcess
    PROTEIN_CELLULARCOMPONENT: Between Protein and CellularComponent

    Species-related Relationships
    Species_AssociatedWith: This relation connects the nodes of the graph with the species those nodes belongs to.

    **STRICT Follow-up Response Guidelines**:
    If the user provides or references the unique identifier of an entity (including identifiers mentioned in previous responses), suggest possible relationships for tail prediction based on the entity type.

    For example:
    If the entity is a Gene, suggest relationships like GENE_GENE, GENE_PROTEIN, or GENE_DISEASE.
    If the entity is a ChemicalEntity, suggest relationships like CHEMICALENTITY_GENE, CHEMICALENTITY_PROTEIN, or CHEMICALENTITY_DISEASE.
    If the entity is a Protein, suggest relationships like PROTEIN_PROTEIN, PROTEIN_GENE, or PROTEIN_DISEASE.

    Use phrasing like:
    "Using the unique identifier of this [entity type] (e.g., from the previous response), would you like to predict tail entities using relationships such as [examples of relationships for that type]? For instance, would you like to use the GENE_GENE relationship for predictions involving this gene?"
    Ensure suggestions are specific and contextually relevant to the entity type and relationships in Evo-KG. Always leverage available identifiers to streamline the process and improve user experience.
    Always follow up with suggestions when a valid unique identifier is provided or referenced. Failing to do so is not acceptable.

    **STRICT General Guidelines**:
    For `/search_biological_entities` endpoint:
    - Always use this before any other endpoint to fetch general information about the entity, but **not for hypothesis_testing
    - The user asks for a biological entity by its name, id or mentions a term that might match a Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract by name (e.g., "What diseases are related to 'lung'?" or "Show me tissues containing 'lung'").
    - The user query involves partial or fuzzy matching of names.
    - Use this endpoint if the user provides a general or incomplete term, and the exact match is not necessary.

    For '/run_hypothesis_pipeline' endpoints:
        Trigger condition
        Use this when the user input is hypothesis-like (e.g., “I hypothesize…”, “I propose…”, “I suspect…”, “Could X…”, “Is there evidence that…”, or any causal/mechanistic biomedical claim).
        Pre-processing (Agent-side term extraction)
        Extract **all possible biological entities** from the query question which could be nodes in the knowledge graph,
            These are some few example biological entities extracted from the hypothesis questions:
            **Query**: I hypothesise Roxadustat increases hemoglobin levels and reduces transfusion needs in patients with CKD-related anemia not on dialysis.
            ** Entity extracted**: 'Roxadustat', 'hemoglobin', 'CKD-related anemia', 'dialysis'

            **Query**: Hypothesis Administration of lithocholic acid (LCA), a calorie restriction–induced metabolite, promotes health- and life-span extension in metazoans by activating AMP-activated protein kinase (AMPK), thereby mimicking the anti-aging benefits of calorie restriction.
            **Entity extracted**: 'lithocholic acid', 'LCA', 'calorie restriction', 'life-span', 'aging', 'anti-aging', 'AMP-activated protein kinase (AMPK)'

        Extract entities like mentioned above. 
        Preserve order and uniqueness.
        Cap at 50 terms. Do not fabricate terms.

        DO: Entity extraction (quotes optional)
        Collect in this order (keep original order; case-insensitive dedupe; cap 50):
        CURIE/ontology IDs: GO:, MONDO:, DOID:, HP:/HPO:, UBERON:, CHEBI:, HGNC:, ENSG:, PMID:.
        
        Quoted blocks "..." → split by commas inside the quotes.
        Also send the complete user asked question as a string
        Parentheses content e.g., (AMPK) (keep the acronym).
        Biomedical phrases (2–4 tokens or hyphenated) containing hints: acid|anemia|kinase|protein|disease|pathway|receptor|metabolite|dialysis|hemoglobin|autophagy|apoptosis|senescence|aging|health[- ]?span|life[- ]?span|transfusion.
        Capitalized single words (≥3 chars) likely to be drug/gene/protein names (exclude stopwords like “Hypothesis”, “Patients”, etc.).
        Prefer long canonical forms if both long+short appear (e.g., keep "AMP-activated protein kinase"  alongside or instead of “AMPK”).

        Optional verification: For each candidate, call GET /search_biological_entities?targetTerm=<term>; keep the term if any hits are returned. If the search errors out, keep the candidate (don’t block).
        DON’T: Extraction
        Do NOT require the user to add quotes.
        Do NOT fabricate or normalize into IDs you don’t actually have.
        Do NOT exceed 10 terms.
        Do NOT change user order (other than dedup).

        Backend call (mandatory)
        Use POST via your existing api_post helper:

        Endpoint: hypothesis/run_hypothesis_pipeline

        Body (JSON):
            {
            "hypothesis": hypothesis"(String)"
            "terms": ["<entity1>", "<entity2>", "..."],
            "per_type_limit": 10,}
        so when run_hypothesis_pipeline is hitted, just send, quotted comma seperated list of biological entities, 
        and quotted string of asked hypothesis question.

        Output:
        In return the backend will give well generated response, send that directly to the user.
        Send exact what is in responce, no manipulation.
        Keep terms like partially support and strong support like staements in green color.
        Keep the exact numbers coming from the response of prediction count and all.
        from all the triples generated by backend  get most relevnt triple and and based on those give well answered response.
        add detailed resoning for the asked question.
        Add Emoticons in the output after heading in between the texts. (example: magnifying glass, literature, brain and other scientific emojies.)
        in backend all-with-all entities triples are made, their RotatE score is checked for each triple, compared with cutoff of particular relationtype. and result is generated.

        Timeout: 1200s.

        If the POST fails (network/non-200), return a brief error message (no stack traces).
        Kindly return the well formated response from the API as the interpretation of the above hypothesis.

Clarity: ALWAYS SPECIFY IF ANSWER IS EvoAge DATA AND GPT GENERATED ("generated by GPT-4o-mini").
Relevance: Limit responses to Evo-KG-related questions or relevant supplementary GPT-4o-mini insights.
Interaction: Keep responses concise and offer summaries or options for large datasets.""".strip()

        super().__init__(*args, **kwargs)
        self.greeting = """
        <style>

            html, body {
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden; /* Make page unscrollable */
            }
            [data-testid="stHeader"] {{ display: none !important; }}
            .block-container {
                max-width: 100% !important;
                margin: 0 auto;
                padding-top: 1.5rem; /* Reduced */
            }

            /* Compact Glassmorphic Card */
            .evo-hypo-box {
                position: sticky;
                top: 0;
                background: rgba(255, 255, 255, 0.65);
                backdrop-filter: blur(14px) saturate(150%);
                -webkit-backdrop-filter: blur(14px) saturate(150%);
                
                border-radius: 22px;
                padding: 1.8rem 2rem; /* Compact like chatbot header */
                margin: 0rem 2rem 9rem;

                animation: fadeIn 1s ease-out;

                border: 1.4px solid rgba(190, 210, 255, 0.35);
                box-shadow:
                    0 10px 28px rgba(0, 0, 0, 0.08),
                    inset 0 0 16px rgba(180, 200, 255, 0.15);

                position: relative;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                align-items: center;
            }

            /* Animated glass border */
            .evo-hypo-box::before {
                content: "";
                position: absolute;
                inset: 0;
                border-radius: 22px;
                padding: 2px;
                background: linear-gradient(
                    120deg,
                    rgba(140,180,255,0.45),
                    rgba(255,255,255,0.15),
                    rgba(110,160,255,0.45)
                );
                mask:
                    linear-gradient(#fff 0 0) content-box,
                    linear-gradient(#fff 0 0);
                mask-composite: exclude;
                animation: borderGlow 6s linear infinite;
            }

            @keyframes borderGlow {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* DNA Glow + Hover Spin */
            @keyframes dnaGlow {
                0% { filter: drop-shadow(0 0 0px rgba(93,165,255,0.4)); }
                50% { filter: drop-shadow(0 0 12px rgba(93,165,255,0.9)); }
                100% { filter: drop-shadow(0 0 0px rgba(93,165,255,0.4)); }
            }

            @keyframes emojiSpin {
                0% { transform: rotate(0deg) scale(1); }
                40% { transform: rotate(14deg) scale(1.12); }
                100% { transform: rotate(0deg) scale(1); }
            }

            /* INLINE TITLE (Emoji + Text in one line) */
            .evo-hypo-title-inline {
                font-size: 2.4rem;
                font-weight: 800;
                text-align: center;
                color: #1a2b47;
                margin-bottom: 0.4rem;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 0.55rem;
            }

            .evo-dna-emoji-inline {
                font-size: 2.4rem;
                animation: dnaGlow 2.8s infinite ease-in-out;
                cursor: pointer;
                transition: 0.3s ease;
                display: inline-block;
            }

            .evo-dna-emoji-inline:hover {
                animation: emojiSpin 0.7s ease-in-out, dnaGlow 2.8s infinite ease-in-out;
            }

            /* Subtext under title */
            .evo-hypo-subtext {
                font-size: 1rem;
                text-align: center;
                color: #3d4b5c;
                line-height: 1.45;
                margin-bottom: 1.2rem;
                max-width: 850px;
                margin-left: auto;
                margin-right: auto;
            }

            .evo-divider {
                width: 80%;
                height: 1px;
                margin: 0.4rem auto 1.2rem;
                background: linear-gradient(to right, transparent, #a0c8ff, transparent);
                opacity: 0.55;
            }

            .sample-title {
                font-size: 1.25rem;
                text-align: center;
                color: #1a2b47;
                font-weight: 700;
                margin-bottom: 0.6rem;
            }

            /* Hypothesis sample grid */
            .hypo-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 1rem;
                margin-bottom: 1.2rem;
            }

            .hypo-card {
                background: rgba(255,255,255,0.75);
                border-radius: 16px;
                padding: 1rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                border: 1px solid rgba(200,220,255,0.4);
                backdrop-filter: blur(8px);
                transition: 0.25s ease;
            }

            .hypo-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 18px rgba(0,0,0,0.12);
                background: rgba(250,250,255,0.85);
            }

            .hypo-card p {
                font-size: 0.9rem;
                color: #4a5664;
                line-height: 1.45;
            }

            .hypo-note {
                text-align: center;
                font-weight: 600;
                color: #1565c0;
                font-size: 0.95rem;
            }

        </style>

        <div class="evo-hypo-box">
            <h1 class="evo-hypo-title-inline">
                <span class="evo-dna-emoji-inline">🧬</span>
                Test Your Hypothesis
            </h1>
            <p class="evo-hypo-subtext">
                Submit your biological hypothesis, and EvoAge will analyze it against  
                scientific knowledge to give you an evidence-based assessment.
            </p>
            <h3 class="sample-title">📌 Sample Questions You Can Ask</h3>
            <div class="hypo-grid">
                <div class="hypo-card">
                    <p><b>Hypothesis:</b>  
                    “Spermine, a polyamine involved in metabolism and neuroprotection,  
                    may influence Hyperkinesis through neurotransmitter and oxidative-stress pathways.”</p>
                </div>
                <div class="hypo-card">
                    <p><b>I hypothesize</b> that administration of lithocholic acid (LCA),  
                    a calorie-restriction metabolite, promotes health- and lifespan  
                    extension by activating AMPK and mimicking CR benefits.</p>
                </div>
            </div>
            <div class="evo-divider"></div>
            <p class="hypo-note">
                Note: Maximum input length is 600 characters.<br>
                <i><u>Each hypothesis may take 2–3 minutes to compute.</i></u>
            </p>
            <div style="margin-top:0.6rem; text-align:center; max-width:760px; animation: fadeSlideUp 0.6s ease;">
            <p style="
                font-size:0.82rem;
                color:#35507a;
                line-height:1.35;
                background:rgba(230,238,255,0.6);
                padding:0.45rem 0.8rem;
                border-radius:12px;
                display:inline-block;
                border:1px solid rgba(150,180,240,0.35);
                backdrop-filter:blur(6px);
            ">
                <strong>💡 Tip:</strong> For best results, start hypothesis prompts with   
                <em>“I hypothesize…”</em> or <em>“My hypothesis…”</em>.
            </p>
            </div>
        </div>
        """

        self.description = "Queries the EvoAge knowledge graph."
        self.avatar = "🧬"
        self.user_avatar = "👤"
        self.name = "EvoAge Assistant"

        self.api_base = API_BASE_URL

    # helper function to make API calls
    def api_call(self, endpoint, timeout= 600, **kwargs):
        url = f"{self.api_base}/{endpoint}"
        logging.info(f"############ api_call: url={url}, kwargs={kwargs}")
        response = requests.get(url, params=kwargs, timeout=timeout)
        response.raise_for_status()
        return response.json()

    # helper function to make POST API calls (JSON body)
    def api_post(self, endpoint, json=None, timeout=120):
        url = f"{self.api_base}/{endpoint}"
        logging.info(f"############ api_post: url={url}, json={json}")
        response = requests.post(url, json=json, timeout=timeout)
        response.raise_for_status()
        return response.json()

    @ai_function
    def search_biological_entities(
        self,
        targetTerm: Annotated[
            str,
            AIParam(
                desc="The name or id or the term to search for in biological entities"
            ),
        ],
    ) -> List[dict]:
        """
        Search biological entities such as  Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract by name or id

        Args:
          targetTerm: The name or id or the term to search for in biological entities

        Returns:
          List[dict]: A list of entity types with their top 3 matching entities
        """
        try:
            response = self.api_call(
                "search_biological_entities", targetTerm=targetTerm
            )
            return response
        except Exception as e:
            logging.error(
                f"Error calling search_biological_entities endpoint: {str(e)}"
            )
            return {"error": f"Failed to search biological entities: {str(e)}"}


            
    @ai_function
    def run_hypothesis_from_text(
        self,
        extracted_terms: Annotated[
            list[str],
            AIParam(desc="Final list of biomedical entities extracted upstream (order preserved, unique). Example: ['Roxadustat','hemoglobin','CKD-related anemia','dialysis']")
        ],
        hypothesis: Annotated[
            str,
            AIParam(desc=" Original user hypothesis text for UI context")
        ] = ""
    ) -> dict:
        """
        Uses the entities extracted upstream by the agent to call
        /hypothesis/run_hypothesis_pipeline and returns:
        - summary (one paragraph)
        - extracted_terms (echoed)
        - perTermSummary (if available)
        - full backend response (under 'response')
        NOTE: This function does NOT extract entities itself.
        """
        try:
            # 0) sanitize input from agent
            terms = [t.strip() for t in (extracted_terms or []) if isinstance(t, str) and t.strip()]
            if not terms:
                return {"error": "No extracted terms were provided to the function."}

            # 1) call backend (POST JSON) — per your spec use per_type_limit=10
            payload = {"terms": terms,"per_type_limit": 10,"hypothesis": hypothesis   # <-- include the full user query
            }
            resp = self.api_post("hypothesis/run_hypothesis_pipeline", json=payload, timeout= 1200)

            # 2) build one-paragraph summary
            entity_union = resp.get("entityUnionCount", 0)
            triple_count = resp.get("tripleCount", 0)
            counts = resp.get("categoryCounts", {}) or {}
            cat = resp.get("categorizedRows", {}) or {}

            novel_rows = cat.get("2_inKG_false_ACCEPT", []) or []
            # top-3 novel by highest score (RotatE/logsigmoid: higher = stronger)
            try:
                top3 = sorted(novel_rows, key=lambda r: float(r.get("score", 0)), reverse=True)[:3]
            except Exception:
                top3 = novel_rows[:3]

            def _fmt(r):
                hn = r.get("head_name") or r.get("head")
                tn = r.get("tail_name") or r.get("tail")
                rel = r.get("rel")
                sc = r.get("score"); cf = r.get("cutoff")
                try: sc = f"{float(sc):.2f}"
                except Exception: sc = str(sc)
                try: cf = f"{float(cf):.2f}"
                except Exception: cf = str(cf)
                return f"{hn} —[{rel}]→ {tn} (score ≈ {sc}; cutoff ≈ {cf})"

            novel_n     = counts.get("2_inKG_false_ACCEPT", 0)
            known_n     = counts.get("1_inKG_true_ACCEPT", 0)
            rej_false_n = counts.get("3_inKG_false_REJECT", 0)
            rej_true_n  = counts.get("4_inKG_true_REJECT", 0)

            reps = "; ".join(_fmt(r) for r in top3) if top3 else \
                "no high-confidence novel pairs surfaced under the current cutoff"

            summary = (
                f"I tested {entity_union} unique entities, generating {triple_count} candidate pairs. "
                f"The model surfaced {novel_n} novel high-confidence links (not present in the KG) and supported {known_n} known links. "
                f"Rejected candidates included {rej_false_n} absent-in-KG and {rej_true_n} present-in-KG cases. "
                f"Representative novel hypotheses: {reps}. "
                f"Note: with RotatE/logsigmoid scoring, higher (less negative) values indicate stronger predictions; a triple is ACCEPTED when score ≥ the relation-specific cutoff."
            )

            per_term = (resp.get("debug") or {}).get("perTermSummary")

            out = {
                "summary": summary,
                "extracted_terms": terms,
                "perTermSummary": per_term,
                "response": resp,
            }
            if hypothesis:
                out["hypothesis"] = hypothesis
            return out

        except Exception as e:
            logging.error(f"Error in run_hypothesis_from_text: {str(e)}")
            return {"error": f"Failed to run hypothesis pipeline: {str(e)}"}
