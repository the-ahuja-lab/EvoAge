import streamlit as st
import requests
import logging
import os
from dotenv import load_dotenv
# You can move this to a config file or st.secrets if you like
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _api_get(endpoint: str, timeout: int = 600, **params):
    url = f"{API_BASE_URL}/{endpoint}"
    logging.info(f"[MicroServices] GET {url} params={params}")
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _api_post(endpoint: str, json_body: dict | None = None, timeout: int = 1200):
    url = f"{API_BASE_URL}/{endpoint}"
    logging.info(f"[MicroServices] POST {url} json={json_body}")
    resp = requests.post(url, json=json_body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def show_microservices_page():
    # ---------- PAGE CSS ----------
    st.markdown(
        """
    <style>
    /* -----------------------------------------------------------
    GLOBAL FONT + CONTAINER
    ------------------------------------------------------------*/
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .block-container {
        max-width: 92%;
        margin: 0 auto;
        padding-top: 1.6rem;
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont,
                    'Segoe UI', Roboto, sans-serif;
    }

    /* -----------------------------------------------------------
    PAGE WRAPPER (white → blue premium gradient)
    ------------------------------------------------------------*/
    .micro-page-wrapper {
        background: linear-gradient(180deg, #ffffff 0%, #f3f7ff 100%);
        border-radius: 26px;
        padding: 1.6rem 1.8rem 2.4rem;
        border: 1px solid rgba(180, 200, 255, 0.55);
        box-shadow: 0 15px 55px rgba(0, 0, 0, 0.05);
    }

    /* -----------------------------------------------------------
    HEADER
    ------------------------------------------------------------*/
    .micro-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 1.2rem;
    }

    .micro-title {
        font-size: 2.15rem;
        font-weight: 800;
        color: #1c273c;
    }

    .micro-title span {
        font-size: 2rem;
        margin-right: 0.4rem;
        display: inline-block;
        animation: emojiGlow 3s ease-in-out infinite;
    }

    .micro-subtitle {
        font-size: 0.92rem;
        color: #5d6b8c;
        margin-top: 0.3rem;
    }

    /* Badge */
    .micro-refresh-badge {
        padding: 0.55rem 0.95rem;
        border-radius: 999px;
        border: 1px solid rgba(150, 180, 255, 0.6);
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        background: rgba(240, 245, 255, 0.65);
        backdrop-filter: blur(6px);
        color: #1d2639;
    }

    .micro-refresh-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #22c55e;
        box-shadow: 0 0 8px rgba(34,197,94,0.9);
        animation: pulseDot 2s ease-in-out infinite;
    }

    /* -----------------------------------------------------------
    GRID
    ------------------------------------------------------------*/
    .micro-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        grid-gap: 1.5rem;
        margin-top: 1.3rem;
    }

    /* -----------------------------------------------------------
    PREMIUM GLASSMORPHISM CARD
    ------------------------------------------------------------*/
    .micro-card {
        position: relative;
        border-radius: 22px;
        padding: 1.4rem 1.4rem 1.3rem;

        /* Premium frosted glass look */
        background: rgba(255, 255, 255, 0.58);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);

        border: 1px solid rgba(180, 200, 255, 0.45);

        box-shadow:
            0 6px 26px rgba(0, 0, 0, 0.08),
            inset 0 0 0 1px rgba(255,255,255,0.55);

        transition: transform .35s ease,
                    box-shadow .35s ease,
                    border-color .35s ease,
                    background .35s ease;
        overflow: hidden;
        min-height: 140px;        /* ensure all cards same height */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding-bottom: 1.1rem;
    }

    /* Border highlight effect */
    .micro-card::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 22px;
        padding: 2px;
        background: linear-gradient(
            135deg,
            rgba(118,169,252,0.55),
            rgba(52,211,235,0.35),
            rgba(129,140,248,0.45)
        );
        opacity: 0;
        transition: opacity .4s ease;
        mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0);
        mask-composite: exclude;
        pointer-events: none;
    }

    .micro-card:hover::before {
        opacity: 1;
    }

    /* Hover state — slightly more opaque & raised */
    .micro-card:hover {
        background: rgba(255, 255, 255, 0.78);
        transform: translateY(-6px) scale(1.01);
        box-shadow: 0 14px 45px rgba(0, 0, 0, 0.12);
        border-color: rgba(150, 180, 255, 0.85);
    }

    /* -----------------------------------------------------------
    CARD CONTENT
    ------------------------------------------------------------*/
    .micro-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.7rem;
    }
    .micro-card-footer {
        width: 100%;
        padding-top: 0.5rem;
    }
    .micro-card-main {
        display: flex;
        gap: 0.9rem;
        align-items: flex-start;
    }

    /* ICON */
    .micro-icon {
        width: 44px;
        height: 44px;
        border-radius: 16px;

        background: linear-gradient(135deg, #8ec5ff, #5c7cfa);
        display: flex;
        align-items: center;
        justify-content: center;

        color: #ffffff;
        font-size: 1.65rem;
        box-shadow: 0 8px 18px rgba(100,140,255,0.35);
    }

    /* TEXT COLORS — readable & professional */
    .micro-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1d2533;
    }

    .micro-card-desc {
        font-size: 0.85rem;
        color: #4d5972;
        margin-top: 2px;
    }

    /* STATUS */
    .micro-card-status {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        color: #1f3d28;
        font-size: 0.82rem;
    }

    .micro-card-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: #22c55e;
        box-shadow: 0 0 8px rgba(34,197,94,0.95);
    }

    /* -----------------------------------------------------------
    STREAMLIT BUTTON
    ------------------------------------------------------------*/

    /* Sample Triples */
    .st-key-btn_sample_triples button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 100%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Nodes by Label */
    .st-key-btn_nodes_by_label button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 100%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Subgraph Explorer */
    .st-key-btn_subgraph button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 100%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Search Entities */
    .st-key-btn_search_entities button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 30%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Entity Relationships */
    .st-key-btn_entity_relationships button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 100%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Check Relationship */
    .st-key-btn_check_relationship button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 100%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Predict Tail */
    .st-key-btn_predict_tail button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 100%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Prediction Rank */
    .st-key-btn_prediction_rank button {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: linear-gradient(to right, #dbe4ec, #f0f2f5);
        border: none;
        width: 100%;
        color: #2E7D32;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* Hypothesis Pipeline */
    .st-key-btn_hypothesis button {
    }

    /* -----------------------------------------------------------
    ANIMATIONS
    ------------------------------------------------------------*/
    @keyframes pulseDot {
        0%   { transform: scale(1);   opacity: .9; }
        50%  { transform: scale(1.25); opacity: 1; }
        100% { transform: scale(1);   opacity: .9; }
    }

    @keyframes emojiGlow {
        0% { filter: drop-shadow(0 0 0px rgba(96,165,250,0.25)); }
        50% { filter: drop-shadow(0 0 10px rgba(96,165,250,0.55)); }
        100% { filter: drop-shadow(0 0 0px rgba(96,165,250,0.25)); }
    }
    div[data-testid="column"] {
        margin-right: 1.2rem;
    }

    div[data-testid="column"]:last-child {
        margin-right: 0;
    }

    </style>
    """,
        unsafe_allow_html=True,
    )



    # ---------- DIALOGS FOR EACH SERVICE ----------

    @st.dialog("Sample Triples")
    def dlg_sample_triples():
        st.markdown("Retrieve representative triples for a given **relationship type**.")
        rel_type = st.text_input(
            "Relationship type",
            placeholder="e.g. GENE_GENE, GENE_DISEASE, GENE_PHENOTYPE",
        )
        if st.button("Fetch sample triples", disabled=not rel_type.strip()):
            try:
                with st.spinner("Fetching sample triples…"):
                    resp = _api_get("sample_triples", rel_type=rel_type.strip())
                st.success("Received triples:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")

    @st.dialog("Nodes by Label")
    def dlg_nodes_by_label():
        st.markdown(
            "Retrieve up to **10 nodes** for a given label "
            "(Gene, Protein, Disease, ChemicalEntity, Phenotype, Pathway, …)."
        )
        label = st.text_input(
            "Node label",
            placeholder="e.g. Gene, Protein, Disease, ChemicalEntity, Pathway",
        )
        if st.button("Get nodes", disabled=not label.strip()):
            try:
                with st.spinner("Calling `/get_nodes_by_label`…"):
                    resp = _api_get("get_nodes_by_label", label=label.strip())
                st.success("Nodes retrieved:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")


    @st.dialog("Subgraph Viewer")
    def dlg_subgraph():
        st.markdown(
            "Fetch a **local subgraph** around a node, defined by its label and ID/name."
        )
        col1, col2 = st.columns(2)
        with col1:
            node_label = st.text_input("Node label", placeholder="e.g. Gene, Protein")
            property_name = st.text_input(
                "Property name", placeholder="e.g. id, name"
            )
        with col2:
            property_value = st.text_input(
                "Property value", placeholder="e.g. ENSG00000141510 or TP53"
            )

        if st.button(
            "Retrieve subgraph",
            disabled=not (node_label.strip() and property_name.strip() and property_value.strip()),
        ):
            try:
                with st.spinner("Calling `/subgraph`…"):
                    resp = _api_get(
                        "subgraph",
                        property_name=property_name.strip(),
                        property_value=property_value.strip(),
                        node_label=node_label.strip(),
                    )
                st.success("Subgraph returned:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")


    @st.dialog("Search Biological Entities")
    def dlg_search_entities():
        st.markdown(
            "Search across genes, proteins, diseases, chemicals, pathways, phenotypes and more."
        )
        term = st.text_input(
            "Search term",
            placeholder="e.g. TP53, Alzheimer, metformin, cellular senescence",
        )
        if st.button("Search", disabled=not term.strip()):
            try:
                with st.spinner("Calling `/search_biological_entities`…"):
                    resp = _api_get(
                        "search_biological_entities", targetTerm=term.strip()
                    )
                st.success("Search results:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")


    @st.dialog("Entity Relationships")
    def dlg_entity_relationships():
        st.markdown(
            "Get related entities for a given node, optionally filtered by **relationship type**."
        )
        entity_type = st.text_input("Entity type", placeholder="e.g. Gene, Disease")
        property_name = st.text_input("Property name", placeholder="e.g. id, name")
        property_value = st.text_input(
            "Property value", placeholder="e.g. ENSG00000141510 or TP53"
        )
        relationship_type = st.text_input(
            "Relationship type (optional)",
            placeholder="e.g. GENE_DISEASE, PROTEIN_PROTEIN",
        )

        if st.button(
            "Retrieve relationships",
            disabled=not (entity_type.strip() and property_name.strip() and property_value.strip()),
        ):
            try:
                params = dict(
                    entity_type=entity_type.strip(),
                    property_name=property_name.strip(),
                    property_value=property_value.strip(),
                )
                if relationship_type.strip():
                    params["relationship_type"] = relationship_type.strip()

                with st.spinner("Calling `/entity_relationships`…"):
                    resp = _api_get("entity_relationships", **params)
                st.success("Relationships retrieved:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")


    @st.dialog("Check Relationship")
    def dlg_check_relationship():
        st.markdown("Check if a relationship exists between **two entities**.")

        st.caption("Entity 1")
        c1, c2, c3 = st.columns(3)
        with c1:
            e1_type = st.text_input("Type 1", placeholder="e.g. Gene")
        with c2:
            e1_prop = st.text_input("Prop 1", placeholder="e.g. id, name")
        with c3:
            e1_val = st.text_input("Value 1", placeholder="e.g. TP53")

        st.caption("Entity 2")
        d1, d2, d3 = st.columns(3)
        with d1:
            e2_type = st.text_input("Type 2", placeholder="e.g. Disease")
        with d2:
            e2_prop = st.text_input("Prop 2", placeholder="e.g. id, name")
        with d3:
            e2_val = st.text_input("Value 2", placeholder="e.g. lung cancer")

        disabled = not all(
            [
                e1_type.strip(),
                e1_prop.strip(),
                e1_val.strip(),
                e2_type.strip(),
                e2_prop.strip(),
                e2_val.strip(),
            ]
        )

        if st.button("Check relationship", disabled=disabled):
            try:
                params = dict(
                    entity1_type=e1_type.strip(),
                    entity1_property_name=e1_prop.strip(),
                    entity1_property_value=e1_val.strip(),
                    entity2_type=e2_type.strip(),
                    entity2_property_name=e2_prop.strip(),
                    entity2_property_value=e2_val.strip(),
                )
                with st.spinner("Calling `/check_relationship`…"):
                    resp = _api_get("check_relationship", **params)
                st.success("Result:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")


    @st.dialog("Predict Tail")
    def dlg_predict_tail():
        st.markdown(
            "Use EvoKG link prediction to suggest **tail entities** for a given head + relation."
        )
        head = st.text_input("Head model_id", placeholder="e.g. 12345")
        relation = st.text_input("Relation", placeholder="e.g. GENE_DISEASE")
        top_k = st.number_input("Top K predictions", min_value=1, max_value=50, value=10)

        if st.button(
            "Predict tails",
            disabled=not (head.strip() and relation.strip()),
        ):
            try:
                with st.spinner("Calling `/predict_tail`…"):
                    resp = _api_get(
                        "predict_tail",
                        head=str(head).strip(),
                        relation=relation.strip(),
                        top_k_predictions=int(top_k),
                    )
                st.success("Predictions:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")

    @st.dialog("Get Prediction Rank")
    def dlg_prediction_rank():
        st.markdown(
            "Retrieve the **rank and score** of a given head–relation–tail triple."
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            head = st.text_input("Head model_id", placeholder="e.g. 12345")
        with c2:
            relation = st.text_input("Relation", placeholder="e.g. GENE_DISEASE")
        with c3:
            tail = st.text_input("Tail model_id", placeholder="e.g. 67890")

        disabled = not (head.strip() and relation.strip() and tail.strip())

        if st.button("Get rank", disabled=disabled):
            try:
                with st.spinner("Calling `/get_prediction_rank`…"):
                    resp = _api_get(
                        "get_prediction_rank",
                        head=head.strip(),
                        relation=relation.strip(),
                        tail=tail.strip(),
                    )
                st.success("Rank info:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")


    @st.dialog("Run Hypothesis from Text")
    def dlg_hypothesis():
        st.markdown(
            "Run the full **hypothesis pipeline** using pre-extracted entities and a free-text hypothesis."
        )
        terms_str = st.text_input(
            "Extracted terms (comma-separated)",
            placeholder="e.g. Roxadustat, hemoglobin, CKD-related anemia, dialysis",
        )
        hypothesis = st.text_area(
            "Hypothesis text (optional, for context)",
            placeholder="Enter the original hypothesis text here…",
            height=120,
        )

        terms = [t.strip() for t in terms_str.split(",") if t.strip()]

        if st.button("Run hypothesis pipeline", disabled=not terms):
            try:
                payload = {
                    "terms": terms,
                    "per_type_limit": 10,
                    "hypothesis": hypothesis,
                }
                with st.spinner("Calling `/hypothesis/run_hypothesis_pipeline`…"):
                    resp = _api_post(
                        "hypothesis/run_hypothesis_pipeline", json_body=payload
                    )
                st.success("Pipeline output:")
                st.json(resp)
            except Exception as e:
                st.error("No matching result found.")


    # ---------- MICRO-SERVICE CARDS DEFINITION ----------
    services = [
        {
            "id": "sample_triples",
            "title": "Sample Triples",
            "emoji": "🧱",
            "desc": "Inspect representative KG triples for a given relation type.",
            "dialog": dlg_sample_triples,
        },
        {
            "id": "nodes_by_label",
            "title": "Nodes by Label",
            "emoji": "🏷️",
            "desc": "Fetch example nodes for a selected label (Gene, Protein, Disease…).",
            "dialog": dlg_nodes_by_label,
        },
        {
            "id": "subgraph",
            "title": "Subgraph Explorer",
            "emoji": "🕸️",
            "desc": "Retrieve a local neighborhood subgraph around a single node.",
            "dialog": dlg_subgraph,
        },
        {
            "id": "search_entities",
            "title": "Search Entities",
            "emoji": "🔍",
            "desc": "Search genes, diseases, chemicals, pathways and more by name or ID.",
            "dialog": dlg_search_entities,
        },
        {
            "id": "entity_relationships",
            "title": "Entity Relationships",
            "emoji": "🔗",
            "desc": "List related entities for a given node and relationship type.",
            "dialog": dlg_entity_relationships,
        },
        {
            "id": "check_relationship",
            "title": "Check Relationship",
            "emoji": "❓",
            "desc": "Verify whether a relationship exists between two entities.",
            "dialog": dlg_check_relationship,
        },
        {
            "id": "predict_tail",
            "title": "Predict Tail",
            "emoji": "🎯",
            "desc": "Run EvoKG link prediction to suggest plausible tail entities.",
            "dialog": dlg_predict_tail,
        },
        {
            "id": "prediction_rank",
            "title": "Prediction Rank",
            "emoji": "📊",
            "desc": "Inspect the rank and score of a specific head–relation–tail triple.",
            "dialog": dlg_prediction_rank,
        },
        {
            "id": "hypothesis",
            "title": "Hypothesis Pipeline",
            "emoji": "🧪",
            "desc": "Run the full hypothesis scoring and explanation pipeline from text.",
            "dialog": dlg_hypothesis,
        },
    ]

    # ---------- PAGE LAYOUT ----------
    st.markdown(
        """
        <div class="micro-page-wrapper">
            <div class="micro-header">
                <div>
                    <div class="micro-title">
                        <span>🧩</span> Micro-services
                    </div>
                    <div class="micro-subtitle">
                        Direct access to EvoAge’s knowledge-graph micro-services — ideal for debugging, exploration, and expert workflows.
                    </div>
                </div>
                <div class="micro-refresh-badge">
                    <div class="micro-refresh-dot"></div>
                    <span>Backend status: Healthy</span>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---------- MICRO SERVICE CARD RENDERING FUNCTION ----------
    def render_service_card(svc):
        st.markdown(
            f"""
            <div class="micro-card">
                <div class="micro-card-header">
                    <div class="micro-card-main">
                        <div class="micro-icon">{svc['emoji']}</div>
                        <div>
                            <div class="micro-card-title">{svc['title']}</div>
                            <div class="micro-card-desc">{svc['desc']}</div>
                        </div>
                    </div>
                    <div class="micro-card-status">
                        <span class="micro-card-status-dot"></span>
                        Healthy
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Open Service",
            key=f"btn_{svc['id']}",
            type="secondary",
            use_container_width=True,
        ):
            svc["dialog"]()

        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- RENDER MICRO-SERVICES USING 3-COLUMN LAYOUT ----------
    # Layout: [ LEFT CARD ]   [ SPACER ]   [ RIGHT CARD ]
    for i in range(0, len(services), 2):
        col_left, col_space, col_right = st.columns([1, 0.05, 1])  # middle = gap

        # LEFT ITEM
        with col_left:
            render_service_card(services[i])

        # RIGHT ITEM (if available)
        if i + 1 < len(services):
            with col_right:
                render_service_card(services[i + 1])

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

