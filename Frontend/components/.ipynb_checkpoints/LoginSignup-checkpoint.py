import streamlit as st
import base64

# Initial Page CSS Setting -> Hide
def css_setting():
    # — Load background image as base64 —
    try:
        with open("assets/bg6.png", "rb") as bg_file:
            image = base64.b64encode(bg_file.read()).decode()
    except FileNotFoundError:
        image = None

    css = f"""
    <style>
        /* Base style for stColumn */
        .right-welcome {{
            background: rgba(255, 255, 255, 0.9);
            padding: 0.8rem 0rem 0rem 0rem;
            /* top    right   bottom   left */
            border-radius: 16px;
            width: 540px;
            margin-top: 4vh;
            max-width: 95%;
            font-family: 'Poppins', sans-serif;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15); /* subtle initial shadow */
        }}
        
        .block-container {{
        max-width: 1200px;
        margin: 0 auto;
        padding-top: 0rem;
        }}

        [data-testid="stRadio"] {{
            background: rgba(255, 255, 255, 0.9);
            padding: 0.5rem 1rem;
            border-radius: 16px;
            width: 540px;
            margin-top: 2vh;
            max-width: 95%;
            font-family: 'Poppins', sans-serif;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
            transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
        }}
        
        /* Hover effect for stColumn */
        [data-testid="stRadio"]:hover {{
            transform: translateY(-6px);
            box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
        }}

        
        [data-testid="stForm"] {{
            background: rgba(255, 255, 255, 0.9);
            padding: 1.25rem 2rem;
            border-radius: 16px;
            width: 540px;
            margin-top: 0vh;
            max-width: 95%;
            font-family: 'Poppins', sans-serif;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
            transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
        }}
        
        /* Hover effect for stColumn */
        [data-testid="stForm"]:hover {{
            transform: translateY(-6px);
            box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
        }}

        [data-testid="stExpander"] {{
            background: rgba(255, 255, 255, 0.9);
            padding: 0.5rem 0.5rem;
            border-radius: 16px;
            margin-top: 0.5vh;
            max-width: 80%;
            max-height: 30%;
            font-family: 'Poppins', sans-serif;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
            transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
        }}
        
        /* Hover effect for stColumn */
        [data-testid="stExpander"]:hover {{
            transform: translateY(-6px);
            box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
        }}
        
        [data-testid="stHeader"] {{
            display: none !important;
        }}
        [data-testid="stAppViewContainer"]{{
            background: url("data:image/png;base64,{image}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}

        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            height: 100vh !important;
            overflow: hidden !important;
        }}

        [data-testid="stMainBlockContainer"] {{
            padding: 0 !important;
            margin: 0 !important;
        }}

       /* Updated EvoAge intro block styling */

        .intro-wrapper {{
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem;
        }}

        .intro-block {{
            background: rgba(255, 255, 255, 0.9);
            padding: 1.25rem 2rem;
            border-radius: 16px;
            width: 540px;
            max-width: 95%;
            font-family: 'Poppins', sans-serif;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
            transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
        }}
        
        .intro-block:hover {{
            transform: translateY(-6px);
            box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
        }}


        .intro-block h2 {{
            color: #1c3f80;
            font-size: 1.6rem;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .intro-block p {{
            font-size: 1rem;
            line-height: 1.6;
            color: #333;
            margin: 0;
        }}

        .intro-block ul {{
            list-style-type: disc;
            padding-left: 1.2rem;
            margin: 0;
            font-size: 0.95rem;
            line-height: 1.5;
            color: #444;
        }}

        .cta-button {{
            all: unset;
            display: block !important;
            padding: 8px 12px !important;
            background: linear-gradient(to right, #dbe4ec, #f0f2f5) !important;
            color: #2f4f60 !important;
            border: 1px solid #bfc9d1 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            text-align: center !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important;
            cursor: pointer;
            margin: 6px 0 !important;
        }}

        .cta-button:hover {{
            background: linear-gradient(to right, #c3d9e9, #e0ebf3) !important;
            color: #1d3a49 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.15) !important;
        }}

        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(2) {{
            padding-top: 1rem !important;     /* Adjust top spacing */
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
            margin-top: 0 !important;         /* Avoid vertical centering stretch */
            align-items: flex-start !important;
        }}

        .right-welcome {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }}

        .welcome-logo {{
            width: 120px;
        }}

        .welcome-heading {{
            font-family: 'Poppins', sans-serif;
            color: #1c3f80;
            font-size: 1.4rem;
            font-weight: 500;           
            margin-top: 0.75rem;
            margin-bottom: 1rem;
            letter-spacing: 0.5px;
            line-height: 1.3;
            position: relative;
        }}

        .welcome-heading::after {{
            content: "";
            display: block;
            width: 40px;
            height: 3px;
            background: #f26b3a;
            margin: 0.4rem auto 0 auto;
            border-radius: 2px;
        }}

        h1 a {{
            display: none !important;
        }}

        .form-wrapper {{
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 12px;
            max-width: 500px;
            margin: auto;
            box-shadow: 0 0 16px rgba(0, 0, 0, 0.08);
            font-family: 'Poppins', sans-serif;
        }}

        .test-account-box {{
            background-color: rgba(28, 63, 128, 0.05); /* subtle EvoAge blue tint */
            border-left: 4px solid #f26b3a;           /* EvoAge orange accent */
            padding: 0.75rem 1rem;
            margin-top: 1.5rem;
            font-size: 0.85rem;
            color: #1c3f80;
            border-radius: 6px;
            max-width: 450px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
        }}

        .test-account-box ul {{
            padding-left: 1.25rem;
            margin: 0.25rem 0 0 0;
        }}

        .test-account-box li {{
            line-height: 1.4;
        }}

        .test-account-box span {{
            color: #333;
            font-family: monospace;
        }}

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Testing CSS
# def testing_css():
#     testing_css = f"""
#     <style>
#         [data-testid="stElementContainer"]{{
#             background-color: #000000
#         }}
#     </style>
#     """
#     st.markdown(testing_css, unsafe_allow_html=True)


def show_login_signup():
    # Page Config
    st.set_page_config(
        page_title="EvoAge",
        layout="wide",
        page_icon="assets/logo.png"
    )
    
    # Calling Page setup CSS.
    css_setting()

    # — Two‑column layout —
    _,right_col,left_col = st.columns([0.3, 4.5, 5.2], gap=None, vertical_alignment="center")

    with left_col:
            st.markdown("""
            <div class="intro-wrapper">
                <div class="intro-block">
                    <h2>Introducing <strong>EvoAge</strong> 🔬</h2>
                    <p>
                        EvoAge is an AI-powered biological assistant built on top of EvoKG,
                        a multi-species evolutionary knowledge graph. It allows researchers
                        to explore gene, disease, chemical, and pathway connections using natural language queries.
                    </p>
                    <ul>
                        <li>Built with GPT-4o-mini & Kani framework</li>
                        <li>Powered by curated biological knowledge of EvoKG</li>
                        <li>Open-source & community-driven</li>
                    </ul>
                    <a href="#" class="cta-button">Learn More ➔</a>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Optional: placeholder right column
    with right_col:
        # — Load logo as base64 —
        try:
            with open("assets/logo.png", "rb") as img_file:
                logo = base64.b64encode(img_file.read()).decode()
        except FileNotFoundError:
            logo = None
        st.markdown(f"""
        <div class="right-welcome">
            <img src="data:image/png;base64,{logo}" class="welcome-logo" alt="EvoAge Logo" />
            <h1 class="welcome-heading">Welcome to EvoAge</h1>
        </div>
        """, unsafe_allow_html=True)


        # Toggle radio
        choice = st.radio("Login/Signup Radio", ["LOGIN", "SIGN UP"], index=0, horizontal=True, label_visibility="collapsed", width="stretch")

        # Define form key and label
        form_key   = "login_form"  if choice == "LOGIN"  else "signup_form"
        submit_lbl = "LOGIN"       if choice == "LOGIN"  else "SIGN UP"

        # Define form
        with st.form(key=form_key, height=240):
            username = st.text_input(
                "Username",
                placeholder="Enter your username" if choice == "LOGIN" else "Pick a username"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password" if choice == "LOGIN" else "Choose a password"
            )

            # Additional fields for SIGN UP
            if choice == "SIGN UP":
                email = st.text_input(
                    "Email",
                    placeholder="Enter your email address"
                )

                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Repeat your password"
                )

                first_name = st.text_input("First Name", placeholder="Enter your first name")
                last_name  = st.text_input("Last Name",  placeholder="Enter your last name")
                organization = st.text_input("Organization", placeholder="Enter your organization")

                api_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    placeholder="Paste your OpenAI API key"
                )

            submitted = st.form_submit_button(submit_lbl)

        # -- Quick Test Account Box --
        with st.expander("🧪 Quick Access (Test Credentials)"):
            test_username = ("ankiss")
            test_password = ("huihuihui")
            st.markdown(f"""
            Username: {test_username}\n
            Password: {test_password}
            """, unsafe_allow_html=True)

        if submitted:
            if choice == "LOGIN":
                return {"action": "login", "username": username, "password": password}
            else:
                return {
                    "action": "signup",
                    "username": username,
                    "password": password,
                    "confirm_password": confirm_password,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "organization": organization,
                    "api_key": api_key,
                }
        return None
