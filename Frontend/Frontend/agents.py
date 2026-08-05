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


class EvoKgAgent(StreamlitKani):
    """
    A **strict** EvoAge agent that:
    - Never fabricates entity IDs or types (always resolves via /search_biological_entities),
    - Validates relations against allowed schemas, and
    - Refuses to call prediction/rank endpoints if inputs are invalid or mismatched.
    - Predict function will always return results along with the score
    -
    """
    def __init__(self, *args, **kwargs):
        kwargs["system_prompt"] = """
    You are the EvoAge Assistant, an AI chatbot designed to answer queries about the EvoAge knowledge graph and to run hypothesis testing. EvoAge contains information on entities such as Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mirna, Mutation, PMID, Species and PlantExtract.

    Each entity in EvoAge has a unique "model_id" which is a unique identifier for that entity and will be used for prediction queries.
    When giving details about an entity, or its subgraph, never output the "model_id" as it is an internal identifier.

    Relationships in EvoAge (89 total):

    AnatomicalEntity-related Relationships
    ANATOMICALENTITY_ANATOMICALENTITY: Between AnatomicalEntity and AnatomicalEntity
    ANATOMICALENTITY_BIOLOGICALPROCESS: Between AnatomicalEntity and BiologicalProcess
    ANATOMICALENTITY_CELLULARCOMPONENT: Between AnatomicalEntity and CellularComponent
    ANATOMICALENTITY_CHEMICALENTITY: Between AnatomicalEntity and ChemicalEntity
    ANATOMICALENTITY_GENE: Between AnatomicalEntity and Gene

    BiologicalProcess-related Relationships
    BIOLOGICALPROCESS_BIOLOGICALPROCESS: Between BiologicalProcess and BiologicalProcess
    BIOLOGICALPROCESS_CELLULARCOMPONENT: Between BiologicalProcess and CellularComponent
    BIOLOGICALPROCESS_CHEMICALENTITY: Between BiologicalProcess and ChemicalEntity
    BIOLOGICALPROCESS_GENE: Between BiologicalProcess and Gene
    BIOLOGICALPROCESS_MOLECULARFUNCTION: Between BiologicalProcess and MolecularFunction
    BIOLOGICALPROCESS_PROTEIN: Between BiologicalProcess and Protein

    CellularComponent-related Relationships
    CELLULARCOMPONENT_CELLULARCOMPONENT: Between CellularComponent and CellularComponent
    CELLULARCOMPONENT_CHEMICALENTITY: Between CellularComponent and ChemicalEntity
    CELLULARCOMPONENT_GENE: Between CellularComponent and Gene

    ChemicalEntity-related Relationships
    CHEMICALENTITY_BIOLOGICALPROCESS: Between ChemicalEntity and BiologicalProcess
    CHEMICALENTITY_CHEMICALENTITY: Between ChemicalEntity and ChemicalEntity
    CHEMICALENTITY_DISEASE: Between ChemicalEntity and Disease
    CHEMICALENTITY_GENE: Between ChemicalEntity and Gene
    CHEMICALENTITY_MUTATION: Between ChemicalEntity and Mutation
    CHEMICALENTITY_PATHWAY: Between ChemicalEntity and Pathway
    CHEMICALENTITY_PROTEIN: Between ChemicalEntity and Protein
    CHEMICALENTITY_TISSUE: Between ChemicalEntity and Tissue
    CHEMICALENTITY_INHIBITS_BIOLOGICALPROCESS: Between ChemicalEntity that Inhibits BiologicalProcess
    CHEMICALENTITY_PROMOTES_BIOLOGICALPROCESS: Between ChemicalEntity that Promotes BiologicalProcess
    CHEMICALENTITY_POSITIVELYASSOCIATEDWITH_BIOLOGICALPROCESS: Between ChemicalEntity Positively Associated With BiologicalProcess
    CHEMICALENTITY_NEGATIVELYASSOCIATEDWITH_BIOLOGICALPROCESS: Between ChemicalEntity Negatively Associated With BiologicalProcess
    CHEMICALENTITY_NOTASSOCIATEDWITH_BIOLOGICALPROCESS: Between ChemicalEntity Not Associated With BiologicalProcess
    CHEMICALENTITY_NOEFFECT_BIOLOGICALPROCESS: Between ChemicalEntity that Does Not Affect BiologicalProcess

    Disease-related Relationships
    DISEASE_ANATOMICALENTITY: Between Disease and AnatomicalEntity
    DISEASE_CHEMICALENTITY: Between Disease and ChemicalEntity
    DISEASE_DISEASE: Between Disease and Disease
    DISEASE_GENE: Between Disease and Gene
    DISEASE_MUTATION: Between Disease and Mutation
    DISEASE_PATHWAY: Between Disease and Pathway
    DISEASE_PHENOTYPE: Between Disease and Phenotype

    Gene-related Relationships
    GENE_ANATOMICALENTITY: Between Gene and AnatomicalEntity
    GENE_BIOLOGICALPROCESS: Between Gene and BiologicalProcess
    GENE_CELLULARCOMPONENT: Between Gene and CellularComponent
    GENE_CHEMICALENTITY: Between Gene and ChemicalEntity
    GENE_DISEASE: Between Gene and Disease
    GENE_GENE: Between Gene and Gene
    GENE_MOLECULARFUNCTION: Between Gene and MolecularFunction
    GENE_MUTATION: Between Gene and Mutation
    GENE_PATHWAY: Between Gene and Pathway
    GENE_PHENOTYPE: Between Gene and Phenotype
    GENE_PROTEIN: Between Gene and Protein
    GENE_TISSUE: Between Gene and Tissue
    GENE_INHIBITS_BIOLOGICALPROCESS: Between Gene that Inhibits BiologicalProcess
    GENE_PROMOTES_BIOLOGICALPROCESS: Between Gene that Promotes BiologicalProcess
    GENE_NOEFFECT_BIOLOGICALPROCESS: Between Gene that Does Not Affect BiologicalProcess
    GENE_POSITIVELYASSOCIATEDWITH_BIOLOGICALPROCESS: Between Gene Positively Associated With BiologicalProcess
    GENE_NEGATIVELYASSOCIATEDWITH_BIOLOGICALPROCESS: Between Gene Negatively Associated With BiologicalProcess
    GENE_NOTASSOCIATEDWITH_BIOLOGICALPROCESS: Between Gene Not Associated With BiologicalProcess

    miRNA-related Relationships
    MIRNA_GENE: Between miRNA and Gene

    MolecularFunction-related Relationships
    MOLECULARFUNCTION_BIOLOGICALPROCESS: Between MolecularFunction and BiologicalProcess
    MOLECULARFUNCTION_CHEMICALENTITY: Between MolecularFunction and ChemicalEntity
    MOLECULARFUNCTION_MOLECULARFUNCTION: Between MolecularFunction and MolecularFunction
    MOLECULARFUNCTION_PROTEIN: Between MolecularFunction and Protein

    Mutation-related Relationships
    MUTATION_CHEMICALENTITY: Between Mutation and ChemicalEntity
    MUTATION_DISEASE: Between Mutation and Disease
    MUTATION_GENE: Between Mutation and Gene
    MUTATION_MUTATION: Between Mutation and Mutation
    MUTATION_PROTEIN: Between Mutation and Protein

    Pathway-related Relationships
    PATHWAY_GENE: Between Pathway and Gene
    PATHWAY_PATHWAY: Between Pathway and Pathway

    Phenotype-related Relationships
    PHENOTYPE_BIOLOGICALPROCESS: Between Phenotype and BiologicalProcess
    PHENOTYPE_CELLULARCOMPONENT: Between Phenotype and CellularComponent
    PHENOTYPE_CHEMICALENTITY: Between Phenotype and ChemicalEntity
    PHENOTYPE_DISEASE: Between Phenotype and Disease
    PHENOTYPE_GENE: Between Phenotype and Gene
    PHENOTYPE_MOLECULARFUNCTION: Between Phenotype and MolecularFunction
    PHENOTYPE_PHENOTYPE: Between Phenotype and Phenotype
    PHENOTYPE_PROTEIN: Between Phenotype and Protein

    PlantSpecies-related Relationships
    PLANTSPECIES_CHEMICALENTITY: Between PlantSpecies and ChemicalEntity
    PLANTSPECIES_DISEASE: Between PlantSpecies and Disease

    PMID-related Relationships
    PMID_CELLULARCOMPONENT: Between PMID and CellularComponent
    PMID_CHEMICALENTITY: Between PMID and ChemicalEntity
    PMID_DISEASE: Between PMID and Disease
    PMID_PROTEIN: Between PMID and Protein
    PMID_TISSUE: Between PMID and Tissue

    Protein-related Relationships
    PROTEIN_BIOLOGICALPROCESS: Between Protein and BiologicalProcess
    PROTEIN_CELLULARCOMPONENT: Between Protein and CellularComponent
    PROTEIN_CHEMICALENTITY: Between Protein and ChemicalEntity
    PROTEIN_DISEASE: Between Protein and Disease
    PROTEIN_MOLECULARFUNCTION: Between Protein and MolecularFunction
    PROTEIN_PATHWAY: Between Protein and Pathway
    PROTEIN_PHENOTYPE: Between Protein and Phenotype
    PROTEIN_PROTEIN: Between Protein and Protein
    PROTEIN_TISSUE: Between Protein and Tissue

    Species-related Relationships
    Species_AssociatedWith: Connects each node to the species it belongs to.

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
    - Always use this before any other endpoint to fetch general information about the entity.
    - Always use search_biological_entity if any biological term is added by the user. to fetch it's info from the database.
    - The user asks for a biological entity by its name, id or mentions a term that might match a Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract by name (e.g., "What diseases are related to 'lung'?" or "Show me tissues containing 'lung'").
    - The user query involves partial or fuzzy matching of names.
    - Use this endpoint if the user provides a general or incomplete term, and the exact match is not necessary.

    For '/predict_tail' endpoints:
    - Before calling /predict_tail, always resolve entity IDs.
    - Use the /search_biological_entities endpoint to get the model_id for every entity the user mentions — including the head and tail (if provided). Do not call /predict_tail unless all required model IDs are confirmed.
    - If the user input contains words like “predict / prediction” or patterns like “predict * for *”, treat it as a /predict_tail request (after validating the entities).
    - When giving prediction results, you must always include both: (strictly) the Entity name (Detailed name); if properties.name is missing, fall back to alternative_name or id) and the Prediction score for each predicted entity (strictly required). After the predictions, briefly explain that scores closer to zero (less negative) indicate stronger predictions.
    
    For '/get_prediction_rank' endpoints:
    -If the user input contains phrases like "Predict rank / prediction rank / give triple score" between  * and *  or  * for *( for eg: Predict rank of TP53 and ABL1. OR what is triple score of TP53 and ABL1. etc)
    - returning prediction score  and rank of the triple (head relation tail) is must 
    -*Important Strict guide line: Always use the `/search_biological_entities` endpoint to get the model_id of the head entity and tail entity before using these endpoints.
    -Make sure the head and tail entities model id is their before hitting this api.
    -Strictly do this, Always output the prediction scores(Strictly) and briefly tell the user that the scores closer to zero (less negative) indicate a stronger prediction.
    -After getting the predictions, always use the `/search_biological_entities` endpoint to get all the details of the predicted tail entities and display them.
    -Always ensure that the provided head, relation, and tail (if applicable) match the model_id and relationship names as defined in the EvoAge by first using the `/search_biological_entities` endpoint.
    -If the user provides ambiguous or partial input, clarify or guide them to provide exact identifiers before using these endpoints.
    -If the requested entity or relationship is not found in Evo-KG, return an appropriate error message or clarification request rather than invoking the endpoint.
    
    Special Rule for Invalid Relations (VERY IMPORTANT):
    - If the backend returns a 400 error stating that a relation does not exist in Evo-Age
      (e.g., “This relation doesn't exist in Evo-Age, relation: disease_biologicalprocess”),
      then you MUST:
        1) Tell the user **“This relation doesn't exist in Evo-Age.”**
        2) Provide a small, relevant subset of valid EvoAge relationship types 
           (NOT the full list), chosen based on the entity types involved in the user's query.
      This applies to ANY invalid or unrecognized relation.
    Always return backend errors in a well formated way.

    Identity & Origin Rules (STRICT):
    - If the user asks “who made you”, “who developed you”, “who created you”, “who built you”, 
      or any similar question about your origin:
      ALWAYS answer exactly:
      "I was developed by a team of researchers at Ahuja Lab, IIITD."
    - Never mention OpenAI, GPT, ChatGPT, Microsoft, or any other organization when asked about your developers.
    - Never provide alternative origins or disclaimers.
    

Clarity: ALWAYS SPECIFY IF ANSWER IS EvoAge DATA AND GPT GENERATED ("generated by GPT-4o-mini").
Relevance: Limit responses to Evo-KG-related questions or relevant supplementary GPT-4o-mini insights.
Interaction: Keep responses concise and offer summaries or options for large datasets.""".strip()

        super().__init__(*args, **kwargs)
        self.greeting = """
        <style>
            [data-testid="stHeader"] {{ display: none !important; }}
            .block-container {
                max-width: 100% !important;
                margin: 0 auto;
                padding-top: 1.5rem;     /* Reduced */
            }

            /* Glassmorphic Card (shorter + premium spacing) */
            .evo-header-box {
                position: sticky;
                top: 0;

                background: rgba(255, 255, 255, 0.65);
                backdrop-filter: blur(14px) saturate(150%);
                -webkit-backdrop-filter: blur(14px) saturate(150%);

                border-radius: 22px;
                padding: 1.8rem 2rem;       /* Reduced height */
                margin: 0rem 4rem 9rem;

                animation: fadeIn 1s ease-out, floatUpDown 8s ease-in-out infinite;

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
            .sample-title {
                font-size: 1.25rem;
                text-align: center;
                color: #1a2b47;
                font-weight: 700;
                margin-bottom: 0.6rem;
            }
            /* Glowing gradient border */
            .evo-header-box::before {
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

            /* Soft floating */
            @keyframes floatUpDown {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-5px); }
                100% { transform: translateY(0px); }
            }

            /* DNA emoji animations */
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

            .evo-dna-emoji {
                font-size: 3rem;     /* Slightly smaller */
                animation: dnaGlow 2.8s infinite ease-in-out;
                display: block;
                text-align: center;
                margin-bottom: 0.4rem;
                transition: 0.3s ease;
                cursor: pointer;
            }

            .evo-dna-emoji:hover {
                animation: emojiSpin 0.7s ease-in-out, dnaGlow 2.8s ease-in-out infinite;
            }

            .evo-header-title {
                font-size: 2.4rem;      /* Reduced size */
                text-align: center;
                font-weight: 800;
                margin-bottom: 0.4rem;
                color: #1a2b47;
                letter-spacing: -0.5px;
            }

            .evo-header-subtext {
                font-size: 1rem;      /* Reduced */
                color: #3d4b5c;
                text-align: center;
                line-height: 1.45;
                margin-bottom: 1.2rem;
                margin-top: 0.2rem !important;
                max-width: 850px;
                margin-left: auto;
                margin-right: auto;
                text-align: center;
                display: block;
            }

            .evo-divider {
                width: 80%;
                height: 1px;
                margin: 0.4rem auto 1.2rem;
                background: linear-gradient(to right, transparent, #a0c8ff, transparent);
                opacity: 0.55;
            }

            .evo-callout {
                font-size: 1rem;
                color: #1c4fa0;
                text-align: center;
                font-weight: 600;
                margin-top: 0.2rem;
            }
            .hypo-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
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
            .evo-title-row {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.6rem;     /* space between emoji + text */
                margin-bottom: 0.6rem;
            }

            /* Inline emoji */
            .evo-dna-emoji-inline {
                font-size: 2.4rem;
                animation: dnaGlow 2.8s infinite ease-in-out;
                cursor: pointer;
                transition: 0.3s ease;
            }

            .evo-dna-emoji-inline:hover {
                animation: emojiSpin 0.7s ease-in-out, dnaGlow 2.8s ease-in-out infinite;
            }

            /* Title inline */
            .evo-header-title-inline {
                font-size: 2.4rem;
                font-weight: 800;
                color: #1a2b47;
                letter-spacing: -0.5px;
                margin: 0;
                margin-bottom: 0.2rem !important;
                padding: 0;
            }
            @keyframes fadeSlideUp {
                0% {
                    opacity: 0;
                    transform: translateY(18px) scale(0.98);
                }
                100% {
                    opacity: 1;
                    transform: translateY(0px) scale(1);
                }
            }

            .animated-section {
                animation: fadeSlideUp 0.9s ease forwards;
            }
        /* Smooth entrance animation (same as hypothesis page) */
        @keyframes fadeSlideUp {
            0% {
                opacity: 0;
                transform: translateY(18px) scale(0.98);
            }
            100% {
                opacity: 1;
                transform: translateY(0px) scale(1);
            }
        }

        /* Apply animation SAME as hypothesis page */
        .evo-header-box {
            position: sticky;
            top: 0;

            background: rgba(255, 255, 255, 0.65);
            backdrop-filter: blur(14px) saturate(150%);
            -webkit-backdrop-filter: blur(14px) saturate(150%);

            border-radius: 22px;
            padding: 1.8rem 2rem;

            /* 🔥 replaced old fadeIn + floatUpDown */
            animation: fadeSlideUp 0.9s ease forwards;

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
        </style>
        <div class="evo-header-box">
            <div class="evo-title-row">
                <span class="evo-dna-emoji-inline">🧬</span>
                <h1 class="evo-header-title-inline">Welcome to EvoAge Chatbot</h1>
            </div>
            <p class="evo-header-subtext" style="text-align: center; line-height: 1.6; margin-top: 1rem;">
                Ask me about <em>genes</em>, <em>diseases</em>, <em>chemicals</em>, <em>proteins</em>,  
                <em>biological processes</em>, <em>molecular functions</em>,  
                <em>cellular components</em>, <em>pathways</em>, and more —  
                and I’ll help you explore and predict meaningful biological links.
            </p>
            <h3 class="sample-title">📌 Sample Questions You Can Ask</h3>
            <div class="hypo-grid">
                <div class="hypo-card">
                    <p>"Give information of TP53 from EvoAge KG.”</p>
                </div>
                <div class="hypo-card">
                    <p>"Predict potential disease associations for gene TP53 using KG"</p>
                </div>
                <div class="hypo-card">
                    <p>"Is node TP53 connected to gene ABL1?"</p>
                </div>
            </div>
            <div class="evo-divider"></div>
            <p class="evo-callout">
                💬 Ask away — EvoAge is ready to explore with you.
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
                <strong>💡 Tip:</strong> For best results, start prediction prompts with  
                <em>“predict”</em>.
            </p>
            </div>
        </div>

        """

        self.description = "Queries the EvoAge knowledge graph."
        self.avatar = "🧬"
        self.user_avatar = "👤"
        self.name = "EvoAge Assistant"
        # self.engine.track_usage = True
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
    def hello_world(self) -> dict:
        """
        A simple test endpoint that returns 'Hello, World!'

        Returns:
          dict: A simple greeting message
        """
        try:
            response = self.api_call("hello_world")
            return response
        except Exception as e:
            logging.error(f"Error calling hello_world endpoint: {str(e)}")
            return {"error": f"Failed to get hello world message: {str(e)}"}

    @ai_function
    def get_kg_ranking(
        self,
        source_label: Annotated[
            str,
            AIParam(
                desc="Label of the entities to rank (e.g. Disease, Gene, Protein, ChemicalEntity)"
            ),
        ],
        target_label: Annotated[
            str,
            AIParam(
                desc="Label of the neighbours to count (e.g. Gene, BiologicalProcess, Phenotype)"
            ),
        ] = "",
        rel_type: Annotated[
            str,
            AIParam(
                desc="Optional single relationship type to restrict to (e.g. Disease_Gene)"
            ),
        ] = "",
        entity_name: Annotated[
            str,
            AIParam(
                desc="Optional: restrict to entities whose name contains this text, e.g. 'cellular senescence'"
            ),
        ] = "",
        limit: Annotated[
            int,
            AIParam(desc="How many entities to return, default 10"),
        ] = 10,
    ) -> dict:
        """
        Rank entities by how many neighbours they have, computed across the ENTIRE
        knowledge graph.

        Use this for superlative and ranking questions -- "which disease has the
        most associated genes", "top 10 genes by number of biological processes",
        "which chemical affects the most pathways" -- and for counting the
        neighbours of one named entity, by setting entity_name and limit=1
        (e.g. "how many genes are associated with cellular senescence").

        Never answer a "which has the most" question by fetching a few example
        nodes and comparing them: that returns the maximum of the sample, not of
        the graph, and the graph contains tens of thousands of entities per label.

        Args:
          source_label: Label of the entities being ranked
          target_label: Label of the neighbours being counted
          rel_type: Optional relationship type to restrict to
          entity_name: Optional name filter on the ranked entities
          limit: Number of results to return

        Returns:
          dict: entities ordered by neighbour count, highest first
        """
        try:
            params = {"source_label": source_label, "limit": limit}
            if target_label:
                params["target_label"] = target_label
            if rel_type:
                params["rel_type"] = rel_type
            if entity_name:
                params["entity_name"] = entity_name
            # Aggregations scan many relationships; allow well beyond the default.
            return self.api_call("kg_aggregate", timeout=900, **params)
        except Exception as e:
            logging.error(f"Error calling kg_aggregate endpoint: {str(e)}")
            return {"error": f"Failed to compute knowledge graph ranking: {str(e)}"}

    @ai_function
    def get_kg_statistics(
        self,
        label: Annotated[
            str,
            AIParam(
                desc="Optional single node label to count (e.g. Gene, Disease, Protein, ChemicalEntity). Leave empty to get counts for every label."
            ),
        ] = "",
        rel_type: Annotated[
            str,
            AIParam(
                desc="Optional single relationship type to count (e.g. Gene_Disease, Disease_Gene). Leave empty to get counts for every relationship type."
            ),
        ] = "",
    ) -> dict:
        """
        Count what the knowledge graph contains. Use this for any question about
        how many nodes, entities, relationships or edges exist -- for example
        "how many diseases are in the knowledge graph", "how many genes are
        there", "what is the total number of edges", "how many node types exist"
        or "how many relationship types are there".

        Args:
          label: Optional node label to restrict the node counts to (e.g. Gene, Disease)
          rel_type: Optional relationship type to restrict the relationship counts to (e.g. Gene_Disease)

        Returns:
          dict: total_nodes, total_relationships, node_label_count,
            relationship_type_count, and per-label / per-relationship-type counts
        """
        try:
            params = {}
            if label:
                params["label"] = label
            if rel_type:
                params["rel_type"] = rel_type
            response = self.api_call("kg_statistics", **params)
            return response
        except Exception as e:
            logging.error(f"Error calling kg_statistics endpoint: {str(e)}")
            return {"error": f"Failed to retrieve knowledge graph statistics: {str(e)}"}

    @ai_function
    def get_sample_triples(
        self,
        rel_type: Annotated[
            str,
            AIParam(
                desc="The relationship type to filter triples (e.g. GENE_GENE, GENE_DISEASE, GENE_PHENOTYPE)"
            ),
        ],
    ) -> List[dict]:
        """
        Retrieve sample triples based on the relationship type

        Args:
          rel_type: The relationship type to filter triples. (e.g. GENE_GENE, GENE_DISEASE, GENE_PHENOTYPE)

        Returns:
          List[dict]: A list of triples with head, relation, and tail
        """
        try:
            response = self.api_call("sample_triples", rel_type=rel_type)
            return response
        except Exception as e:
            logging.error(f"Error calling sample_triples endpoint: {str(e)}")
            return {"error": f"Failed to retrieve sample triples: {str(e)}"}

    @ai_function
    def get_nodes_by_label(
        self,
        label: Annotated[
            str,
            AIParam(
                desc="The label of the nodes to retrieve (e.g., Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species, PlantExtract)"
            ),
        ],
    ) -> List[dict]:
        """
        Retrieve a SAMPLE of up to 10 example nodes of a given type, to show what
        nodes of that type look like.

        This returns only a small sample, NEVER the full set and NEVER a total.
        Do not use it to count anything or to answer "how many" questions -- the
        number of rows it returns says nothing about how many such nodes exist.
        For counts and totals use get_kg_statistics instead.

        Args:
          label: The label of the nodes to retrieve (e.g., Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species, PlantExtract)

        Returns:
          List[dict]: A list of up to 10 nodes with their primary identifiers
        """
        try:
            response = self.api_call("get_nodes_by_label", label=label)
            return response
        except Exception as e:
            logging.error(f"Error calling get_nodes_by_label endpoint: {str(e)}")
            return {"error": f"Failed to retrieve nodes by label: {str(e)}"}

    @ai_function
    def get_subgraph(
        self,
        property_name: Annotated[
            str,
            AIParam(
                desc="Property name of the start node to search for (e.g., name, id)"
            ),
        ],
        property_value: Annotated[
            str, AIParam(desc="Value of the property to search for")
        ],
        node_label: Annotated[
            str,
            AIParam(desc="Label of the start node to search for (e.g., Gene, Protein)"),
        ],
    ) -> dict:
        """
        Retrieve a subgraph of related nodes by specifying the property and value of the start node

        Args:
            property_name: Property name of the start node to search for (e.g., name, id)
            property_value: Value of the property to search for
            node_label: Label of the start node to search for (e.g., Gene, Protein)

        Returns:
            dict: A subgraph of nodes related to the specified node
        """
        try:
            params = {
                "property_name": property_name,
                "property_value": property_value,
                "node_label": node_label,
            }
            response = self.api_call("subgraph", **params)
            return response
        except Exception as e:
            logging.error(f"Error calling subgraph endpoint: {str(e)}")
            return {"error": f"Failed to retrieve subgraph: {str(e)}"}

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
        Search biological entities such as  Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mirna, Mutation, PMID, Species or PlantExtract by name or id

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
    def get_entity_relationships(
        self,
        entity_type: Annotated[
            str,
            AIParam(
                desc="The type of entity to search for (e.g., Gene, Protein, Disease)"
            ),
        ],
        property_name: Annotated[
            str,
            AIParam(desc="The property used to identify the entity (e.g., id, name)"),
        ],
        property_value: Annotated[
            str, AIParam(desc="The value of the property for the entity")
        ],
        relationship_type: Annotated[
            str,
            AIParam(
                desc="The type of relationship to filter by (e.g., GENE_DISEASE, PROTEIN_PROTEIN)"
            ),
        ] = None,
    ) -> dict:
        """
        Retrieve the count and list of related entities for a specified entity and optionally by relationship type

        Args:
          entity_type: The type of entity to search for (e.g., Gene, Protein)
          property_name: The property used to identify the entity (e.g., id, name)
          property_value: The value of the property for the entity
          relationship_type: The type of relationship to filter by (optional)

        Returns:
          dict: The count and details of related entities, optionally filtered by relationship type
        """
        try:
            params = {
                "entity_type": entity_type,
                "property_name": property_name,
                "property_value": property_value,
            }
            if relationship_type:
                params["relationship_type"] = relationship_type

            response = self.api_call("entity_relationships", **params)
            return response
        except Exception as e:
            logging.error(f"Error calling entity_relationships endpoint: {str(e)}")
            return {"error": f"Failed to retrieve entity relationships: {str(e)}"}

    @ai_function
    def check_relationship(
        self,
        entity1_type: Annotated[
            str, AIParam(desc="The type of the first entity (e.g., Gene, Protein)")
        ],
        entity1_property_name: Annotated[
            str,
            AIParam(
                desc="The property name to identify the first entity (e.g., id, name)"
            ),
        ],
        entity1_property_value: Annotated[
            str, AIParam(desc="The property value to identify the first entity")
        ],
        entity2_type: Annotated[
            str, AIParam(desc="The type of the second entity (e.g., Disease, Protein)")
        ],
        entity2_property_name: Annotated[
            str,
            AIParam(
                desc="The property name to identify the second entity (e.g., id, name)"
            ),
        ],
        entity2_property_value: Annotated[
            str, AIParam(desc="The property value to identify the second entity")
        ],
    ) -> dict:
        """
        Check if a relationship exists between two entities and return the type of relationship

        Args:
          entity1_type: The type of the first entity (e.g., Gene, Protein)
          entity1_property_name: The property name to identify the first entity (e.g., id, name)
          entity1_property_value: The property value to identify the first entity
          entity2_type: The type of the second entity (e.g., Disease, Protein)
          entity2_property_name: The property name to identify the second entity (e.g., id, name)
          entity2_property_value: The property value to identify the second entity

        Returns:
          dict: Information whether a relationship exists and its type
        """
        try:
            params = {
                "entity1_type": entity1_type,
                "entity1_property_name": entity1_property_name,
                "entity1_property_value": entity1_property_value,
                "entity2_type": entity2_type,
                "entity2_property_name": entity2_property_name,
                "entity2_property_value": entity2_property_value,
            }
            response = self.api_call("check_relationship", **params)
            return response
        except Exception as e:
            logging.error(f"Error calling check_relationship endpoint: {str(e)}")
            return {"error": f"Failed to check relationship: {str(e)}"}

    @ai_function
    def predict_tail(
        self,
        head: Annotated[str, AIParam(desc="model_id for the head entity for the prediction")],
        relation: Annotated[str, AIParam(desc="Relation for the prediction")],
        top_k_predictions: Annotated[int, AIParam(desc="Number of top predictions to return (default is 10)")] = 10,
    ) -> dict:
        """
        Predict the top-K tail entities for a given head (model_id) and relation using the backend.
        Always returns scores and name/alternative-name (if present).
        """
        try:
            # If your backend expects lowercase, uncomment the next line:
            # wire_rel = relation.lower()
            wire_rel = relation

            params = {
                "head": str(head),
                "relation": wire_rel,
                "top_k_predictions": int(top_k_predictions),
            }
            resp = self.api_call("predict_tail", **params)

            raw_preds = resp.get("predictions", []) or resp.get("tails", [])

            enriched = []
            for idx, p in enumerate(raw_preds, start=1):
                tail_id = (
                    p.get("tail_entity")
                    or p.get("tail")
                    or p.get("model_id")
                    or p.get("id")
                )
                score = p.get("score")  # keep the original score
                name = p.get("properties", {}).get("name") or ""
                alternative_name = p.get("properties", {}).get("alternative_name") or ""

                enriched.append({
                    "tail_name": name,
                    "tail_type": wire_rel.split('_')[-1],
                    "score": score,      
                })

            return {
                "provenance": "[EvoAge]",
                "head_model_id": resp.get("head_entity") or str(head),
                "relation": resp.get("relation") or wire_rel,
                "predictions": enriched,
                "note": "Scores are backend scores; lower magnitude (closer to 0) is stronger if using RotatE-style scoring.",
            }

        except Exception as e:
            logging.error(f"Error calling predict_tail endpoint: {str(e)}")
            return {"error": f"Failed to predict tail entities: {str(e)}"}

    @ai_function
    def get_prediction_rank(
        self,
        head: Annotated[
            str, AIParam(desc="model_id for head entity for the prediction")
        ],
        relation: Annotated[
            str,
            AIParam(desc="Relation for the prediction"),
        ],
        tail: Annotated[
            str, AIParam(desc="model_id for tail entity to check for its rank")
        ],
    ) -> dict:
        """
        Get the rank and score of a specific tail entity for a given head and relation, along with the maximum score.

        Args:
          head: model_id for head entity for the prediction
          relation: Relation for the prediction
          tail: model_id for tail entity to check for its rank

        Returns:
          dict: The rank, score, and maximum score of the prediction
        """
        try:
            params = {"head": head, "relation": relation, "tail": tail}
            response = self.api_call("get_prediction_rank", **params)
            return response
        except Exception as e:
            logging.error(f"Error calling get_prediction_rank endpoint: {str(e)}")
            return {"error": f"Failed to get prediction rank: {str(e)}"}
            