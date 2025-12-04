import streamlit as st

def show_intro_page():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    [data-testid="stMainBlockContainer"] {{
        padding-bottom: 0 !important;
        margin-bottom: 0 !important;
    }}
    :root {{
        --primary:#0f4c81;
        --gradient:linear-gradient(135deg,#1f8ef1,#0f4c81);
        --text:#3d3e40;
        --muted:#6e7c95;
        --card-bg:#ffffff;
        --radius:14px;
        --shadow:0 25px 60px -15px rgba(31,45,58,0.08);
        --transition:.18s ease;
        --body-font: 'Inter', system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    }}

    .evokg-container {{
        max-width: 1150px;
        margin: 0 auto;
        padding: 1rem 1rem 3rem;
        font-family: var(--body-font);
        color: var(--text);
    }}

    .evokg-header-wrapper {{
        text-align: center;
        margin-bottom: 0.5rem;
    }}

    .evokg-header {{
        font-size: 2.8rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.05;
        letter-spacing: -0.5px;
        font-family: var(--body-font);
    }}

    .evokg-subheader {{
        font-size: 1rem;
        margin-top: 4px;
        color: var(--muted);
        font-weight: 500;
        line-height: 1.4;
    }}

    .evokg-divider {{
        width: 70px;
        height: 4px;
        background: var(--primary);
        border-radius: 2px;
        margin: 0.75rem auto 1.25rem;
    }}

    .evokg-page-card {{
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 1.5rem 1.75rem;
        margin: 0.5rem 0;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow);
        border: 1px solid rgba(15,76,129,0.07);
        transition: transform var(--transition), box-shadow var(--transition);
    }}

    .evokg-page-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 35px 80px -20px rgba(31,45,58,0.12);
    }}

    .evokg-page-title {{
        font-size: 1.6rem;
        font-weight: 600;
        margin: 0 0 6px;
        color: #3d3e40;
        position: relative;
        display: inline-block;
        font-family: var(--body-font);
    }}

    .evokg-page-title:after {{
        content: "";
        display: block;
        height: 3px;
        width: 60px;
        background: var(--primary);
        border-radius: 2px;
        margin-top: 6px;
    }}

    .evokg-page-content {{
        font-size: 1rem;
        line-height: 1.55;
        margin-top: 6px;
        color: #2f3e52;
    }}

    .evokg-features-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit,minmax(260px,1fr));
        gap: 1.5rem;
        margin: 1.5rem 0 2rem;
    }}

    .evokg-feature-card {{
        background: #eeeeee;
        border-radius: 12px;
        padding: 1.25rem 1rem 1.5rem;
        display: flex;
        flex-direction: column;
        min-height: 190px;
        border: 1px solid rgba(15,76,129,0.05);
        transition: transform var(--transition), box-shadow var(--transition);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }}

    .evokg-feature-card:hover {{
        transform: translateY(-1px);
        box-shadow: 0 25px 65px -15px rgba(31,45,58,0.3);
    }}

    .evokg-feature-icon {{
        font-size: 1.8rem;
        margin-bottom: 6px;
    }}

    .evokg-feature-title {{
        font-size: 1.1rem;
        font-weight: 600;
        margin: 4px 0 6px;
        color: #3d3e40;
    }}

    .evokg-feature-desc {{
        flex-grow: 1;
        font-size: 0.9rem;
        color: #455a7f;
        line-height: 1.35;
    }}

    .evokg-cta {{
        display: flex;
        justify-content: center;
        margin: 2rem 0 1rem;
    }}

    .evokg-cta-button {{
        background: #dbe4ec;
        color: #ffffff;
        padding: 0.9rem 2rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 1.05rem;
    }}
    .evokg-cta-button:hover {{
        filter: brightness(1.1);
        transform: translateY(-1px);
        box-shadow: 0 25px 70px -10px rgba(47, 47, 56, 0.55);
    }}
    .evokg-cta-button:active {{
        transform: translateY(1px);
        box-shadow: 0 12px 40px -5px rgba(15, 76, 129, 0.35);
    }}
    /* if using <a> ensure no underline */
    .evokg-cta-button[href] {{
        text-decoration: none;
    }}

    @media (max-width: 980px) {{
        .evokg-header {{ font-size: 2.2rem; }}
        .evokg-page-title {{ font-size: 1.4rem; }}
    }}
    </style>

    <div class="evokg-container">
        <div class="evokg-header-wrapper">
            <div class="evokg-header">Welcome to EvoAge</div>
            <div class="evokg-subheader">
                Your knowledge-augmented interface for exploring evolutionary biological insights and predicting connections.
            </div>
            <div class="evokg-divider"></div>
        </div>
        <div class="evokg-page-card">
            <div class="evokg-page-title">What is EvoAge?</div>
            <div class="evokg-page-content">
                EvoAge fuses a large language model with a deep evolutionary knowledge graph to power biologically grounded
                reasoning. Query cross-species relationships, prioritize aging influencers from transcriptomic signal, and generate
                explainable hypotheses by combining graph topology, gene embeddings, and expression context.
            </div>
        </div>
        <div class="evokg-features-grid">
            <div class="evokg-feature-card">
                <div class="evokg-feature-icon">🧬</div>
                <div class="evokg-feature-title">Cross-species Insight</div>
                <div class="evokg-feature-desc">
                    Transfer knowledge along evolutionary paths to uncover conserved aging mechanisms and infer missing links.
                </div>
            </div>
            <div class="evokg-feature-card">
                <div class="evokg-feature-icon">📊</div>
                <div class="evokg-feature-title">Transcriptomic Context</div>
                <div class="evokg-feature-desc">
                    Weight graph evidence by sample-level gene expression to highlight genes or chemicals most likely influencing age-related phenotypes.
                </div>
            </div>
            <div class="evokg-feature-card">
                <div class="evokg-feature-icon">🤖</div>
                <div class="evokg-feature-title">LLM-Augmented Reasoning</div>
                <div class="evokg-feature-desc">
                    Natural language queries are enriched with structured KG signals, producing interpretable answers and candidate hypotheses.
                </div>
            </div>
        </div>
        <div class="evokg-page-card">
            <div class="evokg-page-title">Getting Started</div>
            <div class="evokg-page-content">
                <p>Click on <strong>"Start Chatting"</strong> or type your query to begin. Ask about genes, aging markers,
                or potential chemical modulators and receive biologically contextualized insights.</p>
                <p>Switch modes in the sidebar: <em>Exploration</em>, <em>Prediction</em>, and <em>Evidence</em> to tailor the workflow.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
