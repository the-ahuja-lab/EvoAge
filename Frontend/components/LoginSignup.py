import streamlit as st
import base64

# ==========================================================
#                    CSS SETTINGS
# ==========================================================
def css_setting():
    # Load background image
    try:
        with open("assets/bg6.png", "rb") as bg_file:
            image = base64.b64encode(bg_file.read()).decode()
    except FileNotFoundError:
        image = None 
    
    bg_style = f"""
        background: url("data:image/png;base64,{image}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
    """ if image else "background-color: #f0f2f6;"

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        :root {{
            --primary:#0f4c81;
            --text:#2f3e52;
            --muted:#6e7c95;
            --card-bg:rgba(255,255,255,0.75);
            --shadow:0 25px 60px -15px rgba(31,45,58,0.10);
        }}

        html, body {{
            margin: 0 !important;
            padding: 0 !important;
            height: 100vh;
        }}

        [data-testid="stHeader"] {{ display: none !important; }}

        [data-testid="stAppViewContainer"] {{
            {bg_style};
            height: 100vh;
            overflow-y: hidden;
        }}

        .block-container {{
            max-width: 90%;
            margin: 0 auto;
            padding-top: 2rem; 
        }}

        /* ===================================
                LEFT INTRO-BOX + FEATURES
        ====================================== */

        .evokg-header-wrapper {{
            text-align: center;
            padding: 1.8rem 1.5rem;
            border-radius: 22px;
            background: rgba(255,255,255,0.92);
            backdrop-filter: blur(10px);
            box-shadow: 0 12px 25px rgba(0,0,0,0.18);
            border: 1px solid rgba(150,170,240,0.4);
            animation: fadeIn 1s ease-in-out;
            position: relative;     /* REQUIRED for glowing border */
            overflow: hidden; 
        }}
        .evokg-header-wrapper::before {{
            content: "";
            position: absolute;
            inset: 0;
            padding: 2px;
            border-radius: 22px;  /* slightly larger than card's radius */
            background: linear-gradient(
                120deg,
                rgba(150,180,255,0.55),
                rgba(255,255,255,0.20),
                rgba(130,160,255,0.50),
                rgba(255,255,255,0.20),
                rgba(150,180,255,0.55)
            );
            background-size: 300% 300%;
            mask:
                linear-gradient(#fff 0 0) content-box,
                linear-gradient(#fff 0 0);
            mask-composite: exclude;
            animation: borderGlow 6s linear infinite;
            pointer-events: none;
            z-index: 1;
        }}

        .evokg-header {{
            font-size: 2.4rem;
            font-weight: 800;
            color: #1a2b47;
        }}

        .evo-header-subtext {{
            font-size: 1.0rem;
            color: var(--muted);
            margin-top: 0.6rem;
        }}

        /* Feature Grid */
        .evo-feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 18px;
            margin-top: 1.4rem;
            animation: fadeIn 1s ease;
        }}

        .evo-feature-card {{
            background: rgba(255,255,255,0.92);
            border-radius: 18px;
            padding: 1.2rem 1rem 1.5rem;
            text-align: center;
            border: 1px solid rgba(130,160,255,0.25);
            box-shadow: 0 6px 18px rgba(0,0,0,0.15);
            animation: subtleFloat 4s ease-in-out infinite;
            transition: all 0.3s ease;
        }}

        .evo-feature-card:hover {{
            transform: translateY(-10px) scale(1.04);
            box-shadow: 0 18px 35px rgba(0,0,0,0.25);
            border-color: #0f4c81;
            animation-play-state: paused;
        }}

        .evo-feature-icon {{
            font-size: 2.2rem;
            margin-bottom: 0.4rem;
            animation: emojiGlow 1s ease-in-out infinite;
        }}

        .evo-feature-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #1a2b47;
            margin-bottom: 0.3rem;
        }}

        .evo-feature-desc {{
            font-size: 0.88rem;
            color: #45546d;
            line-height: 1.3rem;
        }}

        @keyframes subtleFloat {{
            0% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-6px); }}
            100% {{ transform: translateY(0); }}
        }}

        @keyframes emojiGlow {{
            50% {{ filter: drop-shadow(0 0 12px rgba(80, 150, 255, 0.9)); }}
        }}
        /* Spin animation keyframes */
        @keyframes spinEmoji {{
            0% {{ transform: rotate(0deg) scale(1); }}
            40% {{ transform: rotate(14deg) scale(1.12); }}
            100% {{ transform: rotate(0deg) scale(1); }}
        }}

        /* Apply on hover */
        .evo-feature-card:hover .evo-feature-icon {{
            animation: spinEmoji 1.2s linear infinite,
                    emojiGlow 3s ease-in-out infinite;  /* keep existing glow */
        }}

        @keyframes fadeIn {{
            from {{ opacity:0; transform: translateY(10px); }}
            to {{ opacity:1; transform: translateY(0); }}
        }}
        @keyframes borderGlow {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        /* Right Side Forms */
        [data-testid="stRadio"] {{
            margin-top: 2.1rem;  
            background: rgba(255, 255, 255, 0.9);
            padding: 0.5rem 1rem;
            border-radius: 16px;
            width: 100%;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }}

        [data-testid="stForm"] {{
            background: rgba(255,255,255,0.95);
            padding: 1.5rem 2rem;
            border-radius: 16px;
            width: 100%;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }}

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)



# ==========================================================
#                    MAIN LOGIN / SIGNUP UI
# ==========================================================
def show_login_signup(initial_choice_index=0):

    st.set_page_config(
        page_title="EvoAge - Login",
        layout="wide",
        page_icon="assets/logo.png"
    )

    css_setting()

    # ▒▒▒ Load the Logo ▒▒▒
    logo = None
    try:
        with open("assets/logo.png", "rb") as img_file:
            logo = base64.b64encode(img_file.read()).decode()
    except:
        pass

    # ▒▒▒ Two column layout ▒▒▒
    left_col, right_col = st.columns([6, 5], gap="large")

    # ==========================================================
    #                 LEFT COLUMN — REWRITTEN
    # ==========================================================
    with left_col:
        st.markdown(
        """
        <div class="evokg-header-wrapper">
            <div class="evokg-header">
                🧬 Welcome to <strong>EvoAge</strong>
            </div>
            <p class="evo-header-subtext">
                A next-generation, multi-species platform that integrates  
                <strong>48 biological databases</strong>, <strong>6 model organisms</strong>,  
                and <strong>1.04B knowledge graph triples</strong>  
                to power AI-driven discovery in aging biology.
            </p>
        </div>
        <div class="evo-feature-grid">
            <div class="evo-feature-card">
                <div class="evo-feature-icon">🌍</div>
                <div class="evo-feature-title">Cross-Species Integration</div>
                <div class="evo-feature-desc">
                    Harmonizes 80,000+ genes across six species  
                    into a unified human-centric framework.
                </div>
            </div>
            <div class="evo-feature-card">
                <div class="evo-feature-icon">🕸️</div>
                <div class="evo-feature-title">1.04B-Triple Knowledge Graph</div>
                <div class="evo-feature-desc">
                    A dense biological network connecting genes, chemicals,  
                    diseases, pathways, and phenotypes.
                </div>
            </div>
            <div class="evo-feature-card">
                <div class="evo-feature-icon">🤖</div>
                <div class="evo-feature-title">AI-Powered Reasoning</div>
                <div class="evo-feature-desc">
                    LLM + KG embeddings for link prediction.
                </div>
            </div>
            <div class="evo-feature-card">
                <div class="evo-feature-icon">🔬</div>
                <div class="evo-feature-title">Hypothesis Testing</div>
                <div class="evo-feature-desc">
                    Evidence-grounded, knowledge-graph–driven evaluation of biological hypotheses.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True)



    # ==========================================================
    #               RIGHT COLUMN — FORMS (UNCHANGED)
    # ==========================================================
    with right_col:

        st.markdown("<div class='auth-column-wrapper'>", unsafe_allow_html=True)
        # error_placeholder = st.empty()
        result = None

        form_choice = st.radio(
            "Select action",
            ["Login", "Sign Up", "Reset Password"],
            horizontal=True,
            label_visibility="collapsed"
        )

        # LOGIN FORM
        if form_choice == "Login":
            with st.form(key="login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_login = st.form_submit_button("LOGIN")
                error_placeholder = st.empty()
                if submit_login:
                    result = {
                        "action": "login",
                        "username": username,
                        "password": password,
                        "error_placeholder": error_placeholder
                    }

        # SIGN UP FORM
        elif form_choice == "Sign Up":
            with st.form(key="signup_form"):
                col1, col3 = st.columns(2)

                with col1:
                    su_username = st.text_input("Username", placeholder="Choose username", key="signup_user")
                    first_name = st.text_input("First Name", placeholder="Enter first name", key="signup_fn")
                    last_name = st.text_input("Last Name", placeholder="Enter last name", key="signup_ln")

                with col3:
                    email = st.text_input("Email", placeholder="Enter your email", key="signup_email")
                    organization = st.text_input("Organization", placeholder="Enter organization", key="signup_org")
                    api_key = st.text_input("OpenAI API Key", type="password", placeholder="Paste API key", key="signup_api")

                su_password = st.text_input("Password", type="password", placeholder="Choose password", key="signup_pass")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="signup_confpass")

                submit_signup = st.form_submit_button("SIGN UP")
                error_placeholder = st.empty()

                if submit_signup:

                    # --- VALIDATIONS ---

                    # Username check
                    if len(su_username.strip()) < 3:
                        error_placeholder.error("Username must be at least 3 characters long.")
                        return None

                    # Password match check
                    if su_password != confirm_password:
                        error_placeholder.error("Passwords do not match.")
                        return None

                    # API key check
                    if len(api_key.strip()) < 10:
                        error_placeholder.error("OpenAI API Key must be at least 10 characters long.")
                        return None

                    if len(su_password.strip()) < 8:
                        error_placeholder.error("Passowrd must be at least 8 characters long.")
                        return None

                    # Email basic check
                    if "@" not in email or "." not in email:
                        error_placeholder.error("Please enter a valid email address.")
                        return None

                    # If all validations pass → return signup data
                    result = {
                        "action": "signup",
                        "username": su_username,
                        "password": su_password,
                        "confirm_password": confirm_password,
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "organization": organization,
                        "api_key": api_key,
                        "error_placeholder": error_placeholder
                    }
                    

        # SIGN UP FORM
        # elif form_choice == "Sign Up":
        #     with st.form(key="signup_form"):
        #         col1, col3 = st.columns(2)

        #         with col1:
        #             su_username = st.text_input("Username", placeholder="Choose username", key="signup_user")
        #             first_name = st.text_input("First Name", placeholder="Enter first name", key="signup_fn")
        #             last_name = st.text_input("Last Name", placeholder="Enter last name", key="signup_ln")

        #         with col3:
        #             email = st.text_input("Email", placeholder="Enter your email", key="signup_email")
        #             organization = st.text_input("Organization", placeholder="Enter organization", key="signup_org")
        #             api_key = st.text_input("OpenAI API Key", type="password", placeholder="Paste API key", key="signup_api")

        #         su_password = st.text_input("Password", type="password", placeholder="Choose password", key="signup_pass")
        #         confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="signup_confpass")

        #         submit_signup = st.form_submit_button("SIGN UP")
        #         error_placeholder = st.empty()
        #         if submit_signup:
        #             result = {
        #                 "action": "signup",
        #                 "username": su_username,
        #                 "password": su_password,
        #                 "confirm_password": confirm_password,
        #                 "email": email,
        #                 "first_name": first_name,
        #                 "last_name": last_name,
        #                 "organization": organization,
        #                 "api_key": api_key,
        #                 "error_placeholder": error_placeholder
        #             }

        # RESET PASSWORD
        else:
            with st.form(key="forgot_form"):
                fp_email = st.text_input("Email", placeholder="Enter your registered email")
                submit_forgot = st.form_submit_button("RESET PASSWORD")
                error_placeholder = st.empty()
                if submit_forgot:
                    result = {
                        "action": "forget_password",
                        "email": fp_email,
                        "error_placeholder": error_placeholder
                    }

        st.markdown("</div>", unsafe_allow_html=True)
        return result
#########################################################################################################@###########################





    # with right_col:
    #     st.markdown('<div class="auth-column-wrapper">', unsafe_allow_html=True)

    #     # Create a session state variable to track which expander is open
    #     if 'active_expander' not in st.session_state:
    #         st.session_state.active_expander = 'login'  # Default open expander

    #     # ---------------- LOGIN ----------------
    #     with st.expander("Log In to Your Account", expanded=(st.session_state.active_expander == "login")):
    #         with st.form(key="login_form"):
    #             username = st.text_input("Username", placeholder="Enter your username", key="login_user")
    #             password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
    #             submit_login = st.form_submit_button("LOGIN")

    #             if submit_login:
    #                 st.session_state.auth_active_form = "login"
    #                 st.session_state.active_expander = "login"
    #                 result = {
    #                     "action": "login",
    #                     "username": username,
    #                     "password": password,
    #                     "error_placeholder": error_placeholder
    #                 }

    #     # ---------------- SIGNUP ----------------
    #     with st.expander("Create a New Account", expanded=(st.session_state.active_expander == "signup")):
    #         with st.form(key="signup_form"):
    #             col1, col3 = st.columns(2)

    #             with col1:
    #                 su_username = st.text_input("Username", placeholder="Choose username", key="signup_user")
    #                 first_name = st.text_input("First Name", placeholder="Enter first name", key="signup_fn")
    #                 last_name = st.text_input("Last Name", placeholder="Enter last name", key="signup_ln")

    #             with col3:
    #                 email = st.text_input("Email", placeholder="Enter your email", key="signup_email")
    #                 organization = st.text_input("Organization (Optional)", placeholder="Enter organization", key="signup_org")
    #                 api_key = st.text_input("OpenAI API Key", type="password", placeholder="Paste API key", key="signup_api")

    #             su_password = st.text_input("Password", type="password", placeholder="Choose password", key="signup_pass")
    #             confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="signup_confpass")

    #             submit_signup = st.form_submit_button("SIGN UP")

    #             if submit_signup:
    #                 st.session_state.auth_active_form = "signup"
    #                 st.session_state.active_expander = "signup"
    #                 result = {
    #                     "action": "signup",
    #                     "username": su_username,
    #                     "password": su_password,
    #                     "confirm_password": confirm_password,
    #                     "email": email,
    #                     "first_name": first_name,
    #                     "last_name": last_name,
    #                     "organization": organization,
    #                     "api_key": api_key,
    #                     "error_placeholder": error_placeholder
    #                 }

    #     # ---------------- FORGOT PASSWORD ----------------
    #     with st.expander("Reset Your Password", expanded=(st.session_state.active_expander == "forgot")):
    #         with st.form(key="forgot_form"):
    #             fp_email = st.text_input("Email", placeholder="Enter your email", key="forgot_email_input")
    #             submit_forgot = st.form_submit_button("RESET PASSWORD")

    #             if submit_forgot:
    #                 st.session_state.auth_active_form = "forgot"
    #                 st.session_state.active_expander = "forgot"
    #                 result = {
    #                     "action": "forget_password",
    #                     "email": fp_email,
    #                     "error_placeholder": error_placeholder
    #                 }

    #     st.markdown('</div>', unsafe_allow_html=True)

    #     return result




############################################################ using st.form ###########################################################

# def show_login_signup(initial_choice_index=0):
#     st.set_page_config(
#         page_title="EvoAge - Login",
#         layout="wide",
#         page_icon="assets/logo.png"
#     )
    
#     css_setting()

#     # --- Load Logo (for header) ---
#     logo = None
#     try:
#         with open("assets/logo.png", "rb") as img_file:
#             logo = base64.b64encode(img_file.read()).decode()
#     except FileNotFoundError:
#         pass

#     # --- 1. Custom Animated Header ---
#     st.markdown(f"""
#     <div class="evokg-header-wrapper">
#         <div class="evokg-header">
#             {'<img src="data:image/png;base64,' + logo + '" class="logo-small evokg-header-emoji" alt="EvoAge Logo" />' if logo else ''}
#             Welcome to EvoAge
#         </div>
#     </div>
#     """, unsafe_allow_html=True)


#     # --- 2. Stat Strips ---
#     st.markdown("""
#     <div class="stat-strips-wrapper">
#         <div class="stat-card">
#             <div class="stat-value">1.04B+</div>
#             <div class="stat-label">KG Triples</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-value">Agent-LLM</div>
#             <div class="stat-label">Powered</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-value">Multi-Species</div>
#             <div class="stat-label">Evolution Data</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-value">Real-time</div>
#             <div class="stat-label">Analysis</div>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)
    
    
#     # --- 3. Login/Signup Form Area (Centered & Narrow) ---
#     st.markdown('<div class="form-area-wrapper">', unsafe_allow_html=True)
    
#     # Toggle radio 
#     choice = st.radio(
#         "Login/Signup/Forget Password Radio", 
#         ["LOGIN", "SIGN UP", "FORGET PASSWORD"], 
#         index=initial_choice_index, 
#         horizontal=True, 
#         label_visibility="collapsed",
#         key="login_radio_buttons"
#     )

#     # Define form key and label (Logic remains the same)
#     if choice == "LOGIN":
#         form_key   = "login_form"
#         form_title = "Log In to Your Account"
#         submit_lbl = "LOGIN"
#     elif choice == "SIGN UP":
#         form_key   = "signup_form"
#         form_title = "Create a New Account"
#         submit_lbl = "SIGN UP"
#     else: # FORGET PASSWORD
#         form_key   = "forget_password_form"
#         form_title = "Reset Your Password"
#         submit_lbl = "RESET PASSWORD"

#     # Define form (Dynamic height)
#     with st.form(key=form_key): 

#         # -----------------------------------------------------------------
#         # --- FORM FIELDS LOGIC ---
#         # -----------------------------------------------------------------

#         if choice == "LOGIN":
#             username = st.text_input("Username", placeholder="Enter your username", key=f"username_{form_key}")
#             password = st.text_input("Password", type="password", placeholder="Enter your password", key=f"password_{form_key}")

#         elif choice == "FORGET PASSWORD":
#             email = st.text_input("Email", placeholder="Enter your email address", key=f"email_{form_key}")

#         elif choice == "SIGN UP":
#             # --- START SIGN UP COLUMNS (PRESERVED ORIGINAL UNCONVENTIONAL STRUCTURE) ---

#             # Row 1: Username and Email (Side-by-side)
#             col1, col3, col5, col7 = st.columns(4)
#             with col1:
#                 username = st.text_input("Username", placeholder="Choose your username", key=f"username_{form_key}")
#             # with col2: (This was missing/merged in original, leading to stacking)
#                 email = st.text_input("Email", placeholder="Enter your email address", key=f"email_{form_key}")

#             # Row 2: First Name and Last Name (Side-by-side)
#             with col3:
#                 first_name = st.text_input("First Name", placeholder="Enter your first name", key=f"first_name_{form_key}")
#             # with col4:
#                 last_name = st.text_input("Last Name", placeholder="Enter your last name", key=f"last_name_{form_key}")

#             # Row 3: Organization and Password (Grouping Organization with Password input)
#             with col5:
#                 organization = st.text_input("Organization (Optional)", placeholder="Enter your organization", key=f"organization_{form_key}")
#             # with col6:
#                 password = st.text_input("Password", type="password", placeholder="Choose a strong password", key=f"password_{form_key}")
            
#             # Row 4: Confirm Password and an empty slot for alignment (or a short label)
#             with col7:
#                 confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat your password", key=f"confirm_password_{form_key}")
#                 api_key = st.text_input("OpenAI API Key", type="password", placeholder="Paste your required OpenAI API key", key=f"api_key_{form_key}")
            
#             # --- END SIGN UP COLUMNS ---

#         submitted = st.form_submit_button(submit_lbl, use_container_width=True)
    
#     error_placeholder = st.empty()


#     # -- Quick Test Account Box -- 
#     # Add a check here if you want to include the test box
#     # with st.expander("🧪 Quick Access (Test Credentials)"):
#     #     st.markdown("...", unsafe_allow_html=True)
            
#     st.markdown('</div>', unsafe_allow_html=True)

#     # Remaining return logic 
#     if submitted:
#         if choice == "LOGIN":
#             return {"action": "login", "username": username, "password": password, "error_placeholder": error_placeholder}
#         elif choice == "SIGN UP":
#             return {
#                 "action": "signup",
#                 "username": username, "password": password, "confirm_password": confirm_password, 
#                 "email": email, "first_name": first_name, "last_name": last_name, 
#                 "organization": organization, "api_key": api_key, "error_placeholder": error_placeholder
#             }
#         elif choice == "FORGET PASSWORD":
#             return {"action": "forget_password", "email": email, "error_placeholder": error_placeholder}
    
#     return None

# def show_login_signup(initial_choice_index=0):
#     # Page Config (Note: This should ideally be called once at the start of the app)
#     # Since it's decoupled, we'll keep it here but know it's best practice elsewhere.
#     st.set_page_config(
#         page_title="EvoAge - Login",
#         layout="wide",
#         page_icon="assets/logo.png"
#     )
    
#     # Calling Page setup CSS.
#     css_setting()

#     # --- Load Logo ---
#     logo = None
#     try:
#         with open("assets/logo.png", "rb") as img_file:
#             logo = base64.b64encode(img_file.read()).decode()
#     except FileNotFoundError:
#         pass

#     # --- 1. Custom Top Banner (Like the Video Header) ---
#     st.markdown(f"""
#     <div class="top-banner">
#         {'<img src="data:image/png;base64,' + logo + '" class="logo-small" alt="EvoAge Logo" />' if logo else ''}
#         <div class="banner-heading">EvoAge</div>
#         <p class="banner-subheading">
#             AI-Powered Biological Research Assistant. Explore gene, disease, chemical, and pathway connections using natural language queries. Powered by 1.5 Billion Knowledge Graph Triples.
#         </p>
#     </div>
#     """, unsafe_allow_html=True)


#     # --- 2. Stat Strips (Horizontal Info Blocks) ---
#     st.markdown("""
#     <div class="stat-strips-wrapper">
#         <div class="stat-card">
#             <div class="stat-value">1.5B+</div>
#             <div class="stat-label">KG Triples</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-value">Agent-LLM</div>
#             <div class="stat-label">Powered</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-value">Multi-Species</div>
#             <div class="stat-label">Evolution Data</div>
#         </div>
#         <div class="stat-card">
#             <div class="stat-value">Real-time</div>
#             <div class="stat-label">Analysis</div>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)
    
    
#     # --- 3. Login/Signup Form Area (Centered) ---
#     st.markdown('<div class="form-area-wrapper">', unsafe_allow_html=True)
    
#     # We use a placeholder column structure for centering the form stack
#     col_spacer_left, col_form, col_spacer_right = st.columns([1, 2, 1])

#     with col_form:
#         # Toggle radio 
#         choice = st.radio(
#             "Login/Signup/Forget Password Radio", 
#             ["LOGIN", "SIGN UP", "FORGET PASSWORD"], 
#             index=initial_choice_index, # Use the passed index
#             horizontal=True, 
#             label_visibility="collapsed", 
#             width="stretch"
#         )

#         # Define form key and label
#         if choice == "LOGIN":
#             form_key   = "login_form"
#             form_title = "Log In to Your Account"
#             submit_lbl = "LOGIN"
#         elif choice == "SIGN UP":
#             form_key   = "signup_form"
#             form_title = "Create a New Account"
#             submit_lbl = "SIGN UP"
#         else: # FORGET PASSWORD
#             form_key   = "forget_password_form"
#             form_title = "Reset Your Password"
#             submit_lbl = "RESET PASSWORD"

#         # Define form (Dynamic height)
#         with st.form(key=form_key): 
#             st.markdown(f'<div class="form-header">{form_title}</div>', unsafe_allow_html=True)

#             # --- Form Fields ---
#             if choice in ["LOGIN", "SIGN UP"]:
#                 username = st.text_input("Username", placeholder="Enter your username")

#             if choice in ["LOGIN", "SIGN UP"]:
#                 password = st.text_input("Password", type="password", placeholder="Enter your password" if choice == "LOGIN" else "Choose a strong password")
            
#             if choice in ["SIGN UP", "FORGET PASSWORD"]:
#                 email = st.text_input("Email", placeholder="Enter your email address")

#             # Additional fields for SIGN UP only
#             if choice == "SIGN UP":
#                 confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat your password")
#                 first_name = st.text_input("First Name", placeholder="Enter your first name")
#                 last_name  = st.text_input("Last Name",  placeholder="Enter your last name")
#                 organization = st.text_input("Organization", placeholder="Enter your organization (Optional)")
#                 api_key = st.text_input("OpenAI API Key", type="password", placeholder="Paste your required OpenAI API key")

#             submitted = st.form_submit_button(submit_lbl, use_container_width=True)
        
#         error_placeholder = st.empty()


#         # -- Quick Test Account Box -- (The Expander also now dynamically sizes)
#         with st.expander("🧪 Quick Access (Test Credentials)"):
#             test_username = ("ankiss")
#             test_password = ("huihuihui")
#             st.markdown(f"""
#             **Username**: <span>{test_username}</span><br>
#             **Password**: <span>{test_password}</span>
#             """, unsafe_allow_html=True)
            
#     # Close form wrapper
#     st.markdown('</div>', unsafe_allow_html=True)

#     # Remaining form submission logic (Return a dict for the main script to handle)
#     if submitted:
#         if choice == "LOGIN":
#             return {"action": "login", "username": username, "password": password, "error_placeholder": error_placeholder}
#         elif choice == "SIGN UP":
#             # (Simplified return, full validation should be in main script)
#             return {"action": "signup", "username": username, "password": password, "confirm_password": confirm_password, "email": email, "first_name": first_name, "last_name": last_name, "organization": organization, "api_key": api_key, "error_placeholder": error_placeholder}
#         elif choice == "FORGET PASSWORD":
#             return {"action": "forget_password", "email": email, "error_placeholder": error_placeholder}
    
#     return None



# import streamlit as st
# import base64


# def css_setting():
#     # — Load background image as base64 —
#     try:
#         with open("assets/bg6.png", "rb") as bg_file:
#             image = base64.b64encode(bg_file.read()).decode()
#     except FileNotFoundError:
#         image = None

#     css = f"""
#     <style>
#         /* FIX error messages getting hidden */

#         /* Base style for stColumn */
#         .right-welcome {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 0.8rem 0rem 0rem 0rem;
#             /* top    right   bottom   left */
#             border-radius: 16px;
#             width: 540px;
#             margin-top: 4vh;
#             max-width: 95%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 0.5rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15); /* subtle initial shadow */
#         }}
        
#         .block-container {{
#             max-width: 90%;
#             margin: 0 auto;
#             padding-top: 2rem;
#         }}
#         [data-testid="stRadio"] {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 0.5rem 1rem;
#             border-radius: 16px;
#             width: 540px;
#             margin-top: 2vh;
#             max-width: 95%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 0.5rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         /* Hover effect for stColumn */
#         [data-testid="stRadio"]:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}

        
#         [data-testid="stForm"] {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 1.25rem 2rem;
#             border-radius: 16px;
#             width: 100%;
#             margin-top: 0vh;
#             max-width: 95%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 0.5rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         /* Hover effect for stColumn */
#         [data-testid="stForm"]:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}

#         [data-testid="stExpander"] {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 0.5rem 0.5rem;
#             border-radius: 16px;
#             margin-top: 0.5vh;
#             max-width: 95%;
#             max-height: 30%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 1rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         /* Hover effect for stColumn */
#         [data-testid="stExpander"]:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}
        
#         [data-testid="stHeader"] {{
#             display: none !important;
#         }}
#         [data-testid="stAppViewContainer"]{{
#             background: url("data:image/png;base64,{image}");
#             background-size: cover;
#             background-repeat: no-repeat;
#             background-attachment: fixed;
#             background-position: center;
#         }}

#         html, body,
#         [data-testid="stAppViewContainer"],
#         [data-testid="stMain"] {{
#             height: 100vh !important;
#             overflow: auto !important;
#         }}

#         [data-testid="stMainBlockContainer"] {{
#             padding: 0 !important;
#             margin: 0 !important;
#         }}

#        /* Updated EvoAge intro block styling */

#         .intro-wrapper {{
#             display: flex;
#             align-items: top;
#             padding: 2rem;
#         }}

#         .intro-block {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 1.25rem 2rem;
#             border-radius: 16px;
#             width: 800px;
#             max-width: 100%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 1rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         .intro-block:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}


#         .intro-block h2 {{
#             color: #1c3f80;
#             font-size: 1.6rem;
#             margin: 0;
#             display: flex;
#             align-items: center;
#             gap: 0.5rem;
#         }}

#         .intro-block p {{
#             font-size: 1rem;
#             line-height: 1.6;
#             color: #333;
#             margin: 0;
#         }}

#         .intro-block ul {{
#             list-style-type: disc;
#             padding-left: 1.2rem;
#             margin: 0;
#             font-size: 0.95rem;
#             line-height: 1.5;
#             color: #444;
#         }}

#         .cta-button {{
#             all: unset;
#             display: block !important;
#             padding: 8px 12px !important;
#             background: linear-gradient(to right, #dbe4ec, #f0f2f5) !important;
#             color: #2f4f60 !important;
#             border: 1px solid #bfc9d1 !important;
#             border-radius: 10px !important;
#             font-weight: 600 !important;
#             text-align: center !important;
#             box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important;
#             cursor: pointer;
#             margin: 6px 0 !important;
#         }}

#         .cta-button:hover {{
#             background: linear-gradient(to right, #c3d9e9, #e0ebf3) !important;
#             color: #1d3a49 !important;
#             transform: translateY(-2px);
#             box-shadow: 0 6px 14px rgba(0, 0, 0, 0.15) !important;
#         }}

#         div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(2) {{
#             padding-top: 1rem !important;     /* Adjust top spacing */
#             padding-left: 2.5rem !important;
#             padding-right: 2.5rem !important;
#             margin-top: 0 !important;         /* Avoid vertical centering stretch */
#             align-items: flex-start !important;
#         }}

#         .right-welcome {{
#             display: flex;
#             flex-direction: column;
#             align-items: center;
#             text-align: center;
#         }}

#         .welcome-logo {{
#             width: 120px;
#         }}

#         .welcome-heading {{
#             font-family: 'Poppins', sans-serif;
#             color: #1c3f80;
#             font-size: 1.4rem;
#             font-weight: 500;           
#             margin-top: 0.75rem;
#             margin-bottom: 1rem;
#             letter-spacing: 0.5px;
#             line-height: 1.3;
#             position: relative;
#         }}

#         .welcome-heading::after {{
#             content: "";
#             display: block;
#             width: 40px;
#             height: 3px;
#             background: #f26b3a;
#             margin: 0.4rem auto 0 auto;
#             border-radius: 2px;
#         }}

#         h1 a {{
#             display: none !important;
#         }}

#         .form-wrapper {{
#             background: rgba(255, 255, 255, 0.95);
#             padding: 2rem;
#             border-radius: 12px;
#             max-width: 500px;
#             margin: auto;
#             box-shadow: 0 0 16px rgba(0, 0, 0, 0.08);
#             font-family: 'Poppins', sans-serif;
#         }}

#         .test-account-box {{
#             background-color: rgba(28, 63, 128, 0.05); /* subtle EvoAge blue tint */
#             border-left: 4px solid #f26b3a;           /* EvoAge orange accent */
#             padding: 0.75rem 1rem;
#             margin-top: 1.5rem;
#             font-size: 0.85rem;
#             color: #1c3f80;
#             border-radius: 6px;
#             max-width: 450px;
#             box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
#         }}

#         .test-account-box ul {{
#             padding-left: 1.25rem;
#             margin: 0.25rem 0 0 0;
#         }}

#         .test-account-box li {{
#             line-height: 1.4;
#         }}

#         .test-account-box span {{
#             color: #333;
#             font-family: monospace;
#         }}
#         /* Data Stats Block */
#         .data-stats-container {{
#             background: linear-gradient(135deg, #1c3f80, #3a60a8);
#             color: #fff;
#             padding: 1rem;
#             border-radius: 12px;
#             margin-top: 1.5rem;
#             box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
#             display: flex;
#             justify-content: space-around;
#             text-align: center;
#             max-width: 500px;
#             width: 100%;
#             margin-left: auto;
#             margin-right: auto;
#         }}
#         .stat-item {{
#             display: flex;
#             flex-direction: column;
#             align-items: center;
#         }}
#         .stat-value {{
#             font-size: 1.5rem;
#             font-weight: 700;
#             color: #f26b3a;
#             line-height: 1.2;
#         }}
#         .stat-label {{
#             font-size: 0.75rem;
#             font-weight: 400;
#             opacity: 0.85;
#             margin-top: 0.2rem;
#             text-transform: uppercase;
#             letter-spacing: 0.5px;
#         }}

#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# ### 2. Streamlit Layout Implementation


# def show_login_signup():
#     # Page Config
#     st.set_page_config(
#         page_title="EvoAge",
#         layout="wide",
#         page_icon="assets/logo.png"
#     )
    
#     # Calling Page setup CSS.
#     css_setting()

#     # — Two-column layout — (Adjusted ratios slightly for better space)
#     _,right_col,left_col = st.columns([0.001, 5.0, 4.99], gap="medium", vertical_alignment="center")

#     with left_col:
#         # — Load logo as base64 —
#         try:
#             with open("assets/logo.png", "rb") as img_file:
#                 logo = base64.b64encode(img_file.read()).decode()
#         except FileNotFoundError:
#             logo = None
            
#         st.markdown(f"""
#             <div class="right-welcome">
#                 {'<img src="data:image/png;base64,' + logo + '" class="welcome-logo" alt="EvoAge Logo" />' if logo else ''}
#                 <h1 class="welcome-heading">Welcome to EvoAge</h1>
#             </div>
#             """, unsafe_allow_html=True)
#         # Left column content remains the same, but smaller
#         st.markdown("""
#             <div class="intro-wrapper">
#                 <div class="intro-block">
#                     <h2>Introducing <strong>EvoAge</strong> 🔬</h2>
#                     <p>
#                         EvoAge is an AI-powered biological assistant built on top of EvoKG,
#                         a multi-species evolutionary knowledge graph. It allows researchers
#                         to explore gene, disease, chemical, and pathway connections using natural language queries.
#                     </p>
#                     <ul>
#                         <li>Built with **OpenAI & Kani** framework</li>
#                         <li>Powered by curated biological knowledge of **EvoKG**</li>
#                         <li>Open-source & community-driven</li>
#                     </ul>
#                     <a href="https://www.ahuja-lab.in/" class="cta-button">Learn More ➔</a>
#                     <div class="data-stats-container">
#                         <div class="stat-item">
#                             <div class="stat-value">30M+</div>
#                             <div class="stat-label">Nodes (Entities)</div>
#                         </div>
#                         <div class="stat-item">
#                             <div class="stat-value">1B+</div>
#                             <div class="stat-label">Edges (Triples)</div>
#                         </div>
#                     </div>
#                 </div>
#             </div>
#         """, unsafe_allow_html=True)

#     with right_col:
#         # # — Load logo as base64 —
#         # try:
#         #     with open("assets/logo.png", "rb") as img_file:
#         #         logo = base64.b64encode(img_file.read()).decode()
#         # except FileNotFoundError:
#         #     logo = None

#         # Welcome Block (Now more compact)
#         # st.markdown(f"""
#         # <div class="right-welcome">
#         #     {'<img src="data:image/png;base64,' + logo + '" class="welcome-logo" alt="EvoAge Logo" />' if logo else ''}
#         #     <h1 class="welcome-heading">Welcome to EvoAge</h1>
#         # </div>
#         # """, unsafe_allow_html=True)


#         # Toggle radio (Now more compact)
#         choice = st.radio(
#             "Login/Signup/Forget Password Radio", 
#             ["LOGIN", "SIGN UP", "FORGET PASSWORD"], 
#             index=0, 
#             horizontal=True, 
#             label_visibility="collapsed", 
#             width="stretch"
#         )

#         # Define form key and label
#         if choice == "LOGIN":
#             form_key   = "login_form"
#             form_title = "Log In to Your Account"
#             submit_lbl = "LOGIN"
#         elif choice == "SIGN UP":
#             form_key   = "signup_form"
#             form_title = "Create a New Account"
#             submit_lbl = "SIGN UP"
#         else: # FORGET PASSWORD
#             form_key   = "forget_password_form"
#             form_title = "Reset Your Password"
#             submit_lbl = "RESET PASSWORD"

#         # Define form (Dynamic height and compact fields)
#         with st.form(key=form_key): 
#             st.markdown(f'<div class="form-header">{form_title}</div>', unsafe_allow_html=True)

#             if choice in ["LOGIN"]:
#                 username = st.text_input("Username", placeholder="Enter your username")

#             if choice in ["LOGIN"]:
#                 password = st.text_input("Password", type="password", placeholder="Enter your password" if choice == "LOGIN" else "Choose a strong password")
            
#             if choice in ["FORGET PASSWORD"]:
#                 email = st.text_input("Email", placeholder="Enter your email address")

#             # Additional fields for SIGN UP only
#             if choice == "SIGN UP":
#                 username = st.text_input("Username", placeholder="Enter your username")
#                 email = st.text_input("Email", placeholder="Enter your email address")
#                 first_name = st.text_input("First Name", placeholder="Enter your first name")
#                 last_name  = st.text_input("Last Name",  placeholder="Enter your last name")
#                 organization = st.text_input("Organization", placeholder="Enter your organization (Optional)")
#                 password = st.text_input("Password", type="password", placeholder="Enter your password" if choice == "LOGIN" else "Choose a strong password")
#                 confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat your password")
#                 api_key = st.text_input("OpenAI API Key", type="password", placeholder="Paste your required OpenAI API key")

#             submitted = st.form_submit_button(submit_lbl, use_container_width=True)
        
#         error_placeholder = st.empty()


#         # -- Quick Test Account Box -- (The Expander also now dynamically sizes)
#         # with st.expander("🧪 Quick Access (Test Credentials)"):
#         #     test_username = ("ankiss")
#         #     test_password = ("huihuihui")
#         #     st.markdown(f"""
#         #     **Username**: <span>{test_username}</span><br>
#         #     **Password**: <span>{test_password}</span>
#         #     """, unsafe_allow_html=True)
#             # Added slight markdown changes for better visibility in the expander

#         # Remaining form submission logic
#         if submitted:
#             if choice == "LOGIN":
#                 # Add validation for empty fields here if needed
#                 if not username or not password:
#                     error_placeholder.error("Username and Password are required.")
#                     return None
#                 return {"action": "login", "username": username, "password": password, "error_placeholder": error_placeholder}
            
#             elif choice == "SIGN UP":
#                 # Mandatory fields check for signup
#                 required_fields = {
#                     "Password": password, "Username": username,  "Confirm Password": confirm_password, 
#                     "Email": email, "First Name": first_name, "Last Name": last_name, "OpenAI API Key": api_key
#                 }
#                 if any(not val.strip() for val in required_fields.values()):
#                     error_placeholder.error("All fields (except Organization) are required.")
#                     return None

#                 # Username length check
#                 if len(username.strip()) < 3:
#                     error_placeholder.error("Username must be at least 3 characters long.")
#                     return None

#                 # API key length check
#                 if len(api_key.strip()) < 10:
#                     error_placeholder.error("OpenAI API Key must be at least 10 characters long.")
#                     return None

#                 # Password match check
#                 if password != confirm_password:
#                     error_placeholder.error("Passwords do not match.")
#                     return None
                    
#                 return {
#                     "action": "signup",
#                     "username": username,
#                     "password": password,
#                     "confirm_password": confirm_password,
#                     "email": email,
#                     "first_name": first_name,
#                     "last_name": last_name,
#                     "organization": organization,
#                     "api_key": api_key,
#                     "error_placeholder": error_placeholder
#                 }
            
#             elif choice == "FORGET PASSWORD":
#                 # error_placeholder.info("Email is required to reset your password.")
#                 # if not email:
#                 #     # error_placeholder.error("Email is required to reset your password.")
#                 #     return None
#                 # error_placeholder.success("A password reset link has been sent to your registered email address.")
#                 return {
#                     "action": "forget_password", 
#                     "email": email,
#                     "error_placeholder": error_placeholder
#                 }
        
#         return None

# ############################################################################### with emptyholder for error #############################################

# # import streamlit as st
# # import base64

# # # Initial Page CSS Setting -> Hide
# # def css_setting():
# #     # — Load background image as base64 —
# #     try:
# #         with open("assets/bg6.png", "rb") as bg_file:
# #             image = base64.b64encode(bg_file.read()).decode()
# #     except FileNotFoundError:
# #         image = None

# #     css = f"""
# #     <style>
# #         /* FIX error messages getting hidden */

# #         /* Base style for stColumn */
# #         .right-welcome {{
# #             background: rgba(255, 255, 255, 0.9);
# #             padding: 0.8rem 0rem 0rem 0rem;
# #             /* top    right   bottom   left */
# #             border-radius: 16px;
# #             width: 540px;
# #             margin-top: 4vh;
# #             max-width: 95%;
# #             font-family: 'Poppins', sans-serif;
# #             display: flex;
# #             flex-direction: column;
# #             gap: 0.5rem;
        
# #             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15); /* subtle initial shadow */
# #         }}
        
# #         .block-container {{
# #         max-width: 1200px;
# #         margin: 0 auto;
# #         padding-top: 0rem;
# #         }}

# #         [data-testid="stRadio"] {{
# #             background: rgba(255, 255, 255, 0.9);
# #             padding: 0.5rem 1rem;
# #             border-radius: 16px;
# #             width: 540px;
# #             margin-top: 2vh;
# #             max-width: 95%;
# #             font-family: 'Poppins', sans-serif;
# #             display: flex;
# #             flex-direction: column;
# #             gap: 0.5rem;
        
# #             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
# #             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
# #         }}
        
# #         /* Hover effect for stColumn */
# #         [data-testid="stRadio"]:hover {{
# #             transform: translateY(-6px);
# #             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
# #         }}

        
# #         [data-testid="stForm"] {{
# #             background: rgba(255, 255, 255, 0.9);
# #             padding: 1.25rem 2rem;
# #             border-radius: 16px;
# #             width: 540px;
# #             margin-top: 0vh;
# #             max-width: 95%;
# #             font-family: 'Poppins', sans-serif;
# #             display: flex;
# #             flex-direction: column;
# #             gap: 0.5rem;
        
# #             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
# #             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
# #         }}
        
# #         /* Hover effect for stColumn */
# #         [data-testid="stForm"]:hover {{
# #             transform: translateY(-6px);
# #             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
# #         }}

# #         [data-testid="stExpander"] {{
# #             background: rgba(255, 255, 255, 0.9);
# #             padding: 0.5rem 0.5rem;
# #             border-radius: 16px;
# #             margin-top: 0.5vh;
# #             max-width: 95%;
# #             max-height: 30%;
# #             font-family: 'Poppins', sans-serif;
# #             display: flex;
# #             flex-direction: column;
# #             gap: 1rem;
        
# #             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
# #             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
# #         }}
        
# #         /* Hover effect for stColumn */
# #         [data-testid="stExpander"]:hover {{
# #             transform: translateY(-6px);
# #             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
# #         }}
        
# #         [data-testid="stHeader"] {{
# #             display: none !important;
# #         }}
# #         [data-testid="stAppViewContainer"]{{
# #             background: url("data:image/png;base64,{image}");
# #             background-size: cover;
# #             background-repeat: no-repeat;
# #             background-attachment: fixed;
# #             background-position: center;
# #         }}

# #         html, body,
# #         [data-testid="stAppViewContainer"],
# #         [data-testid="stMain"] {{
# #             height: 100vh !important;
# #             overflow: auto !important;
# #         }}

# #         [data-testid="stMainBlockContainer"] {{
# #             padding: 0 !important;
# #             margin: 0 !important;
# #         }}

# #        /* Updated EvoAge intro block styling */

# #         .intro-wrapper {{
# #             min-height: 100vh;
# #             display: flex;
# #             justify-content: center;
# #             align-items: center;
# #             padding: 2rem;
# #         }}

# #         .intro-block {{
# #             background: rgba(255, 255, 255, 0.9);
# #             padding: 1.25rem 2rem;
# #             border-radius: 16px;
# #             width: 540px;
# #             max-width: 95%;
# #             font-family: 'Poppins', sans-serif;
# #             display: flex;
# #             flex-direction: column;
# #             gap: 1rem;
        
# #             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
# #             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
# #         }}
        
# #         .intro-block:hover {{
# #             transform: translateY(-6px);
# #             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
# #         }}


# #         .intro-block h2 {{
# #             color: #1c3f80;
# #             font-size: 1.6rem;
# #             margin: 0;
# #             display: flex;
# #             align-items: center;
# #             gap: 0.5rem;
# #         }}

# #         .intro-block p {{
# #             font-size: 1rem;
# #             line-height: 1.6;
# #             color: #333;
# #             margin: 0;
# #         }}

# #         .intro-block ul {{
# #             list-style-type: disc;
# #             padding-left: 1.2rem;
# #             margin: 0;
# #             font-size: 0.95rem;
# #             line-height: 1.5;
# #             color: #444;
# #         }}

# #         .cta-button {{
# #             all: unset;
# #             display: block !important;
# #             padding: 8px 12px !important;
# #             background: linear-gradient(to right, #dbe4ec, #f0f2f5) !important;
# #             color: #2f4f60 !important;
# #             border: 1px solid #bfc9d1 !important;
# #             border-radius: 10px !important;
# #             font-weight: 600 !important;
# #             text-align: center !important;
# #             box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important;
# #             cursor: pointer;
# #             margin: 6px 0 !important;
# #         }}

# #         .cta-button:hover {{
# #             background: linear-gradient(to right, #c3d9e9, #e0ebf3) !important;
# #             color: #1d3a49 !important;
# #             transform: translateY(-2px);
# #             box-shadow: 0 6px 14px rgba(0, 0, 0, 0.15) !important;
# #         }}

# #         div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(2) {{
# #             padding-top: 1rem !important;     /* Adjust top spacing */
# #             padding-left: 2.5rem !important;
# #             padding-right: 2.5rem !important;
# #             margin-top: 0 !important;         /* Avoid vertical centering stretch */
# #             align-items: flex-start !important;
# #         }}

# #         .right-welcome {{
# #             display: flex;
# #             flex-direction: column;
# #             align-items: center;
# #             text-align: center;
# #         }}

# #         .welcome-logo {{
# #             width: 120px;
# #         }}

# #         .welcome-heading {{
# #             font-family: 'Poppins', sans-serif;
# #             color: #1c3f80;
# #             font-size: 1.4rem;
# #             font-weight: 500;           
# #             margin-top: 0.75rem;
# #             margin-bottom: 1rem;
# #             letter-spacing: 0.5px;
# #             line-height: 1.3;
# #             position: relative;
# #         }}

# #         .welcome-heading::after {{
# #             content: "";
# #             display: block;
# #             width: 40px;
# #             height: 3px;
# #             background: #f26b3a;
# #             margin: 0.4rem auto 0 auto;
# #             border-radius: 2px;
# #         }}

# #         h1 a {{
# #             display: none !important;
# #         }}

# #         .form-wrapper {{
# #             background: rgba(255, 255, 255, 0.95);
# #             padding: 2rem;
# #             border-radius: 12px;
# #             max-width: 500px;
# #             margin: auto;
# #             box-shadow: 0 0 16px rgba(0, 0, 0, 0.08);
# #             font-family: 'Poppins', sans-serif;
# #         }}

# #         .test-account-box {{
# #             background-color: rgba(28, 63, 128, 0.05); /* subtle EvoAge blue tint */
# #             border-left: 4px solid #f26b3a;           /* EvoAge orange accent */
# #             padding: 0.75rem 1rem;
# #             margin-top: 1.5rem;
# #             font-size: 0.85rem;
# #             color: #1c3f80;
# #             border-radius: 6px;
# #             max-width: 450px;
# #             box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
# #         }}

# #         .test-account-box ul {{
# #             padding-left: 1.25rem;
# #             margin: 0.25rem 0 0 0;
# #         }}

# #         .test-account-box li {{
# #             line-height: 1.4;
# #         }}

# #         .test-account-box span {{
# #             color: #333;
# #             font-family: monospace;
# #         }}


# #     </style>
# #     """
# #     st.markdown(css, unsafe_allow_html=True)

# # # Testing CSS
# # # def testing_css():
# # #     testing_css = f"""
# # #     <style>
# # #         [data-testid="stElementContainer"]{{
# # #             background-color: #000000
# # #         }}
# # #     </style>
# # #     """
# # #     st.markdown(testing_css, unsafe_allow_html=True)


# # def show_login_signup():
# #     # Page Config
# #     st.set_page_config(
# #         page_title="EvoAge",
# #         layout="wide",
# #         page_icon="assets/logo.png"
# #     )
    
# #     # Calling Page setup CSS.
# #     css_setting()

# #     # — Two‑column layout —
# #     _,right_col,left_col = st.columns([0.3, 4.5, 5.2], gap=None, vertical_alignment="center")

# #     with left_col:
# #             st.markdown("""
# #             <div class="intro-wrapper">
# #                 <div class="intro-block">
# #                     <h2>Introducing <strong>EvoAge</strong> 🔬</h2>
# #                     <p>
# #                         EvoAge is an AI-powered biological assistant built on top of EvoKG,
# #                         a multi-species evolutionary knowledge graph. It allows researchers
# #                         to explore gene, disease, chemical, and pathway connections using natural language queries.
# #                     </p>
# #                     <ul>
# #                         <li>Built with OpenAI & Kani framework</li>
# #                         <li>Powered by curated biological knowledge of EvoKG</li>
# #                         <li>Open-source & community-driven</li>
# #                     </ul>
# #                     <a href="#" class="cta-button">Learn More ➔</a>
# #                 </div>
# #             </div>
# #         """, unsafe_allow_html=True)

# #     # Optional: placeholder right column
# #     with right_col:
# #         # — Load logo as base64 —
# #         try:
# #             with open("assets/logo.png", "rb") as img_file:
# #                 logo = base64.b64encode(img_file.read()).decode()
# #         except FileNotFoundError:
# #             logo = None
# #         st.markdown(f"""
# #         <div class="right-welcome">
# #             <img src="data:image/png;base64,{logo}" class="welcome-logo" alt="EvoAge Logo" />
# #             <h1 class="welcome-heading">Welcome to EvoAge</h1>
# #         </div>
# #         """, unsafe_allow_html=True)


# #         # Toggle radio - **MODIFIED** to include "FORGET PASSWORD"
# #         choice = st.radio(
# #             "Login/Signup/Forget Password Radio", 
# #             ["LOGIN", "SIGN UP", "FORGET PASSWORD"], 
# #             index=0, 
# #             horizontal=True, 
# #             label_visibility="collapsed", 
# #             width="stretch"
# #         )

# #         # Define form key and label - **MODIFIED** for the new choice
# #         if choice == "LOGIN":
# #             form_key   = "login_form"
# #             submit_lbl = "LOGIN"
# #         elif choice == "SIGN UP":
# #             form_key   = "signup_form"
# #             submit_lbl = "SIGN UP"
# #         else: # FORGET PASSWORD
# #             form_key   = "forget_password_form"
# #             submit_lbl = "RESET PASSWORD"

# #         # Define form
# #         with st.form(key=form_key, height=240):
            
# #             # Fields for LOGIN, SIGN UP, and FORGET PASSWORD
# #             if choice in ["LOGIN", "SIGN UP"]:
# #                 username = st.text_input(
# #                     "Username",
# #                     placeholder="Enter your username"
# #                 )

# #             # Fields for LOGIN and SIGN UP
# #             if choice in ["LOGIN", "SIGN UP"]:
# #                 password = st.text_input(
# #                     "Password",
# #                     type="password",
# #                     placeholder="Enter your password" if choice == "LOGIN" else "Choose a password"
# #                 )
            
# #             # Fields for SIGN UP and FORGET PASSWORD
# #             if choice in ["SIGN UP", "FORGET PASSWORD"]:
# #                 email = st.text_input(
# #                     "Email",
# #                     placeholder="Enter your email address"
# #                 )

# #             # Additional fields for SIGN UP only
# #             if choice == "SIGN UP":
# #                 confirm_password = st.text_input(
# #                     "Confirm Password",
# #                     type="password",
# #                     placeholder="Repeat your password"
# #                 )

# #                 first_name = st.text_input("First Name", placeholder="Enter your first name")
# #                 last_name  = st.text_input("Last Name",  placeholder="Enter your last name")
# #                 organization = st.text_input("Organization", placeholder="Enter your organization")

# #                 api_key = st.text_input(
# #                     "OpenAI API Key",
# #                     type="password",
# #                     placeholder="Paste your OpenAI API key"
# #                 )

# #             submitted = st.form_submit_button(submit_lbl)
# #         error_placeholder = st.empty()


# #         # -- Quick Test Account Box --
# #         with st.expander("🧪 Quick Access (Test Credentials)"):
# #             test_username = ("ankiss")
# #             test_password = ("huihuihui")
# #             st.markdown(f"""
# #             Username: <span>{test_username}</span>\n
# #             Password: <span>{test_password}</span>
# #             """, unsafe_allow_html=True)

# #         if submitted:
# #             if choice == "LOGIN":
# #                 return {"action": "login", "username": username, "password": password, "error_placeholder": error_placeholder}
# #             elif choice == "SIGN UP":
# #                 # Username length check
# #                 if len(username.strip()) < 3:
# #                     error_placeholder.error("Username must be at least 3 characters long.")
# #                     return None

# #                 # API key length check
# #                 if len(api_key.strip()) < 10:
# #                     error_placeholder.error("OpenAI API Key must be at least 10 characters long.")
# #                     return None

# #                 # Password match check
# #                 if password != confirm_password:
# #                     error_placeholder.error("Passwords do not match.")
# #                     return None
                    
# #                 return {
# #                     "action": "signup",
# #                     "username": username,
# #                     "password": password,
# #                     "confirm_password": confirm_password,
# #                     "email": email,
# #                     "first_name": first_name,
# #                     "last_name": last_name,
# #                     "organization": organization,
# #                     "api_key": api_key,
# #                     "error_placeholder": error_placeholder
# #                 }
# #             elif choice == "FORGET PASSWORD":
# #                 return {
# #                     "action": "forget_password", 
# #                     "email": email,
# #                     "error_placeholder": error_placeholder
# #                 }
# #         return None
# ################################################################### first #########################################################################
# import streamlit as st
# import base64

# # Initial Page CSS Setting -> Hide
# def css_setting():
#     # — Load background image as base64 —
#     try:
#         with open("assets/bg6.png", "rb") as bg_file:
#             image = base64.b64encode(bg_file.read()).decode()
#     except FileNotFoundError:
#         image = None

#     css = f"""
#     <style>
#         /* Base style for stColumn */
#         .right-welcome {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 0.8rem 0rem 0rem 0rem;
#             /* top    right   bottom   left */
#             border-radius: 16px;
#             width: 540px;
#             margin-top: 4vh;
#             max-width: 95%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 0.5rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15); /* subtle initial shadow */
#         }}
        
#         .block-container {{
#         max-width: 1200px;
#         margin: 0 auto;
#         padding-top: 0rem;
#         }}

#         [data-testid="stRadio"] {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 0.5rem 1rem;
#             border-radius: 16px;
#             width: 540px;
#             margin-top: 2vh;
#             max-width: 95%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 0.5rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         /* Hover effect for stColumn */
#         [data-testid="stRadio"]:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}

        
#         [data-testid="stForm"] {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 1.25rem 2rem;
#             border-radius: 16px;
#             width: 540px;
#             margin-top: 0vh;
#             max-width: 95%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 0.5rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         /* Hover effect for stColumn */
#         [data-testid="stForm"]:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}

#         [data-testid="stExpander"] {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 0.5rem 0.5rem;
#             border-radius: 16px;
#             margin-top: 0.5vh;
#             max-width: 95%;
#             max-height: 30%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 1rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         /* Hover effect for stColumn */
#         [data-testid="stExpander"]:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}
        
#         [data-testid="stHeader"] {{
#             display: none !important;
#         }}
#         [data-testid="stAppViewContainer"]{{
#             background: url("data:image/png;base64,{image}");
#             background-size: cover;
#             background-repeat: no-repeat;
#             background-attachment: fixed;
#             background-position: center;
#         }}

#         html, body,
#         [data-testid="stAppViewContainer"],
#         [data-testid="stMain"] {{
#             height: 100vh !important;
#             overflow: hidden !important;
#         }}

#         [data-testid="stMainBlockContainer"] {{
#             padding: 0 !important;
#             margin: 0 !important;
#         }}

#        /* Updated EvoAge intro block styling */

#         .intro-wrapper {{
#             min-height: 100vh;
#             display: flex;
#             justify-content: center;
#             align-items: center;
#             padding: 2rem;
#         }}

#         .intro-block {{
#             background: rgba(255, 255, 255, 0.9);
#             padding: 1.25rem 2rem;
#             border-radius: 16px;
#             width: 540px;
#             max-width: 95%;
#             font-family: 'Poppins', sans-serif;
#             display: flex;
#             flex-direction: column;
#             gap: 1rem;
        
#             box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4); /* subtle initial shadow */
#             transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out;
#         }}
        
#         .intro-block:hover {{
#             transform: translateY(-6px);
#             box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2); /* deeper shadow on hover */
#         }}


#         .intro-block h2 {{
#             color: #1c3f80;
#             font-size: 1.6rem;
#             margin: 0;
#             display: flex;
#             align-items: center;
#             gap: 0.5rem;
#         }}

#         .intro-block p {{
#             font-size: 1rem;
#             line-height: 1.6;
#             color: #333;
#             margin: 0;
#         }}

#         .intro-block ul {{
#             list-style-type: disc;
#             padding-left: 1.2rem;
#             margin: 0;
#             font-size: 0.95rem;
#             line-height: 1.5;
#             color: #444;
#         }}

#         .cta-button {{
#             all: unset;
#             display: block !important;
#             padding: 8px 12px !important;
#             background: linear-gradient(to right, #dbe4ec, #f0f2f5) !important;
#             color: #2f4f60 !important;
#             border: 1px solid #bfc9d1 !important;
#             border-radius: 10px !important;
#             font-weight: 600 !important;
#             text-align: center !important;
#             box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important;
#             cursor: pointer;
#             margin: 6px 0 !important;
#         }}

#         .cta-button:hover {{
#             background: linear-gradient(to right, #c3d9e9, #e0ebf3) !important;
#             color: #1d3a49 !important;
#             transform: translateY(-2px);
#             box-shadow: 0 6px 14px rgba(0, 0, 0, 0.15) !important;
#         }}

#         div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(2) {{
#             padding-top: 1rem !important;     /* Adjust top spacing */
#             padding-left: 2.5rem !important;
#             padding-right: 2.5rem !important;
#             margin-top: 0 !important;         /* Avoid vertical centering stretch */
#             align-items: flex-start !important;
#         }}

#         .right-welcome {{
#             display: flex;
#             flex-direction: column;
#             align-items: center;
#             text-align: center;
#         }}

#         .welcome-logo {{
#             width: 120px;
#         }}

#         .welcome-heading {{
#             font-family: 'Poppins', sans-serif;
#             color: #1c3f80;
#             font-size: 1.4rem;
#             font-weight: 500;           
#             margin-top: 0.75rem;
#             margin-bottom: 1rem;
#             letter-spacing: 0.5px;
#             line-height: 1.3;
#             position: relative;
#         }}

#         .welcome-heading::after {{
#             content: "";
#             display: block;
#             width: 40px;
#             height: 3px;
#             background: #f26b3a;
#             margin: 0.4rem auto 0 auto;
#             border-radius: 2px;
#         }}

#         h1 a {{
#             display: none !important;
#         }}

#         .form-wrapper {{
#             background: rgba(255, 255, 255, 0.95);
#             padding: 2rem;
#             border-radius: 12px;
#             max-width: 500px;
#             margin: auto;
#             box-shadow: 0 0 16px rgba(0, 0, 0, 0.08);
#             font-family: 'Poppins', sans-serif;
#         }}

#         .test-account-box {{
#             background-color: rgba(28, 63, 128, 0.05); /* subtle EvoAge blue tint */
#             border-left: 4px solid #f26b3a;           /* EvoAge orange accent */
#             padding: 0.75rem 1rem;
#             margin-top: 1.5rem;
#             font-size: 0.85rem;
#             color: #1c3f80;
#             border-radius: 6px;
#             max-width: 450px;
#             box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
#         }}

#         .test-account-box ul {{
#             padding-left: 1.25rem;
#             margin: 0.25rem 0 0 0;
#         }}

#         .test-account-box li {{
#             line-height: 1.4;
#         }}

#         .test-account-box span {{
#             color: #333;
#             font-family: monospace;
#         }}

#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# # Testing CSS
# # def testing_css():
# #     testing_css = f"""
# #     <style>
# #         [data-testid="stElementContainer"]{{
# #             background-color: #000000
# #         }}
# #     </style>
# #     """
# #     st.markdown(testing_css, unsafe_allow_html=True)


# def show_login_signup():
#     # Page Config
#     st.set_page_config(
#         page_title="EvoAge",
#         layout="wide",
#         page_icon="assets/logo.png"
#     )
    
#     # Calling Page setup CSS.
#     css_setting()

#     # — Two‑column layout —
#     _,right_col,left_col = st.columns([0.3, 4.5, 5.2], gap=None, vertical_alignment="center")

#     with left_col:
#             st.markdown("""
#             <div class="intro-wrapper">
#                 <div class="intro-block">
#                     <h2>Introducing <strong>EvoAge</strong> 🔬</h2>
#                     <p>
#                         EvoAge is an AI-powered biological assistant built on top of EvoKG,
#                         a multi-species evolutionary knowledge graph. It allows researchers
#                         to explore gene, disease, chemical, and pathway connections using natural language queries.
#                     </p>
#                     <ul>
#                         <li>Built with OpenAI & Kani framework</li>
#                         <li>Powered by curated biological knowledge of EvoKG</li>
#                         <li>Open-source & community-driven</li>
#                     </ul>
#                     <a href="#" class="cta-button">Learn More ➔</a>
#                 </div>
#             </div>
#         """, unsafe_allow_html=True)

#     # Optional: placeholder right column
#     with right_col:
#         # — Load logo as base64 —
#         try:
#             with open("assets/logo.png", "rb") as img_file:
#                 logo = base64.b64encode(img_file.read()).decode()
#         except FileNotFoundError:
#             logo = None
#         st.markdown(f"""
#         <div class="right-welcome">
#             <img src="data:image/png;base64,{logo}" class="welcome-logo" alt="EvoAge Logo" />
#             <h1 class="welcome-heading">Welcome to EvoAge</h1>
#         </div>
#         """, unsafe_allow_html=True)


#         # Toggle radio
#         choice = st.radio("Login/Signup Radio", ["LOGIN", "SIGN UP"], index=0, horizontal=True, label_visibility="collapsed", width="stretch")

#         # Define form key and label
#         form_key   = "login_form"  if choice == "LOGIN"  else "signup_form"
#         submit_lbl = "LOGIN"       if choice == "LOGIN"  else "SIGN UP"

#         # Define form
#         with st.form(key=form_key, height=240):
#             username = st.text_input(
#                 "Username",
#                 placeholder="Enter your username" if choice == "LOGIN" else "Pick a username"
#             )

#             password = st.text_input(
#                 "Password",
#                 type="password",
#                 placeholder="Enter your password" if choice == "LOGIN" else "Choose a password"
#             )

#             # Additional fields for SIGN UP
#             if choice == "SIGN UP":
#                 email = st.text_input(
#                     "Email",
#                     placeholder="Enter your email address"
#                 )

#                 confirm_password = st.text_input(
#                     "Confirm Password",
#                     type="password",
#                     placeholder="Repeat your password"
#                 )

#                 first_name = st.text_input("First Name", placeholder="Enter your first name")
#                 last_name  = st.text_input("Last Name",  placeholder="Enter your last name")
#                 organization = st.text_input("Organization", placeholder="Enter your organization")

#                 api_key = st.text_input(
#                     "OpenAI API Key",
#                     type="password",
#                     placeholder="Paste your OpenAI API key"
#                 )

#             submitted = st.form_submit_button(submit_lbl)

#         # -- Quick Test Account Box --
#         with st.expander("🧪 Quick Access (Test Credentials)"):
#             test_username = ("ankiss")
#             test_password = ("huihuihui")
#             st.markdown(f"""
#             Username: {test_username}\n
#             Password: {test_password}
#             """, unsafe_allow_html=True)

#         if submitted:
#             if choice == "LOGIN":
#                 return {"action": "login", "username": username, "password": password}
#             else:
#                 return {
#                     "action": "signup",
#                     "username": username,
#                     "password": password,
#                     "confirm_password": confirm_password,
#                     "email": email,
#                     "first_name": first_name,
#                     "last_name": last_name,
#                     "organization": organization,
#                     "api_key": api_key,
#                 }
#         return None
