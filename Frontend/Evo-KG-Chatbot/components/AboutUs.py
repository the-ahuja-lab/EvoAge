import streamlit as st

def show_about_page():
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

    /* Match intro spacing */
    .block-container {{
        max-width: 90%;
        margin: 0 auto;
        padding-top: 1.7rem;
    }}
    [data-testid="stHeader"] {{ display: none !important; }}
    .about-container {{
        max-width: 100%;
        margin: 0 auto;
        padding: 0.5rem 1rem 2rem;
        font-family: var(--body-font);
    }}

    /* ============================
       ANIMATIONS (restored)
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

    /* Apply glow + spin to ALL emojis inside titles */
    .about-title span,
    .card-title span {{
        animation: emojiGlow 3s ease-in-out infinite;
        display: inline-block;
        cursor: pointer;
        transition: 0.25s ease;
    }}

    .about-title span:hover,
    .card-title span:hover {{
        animation: emojiSpin 0.7s ease-in-out, emojiGlow 3s ease-in-out infinite;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes borderGlow {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    /* ============================
       HEADER CARD (matches intro)
    ============================ */

    .about-header-wrapper {{
        text-align: center;
        padding: 0.9rem 1rem;
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

    .about-header-wrapper::before {{
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

    .about-title {{
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        color: #1a2b47;
    }}

    .about-subtitle {{
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
       CARDS (Intro style matching)
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

    /* ============================
       TEAM GRID (compressed)
    ============================ */

    .team-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 0.7rem;
        margin-top: 0.4rem;
    }}

    .team-member {{
        background: rgba(255,255,255,0.92);
        border-radius: 14px;
        padding: 0.7rem 0.9rem;
        border: 1px solid rgba(120,150,200,0.25);
        box-shadow: 0 10px 22px rgba(0,0,0,0.08);
        transition: .25s;
    }}

    .team-member:hover {{
        transform: translateY(-4px);
        box-shadow: 0 25px 45px rgba(31,45,88,0.18);
    }}

    .member-name {{
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a2b47;
    }}

    .member-role {{
        font-size: .85rem;
        color: var(--muted);
        margin-bottom: .6rem;
    }}
    </style>

    <div class="about-container">
        <div class="about-header-wrapper">
            <div class="about-title">
                <span>📘</span> About EvoAge
            </div>
            <div class="about-subtitle">
                An explainable, knowledge-augmented AI assistant built on evolutionary biology, graph reasoning, and advanced language models.
            </div>
            <div class="divider"></div>
        </div>
        <div class="card">
            <div class="card-title"><span>🎯</span> Our Mission</div>
            <div class="card-content">
                Empower researchers by combining evolution-guided biological knowledge with LLM-based reasoning to
                surface interpretable aging insights, predict novel biological links, and evaluate scientific hypotheses.
            </div>
        </div>
        <div class="card">
            <div class="card-title"><span>🧬</span> What is EvoAge?</div>
            <div class="card-content">
                EvoAge is an integrative, multi-species knowledge graph that consolidates diverse aging databases (AgeAnno, AgeAnnoMO, AgeXtend, Aging Atlas, CellAge, Digital Aging Atlas, DrugAge, GenDR, GeneAge, HALD, MetaboAge, EvoKG) into a unified framework. It enables evolutionary cross-species inference of aging biology, supports systematic evaluation of chemicals, and provides a foundation for explainable hypothesis generation and predictive modeling of novel aging-related mechanisms.
            </div>
        </div>
        <div class="card">
            <div class="card-title"><span>🌐</span> Core Capabilities</div>
            <div class="card-content">
                <ul style="padding-left:1.2em; margin:0;">
                    <li>Evolutionary cross-species inference via orthologous knowledge paths.</li>
                    <li>Graph exploration and query execution powered by Neo4j and Cypher.</li>
                    <li>Predictive modeling of novel links and edges across biological entities.</li>
                    <li>LLM-guided natural language interrogation of the knowledge graph with evidential support.</li>
                    <li>Explainable hypothesis generation, scoring, and comparative ranking.</li>
                </ul>
            </div>
        </div>
        <div class="card">
            <div class="card-title"><span>⚙️</span> Tech Stack</div>
            <div class="card-content">
                FastAPI • DGL-KE • Kani Framework • Neo4j • Cypher • Streamlit • Graph Embeddings • OpenAI Engine
            </div>
        </div>
        <div class="card">
            <div class="card-title"><span>👥</span> Team</div>
            <div class="card-content">
                <div class="team-grid">
                    <div class="team-member">
                        <div class="member-name">Arushi Sharma</div>
                        <div class="member-role">PhD, CB Department</div>
                        <a href="https://github.com/AruShar" target="_blank">GitHub Profile</a>
                    </div>
                    <div class="team-member">
                        <div class="member-name">Ankit Singh</div>
                        <div class="member-role">Developer, CB Department</div>
                        <a href="https://github.com/zakmii" target="_blank">GitHub Profile</a>
                    </div>
                    <div class="team-member">
                        <div class="member-name">Abhinav Kumar Sharma</div>
                        <div class="member-role">PhD (Frontend Developer)</div>
                        <a href="https://github.com/abhinavsharma767" target="_blank">GitHub Profile</a>
                    </div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-title"><span>📞</span> Contact & Feedback</div>
            <div class="card-content">
                <ul>
                    <li><strong>Email:</strong> arushis@iiitd.ac.in, ankit21450@iiitd.ac.in</li>
                    <li><strong>GitHub:</strong> <a href="https://github.com/the-ahuja-lab/EvoAge-backend">EvoAge</a></li>
                    <li><strong>Lab Website:</strong> <a href="https://www.ahuja-lab.in/">Ahuja Lab</a></li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)




# import streamlit as st
# import pathlib

# def show_about_page():
#     current_dir = pathlib.Path(__file__).parent.absolute()
#     logo_path = current_dir / "assets" / "logo.png"
#     logo_path = str(logo_path) if logo_path.exists() else None

#     st.markdown(f"""
#     <style>
#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                
#     [data-testid="stMainBlockContainer"] {{
#         padding-bottom: 0 !important;
#         margin-bottom: 0 !important;
#     }}
#     :root {{
#         --primary:#0f4c81;
#         --accent:#1f8ef1;
#         --text:#1f2d3a;
#         --muted:#6e7c95;
#         --card-bg:#ffffff;
#         --radius:14px;
#         --shadow:0 25px 60px -15px rgba(31,45,58,0.08);
#         --transition:.18s ease;
#         --body-font: 'Inter', system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
#     }}

#     .about-container {{
#         max-width: 1150px;
#         margin: 0 auto;
#         padding: 1rem 1rem 3rem;
#         font-family: var(--body-font);
#         color: var(--text);
#     }}
#     .about-header {{
#         text-align: center;
#         margin-bottom: 0.25rem;
#     }}
#     .about-title {{
#         font-size: 2.8rem;
#         font-weight: 700;
#         margin: 0;
#         letter-spacing: -0.5px;
#     }}
#     .about-subtitle {{
#         font-size: 1rem;
#         color: var(--muted);
#         margin-top: 6px;
#         font-weight: 500;
#     }}
#     .divider {{
#         width: 70px;
#         height: 4px;
#         background: var(--primary);
#         border-radius: 2px;
#         margin: 0.75rem auto 1.5rem;
#     }}

#     .section {{
#         margin-top: 1.75rem;
#         display: flex;
#         flex-wrap: wrap;
#         gap: 1.5rem;
#     }}
#     .card {{
#         background: var(--card-bg);
#         border-radius: var(--radius);
#         padding: 1.5rem 1.75rem;
#         flex: 1 1 320px;
#         box-shadow: var(--shadow);
#         border: 1px solid rgba(15,76,129,0.07);
#         position: relative;
#         transition: transform var(--transition), box-shadow var(--transition);
#     }}
#     .card:hover {{
#         transform: translateY(-2px);
#         box-shadow: 0 35px 80px -20px rgba(31,45,58,0.12);
#     }}
#     .card-title {{
#         font-size: 1.6rem;
#         font-weight: 600;
#         margin-bottom: 6px;
#         color: #3d3e40;
#         position: relative;
#         display: inline-block;
#     }}
#     .card-title:after {{
#         content: "";
#         display: block;
#         height: 3px;
#         width: 50px;
#         background: var(--primary);
#         border-radius: 2px;
#         margin-top: 6px;
#     }}
#     .card-content {{
#         font-size: 1rem;
#         line-height: 1.5;
#         margin-top: 8px;
#         color: #2f3e52;
#     }}
#     .team-grid {{
#         display: grid;
#         grid-template-columns: repeat(auto-fit,minmax(220px,1fr));
#         gap: 1.25rem;
#         margin-top: 0.5rem;
#     }}
#     .team-member {{
#         background: #f7f9fc;
#         border-radius: 10px;
#         padding: 1rem 1rem 1.25rem;
#         display: flex;
#         flex-direction: column;
#         border: 1px solid rgba(15,76,129,0.05);
#     }}
#     .member-name {{
#         font-weight: 600;
#         font-size: 1.05rem;
#         margin: 0;
#         color: #3d3e40;
#     }}
#     .member-role {{
#         font-size: 0.9rem;
#         margin: 4px 0 8px;
#         color: #455a7f;
#     }}
#     .member-links {{
#         margin-top: auto;
#         font-size: 0.85rem;
#     }}
#     .badge {{
#         display: inline-block;
#         background: var(--accent);
#         color: white;
#         padding: 3px 10px;
#         border-radius: 999px;
#         font-size: 0.6rem;
#         font-weight: 600;
#         text-transform: uppercase;
#         letter-spacing: 1px;
#         margin-right: 6px;
#     }}
#     .tech-stack {{
#         display: flex;
#         flex-wrap: wrap;
#         gap: 10px;
#         margin-top: 6px;
#     }}
#     .tech-pill {{
#         background: rgba(15,76,129,0.08);
#         padding: 6px 12px;
#         border-radius: 999px;
#         font-size: 0.8rem;
#         font-weight: 500;
#         color: var(--primary);
#     }}
#     .small {{
#         font-size: 0.9rem;
#     }}

#     /* --- Logo card --- */
#     .card-logo {{
#         display: flex;
#         flex-direction: column;
#         align-items: center;
#         justify-content: center;
#         text-align: center;
#         padding: 2rem 1rem;
#     }}
#     .card-logo img {{
#         max-width: 220px;
#         height: auto;
#         border-radius: 14px;
#         box-shadow: 0 4px 12px rgba(0,0,0,0.15);
#     }}
#     .card-logo .card-content {{
#         margin-top: 10px;
#         font-style: italic;
#         color: #3a4a61;
#     }}
#     </style>
    
#     <div class="about-container">
#         <div class="about-header">
#             <div class="about-title">About EvoAge</div>
#             <div class="about-subtitle">
#                 A knowledge-augmented assistant blending evolutionary biology and language understanding to surface aging-relevant insights.
#             </div>
#             <div class="divider"></div>
#         </div>
#         <div class="section">
#             <!-- Replaced 'Our Mission' card with logo -->
#             <div class="card card-logo">
#                 <img src="/home/pushpendrag/ankiss/evo_chatbot/Evo-KG-Chatbot/assets/logo.png" alt="EvoAge Logo" />
#                 <div class="card-content">
#                     "Integrating Evolutionary Biology with AI-driven Knowledge Discovery"
#                 </div>
#             </div>
#             <div class="card">
#                 <div class="card-title">What is EvoAge?</div>
#                 <div class="card-content">
#                     EvoAge is an integrative, multi-species knowledge graph that consolidates diverse aging databases (AgeAnno, AgeAnnoMO, AgeXtend, Aging Atlas, CellAge, Digital Aging Atlas, DrugAge, GenDR, GeneAge, HALD, MetaboAge, EvoKG) into a unified framework. It enables evolutionary cross-species inference of aging biology, supports systematic evaluation of chemicals in the context of cellular senescence, and provides a foundation for explainable hypothesis generation and predictive modeling of novel aging-related mechanisms.
#                 </div>
#             </div>
#         </div>
#         <div class="section">
#             <div class="card">
#                 <div class="card-title">Core Capabilities</div>
#                 <div class="card-content">
#                     <ul style="padding-left:1.2em; margin:0;">
#                         <li>Evolutionary cross-species inference via orthologous knowledge paths.</li>
#                         <li>Graph exploration and query execution powered by Neo4j and Cypher.</li>
#                         <li>Predictive modeling of novel links and edges across biological entities.</li>
#                         <li>LLM-guided natural language interrogation of the knowledge graph with evidential support.</li>
#                         <li>Explainable hypothesis generation, scoring, and comparative ranking.</li>
#                     </ul>
#                 </div>
#             </div>
#             <div class="card">
#                 <div class="card-title">Tech Stack</div>
#                 <div class="card-content">
#                     <div class="tech-stack">
#                         <div class="tech-pill">PyTorch</div>
#                         <div class="tech-pill">DGL-KE</div>
#                         <div class="tech-pill">Kani Framework</div>
#                         <div class="tech-pill">OpenAI / LLM Engine</div>
#                         <div class="tech-pill">Neo4j</div>
#                         <div class="tech-pill">Cypher</div>
#                         <div class="tech-pill">Streamlit</div>
#                         <div class="tech-pill">NumPy / Pandas</div>
#                         <div class="tech-pill">Custom Fusion Logic</div>
#                     </div>
#                     <div class="small" style="margin-top:8px;">
#                         Plus Auxiliary Tooling for Authentication, User Quotas & Interactive Exploration.
#                     </div>
#                 </div>
#             </div>
#         </div>
#         <div class="section">
#             <div class="card" style="flex:2 1 640px;">
#                 <div class="card-title">Team</div>
#                 <div class="card-content">
#                     <div class="team-grid">
#                         <div class="team-member">
#                             <div class="member-name">Arushi Sharma</div>
#                             <div class="member-role">PhD, CB Department</div>
#                             <div class="member-links"><a href="#" target="_blank">GitHub Profile</a></div>
#                         </div>
#                         <div class="team-member">
#                             <div class="member-name">Ankit Singh</div>
#                             <div class="member-role">Developer, CB Department</div>
#                             <div class="member-links"><a href="#" target="_blank">GitHub Profile</a></div>
#                         </div>
#                         <div class="team-member">
#                             <div class="member-name">Abhinav Kumar Sharma</div>
#                             <div class="member-role">PhD (Frontend Developer), CB Department</div>
#                             <div class="member-links"><a href="#" target="_blank">GitHub Profile</a></div>
#                         </div>
#                     </div>
#                 </div>
#             </div>
#         </div>
#         <div class="section">
#             <div class="card">
#                 <div class="card-title">Contact & Feedback</div>
#                 <div class="card-content">
#                     <p class="small">
#                         For questions, feedback, or to report issues, reach out:
#                     </p>
#                     <ul style="padding-left:1.2em; margin:0;">
#                         <li><strong>Email:</strong> 
#                             <span style="font-size:0.9em;">
#                                 <a href="mailto:arushis@iiitd.ac.in">arushis@iiitd.ac.in</a>, 
#                                 <a href="mailto:ankit21450@iiitd.ac.in">ankit21450@iiitd.ac.in</a>
#                             </span>
#                         </li>
#                         <li><strong>Github:</strong> 
#                             <a href="https://github.com/the-ahuja-lab/EvoAge-backend">EvoAge</a>
#                         </li>
#                         <li><strong>Lab Website:</strong> 
#                             <a href="https://www.ahuja-lab.in/">Ahuja-lab</a>
#                         </li>
#                     </ul>
#                 </div>
#             </div>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

########################################################################### 20 NOV #########################################################
# import streamlit as st

# def show_about_page():
#     st.markdown(f"""
#     <style>
#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                
#     [data-testid="stMainBlockContainer"] {{
#         padding-bottom: 0 !important;
#         margin-bottom: 0 !important;
#     }}
#     :root {{
#         --primary:#0f4c81;
#         --accent:#1f8ef1;
#         --text:#1f2d3a;
#         --muted:#6e7c95;
#         --card-bg:#ffffff;
#         --radius:14px;
#         --shadow:0 25px 60px -15px rgba(31,45,58,0.08);
#         --transition:.18s ease;
#         --body-font: 'Inter', system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
#     }}
#     .block-container {{
#         max-width: 90%;
#         margin: 0 auto;
#         padding-top: 2rem;
#     }}
#     .about-container {{
#         max-width: 100%;
#         margin: 0 auto;
#         padding: 1rem 1rem 3rem;
#         font-family: var(--body-font);
#         color: var(--text);
#     }}
#     .about-header {{
#         text-align: center;
#         margin-bottom: 0.25rem;
#     }}
#     .about-title {{
#         font-size: 2.8rem;
#         font-weight: 700;
#         margin: 0;
#         letter-spacing: -0.5px;
#     }}
#     .about-subtitle {{
#         font-size: 1rem;
#         color: var(--muted);
#         margin-top: 6px;
#         font-weight: 500;
#     }}
#     .divider {{
#         width: 70px;
#         height: 4px;
#         background: var(--primary);
#         border-radius: 2px;
#         margin: 0.75rem auto 1.5rem;
#     }}

#     .section {{
#         margin-top: 1.75rem;
#         display: flex;
#         flex-wrap: wrap;
#         gap: 1.5rem;
#     }}
#     .card {{
#         background: var(--card-bg);
#         border-radius: var(--radius);
#         padding: 1.5rem 1.75rem;
#         flex: 1 1 320px;
#         box-shadow: var(--shadow);
#         border: 1px solid rgba(15,76,129,0.07);
#         position: relative;
#         transition: transform var(--transition), box-shadow var(--transition);
#     }}
#     .card:hover {{
#         transform: translateY(-2px);
#         box-shadow: 0 35px 80px -20px rgba(31,45,58,0.12);
#     }}
#     .card-title {{
#         font-size: 1.6rem;
#         font-weight: 600;
#         margin-bottom: 6px;
#         color: #3d3e40;
#         position: relative;
#         display: inline-block;
#     }}
#     .card-title:after {{
#         content: "";
#         display: block;
#         height: 3px;
#         width: 50px;
#         background: var(--primary);
#         border-radius: 2px;
#         margin-top: 6px;
#     }}
#     .card-content {{
#         font-size: 1rem;
#         line-height: 1.5;
#         margin-top: 8px;
#         color: #2f3e52;
#     }}
#     .team-grid {{
#         display: grid;
#         grid-template-columns: repeat(auto-fit,minmax(220px,1fr));
#         gap: 1.25rem;
#         margin-top: 0.5rem;
#     }}
#     .team-member {{
#         background: #f7f9fc;
#         border-radius: 10px;
#         padding: 1rem 1rem 1.25rem;
#         display: flex;
#         flex-direction: column;
#         border: 1px solid rgba(15,76,129,0.05);
#     }}
#     .member-name {{
#         font-weight: 600;
#         font-size: 1.05rem;
#         margin: 0;
#         color: #3d3e40;
#     }}
#     .member-role {{
#         font-size: 0.9rem;
#         margin: 4px 0 8px;
#         color: #455a7f;
#     }}
#     .member-links {{
#         margin-top: auto;
#         font-size: 0.85rem;
#     }}
#     .badge {{
#         display: inline-block;
#         background: var(--accent);
#         color: white;
#         padding: 3px 10px;
#         border-radius: 999px;
#         font-size: 0.6rem;
#         font-weight: 600;
#         text-transform: uppercase;
#         letter-spacing: 1px;
#         margin-right: 6px;
#     }}
#     .tech-stack {{
#         display: flex;
#         flex-wrap: wrap;
#         gap: 10px;
#         margin-top: 6px;
#     }}
#     .tech-pill {{
#         background: rgba(15,76,129,0.08);
#         padding: 6px 12px;
#         border-radius: 999px;
#         font-size: 0.8rem;
#         font-weight: 500;
#         color: var(--primary);
#     }}
#     .small {{
#         font-size: 0.9rem;
#     }}
#     </style>

#     <div class="about-container">
#         <div class="about-header">
#             <div class="about-title">About EvoAge</div>
#             <div class="about-subtitle">
#                 A knowledge-augmented assistant blending evolutionary biology and language understanding to surface aging-relevant insights.
#             </div>
#             <div class="divider"></div>
#         </div>
#         <div class="section">
#             <div class="card">
#                 <div class="card-title">Our Mission</div>
#                 <div class="card-content">
#                     Empower researchers with biologically grounded, interpretable reasoning by combining evolutionary knowledge graphs
#                     with large language models to identify candidate aging influencers and generate hypotheses with context.
#                 </div>
#             </div>
#             <div class="card">
#                 <div class="card-title">What is EvoAge?</div>
#                 <div class="card-content">
#                     EvoAge is an integrative, multi-species knowledge graph that consolidates diverse aging databases (AgeAnno, AgeAnnoMO, AgeXtend, Aging Atlas, CellAge, Digital Aging Atlas, DrugAge, GenDR, GeneAge, HALD, MetaboAge, EvoKG) into a unified framework. It enables evolutionary cross-species inference of aging biology, supports systematic evaluation of chemicals in the context of cellular senescence, and provides a foundation for explainable hypothesis generation and predictive modeling of novel aging-related mechanisms.
#                 </div>
#             </div>
#         </div>
#         <div class="section">
#             <div class="card">
#                 <div class="card-title">Core Capabilities</div>
#                 <div class="card-content">
#                     <ul style="padding-left:1.2em; margin:0;">
#                         <li>Evolutionary cross-species inference via orthologous knowledge paths.</li>
#                         <li>Graph exploration and query execution powered by Neo4j and Cypher.</li>
#                         <li>Predictive modeling of novel links and edges across biological entities.</li>
#                         <li>LLM-guided natural language interrogation of the knowledge graph with evidential support.</li>
#                         <li>Explainable hypothesis generation, scoring, and comparative ranking.</li>
#                     </ul>
#                 </div>
#             </div>
#             <div class="card">
#                 <div class="card-title">Tech Stack</div>
#                 <div class="card-content">
#                     <div class="tech-stack">
#                         <div class="tech-pill">PyTorch</div>
#                         <div class="tech-pill">DGL-KE</div>
#                         <div class="tech-pill">Kani Framework</div>
#                         <div class="tech-pill">OpenAI / LLM Engine</div>
#                         <div class="tech-pill">Neo4j</div>
#                         <div class="tech-pill">Cypher</div>
#                         <div class="tech-pill">Streamlit</div>
#                         <div class="tech-pill">NumPy / Pandas</div>
#                         <div class="tech-pill">Custom Fusion Logic</div>
#                     </div>
#                     <div class="small" style="margin-top:8px;">
#                         Plus Auxiliary Tooling for Authentication, User Quotas & Interactive Exploration.
#                     </div>
#                 </div>
#             </div>
#         </div>
#         <div class="section">
#             <div class="card" style="flex:2 1 640px;">
#                 <div class="card-title">Team</div>
#                 <div class="card-content">
#                     <div class="team-grid">
#                         <div class="team-member">
#                             <div class="member-name">Arushi Sharma</div>
#                             <div class="member-role">PhD, CB Department</div>
#                             <div class="member-links">
#                                 <div><a href="https://github.com/AruShar" target="_blank">GitHub Profile</a></div>
#                             </div>
#                         </div>
#                         <div class="team-member">
#                             <div class="member-name">Ankit Singh</div>
#                             <div class="member-role">Developer, CB Department</div>
#                             <div class="member-links">
#                                 <div><a href="https://github.com/zakmii" target="_blank">GitHub Profile</a></div>
#                             </div>
#                         </div>
#                         <div class="team-member">
#                             <div class="member-name">Abhinav Kumar Sharma</div>
#                             <div class="member-role">PhD (Frontend Developer), CB Department</div>
#                             <div class="member-links">
#                                 <div><a href="https://github.com/abhinavsharma767" target="_blank">GitHub Profile</a></div>
#                             </div>
#                         </div>
#                     </div>
#                 </div>
#             </div>
#         </div>
#         <div class="section">
#             <div class="card">
#                 <div class="card-title">Contact & Feedback</div>
#                 <div class="card-content">
#                     <p class="small">
#                         For questions, feedback, or to report issues, reach out:
#                     </p>
#                     <ul style="padding-left:1.2em; margin:0;">
#                     <li><strong>Email:</strong> 
#                         <span style="font-size:0.9em;">
#                         <a href="mailto:arushis@iiitd.ac.in">arushis@iiitd.ac.in</a>, 
#                         <a href="mailto:ankit21450@iiitd.ac.in">ankit21450@iiitd.ac.in</a>
#                         </span>
#                     </li>
#                     <li><strong>Github:</strong> 
#                         <a href="https://github.com/the-ahuja-lab/EvoAge-backend">EvoAge</a>
#                     </li>
#                     <li><strong>Lab Website:</strong> 
#                         <a href="https://www.ahuja-lab.in/">Ahuja-lab</a>
#                     </li>
#                     </ul>
#                 </div>
#             </div>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)


