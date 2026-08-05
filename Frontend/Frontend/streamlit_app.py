import datetime
import logging
import pathlib
import base64
import time
import streamlit as st

from utils.auth_utils import login_user, register_user, get_user_details, logout, forgot_password
from utils.account_utils import update_user_query_limits, update_user_openai_key_api
import kani_utils.kani_streamlit_server as ks
from kani.engines.openai import OpenAIEngine
from agents import EvoKgAgent
from hypo_agents import HypoEvoKgAgent

# import the decoupled page
from components.LoginSignup import show_login_signup
from components.Introduction import show_intro_page
from components.AboutUs import show_about_page
from components.MicroServices import show_microservices_page
from components.UnifiedChat import unified_chat_page
from components.how_to_use import show_how_to_use_page

import datetime

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")



# ============================
# CHECK IF RESET PASSWORD PAGE
# ============================
query_params = st.query_params

if "page" in query_params and query_params["page"] == "Reset_Password":
    from components.forget_password import show_reset_password_page
    show_reset_password_page()
    st.stop()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StreamlitApp")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Paths
current_dir = pathlib.Path(__file__).parent.absolute()
logo_path = current_dir / "assets" / "logo.png"
bg_image_path = current_dir / "assets" / "bg6.png"

logo_path = str(logo_path) if pathlib.Path(logo_path).exists() else None
if not pathlib.Path(bg_image_path).exists():
    logger.warning("Background image not found locally; falling back to remote.")
    bg_image_path = "https://www.nayuki.io/res/animated-floating-graph-nodes/floating-graph-nodes.png"
else:
    bg_image_path = str(bg_image_path)


# Session defaults
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_token", None)
st.session_state.setdefault("username", None)
st.session_state.setdefault("auth_view", "Login")
st.session_state.setdefault("query_limits", 10)
st.session_state.setdefault("last_query_reset", datetime.datetime.utcnow().isoformat())
st.session_state.setdefault("openai_api_key", None)

# guard flags to avoid double-processing across reruns
st.session_state.setdefault("login_processed", False)
st.session_state.setdefault("signup_processed", False)
st.session_state.setdefault("forgot_password_processed", False)


def set_bg_from_local(image_path):
    with open(image_path, "rb") as image_file:
        image = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"]{{
            background: url("data:image/png;base64,{image}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
def load_css():
    with open("assets/style.css", "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css()

def initialize_chat_session():
    for page in ["home", "chat", "about", "hypo_test", "microservices", "unified_chat", "how_to_use"]:
    # for page in ["home", "chat", "about", "hypo_test", "microservices"]:
        key = f"messages_{page}"
        if key not in st.session_state:
            st.session_state[key] = []

    # Initialize the common 'messages' for display and interaction
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Track current page to sync messages
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"


def save_current_messages():
    page = st.session_state.current_page
    st.session_state[f"messages_{page}"] = st.session_state.messages


def load_page(page):
    # Save old messages
    if "current_page" in st.session_state:
        save_current_messages()
    
    # 🔥 Reset agents when switching chatbot pages
    if page in ["chat", "hypo_test"]:
        if "agents" in st.session_state:
            del st.session_state["agents"]
        if "current_agent_name" in st.session_state:
            del st.session_state["current_agent_name"]

    st.session_state.current_page = page
    st.session_state.messages = st.session_state[f"messages_{page}"]

    st.rerun()

def Hypothesis_Testing_page():
    user_api_key = st.session_state.get("openai_api_key")

    if user_api_key:
        st.markdown("""
            <style>
                .chat-wrapper {
                    max-width: 900px;
                    margin: auto;
                    padding: 2rem 1rem;
                }
            </style>
            <div class="chat-wrapper">
        """, unsafe_allow_html=True)

        engine1 = OpenAIEngine(user_api_key, model="gpt-4o-mini")
        engine2 = OpenAIEngine(user_api_key, model="gpt-4.1-mini")

        # Always reset agents for this page
        def get_all_agents():
            return {
                "HypoEvoKG (4o-mini)": HypoEvoKgAgent(engine1),
                "HypoEvoKG (4.1-mini)": HypoEvoKgAgent(engine2),
            }
        if "agents" not in st.session_state:
            ks.set_app_agents(get_all_agents)
        if "current_agent_name" not in st.session_state:
            st.session_state.current_agent_name = "HypoEvoKG (4o-mini)"

        ks.serve_app()
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.error(
            "OpenAI API key not found for your account. "
            "Chatbot functionality cannot be initialized. "
            "Please ensure your API key was correctly submitted during registration and is available in your profile."
        )

def Chat_with_me_page():

    user_api_key = st.session_state.get("openai_api_key")

    if user_api_key:
        st.markdown("""
            <style>
                .chat-wrapper {
                    max-width: 900px;
                    margin: auto;
                    padding: 2rem 1rem;
                }
            </style>
            <div class="chat-wrapper">
        """, unsafe_allow_html=True)

        engine1 = OpenAIEngine(user_api_key, model="gpt-4o-mini")
        engine2 = OpenAIEngine(user_api_key, model="gpt-4.1-mini")

        # Always reset agents for this page
        def get_all_agents():
            return {
                "EvoLLM (4o-mini)": EvoKgAgent(engine1),
                "EvoLLM (4.1-mini)": EvoKgAgent(engine2),
            }
        if "agents" not in st.session_state:
            ks.set_app_agents(get_all_agents)


        if "current_agent_name" not in st.session_state:
            st.session_state.current_agent_name = "EvoLLM (4o-mini)"

        ks.serve_app()
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.error(
            "OpenAI API key not found for your account. "
            "Chatbot functionality cannot be initialized. "
            "Please ensure your API key was correctly submitted during registration and is available in your profile."
        )

# If not logged in, render login/signup and handle submission
if not st.session_state["logged_in"]:
    result = show_login_signup()  # must return structured dict or None
    error_placeholder = None
    if isinstance(result, dict):
        error_placeholder = result.get("error_placeholder")

    if result:
        if result["action"] == "login" and not st.session_state["login_processed"]:
            username = result.get("username", "").strip()
            password = result.get("password", "")
            st.session_state["login_processed"] = True  # mark so we don't reprocess after rerun

            if not username or not password:
                # st.error("Please enter both username and password.")
                if error_placeholder:
                    error_placeholder.error("Please enter both username and password.")
                else:
                    st.error("Please enter both username and password.")

                st.session_state["login_processed"] = False  # allow retry
            else:
                success, data = login_user(username, password)
                if success:
                    initialize_chat_session()
                    token = data["access_token"]
                    st.session_state.update({
                        "logged_in": True,
                        "user_token": token,
                        "username": username,
                    })
                    user_details = get_user_details(token)
                    if user_details:
                        st.session_state["query_limits"] = user_details.get("query_limits", 10)
                        st.session_state["last_query_reset"] = user_details.get(
                            "last_query_reset", datetime.datetime.utcnow().isoformat()
                        )
                        st.session_state["openai_api_key"] = user_details.get("OPENAI_API_KEY")
                    error_placeholder.success("Login successful.")
                    st.rerun()
                else:
                    error_placeholder.error(data.get("error", "Login failed."))
                    st.session_state["login_processed"] = False  # allow retry

        elif result["action"] == "signup" and not st.session_state["signup_processed"]:
            st.session_state["signup_processed"] = True  # prevent double submission
            username = result.get("username", "").strip()
            password = result.get("password", "")
            confirm_password = result.get("confirm_password", "")
            email = result.get("email", "").strip()
            first_name = result.get("first_name", "").strip()
            last_name = result.get("last_name", "").strip()
            organization = result.get("organization", "").strip()
            api_key = result.get("api_key", "")

            missing_fields = []
            for field_name, value in [
                ("username", username),
                ("email", email),
                ("password", password),
                ("confirm_password", confirm_password),
                ("first_name", first_name),
                ("last_name", last_name),
                ("organization", organization),
                ("OpenAI API Key", api_key),
            ]:
                if not value:
                    missing_fields.append(field_name)
            if missing_fields:
                # st.error(f"Please fill all fields. Missing: {', '.join(missing_fields)}")
                if error_placeholder:
                    error_placeholder.error(f"Please fill all fields. Missing: {', '.join(missing_fields)}")
                else:
                    error_placeholder.error(f"Please fill all fields. Missing: {', '.join(missing_fields)}")
                st.session_state["signup_processed"] = False
            elif password != confirm_password:
                # st.error("Passwords do not match.")
                error_placeholder.error("Passwords do not match.")
                st.session_state["signup_processed"] = False
            else:
                with error_placeholder.info("Registering user and confirming credentials..."):
                    # time.sleep(1) # Added a small delay for better visual effect, can be removed
                    success, data = register_user(
                        username,
                        email,
                        password,
                        first_name,
                        last_name,
                        organization,
                        api_key,
                    )
                if success:
                    # st.success("Signup successful. Please login.")
                    error_placeholder.success("Signup successful! Please check your email for confirmation and proceed to log in to EvoAge.")
                    # st.rerun()
                else:
                    # st.error(data.get("error", "Signup failed."))
                    error_placeholder.error(data.get("error", "Signup failed."))
                    st.session_state["signup_processed"] = False
        elif result["action"] == "forget_password" and not st.session_state["forgot_password_processed"]:
            st.session_state["forgot_password_processed"] = True
            email = result.get("email", "").strip()
            placeholder = result.get("error_placeholder") if isinstance(result, dict) else None

            if not email:
                msg = "Please enter your email address."
                if placeholder:
                    placeholder.error(msg)
                else:
                    st.error(msg)
                st.session_state["forgot_password_processed"] = False
            else:
                placeholder.info("Verifying email...")
                success, data = forgot_password(email)
                data = data or {}

                if success:
                    success_msg = "If an account with this email exists, a password reset mail has been sent."
                    if placeholder:
                        placeholder.success(success_msg)
                    else:
                        st.success(success_msg)
                else:
                    err_text = data.get("error", "Password reset failed.")
                    if placeholder:
                        placeholder.error(err_text)
                    else:
                        st.error(err_text)

                # allow retry after a completed attempt (success or failure)
                st.session_state["forgot_password_processed"] = False


    st.stop()

if st.session_state["logged_in"]:
    # load_css()
    # Store the function in session_state so kani_streamlit_server.py can access it
    st.session_state.update_user_query_limits_func = update_user_query_limits

    ks.initialize_app_config(
        show_function_calls=True,
        page_title="EVOLLM",
        page_icon=logo_path,
        # layout="centered",
        initial_sidebar_state="expanded",
        # custom_pages=custom_pages,
    )
    
    # load_css()

    set_bg_from_local(bg_image_path)
    with st.sidebar:
        st.logo("assets/logo.svg", size = "large")
        st.write(f"# Welcome, {st.session_state['username']}!")
        
        st.sidebar.markdown("---")
        if st.button("🔒 Logout", disabled=st.session_state.lock_widgets):
                logger.info(f"User '{st.session_state['username']}' logging out.")

                keys_to_clear = [
                    "logged_in",
                    "user_token",
                    "username",
                    "openai_api_key",
                    "current_page",
                    "login_processed",
                    "signup_processed",
                    "update_user_query_limits_func",
                    "current_agent_name",
                    "agents",
                ]

                for page in ["home", "chat", "about"]:
                    keys_to_clear.append(f"messages_{page}")
                keys_to_clear.append("messages")

            
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
            
                # Optionally reset default session state values after logout
                st.session_state["logged_in"] = False
                st.session_state["auth_view"] = "Login"
                st.session_state["query_limits"] = 10
                st.session_state["last_query_reset"] = datetime.datetime.utcnow().isoformat()
            
                st.rerun()
        st.sidebar.markdown("---")
        
        if st.button("Introduction", key="Home", disabled=st.session_state.lock_widgets):
            load_page("home")
    
        # if st.button("🧠 Ask EvoAge!", key="Chat_with_me"):
        #     load_page("chat")
            
        # if st.button("🧪 Hypothesis testing!", key="hypo_test"):
        #     load_page("hypo_test")

        if st.button("How To Use", key="how_to_use", disabled=st.session_state.lock_widgets):
            load_page("how_to_use")
            
        if st.button("Ask EvoAge!", key="UnifiedChat", disabled=st.session_state.lock_widgets):
            load_page("unified_chat")

        if st.button("Micro-services", key="MicroServices", disabled=st.session_state.lock_widgets):
            load_page("microservices")



        if st.button("About Us", key="About_Us", disabled=st.session_state.lock_widgets):
            load_page("about")

        # Show download only on chatbot pages
        if "agents" in st.session_state and st.session_state.get("current_agent_name"):
            filename = f"chat_{timestamp}.txt"
            st.sidebar.markdown("### Download Chat")
            
            from io import StringIO
            agents = st.session_state["agents"]
            agent_name = st.session_state["current_agent_name"]
            agent = agents.get(agent_name)

            if agent:
                output = StringIO()
                for msg in agent.display_messages:
                    role = msg.role.value if hasattr(msg, "role") else "assistant"
                    text = getattr(msg, "text", "")
                    output.write(f"{role.upper()}: {text}\n\n")

                st.sidebar.download_button(
                    label="📁 Download Chat",
                    data=output.getvalue(),
                    file_name=filename,
                    mime="text/plain",
                    key="download_chat_txt",
                    disabled=st.session_state.lock_widgets
                )


        st.sidebar.markdown("---")
        
        st.sidebar.subheader("Update OpenAI API Key")
        new_openai_key_input = st.sidebar.text_input(
            "New OpenAI API Key", type="password", key="new_openai_key_input_field", disabled=st.session_state.lock_widgets
        )
        if st.sidebar.button("Update Key", key="update_openai_key_button_field", disabled=st.session_state.lock_widgets):
            if new_openai_key_input:
                if st.session_state.get("user_token"):
                    success, message = update_user_openai_key_api(
                        st.session_state["user_token"], new_openai_key_input
                    )
                    if success:
                        st.toast(message, icon="✅")
                        
                    else:
                        st.toast(message, icon="❌")
                else:
                    st.toast("User token not found. Please log in again.", icon="⚠️")
            else:
                st.toast("Please enter an API key.", icon="⚠️")
    

    # This renders the selected page
    if st.session_state.current_page == "home":
        show_intro_page()
    elif st.session_state.current_page == "chat":
        Chat_with_me_page()
    elif st.session_state.current_page == "hypo_test":
        Hypothesis_Testing_page()
    elif st.session_state.current_page == "unified_chat":
        unified_chat_page()
    elif st.session_state.current_page == "microservices":
        show_microservices_page()
    elif st.session_state.current_page == "how_to_use":
        show_how_to_use_page()
    elif st.session_state.current_page == "about":
        show_about_page()

    