import streamlit as st

def show_intro_page():
    st.markdown(f"""
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {{
        --primary:#0f4c81;
        --gradient:linear-gradient(135deg,#1f8ef1,#0f4c81);
        --text:#2f3e52;
        --muted:#6e7c95;
        --card-bg:rgba(255,255,255,0.65);
        --shadow:0 25px 60px -15px rgba(31,45,58,0.10);
        --radius:18px;
        --body-font:'Inter',system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;
    }}

    html, body {{
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden;  /* No scrolling */
    }}

    .block-container {{
        max-width: 92%;
        margin: 0 auto;
        padding-top: 1.6rem;    /* Reduced */
    }}
    [data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        height: 100vh;
        overflow: hidden;  /* Important: full-page fixed */
    }}

    .evokg-container {{
        max-width: 100%;
        margin: 0 auto;
        padding: 0.3rem 1rem 0.3rem; /* Reduced vertical padding */
        font-family: var(--body-font);
    }}

    /* ================= HEADER CARD ================== */
    .evokg-header-wrapper {{
        text-align: center;
        padding: 0.7rem 1rem;   /* Reduced */
        border-radius: 20px;
        background: var(--card-bg);
        backdrop-filter: blur(14px);
        border: 1.5px solid rgba(180,200,255,0.30);
        box-shadow: 0 10px 28px rgba(0,0,0,0.08);
        position: relative;
        animation: fadeIn 1.1s ease-out;
        overflow: hidden;
    }}

    .evokg-header-wrapper::before {{
        content: "";
        position: absolute;
        inset: 0;
        padding: 2px;
        border-radius: 18px;
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
        pointer-events: none;
    }}

    .evokg-header {{
        font-size: 2.2rem;     /* Reduced */
        font-weight: 800;
        margin: 0;
        color: #1a2b47;
    }}

    .evokg-subheader {{
        font-size: 0.92rem;    /* Reduced */
        color: var(--muted);
        max-width: 560px;
        margin: 0.1rem auto 0.2rem;
    }}

    .evokg-divider {{
        width: 90px; 
        height: 3px; 
        margin: 0.3rem auto 0.6rem; /* Reduced spacing */
        border-radius: 3px;
        background: linear-gradient(90deg, #74a6f7, #0f4c81, #74a6f7);
        animation: dividerGlow 3s linear infinite;
    }}

    /* ================= CONTENT CARD ================== */
    .evokg-page-card {{
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 1.0rem 1.2rem;   /* Reduced */
        margin: 0.9rem 0 0.6rem 0;  /* Reduced */
        box-shadow: 0 12px 32px -12px rgba(31,45,58,0.12); 
        border: 1px solid rgba(15,76,129,0.10);
        backdrop-filter: blur(10px);
        animation: fadeIn 0.8s ease-out;
    }}

    .evokg-page-title {{
        font-size: 1.35rem;  /* Reduced */
        font-weight: 700;
        margin-bottom: 0.3rem;
    }}

    .evokg-page-content {{
        font-size: 0.90rem; /* Reduced */
        line-height: 1.45;
    }}

    /* ================= FEATURES GRID ================== */
    .evokg-features-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); 
        gap: 0.55rem;   /* Reduced */
        margin: 0.4rem 0;
    }}

    .evokg-feature-card {{
        padding: 0.55rem 0.5rem;  /* Reduced */
        border-radius: 12px;
        border: 1px solid rgba(120,150,200,0.25);
        box-shadow: 0 10px 22px rgba(0,0,0,0.08);
        text-align: center;
        background: rgba(255,255,255,0.92);
    }}

    .evokg-feature-title {{
        font-size: 0.95rem;  /* Reduced */
        font-weight: 700;
        margin-bottom: 3px;
    }}

    .evokg-feature-desc {{
        font-size: 0.78rem;   /* Reduced */
        line-height: 1.2;
    }}

    /* ================= ANIMATIONS ================== */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes borderGlow {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    @keyframes emojiGlow {{
        50% {{ filter: drop-shadow(0 0 10px rgba(80, 150, 255, 0.8)); }}
    }}

    @keyframes emojiSpin {{
        0% {{ transform: rotate(0deg) scale(1); }}
        40% {{ transform: rotate(14deg) scale(1.12); }}
        100% {{ transform: rotate(0deg) scale(1); }}
    }}

    .evokg-header-emoji {{
        font-size: 1.3rem;
        display: inline-block;
        animation: emojiGlow 1s ease-in-out infinite;
        cursor: pointer;
    }}

    .evokg-header-emoji:hover {{
        animation: emojiSpin 0.7s ease-in-out, emojiGlow 3s ease-in-out infinite;
    }}

    .evokg-feature-icon {{
        font-size: 1.6rem;
        animation: emojiGlow 1.4s ease-in-out infinite;
        margin-bottom: 4px;
    }}

    .evokg-feature-icon:hover {{
        animation: emojiSpin 0.7s ease-in-out, emojiGlow 3s ease-in-out infinite;
    }}
    /* Consistent large-title emoji animation (matches header style) */
    .evokg-title-emoji {{
        font-size: 1.5rem;
        display: inline-block;
        animation: emojiGlow 3s ease-in-out infinite;
        cursor: pointer;
        vertical-align: middle;
    }}

    .evokg-title-emoji:hover {{
        animation: emojiSpin 0.7s ease-in-out, emojiGlow 3s ease-in-out infinite;
    }}

    .bubble-highlight {{
    display: inline-block;
    color: #0f4c81;
    font-weight: 700;
    animation: pulseSoft 1s ease-in-out infinite;
    }}
    @keyframes pulseSoft {{
        0% {{ transform: scale(1); opacity: 0.9; }}
        50% {{ transform: scale(1.07); opacity: 1; }}
        100% {{ transform: scale(1); opacity: 0.9; }}
    }}

    </style>
    <div class="evokg-container">
        <!-- ================= HEADER ================= -->
        <div class="evokg-header-wrapper">
            <div class="evokg-header">
                <span class="evokg-header-emoji">✨</span>
                Welcome to EvoAge
            </div>
            <div class="evokg-subheader">
                An AI-powered platform for cross-species aging research—built on a unified graph of 
                <span class="bubble-highlight">1.04B</span> biological relationships.
            </div>
            <div class="evokg-divider"></div>
        </div>
        <!-- ================= WHAT IS ================= -->
        <div class="evokg-page-card">
            <div class="evokg-page-title">
                <span class="evokg-header-emoji">🧬</span> What is EvoAge?
            </div>
            <div class="evokg-page-content">
                EvoAge integrates 48 aging and biomedical databases into a human-centric knowledge graph spanning six model organisms.
                Through orthology-based mapping and optimized graph embeddings, it enables discovery of conserved aging mechanisms 
                and supports AI-driven hypothesis testing.
            </div>
        </div>
        <!-- ================= FEATURES ================= -->
        <div class="evokg-features-grid">
            <div class="evokg-feature-card">
                <div class="evokg-feature-icon">🔍</div>
                <div class="evokg-feature-title">Explore Knowledge</div>
                <div class="evokg-feature-desc">
                    Query over <b>1.04B</b> relationships across six species.
                </div>
            </div>
            <div class="evokg-feature-card">
                <div class="evokg-feature-icon">⚡</div>
                <div class="evokg-feature-title">Predict Links</div>
                <div class="evokg-feature-desc">
                    Discover new connections using optimized KG embeddings.
                </div>
            </div>
            <div class="evokg-feature-card">
                <div class="evokg-feature-icon">🧪</div>
                <div class="evokg-feature-title">Test Hypotheses</div>
                <div class="evokg-feature-desc">
                    Evaluate biological hypotheses with quantitative scoring.
                </div>
            </div>
        </div>
        <!-- ================= GETTING STARTED ================= -->
        <div class="evokg-page-card">
            <div class="evokg-page-title">
                <span class="evokg-title-emoji">🚀</span> Getting Started
            </div>
            <div class="evokg-page-content">
                Enter natural-language queries about genes, pathways, diseases, aging processes, or relationships.<br><br>
                EvoAge will route your request to:
                <br>
                • <strong>Knowledge Retrieval</strong><br>
                • <strong>Link Prediction</strong><br>
                • <strong>Hypothesis Testing</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
#################################################################################################################################################
# import streamlit as st

# def show_intro_page():
#     st.markdown(f"""
#     <style>

#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

#     :root {{
#         --primary:#0f4c81;
#         --gradient:linear-gradient(135deg,#1f8ef1,#0f4c81);
#         --text:#2f3e52;
#         --muted:#6e7c95;
#         --card-bg:rgba(255,255,255,0.65);
#         --shadow:0 25px 60px -15px rgba(31,45,58,0.10);
#         --radius:18px;
#         --body-font:'Inter',system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;
#     }}

#     .block-container {{
#         max-width: 90%;
#         margin: 0 auto;
#         padding-top: 2rem;
#     }}

#     /* Global Container */
#     .evokg-container {{
#         max-width: 100%;
#         margin: 0 auto;
#         padding: 2rem 1rem 4rem;
#         font-family: var(--body-font);
#     }}

#     /* Animated gradient title card */
#     .evokg-header-wrapper {{
#         text-align: center;
#         padding: 2.4rem 1.8rem;
#         border-radius: 26px;
#         background: var(--card-bg);
#         backdrop-filter: blur(14px);
#         -webkit-backdrop-filter: blur(14px);
#         border: 1.5px solid rgba(180,200,255,0.30);
#         box-shadow:
#             0 15px 40px rgba(0,0,0,0.12),
#             inset 0 0 18px rgba(200,220,255,0.22);
#         position: relative;
#         animation: fadeIn 1.3s ease-out;
#         overflow: hidden;
#     }}

#     /* Glowing border */
#     .evokg-header-wrapper::before {{
#         content: "";
#         position: absolute;
#         inset: 0;
#         padding: 2px;
#         border-radius: 26px;
#         background: linear-gradient(
#             120deg,
#             rgba(150,180,255,0.45),
#             rgba(255,255,255,0.20),
#             rgba(130,160,255,0.45)
#         );
#         mask:
#             linear-gradient(#fff 0 0) content-box,
#             linear-gradient(#fff 0 0);
#         mask-composite: exclude;
#         animation: borderGlow 6s linear infinite;
#         pointer-events: none;
#     }}

#     /* Fade In */
#     @keyframes fadeIn {{
#         from {{ opacity: 0; transform: translateY(10px); }}
#         to {{ opacity: 1; transform: translateY(0); }}
#     }}

#     @keyframes borderGlow {{
#         0% {{ background-position: 0% 50%; }}
#         50% {{ background-position: 100% 50%; }}
#         100% {{ background-position: 0% 50%; }}
#     }}

#     /* ✨ GLOW EFFECT for emojis */
#     @keyframes emojiGlow {{
#         0% {{ filter: drop-shadow(0 0 0px rgba(80, 150, 255, 0.4)); }}
#         50% {{ filter: drop-shadow(0 0 12px rgba(80, 150, 255, 0.9)); }}
#         100% {{ filter: drop-shadow(0 0 0px rgba(80, 150, 255, 0.4)); }}
#     }}

#     /* ✨ Hover Spin Animation */
#     @keyframes emojiSpin {{
#         0% {{ transform: rotate(0deg) scale(1); }}
#         40% {{ transform: rotate(14deg) scale(1.12); }}
#         100% {{ transform: rotate(0deg) scale(1); }}
#     }}

#     /* Header emoji class */
#     .evokg-header-emoji {{
#         display: inline-block;
#         animation: emojiGlow 3s ease-in-out infinite;
#         font-size: 1.4rem;
#         margin-right: 6px;
#         cursor: pointer;
#     }}

#     .evokg-header-emoji:hover {{
#         animation: emojiSpin 0.7s ease-in-out, emojiGlow 3s ease-in-out infinite;
#     }}

#     /* Feature icons */
#     .evokg-feature-icon {{
#         font-size: 2.2rem;
#         margin-bottom: 10px;
#         display: inline-block;
#         animation: emojiGlow 1s ease-in-out infinite;
#         cursor: pointer;
#     }}

#     .evokg-feature-icon:hover {{
#         animation: emojiSpin 0.7s ease-in-out, emojiGlow 3s ease-in-out infinite;
#     }}

#     /* Title */
#     .evokg-header {{
#         font-size: 3rem;
#         font-weight: 800;
#         margin-bottom: .3rem;
#         color: #1a2b47;
#     }}

#     .evokg-subheader {{
#         font-size: 1.1rem;
#         color: var(--muted);
#         font-weight: 500;
#         max-width: 650px;
#         margin: 0 auto;
#     }}

#     /* Animated Divider */
#     .evokg-divider {{
#         width: 140px;
#         height: 4px;
#         margin: 1rem auto 1.5rem;
#         border-radius: 4px;
#         background: linear-gradient(90deg, #74a6f7, #0f4c81, #74a6f7);
#         animation: dividerGlow 3s linear infinite;
#     }}

#     @keyframes dividerGlow {{
#         0% {{ background-position: 0% 50%; }}
#         50% {{ background-position: 100% 50%; }}
#         100% {{ background-position: 0% 50%; }}
#     }}

#     /* Content Cards */
#     .evokg-page-card {{
#         background: var(--card-bg);
#         border-radius: var(--radius);
#         padding: 1.8rem 2rem;
#         margin: 1.8rem 0;
#         box-shadow: var(--shadow);
#         border: 1px solid rgba(15,76,129,0.10);
#         backdrop-filter: blur(10px);
#         animation: fadeIn 0.8s ease-out;
#         transition: 0.3s ease;
#     }}

#     .evokg-page-card:hover {{
#         transform: translateY(-3px);
#         box-shadow: 0 35px 70px -15px rgba(31,45,58,0.18);
#     }}

#     .evokg-page-title {{
#         font-size: 1.65rem;
#         font-weight: 700;
#         margin-bottom: .5rem;
#         color: #1a2b47;
#     }}

#     .evokg-page-title::after {{
#         content: "";
#         width: 65px;
#         height: 3px;
#         background: var(--primary);
#         display: block;
#         margin-top: 8px;
#         border-radius: 3px;
#     }}

#     /* Grid */
#     .evokg-features-grid {{
#         display: grid;
#         grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
#         gap: 1.5rem;
#         margin: 2rem 0;
#     }}

#     /* Feature Card */
#     .evokg-feature-card {{
#         background: rgba(250,250,255,0.9);
#         border-radius: 18px;
#         padding: 1.5rem 1.2rem;
#         border: 1px solid rgba(120,150,200,0.25);
#         box-shadow: 0 12px 25px rgba(0,0,0,0.1);
#         text-align: center;
#         transition: 0.3s ease;
#     }}

#     .evokg-feature-card:hover {{
#         transform: translateY(-4px) scale(1.02);
#         box-shadow: 0 25px 65px rgba(31,45,58,0.22);
#         background: rgba(255,255,255,0.95);
#     }}

#     .evokg-feature-title {{
#         font-size: 1.2rem;
#         font-weight: 700;
#         margin-bottom: 6px;
#         color: #1a2b47;
#     }}

#     .evokg-feature-desc {{
#         font-size: 0.95rem;
#         line-height: 1.45;
#         color: var(--muted);
#     }}
#     @keyframes waveText {{
#         0%   {{ transform: translateY(0); }}
#         25%  {{ transform: translateY(-5px); }}
#         50%  {{ transform: translateY(0); }}
#         75%  {{ transform: translateY(5px); }}
#         100% {{ transform: translateY(0); }}
#     }}

#     .wave-highlight {{
#         display: inline-block;
#         font-weight: 700;
#         color: #0f4c81;
#         animation: waveText 2.2s ease-in-out infinite;
#     }}
#     @keyframes bubbleFloat {{
#         0%   {{ transform: translateY(0) scale(1); }}
#         25%  {{ transform: translateY(-4px) scale(1.04); }}
#         50%  {{ transform: translateY(0) scale(0.98); }}
#         75%  {{ transform: translateY(3px) scale(1.02); }}
#         100% {{ transform: translateY(0) scale(1); }}
#     }}

#     .bubble-highlight {{
#         display: inline-block;
#         color: #0f4c81;
#         font-weight: 700;
#         animation: bubbleFloat 2.6s ease-in-out infinite;
#         text-shadow: 0 1px 2px rgba(0,0,0,0.10);
#     }}


#     </style>
#     <div class="evokg-container">
#         <div class="evokg-header-wrapper">
#             <div class="evokg-header">
#                 <span class="evokg-header-emoji">✨</span>
#                 Welcome to EvoAge
#             </div>
#             <div class="evokg-subheader">
#                 An AI-powered platform for cross-species aging research—built on a unified graph of 
#                 <span class="bubble-highlight">1.04B</span> biological relationships.
#             </div>
#             <div class="evokg-divider"></div>
#         </div>
#         <div class="evokg-page-card">
#             <div class="evokg-page-title"><span class="evokg-header-emoji">🧬</span> What is EvoAge?</div>
#             <div class="evokg-page-content">
#                 EvoAge integrates 48 aging and biomedical databases into a human-centric knowledge graph spanning six model organisms.
#                 Through orthology-based mapping and optimized graph embeddings, it enables discovery of conserved aging mechanisms 
#                 and supports AI-driven hypothesis testing.
#             </div>
#         </div>
#         <div class="evokg-features-grid">
#             <div class="evokg-feature-card">
#                 <div class="evokg-feature-icon">🔍</div>
#                 <div class="evokg-feature-title">Explore Knowledge</div>
#                 <div class="evokg-feature-desc">
#                     Query over <b>1.04B</b> relationships across humans, mice, flies, worms, zebrafish, and yeast.
#                 </div>
#             </div>
#             <div class="evokg-feature-card">
#                 <div class="evokg-feature-icon">⚡</div>
#                 <div class="evokg-feature-title">Predict Links</div>
#                 <div class="evokg-feature-desc">
#                     Discover new connections using optimized KG embeddings (RotatE architecture).
#                 </div>
#             </div>
#             <div class="evokg-feature-card">
#                 <div class="evokg-feature-icon">🧪</div>
#                 <div class="evokg-feature-title">Test Hypotheses</div>
#                 <div class="evokg-feature-desc">
#                     Evaluate biological hypotheses with quantitative scoring and graph-supported evidence.
#                 </div>
#             </div>
#         </div>
#         <div class="evokg-page-card">
#             <div class="evokg-page-title"><div class="evokg-feature-icon">🚀</div> Getting Started</div>
#             <div class="evokg-page-content">
#                 Enter natural-language queries about genes, pathways, diseases, aging processes, or relationships.<br><br>
#                 EvoAge will route your request to:
#                 <br><br>
#                 • <strong>Knowledge Retrieval</strong><br>
#                 • <strong>Link Prediction</strong><br>
#                 • <strong>Hypothesis Testing</strong>
#             </div>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)


# def show_intro_page():
#     st.markdown(f"""
#     <style>
#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
#     [data-testid="stMainBlockContainer"] {{
#         padding-bottom: 0 !important;
#         margin-bottom: 0 !important;
#     }}
#     :root {{
#         --primary:#0f4c81;
#         --gradient:linear-gradient(135deg,#1f8ef1,#0f4c81);
#         --text:#3d3e40;
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
#     .evokg-container {{
#         max-width: 100%;
#         width: 100%;
#         margin: 0 auto;
#         padding: 1rem 1rem 3rem;
#         font-family: var(--body-font);
#         color: var(--text);
#     }}


#     .evokg-header-wrapper {{
#         text-align: center;
#         margin-bottom: 0.5rem;
#     }}

#     .evokg-header {{
#         font-size: 2.8rem;
#         font-weight: 700;
#         margin: 0;
#         line-height: 1.05;
#         letter-spacing: -0.5px;
#         font-family: var(--body-font);
#     }}

#     .evokg-subheader {{
#         font-size: 1rem;
#         margin-top: 4px;
#         color: var(--muted);
#         font-weight: 500;
#         line-height: 1.4;
#     }}

#     .evokg-divider {{
#         width: 70px;
#         height: 4px;
#         background: var(--primary);
#         border-radius: 2px;
#         margin: 0.75rem auto 1.25rem;
#     }}

#     .evokg-page-card {{
#         background: var(--card-bg);
#         border-radius: var(--radius);
#         padding: 1.5rem 1.75rem;
#         margin: 0.5rem 0;
#         position: relative;
#         overflow: hidden;
#         box-shadow: var(--shadow);
#         border: 1px solid rgba(15,76,129,0.07);
#         transition: transform var(--transition), box-shadow var(--transition);
#     }}

#     .evokg-page-card:hover {{
#         transform: translateY(-2px);
#         box-shadow: 0 35px 80px -20px rgba(31,45,58,0.12);
#     }}

#     .evokg-page-title {{
#         font-size: 1.6rem;
#         font-weight: 600;
#         margin: 0 0 6px;
#         color: #3d3e40;
#         position: relative;
#         display: inline-block;
#         font-family: var(--body-font);
#     }}

#     .evokg-page-title:after {{
#         content: "";
#         display: block;
#         height: 3px;
#         width: 60px;
#         background: var(--primary);
#         border-radius: 2px;
#         margin-top: 6px;
#     }}

#     .evokg-page-content {{
#         font-size: 1rem;
#         line-height: 1.55;
#         margin-top: 6px;
#         color: #2f3e52;
#     }}

#     .evokg-features-grid {{
#         display: grid;
#         grid-template-columns: repeat(auto-fit,minmax(260px,1fr));
#         gap: 1.5rem;
#         margin: 1.5rem 0 2rem;
#     }}

#     .evokg-feature-card {{
#         background: #eeeeee;
#         border-radius: 12px;
#         padding: 1.25rem 1rem 1.5rem;
#         display: flex;
#         flex-direction: column;
#         min-height: 190px;
#         border: 1px solid rgba(15,76,129,0.05);
#         transition: transform var(--transition), box-shadow var(--transition);
#         box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
#         text-align: center;
#         justify-content: center;
#         align-items: center;

#     }}

#     .evokg-feature-card:hover {{
#         transform: translateY(-1px);
#         box-shadow: 0 25px 65px -15px rgba(31,45,58,0.3);
#     }}

#     .evokg-feature-icon {{
#         font-size: 1.8rem;
#         margin-bottom: 6px;
#     }}

#     .evokg-feature-title {{
#         font-size: 1.1rem;
#         font-weight: 600;
#         margin: 4px 0 6px;
#         color: #3d3e40;
#     }}

#     .evokg-feature-desc {{
#         flex-grow: 1;
#         font-size: 0.9rem;
#         color: #455a7f;
#         line-height: 1.35;
#     }}

#     .evokg-cta {{
#         display: flex;
#         justify-content: center;
#         margin: 2rem 0 1rem;
#     }}

#     .evokg-cta-button {{
#         background: #dbe4ec;
#         color: #ffffff;
#         padding: 0.9rem 2rem;
#         border-radius: 999px;
#         font-weight: 600;
#         font-size: 1.05rem;
#     }}
#     .evokg-cta-button:hover {{
#         filter: brightness(1.1);
#         transform: translateY(-1px);
#         box-shadow: 0 25px 70px -10px rgba(47, 47, 56, 0.55);
#     }}
#     .evokg-cta-button:active {{
#         transform: translateY(1px);
#         box-shadow: 0 12px 40px -5px rgba(15, 76, 129, 0.35);
#     }}
#     /* if using <a> ensure no underline */
#     .evokg-cta-button[href] {{
#         text-decoration: none;
#     }}

#     @media (max-width: 980px) {{
#         .evokg-header {{ font-size: 2.2rem; }}
#         .evokg-page-title {{ font-size: 1.4rem; }}
#     }}
#     </style>
#     <div class="evokg-container">
#         <div class="evokg-header-wrapper">
#             <div class="evokg-header">✨ Welcome to EvoAge</div>
#             <div class="evokg-subheader">
#                 🧬 An AI-powered platform for cross-species aging research, built on a unified knowledge graph of 1.04 billion biological relationships.
#             </div>
#             <div class="evokg-divider"></div>
#         </div>
#         <div class="evokg-page-card">
#             <div class="evokg-page-title">🧬 What is EvoAge?</div>
#             <div class="evokg-page-content">
#                 EvoAge integrates 48 aging and biomedical databases into a human-centric knowledge graph spanning six model organisms. 
#                 Through orthology-based mapping and optimized graph embeddings, it enables discovery of evolutionarily conserved aging mechanisms 
#                 and provides AI-driven hypothesis testing with experimental validation.
#             </div>
#         </div>
#         <div class="evokg-features-grid">
#             <div class="evokg-feature-card">
#                 <div class="evokg-feature-icon">🔍</div>
#                 <div class="evokg-feature-title">Explore Knowledge</div>
#                 <div class="evokg-feature-desc">
#                     Query <b>1.04</b> billion relationships across humans, mice, zebrafish, flies, worms, and yeast through unified orthology mapping.
#                 </div>
#             </div>
#             <div class="evokg-feature-card">
#                 <div class="evokg-feature-icon">⚡</div>
#                 <div class="evokg-feature-title">Predict Links</div>
#                 <div class="evokg-feature-desc">
#                     Discover novel biological connections using optimized knowledge graph embeddings (RotatE architecture).
#                 </div>
#             </div>
#             <div class="evokg-feature-card">
#                 <div class="evokg-feature-icon">🧪</div>
#                 <div class="evokg-feature-title">Test Hypotheses</div>
#                 <div class="evokg-feature-desc">
#                     Evaluate proposed relationships with quantitative scoring, graph validation, and evidence synthesis.
#                 </div>
#             </div>
#         </div>
#         <div class="evokg-page-card">
#             <div class="evokg-page-title">🚀 Getting Started</div>
#             <div class="evokg-page-content">
#                 <p>Enter natural language queries about genes, pathways, or aging processes. The EvoAge agent will route your request to the appropriate module:</p>
#                 <p>• <strong>Knowledge Retrieval</strong> – Search existing facts<br>
#                 • <strong>Link Prediction</strong> – Infer missing connections<br>
#                 • <strong>Hypothesis Testing</strong> – Score proposed relationships</p>
#             </div>
#         </div>
#     </div>

#     """, unsafe_allow_html=True)
