import streamlit as st
import kani_utils.kani_streamlit_server as ks
from kani.engines.openai import OpenAIEngine
from agents import EvoKgAgent
from hypo_agents import HypoEvoKgAgent

# ---------- CSS for Cards ----------
def load_unified_css():
    st.markdown("""
        <style>

        /* Remove header */
        /* [data-testid="stHeader"] { display: none !important; }*/

        /* Container width */
        .block-container {
            max-width: 100%!important;
            margin: 0 auto;
            padding-top: 1.2rem;
        }

        /* --- CARD CONTAINER LAYOUT --- */
        .card-container {
            max-width: 100%;
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 8rem;       /* ↓ reduced from 8rem */
            margin-bottom: 0rem;
            align-items: flex-start;  /* better alignment */
        }


        /* --- CARD BASE STYLE --- */
        .assistant-card {
            width: 100%;
            max-width: 100%;
            min-height: 330px;            /* ↑ increased height */
            padding: 2.4rem;

            background: rgba(255,255,255,0.82);
            border-radius: 26px;

            border: 2px solid rgba(180,200,255,0.45);
            box-shadow: 
                0 12px 35px rgba(0,0,0,0.08),
                0 4px 12px rgba(120,140,255,0.12),
                inset 0 0 22px rgba(200,220,255,0.25);   /* NEW soft inner glow */

            backdrop-filter: blur(16px) saturate(160%);

            transition: all 0.45s cubic-bezier(0.25, 1, 0.5, 1);
            cursor: pointer;
            transform: translateY(0px) scale(1);
        }


        /* Hover effect */
        .assistant-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 16px 30px rgba(0,0,0,0.12);
            border-color: #99b7ff;
        }

        /* Activated card */
        .assistant-card.active {
            background: rgba(225, 255, 237, 0.90) !important;
            border-color: #22c55e !important;
            transform: translateY(-14px) scale(1.04);

            box-shadow:
                0 26px 45px rgba(34, 197, 94, 0.28),
                0 8px 20px rgba(34, 197, 94, 0.25),
                inset 0 0 25px rgba(34, 197, 94, 0.25);  /* green inner glow */
        }

        /* Make activated card move up smoothly */
        .assistant-card {
            animation: fadeSlideUp 0.7s ease both;
        }

        @keyframes fadeSlideUp {
            from { opacity: 0; transform: translateY(25px) scale(0.97); }
            to   { opacity: 1; transform: translateY(0px) scale(1); }
        }


        .assistant-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a2d48;
            margin-bottom: 0.3rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            text-align: center;
            display: block;
        }

        .assistant-desc {
            font-size: 1rem;
            color: #445066;
            margin-bottom: 1rem;
            line-height: 1.5;
            text-align: center;
            display: block;
        }

        /* Emoji styling */
        .assistant-emoji {
            font-size: 2rem;
            display: inline-block;
            transition: transform 0.4s ease, filter 0.4s ease;
            filter: drop-shadow(0 0 0px rgba(0, 150, 255, 0.4));
        }

        .assistant-card:hover .assistant-emoji {
            animation: emojiSpin 0.6s ease-in-out;
            filter: drop-shadow(0 0 10px rgba(0, 150, 255, 0.7));
        }

        @keyframes emojiSpin {
            0% { transform: rotate(0deg) scale(1); }
            40% { transform: rotate(15deg) scale(1.2); }
            100% { transform: rotate(0deg) scale(1); }
        }

        /* Button */
        .activate-btn {
            width: 100%;
            padding: 0.8rem;
            background: linear-gradient(to right, #dbe4fc, #eef1f8);
            border-radius: 12px;
            border: none;
            color: #1a3d7c;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
        }

        .activate-btn:hover {
            transform: translateY(-2px);
        }

        /* Chat wrapper */
        .chat-wrapper {
            max-width: 900px;
            margin: 2rem auto;
            padding: 2rem 1rem;
            animation: fadeInChat 0.5s ease-out;
        }

        @keyframes fadeInChat {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0px); }
        }
        .assistant-emoji-top {
            font-size: 2.8rem;
            display: block;
            width: 100%;
            text-align: center;
            margin-bottom: 0.6rem;
            transition: transform 0.4s ease, filter 0.4s ease;
        }

        .assistant-card:hover .assistant-emoji-top {
            animation: emojiSpin 0.6s ease-in-out;
            filter: drop-shadow(0 0 12px rgba(0, 150, 255, 0.65));
        }

        </style>
    """, unsafe_allow_html=True)


def unified_chat_page():
    load_unified_css()
    
    user_api_key = st.session_state.get("openai_api_key")
    if not user_api_key:
        st.error("API key missing. Please update key in sidebar.")
        return

    # Default selection
    st.session_state.setdefault("active_assistant", None)

    # ---------- Render Two Cards ----------
    def card(key, title, desc, emoji):
        active = st.session_state.active_assistant == key
        active_class = "active" if active else ""

        st.markdown(
            f"""
            <div class="assistant-card {active_class}">
                <div class="assistant-emoji-top">{emoji}</div>
                <div class="assistant-title">{title}</div>
                <div class="assistant-desc">{desc}</div>
            """,
            unsafe_allow_html=True
        )
        
        if st.button(f"Activate", key=f"btn_{key}", use_container_width=True):
            st.session_state.active_assistant = key

            # Reset agents
            for k in ["agents", "current_agent_name"]:
                if k in st.session_state:
                    del st.session_state[k]

            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # Centering the cards using a 3-column layout
    col_l, col_mid, col_r = st.columns([0.5, 2, 0.5])

    with col_mid:
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            card(
                key="evoage",
                title="EvoAge Assistant",
                desc="Explore the Evolutionary Knowledge Graph. Search genes, diseases, chemicals, proteins and discover relationships or predict novel links.",
                emoji="🧬"
            )
        with right:
            card(
                key="hypo",
                title="Hypothesis Testing",
                desc="Run biological hypothesis testing using entity extraction + RotatE scoring pipeline. Generates structured scientific insights.",
                emoji="🧪"
            )
        st.markdown("</div>", unsafe_allow_html=True)


    # ---------- Load Selected Assistant ----------
    if st.session_state.active_assistant in ["evoage", "hypo"]:

        # st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

        # Engines
        engine1 = OpenAIEngine(user_api_key, model="gpt-4o-mini")
        engine2 = OpenAIEngine(user_api_key, model="gpt-4.1-mini")

        # EvoAge block
        if st.session_state.active_assistant == "evoage":
            def get_agents():
                return {
                    "EvoLLM (4o-mini)": EvoKgAgent(engine1),
                    "EvoLLM (4.1-mini)": EvoKgAgent(engine2),
                }

            default_agent = "EvoLLM (4o-mini)"

        # Hypothesis Testing block
        else:
            def get_agents():
                return {
                    "HypoEvoKG (4o-mini)": HypoEvoKgAgent(engine1),
                    "HypoEvoKG (4.1-mini)": HypoEvoKgAgent(engine2),
                }

            default_agent = "HypoEvoKG (4o-mini)"

        # Initialize agents
        if "agents" not in st.session_state:
            ks.set_app_agents(get_agents)

        if "current_agent_name" not in st.session_state:
            st.session_state.current_agent_name = default_agent

        ks.serve_app()

        # st.markdown("</div>", unsafe_allow_html=True)



# import streamlit as st
# import kani_utils.kani_streamlit_server as ks
# from kani.engines.openai import OpenAIEngine
# from agents import EvoKgAgent
# from hypo_agents import HypoEvoKgAgent

# # ---------- CSS for Cards ----------
# def load_unified_css():
#     st.markdown("""
#         <style>
#         [data-testid="stHeader"] {{ display: none !important; }}
#         .block-container {
#             max-width: 1000px !important;
#             margin: 0 auto;
#             padding-top: 1.5rem;     /* Reduced */
#         }
#         .assistant-card {
#             background: rgba(255,255,255,0.75);
#             border-radius: 18px;
#             padding: 1.5rem;
#             margin-bottom: 1.2rem;
#             border: 2px solid #cbd7f0;
#             box-shadow: 0 6px 18px rgba(0,0,0,0.08);
#             transition: all 0.35s ease;
#         }

#         .assistant-card.active {
#             background: #e6f9ea !important;
#             border-color: #2ecc71 !important;
#             box-shadow: 0 10px 25px rgba(46, 204, 113, 0.25);
#             transform: scale(1.02);
#         }

#         .assistant-title {
#             font-size: 1.6rem;
#             font-weight: 700;
#             color: #24324a;
#             margin-bottom: 0.4rem;
#         }

#         .assistant-desc {
#             font-size: 0.95rem;
#             color: #4a5568;
#             margin-bottom: 0.8rem;
#         }

#         .activate-btn {
#             width: 100%;
#             padding: 0.7rem;
#             background: linear-gradient(to right, #dce3f5, #eef1f6);
#             border-radius: 10px;
#             border: none;
#             color: #1a3d7c;
#             font-weight: 600;
#             cursor: pointer;
#             transition: all 0.25s ease;
#         }

#         .activate-btn:hover {
#             transform: translateY(-2px);
#         }

#         </style>
#     """, unsafe_allow_html=True)


# def unified_chat_page():
#     load_unified_css()
    
#     user_api_key = st.session_state.get("openai_api_key")
#     if not user_api_key:
#         st.error("API key missing. Please update key in sidebar.")
#         return

#     # Default selection
#     st.session_state.setdefault("active_assistant", None)

#     # ---------- Render Two Cards ----------
#     def card(key, title, desc, emoji):
#         active = st.session_state.active_assistant == key
#         active_class = "active" if active else ""
#         st.markdown(
#             f"""
#             <div class="assistant-card {active_class}">
#                 <div class="assistant-title">{emoji} {title}</div>
#                 <div class="assistant-desc">{desc}</div>
#             """,
#             unsafe_allow_html=True
#         )
        
#         if st.button(f"Activate {title}", key=f"btn_{key}", use_container_width=True):
#             st.session_state.active_assistant = key
#             # Reset agents
#             if "agents" in st.session_state:
#                 del st.session_state["agents"]
#             if "current_agent_name" in st.session_state:
#                 del st.session_state["current_agent_name"]
#             st.rerun()

#         st.markdown("</div>", unsafe_allow_html=True)

#     col1, col2 = st.columns(2)
#     with col1:
#         card(
#             key="evoage",
#             title="EvoAge Assistant",
#             desc="Query the knowledge graph, search entities, predict links.",
#             emoji="🧬"
#         )
#     with col2:
#         card(
#             key="hypo",
#             title="Hypothesis Testing Assistant",
#             desc="Run advanced hypothesis inference & biological pipeline.",
#             emoji="🧪"
#         )

#     st.markdown("---")

#     # ---------- Load the Selected Assistant ----------
#     if st.session_state.active_assistant == "evoage":
#         engine1 = OpenAIEngine(user_api_key, model="gpt-4o-mini")
#         engine2 = OpenAIEngine(user_api_key, model="gpt-4.1-mini")

#         def get_agents():
#             return {
#                 "EvoLLM (4o-mini)": EvoKgAgent(engine1),
#                 "EvoLLM (4.1-mini)": EvoKgAgent(engine2),
#             }

#         if "agents" not in st.session_state:
#             ks.set_app_agents(get_agents)

#         if "current_agent_name" not in st.session_state:
#             st.session_state.current_agent_name = "EvoLLM (4o-mini)"

#         ks.serve_app()

#     elif st.session_state.active_assistant == "hypo":
#         engine1 = OpenAIEngine(user_api_key, model="gpt-4o-mini")
#         engine2 = OpenAIEngine(user_api_key, model="gpt-4.1-mini")

#         def get_agents():
#             return {
#                 "HypoEvoKG (4o-mini)": HypoEvoKgAgent(engine1),
#                 "HypoEvoKG (4.1-mini)": HypoEvoKgAgent(engine2),
#             }

#         if "agents" not in st.session_state:
#             ks.set_app_agents(get_agents)

#         if "current_agent_name" not in st.session_state:
#             st.session_state.current_agent_name = "HypoEvoKG (4o-mini)"

#         ks.serve_app()

