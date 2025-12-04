import streamlit as st

def show_about_page():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                
    [data-testid="stMainBlockContainer"] {{
        padding-bottom: 0 !important;
        margin-bottom: 0 !important;
    }}
    :root {{
        --primary:#0f4c81;
        --accent:#1f8ef1;
        --text:#1f2d3a;
        --muted:#6e7c95;
        --card-bg:#ffffff;
        --radius:14px;
        --shadow:0 25px 60px -15px rgba(31,45,58,0.08);
        --transition:.18s ease;
        --body-font: 'Inter', system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    }}

    .about-container {{
        max-width: 1150px;
        margin: 0 auto;
        padding: 1rem 1rem 3rem;
        font-family: var(--body-font);
        color: var(--text);
    }}
    .about-header {{
        text-align: center;
        margin-bottom: 0.25rem;
    }}
    .about-title {{
        font-size: 2.8rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }}
    .about-subtitle {{
        font-size: 1rem;
        color: var(--muted);
        margin-top: 6px;
        font-weight: 500;
    }}
    .divider {{
        width: 70px;
        height: 4px;
        background: var(--primary);
        border-radius: 2px;
        margin: 0.75rem auto 1.5rem;
    }}

    .section {{
        margin-top: 1.75rem;
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
    }}
    .card {{
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 1.5rem 1.75rem;
        flex: 1 1 320px;
        box-shadow: var(--shadow);
        border: 1px solid rgba(15,76,129,0.07);
        position: relative;
        transition: transform var(--transition), box-shadow var(--transition);
    }}
    .card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 35px 80px -20px rgba(31,45,58,0.12);
    }}
    .card-title {{
        font-size: 1.6rem;
        font-weight: 600;
        margin-bottom: 6px;
        color: #3d3e40;
        position: relative;
        display: inline-block;
    }}
    .card-title:after {{
        content: "";
        display: block;
        height: 3px;
        width: 50px;
        background: var(--primary);
        border-radius: 2px;
        margin-top: 6px;
    }}
    .card-content {{
        font-size: 1rem;
        line-height: 1.5;
        margin-top: 8px;
        color: #2f3e52;
    }}
    .team-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit,minmax(220px,1fr));
        gap: 1.25rem;
        margin-top: 0.5rem;
    }}
    .team-member {{
        background: #f7f9fc;
        border-radius: 10px;
        padding: 1rem 1rem 1.25rem;
        display: flex;
        flex-direction: column;
        border: 1px solid rgba(15,76,129,0.05);
    }}
    .member-name {{
        font-weight: 600;
        font-size: 1.05rem;
        margin: 0;
        color: #3d3e40;
    }}
    .member-role {{
        font-size: 0.9rem;
        margin: 4px 0 8px;
        color: #455a7f;
    }}
    .member-links {{
        margin-top: auto;
        font-size: 0.85rem;
    }}
    .badge {{
        display: inline-block;
        background: var(--accent);
        color: white;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.6rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-right: 6px;
    }}
    .tech-stack {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 6px;
    }}
    .tech-pill {{
        background: rgba(15,76,129,0.08);
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--primary);
    }}
    .small {{
        font-size: 0.9rem;
    }}
    </style>

    <div class="about-container">
        <div class="about-header">
            <div class="about-title">About EvoAge</div>
            <div class="about-subtitle">
                A knowledge-augmented assistant blending evolutionary biology and language understanding to surface aging-relevant insights.
            </div>
            <div class="divider"></div>
        </div>
        <div class="section">
            <div class="card">
                <div class="card-title">Our Mission</div>
                <div class="card-content">
                    Empower researchers with biologically grounded, interpretable reasoning by combining evolutionary knowledge graphs
                    with large language models to identify candidate aging influencers and generate hypotheses with context.
                </div>
            </div>
            <div class="card">
                <div class="card-title">Our Vision</div>
                <div class="card-content">
                    To make cross-species biological knowledge and transcriptomic context easily queryable in natural language, accelerating
                    discovery in aging biology and translational interventions.
                </div>
            </div>
        </div>
        <div class="section">
            <div class="card" style="flex:2 1 640px;">
                <div class="card-title">Why EvoAge?</div>
                <div class="card-content">
                    Traditional query systems separate structured biological knowledge from flexible reasoning. EvoAge bridges that gap:
                    it fuses a rich evolutionary knowledge graph (capturing conserved relationships across species) with gene expression context,
                    and augments that with large language model understanding to provide natural-language answers that cite biologically meaningful evidence.
                    The result is explainable, multi-view insight into genes, chemicals, and aging phenotypes.
                </div>
            </div>
        </div>
        <div class="section">
            <div class="card">
                <div class="card-title">Core Capabilities</div>
                <div class="card-content">
                    <ul style="padding-left:1.2em; margin:0;">
                        <li>Cross-species inference using evolutionary paths.</li>
                        <li>Expression-weighted prioritization of aging-related genes and chemicals.</li>
                        <li>LLM-augmented natural language querying with KG evidence.</li>
                        <li>Explainable hypothesis generation and ranking.</li>
                    </ul>
                </div>
            </div>
            <div class="card">
                <div class="card-title">Tech Stack</div>
                <div class="card-content">
                    <div class="tech-stack">
                        <div class="tech-pill">PyTorch</div>
                        <div class="tech-pill">DGL-KE</div>
                        <div class="tech-pill">Streamlit</div>
                        <div class="tech-pill">OpenAI / LLM Engine</div>
                        <div class="tech-pill">Knowledge Graphs</div>
                        <div class="tech-pill">GTEx Transcriptomics</div>
                        <div class="tech-pill">NumPy / Pandas</div>
                        <div class="tech-pill">Custom Fusion Logic</div>
                    </div>
                    <div class="small" style="margin-top:8px;">
                        Plus auxiliary tooling for authentication, user quotas, and interactive exploration.
                    </div>
                </div>
            </div>
        </div>
        <div class="section">
            <div class="card" style="flex:2 1 640px;">
                <div class="card-title">Team</div>
                <div class="card-content">
                    <div class="team-grid">
                        <div class="team-member">
                            <div class="member-name">Arushi Sharma</div>
                            <div class="member-role">PhD, CB Department</div>
                            <div class="member-links">
                                <div><a href="#" target="_blank">GitHub Profile</a></div>
                            </div>
                        </div>
                        <div class="team-member">
                            <div class="member-name">Ankit Singh</div>
                            <div class="member-role">Developer, CB Department</div>
                            <div class="member-links">
                                <div><a href="#" target="_blank">GitHub Profile</a></div>
                            </div>
                        </div>
                        <!-- add others similarly -->
                    </div>
                </div>
            </div>
        </div>
        <div class="section">
            <div class="card">
                <div class="card-title">Contact & Feedback</div>
                <div class="card-content">
                    <p class="small">
                        For questions, feedback, or to report issues, reach out:
                    </p>
                    <ul style="padding-left:1.2em; margin:0;">
                        <li><strong>Email:</strong> <a href="mailto:gaurav.ahuja@iiitd.ac.in">gaurav.ahuja@iiitd.ac.in</a></li>
                        <li><strong>Repository:</strong> <a href="#" target="_blank">Evo-KG-Chatbot</a></li>
                    </ul>
                </div>
            </div>
            <div class="card">
                <div class="card-title">Roadmap</div>
                <div class="card-content">
                    <ul style="padding-left:1.2em; margin:0;">
                        <li>Integrate additional species and modalities (e.g., proteomics).</li>
                        <li>Improved causal inference over aging pathways.</li>
                        <li>User-customizable query templates and saved sessions.</li>
                        <li>Feedback loop to refine LLM grounding from user validation.</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
