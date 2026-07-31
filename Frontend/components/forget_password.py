import streamlit as st
import requests


def show_reset_password_page():
    # Set your FastAPI backend URL (load from config if possible)
    BACKEND_URL = "http://192.168.3.153:1026"

    st.set_page_config(page_title="Reset Password")
    st.title("EvoAge • Reset Your Password")

    # --- TOKEN RETRIEVAL AND VALIDATION ---
    token = None
    try:
        # 1. Try to read the 'token' from the URL's query parameters
        token = st.query_params["token"]
    except KeyError:
        # 2. If the token is not present in the URL, display an error and stop.
        st.error("❌ Invalid or missing reset token. This link may be expired or incorrect.")
        # st.page_link("1_Login.py", label="Go to Login")
        st.stop()
        
    if not token or len(token) < 10: # Basic length check for safety
        st.error("❌ Invalid token structure. Please request a new link.")
        st.page_link("1_Login.py", label="Go to Login")
        st.stop()
    # ----------------------------------------

    st.write("Please enter your new password below.")

    with st.form("reset_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Reset Password")

    if submitted:
        if not new_password or not confirm_password:
            st.error("⚠️ Please fill out both password fields.")
        elif new_password != confirm_password:
            st.error("⚠️ Passwords do not match.")
        else:
            # Use a spinner while waiting for the API response
            with st.spinner("🔄 Attempting to reset password..."):
                # try:
                # Call the /auth/reset-password endpoint using the retrieved token
                response = requests.post(
                    f"{BACKEND_URL}/auth/reset-password",
                    json={"token": token, "new_password": new_password}
                )
                
                if response.status_code == 200:
                    st.success("✅ Password reset successfully! You can now log in.")
                    st.balloons()
                    
                    # Clear the token from the URL to prevent re-submission errors
                    if "token" in st.query_params:
                        del st.query_params["token"]
                    
                    # Rerun to clear the form and reflect the clean URL state
                    # st.rerun() 
                
                elif response.status_code == 400:
                    detail = response.json().get('detail', 'Invalid or expired token.')
                    st.error(f"❌ Error: {detail} Please request a new link.")
                
                else:
                    st.error(f"❌ An error occurred: {response.json().get('detail', 'Unknown server error')}")

            # except requests.exceptions.ConnectionError:
            #     st.error("🚫 Connection error. Could not reach the backend server.")
            # except Exception as e:
            #     st.error(f"❌ An unexpected error occurred: {e}")

# import streamlit as st

# st.set_page_config(page_title="EvoAge | Reset Password")
# st.title("EvoAge • Reset Your Password")


# # Input fields
# new_password = st.text_input("New Password", type="password")
# confirm_password = st.text_input("Confirm Password", type="password")

# # Submit button
# if st.button("Submit"):
#     if not new_password or not confirm_password:
#         st.error("Both fields are required.")
#     elif new_password != confirm_password:
#         st.error("Passwords do not match!")
#     else:
#         # Here you can call backend API to save new password
#         st.success("Password successfully reset!")


# import streamlit as st
# import requests

# # Set your FastAPI backend URL (load from config if possible)
# BACKEND_URL = "http://127.0.0.1:8000"

# st.set_page_config(page_title="Reset Password")
# st.title("EvoAge • Reset Your Password")

# # --- THIS IS THE KEY ---
# # Read the 'token' from the URL's query parameters
# # try:
# #     token = st.query_params["token"]
# # except KeyError:
# #     st.error("Invalid or missing reset token. This link may be expired or incorrect.")
# #     st.page_link("1_Login.py", label="Go to Login")
# #     st.stop()
# # ------------------------

# st.write("Please enter your new password below.")

# with st.form("reset_password_form"):
#     new_password = st.text_input("New Password", type="password")
#     confirm_password = st.text_input("Confirm New Password", type="password")
#     submitted = st.form_submit_button("Reset Password")

# if submitted:
#     if not new_password or not confirm_password:
#         st.error("Please fill out both password fields.")
#     elif new_password != confirm_password:
#         st.error("Passwords do not match.")
#     else:
#         try:
#             # Call the /reset-password endpoint
#             response = requests.post(
#                 f"{BACKEND_URL}/auth/reset-password",
#                 json={"token": token, "new_password": new_password}
#             )
            
#             if response.status_code == 200:
#                 st.success("Password reset successfully! You can now log in.")
#                 st.balloons()
#                 # Clear the token from the URL
#                 st.query_params.clear()
            
#             elif response.status_code == 400:
#                 st.error("Invalid or expired token. Please request a new link.")
            
#             else:
#                 st.error(f"An error occurred: {response.json().get('detail', 'Unknown error')}")

#         except Exception as e:
#             st.error(f"An error occurred: {e}")

# st.page_link("1_Login.py", label="Back to Login")