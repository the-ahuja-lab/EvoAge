import streamlit as st

def show_how_to_use_page():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {{
        --primary:#0f4c81;
        --accent:#1f8ef1;
        --text:#1f2d3a;
        --muted:#6e7c95;
        --card-bg:rgba(255,255,255,0.65);
        --radius:22px;
        --shadow:0 18px 48px -18px rgba(20,45,80,0.16);
        --body-font:'Inter',system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;
    }}

    .block-container {{
        max-width: 90%;
        margin: 0 auto;
        padding-top: 1.7rem;
    }}

    [data-testid="stHeader"] {{ display: none !important; }}

    .howto-container {{
        max-width: 100%;
        margin: 0rem 0rem 0rem 0rem;
        padding: 0.5rem 1rem 0.7rem;
        font-family: var(--body-font);
    }}

    /* ============================
       ANIMATIONS
    ============================ */

    @keyframes emojiGlow {{
        0% {{ filter: drop-shadow(0 0 0px rgba(80,150,255,0.4)); }}
        50% {{ filter: drop-shadow(0 0 12px rgba(80,150,255,0.9)); }}
        100% {{ filter: drop-shadow(0 0 0px rgba(80,150,255,0.4)); }}
    }}

    @keyframes emojiSpin {{
        0% {{ transform: rotate(0deg) scale(1); }}
        40% {{ transform: rotate(14deg) scale(1.12); }}
        100% {{ transform: rotate(0deg) scale(1); }}
    }}

    .howto-title span,
    .card-title span {{
        animation: emojiGlow 1s ease-in-out infinite;
        display: inline-block;
        cursor: pointer;
        transition: 0.25s ease;
    }}

    .howto-title span:hover,
    .card-title span:hover {{
        animation: emojiSpin 0.7s ease-in-out, emojiGlow 3s ease-in-out infinite;
    }}

    @keyframes fadeIn {{
        0% {{ opacity: 0; transform: translateY(12px); }}
        100% {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes borderGlow {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    /* ============================
       HEADER CARD
    ============================ */

    .howto-header-wrapper {{
        text-align: center;
        padding: 1rem 1rem;
        margin-bottom: 1rem;
        border-radius: 20px;
        background: var(--card-bg);
        backdrop-filter: blur(14px);
        border: 1.5px solid rgba(180,200,255,0.30);
        box-shadow: 0 12px 32px rgba(0,0,0,0.10),
                    inset 0 0 16px rgba(200,220,255,0.22);
        position: relative;
        animation: fadeIn 1s ease-out;
        overflow: hidden;
    }}

    .howto-header-wrapper::before {{
        content: "";
        position: absolute;
        inset: 0;
        padding: 2px;
        border-radius: 20px;
        background: linear-gradient(
            120deg,
            rgba(150,180,255,0.45),
            rgba(255,255,255,0.20),
            rgba(130,160,255,0.45)
        );
        mask:
            linear-gradient(#fff 0 0) content-box,
            linear-gradient(#fff 0 0);
        mask-composite: exclude;
        animation: borderGlow 6s linear infinite;
    }}

    .howto-title {{
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        color: #1a2b47;
    }}

    .howto-subtitle {{
        font-size: 0.92rem;
        color: var(--muted);
        max-width: 650px;
        margin: 0.3rem auto 0.4rem;
    }}

    .divider {{
        width: 90px;
        height: 3px;
        margin: 0.4rem auto 0.8rem;
        border-radius: 3px;
        background: linear-gradient(90deg, #74a6f7, #0f4c81, #74a6f7);
        animation: borderGlow 3s linear infinite;
    }}

    /* ============================
       CARDS
    ============================ */

    .card {{
        background: var(--card-bg);
        border-radius: 18px;
        padding: 1rem 1.2rem;
        margin: 0.7rem 0;
        box-shadow: var(--shadow);
        border: 1px solid rgba(130,160,255,0.25);
        backdrop-filter: blur(10px);
        animation: fadeIn .7s ease-out;
        transition: 0.25s ease;
    }}

    .card:hover {{
        transform: translateY(-4px) scale(1.01);
        box-shadow: 0 28px 55px -14px rgba(31,45,88,0.18);
    }}

    .card-title {{
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }}

    .card-content {{
        font-size: 0.90rem;
        line-height: 1.45;
    }}

    /* Icon bullets */
    .card-content ul {{
        list-style: none;
        padding-left: 0;
    }}

    .card-content ul li::before {{
        content: "✨";
        margin-right: 0.4rem;
    }}
    /* --- Glass Card Expander Wrapper --- */
    [data-testid="stExpander"] {{
        background: rgba(255, 255, 255, 0.65) !important;
        border-radius: 18px !important;
        padding: 0 !important;
        max-width: 600px !important; 
        margin: 0rem 0rem 0rem 1rem !important;
        border: 1px solid rgba(130,160,255,0.35) !important;
        box-shadow: 0 18px 48px -18px rgba(20,45,80,0.16) !important;
        backdrop-filter: blur(10px) !important;
    }}

    /* --- Glass Card Expander INNER content --- */
    [data-testid="stExpander"] > div {{
        background: rgba(255, 255, 255, 0.75) !important;
        border-radius: 18px !important;
        padding: 1rem 1.2rem !important;
        max-width: 600px !important; 
        border: none !important;
    }}


    </style>

    <div class="howto-container">
        <!-- HEADER -->
        <div class="howto-header-wrapper">
            <div class="howto-title"><span>💡</span> How to Use EvoAge</div>
            <div class="howto-subtitle">
                A quick guide to get the most out of EvoAge’s AI-powered biological knowledge graph assistant.
            </div>
            <div class="divider"></div>
        </div>
        <!-- CARD 1 -->
        <div class="card">
            <div class="card-title"><span>🔍</span> To search nodes of specific node type</div>
            <div class="card-content">
                <ul>
                    <li>“Give sample gene from EvoAge.”</li>
                    <li>“Give sample Biological process which are in EvoAge.”</li>
                </ul>
            </div>
        </div>
        <!-- CARD 2 -->
        <div class="card">
            <div class="card-title"><span>🔗</span> To get sample triples of a relation from EvoAge</div>
            <div class="card-content">
                <ul>
                    <li>"Give sample triple of Gene Disease relation."</li>
                    <li>"Give sample triple of pathway gene relation."</li>
                </ul>
            </div>
        </div>
        <!-- CARD 3 -->
        <div class="card">
            <div class="card-title"><span>🧬</span> To get information of particular node in KG</div>
            <div class="card-content">
                <ul>
                    <li>“Give information of TP53 from EvoAge KG.”</li>
                    <li>“Is node 'Single Strand Break Repair' present in EvoAge?”</li>
                </ul>
            </div>
        </div>
        <!-- CARD 4 -->
        <div class="card">
            <div class="card-title"><span>📊</span> To get no. of connections of a particular nodes in KG</div>
            <div class="card-content">
                <ul>
                    <li>“With how many nodes myocyte enhancer factor 2A is connecte in KG?”</li>
                    <li>“How many connections STAT3 have in KG?”</li>
                </ul>
            </div>
        </div>
        <!-- CARD 5 -->
        <div class="card">
            <div class="card-title"><span>🧠</span> To get ground truth triples connected to a node</div>
            <div class="card-content">
                <ul>
                    <li>“Give gene connected to myocyte enhancer factor 2A in kG.”</li>
                    <li>“What are the biological process with which gene ABL1 is connected?”</li>
                </ul>
            </div>
        </div>
        <!-- CARD 6 -->
        <div class="card">
            <div class="card-title"><span>📈</span> To get predictions</div>
            <div class="card-content">
                <ul>
                    <li>“Predict molecular function for gene STAT3?”</li>
                    <li>“Predict potential relation of disease for gene ABL1.”</li>
                </ul>
            </div>
        </div>
        <!-- CARD 7 -->
        <div class="card">
            <div class="card-title"><span>📏</span> To get triple ranks and score</div>
            <div class="card-content">
                <ul>
                    <li>“Give triple score of TP53 and ABL1.”</li>
                    <li>“Predict rank of SOX2 with Neoplasms.”</li>
                </ul>
            </div>
        </div>
        <!-- CARD 8 -->
        <div class="card">
            <div class="card-title"><span>📁</span> Download Your Chat</div>
            <div class="card-content">
                Every conversation can be exported in TXT format using the sidebar download menu.
            </div>
        </div>
        <!-- CARD 9 -->
        <div class="card">
            <div class="card-title"><span>⚡</span> Quick Tips</div>
            <div class="card-content">
                <ul>
                    <li>Be specific: “TP53 gene in humans” is better than just “TP53”.</li>
                    <li>If unsure, try asking “What can I ask you?”</li>
                    <li>Use prediction tasks when exploring new ideas.</li>
                    <li><strong>For prediction tasks:</strong> Start your query with the keyword  
                        <em>“predict”</em> (e.g., “Predict diseases associated with TP53”).  
                        EvoAge detects predictions more reliably with this prefix.</li>
                    <li><strong>For hypothesis testing:</strong> Begin your query with  
                        <em>“I hypothesize…”</em> or <em>“My hypothesis is…”</em> to ensure EvoAge  
                        automatically triggers the hypothesis pipeline.</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("📂 View All Relation Types in EvoAge"):
        st.markdown(
            """
            <div style="font-size: 0.92rem; line-height: 1.45;">
            <ul>
                <li>phenotype_chemicalentity</li>
                <li>mutation_disease</li>
                <li>molecularfunction_chemicalentity</li>
                <li>disease_anatomy</li>
                <li>chemicalentity_disease</li>
                <li>disease_disease</li>
                <li>biologicalprocess_gene</li>
                <li>protein_protein</li>
                <li>gene_phenotype</li>
                <li>protein_disease</li>
                <li>anatomy_gene</li>
                <li>chemicalentity_biologicalprocess</li>
                <li>disease_gene</li>
                <li>gene_cellularcomponent</li>
                <li>chemicalentity_chemicalentity</li>
                <li>cellularcomponent_gene</li>
                <li>gene_disease</li>
                <li>protein_cellularcomponent</li>
                <li>protein_phenotype</li>
                <li>mutation_protein</li>
                <li>chemicalentity_gene</li>
                <li>chemicalentity_tissue</li>
                <li>chemicalentity_protein</li>
                <li>biologicalprocess_biologicalprocess</li>
                <li>phenotype_phenotype</li>
                <li>phenotype_gene</li>
                <li>chemicalentity_inhibits_biologicalprocess</li>
                <li>gene_inhibits_biologicalprocess</li>
                <li>protein_biologicalprocess</li>
                <li>gene_promotes_biologicalprocess</li>
                <li>gene_molecularfunction</li>
                <li>gene_pathway</li>
                <li>chemicalentity_pathway</li>
                <li>gene_tissue</li>
                <li>disease_phenotype</li>
                <li>chemicalentity_mutation</li>
                <li>gene_anatomy</li>
                <li>phenotype_disease</li>
                <li>pathway_gene</li>
                <li>disease_chemicalentity</li>
                <li>disease_mutation</li>
                <li>gene_chemicalentity</li>
                <li>protein_pathway</li>
                <li>gene_protein</li>
                <li>gene_noeffect_biologicalprocess</li>
                <li>chemicalentity_promotes_biologicalprocess</li>
                <li>gene_biologicalprocess</li>
                <li>protein_molecularfunction</li>
                <li>mutation_gene</li>
                <li>gene_gene</li>
                <li>molecularfunction_molecularfunction</li>
                <li>gene_mutation</li>
                <li>molecularfunction_biologicalprocess</li>
                <li>protein_tissue</li>
                <li>cellularcomponent_cellularcomponent</li>
                <li>pathway_pathway</li>
                <li>anatomy_anatomy</li>
                <li>biologicalprocess_chemicalentity</li>
                <li>plantextract_chemicalentity</li>
                <li>plantextract_disease</li>
                <li>pmid_cellularcomponent</li>
                <li>pmid_chemicalentity</li>
                <li>pmid_disease</li>
                <li>pmid_protein</li>
                <li>pmid_tissue</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True
        )
