# auth_utils.py
import datetime
import json
import logging
import os
import requests
import dotenv
import streamlit as st

dotenv.load_dotenv()
logger = logging.getLogger("AuthUtils")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def get_user_details(token: str):
    url = f"{API_BASE_URL}/users/me"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("Failed to get user details: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error fetching user details: %s", e)
        return None


def login_user(username: str, password: str):
    url = f"{API_BASE_URL}/auth/login"
    payload = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    logger.warning(f"URL: {url}\n Payload: {payload}")

    try:
        resp = requests.post(url, data=payload, headers=headers)

        # If backend returns 401/400, this raises
        resp.raise_for_status()

        data = resp.json()

        # Token missing — treat as error
        if "access_token" not in data:
            return False, {"error": "No access token returned by server."}

        return True, data

    except requests.exceptions.HTTPError as e:
        """ Handle backend errors like:
        {
          "detail": "Incorrect username or password"
        }
        """
        if e.response is not None:
            try:
                backend = e.response.json()
                detail = backend.get("detail")
                if detail:
                    return False, {"error": detail}   # clean output
            except Exception:
                pass

            # fallback if JSON missing
            return False, {"error": f"HTTP {e.response.status_code}: {e.response.reason}"}

        # no response object
        return False, {"error": "Unable to reach authentication server."}

    except Exception as e:
        logger.error("Unexpected login error: %s", e)
        return False, {"error": "Unexpected error during login."}


# def login_user(username: str, password: str):
#     url = f"{API_BASE_URL}/auth/login"
#     payload = {"username": username, "password": password}
#     headers = {"Content-Type": "application/x-www-form-urlencoded"}
#     logger.warning(f"URL: {url}\n Payload: {payload}")
#     try:
#         resp = requests.post(url, data=payload, headers=headers)
#         resp.raise_for_status()
#         data = resp.json()
#         if "access_token" not in data:
#             return False, {"error": "Login succeeded but no token returned."}
#         return True, data
#     except requests.exceptions.RequestException as e:
#         logger.error("Login failed: %s", e)
#         error_msg = ""
#         if e.response is not None:
#             try:
#                 detail = e.response.json().get("detail", "")
#                 error_msg = f"Login failed: {detail or e}"
#             except Exception:
#                 error_msg = f"Login failed: {e.response.status_code} - {e.response.reason}"
#         else:
#             error_msg = f"Login failed: {e}"
#         return False, {"error": error_msg}
#     except Exception as e:
#         logger.error("Unexpected login error: %s", e)
#         return False, {"error": f"Unexpected error: {e}"}


def register_user(
    username, email, password, first_name, last_name, organization, openai_api_key
):
    url = f"{API_BASE_URL}/auth/signup"
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "organization": organization,
        "OPENAI_API_KEY": openai_api_key,
    }
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        return True, resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("Registration failed: %s", e)
        err = {}
        if e.response is not None:
            try:
                detail = e.response.json().get("detail", str(e))
                err["error"] = f"Registration failed: {detail}"
            except Exception:
                err["error"] = f"Registration failed: {e.response.status_code} - {e.response.reason}"
        else:
            err["error"] = f"Registration failed: {e}"
        return False, err
    except Exception as e:
        logger.error("Unexpected registration error: %s", e)
        return False, {"error": f"Unexpected error: {e}"}

def forgot_password(email: str):
    """
    Sends a request to the /auth/forgotpassword endpoint.
    """
    url = f"{API_BASE_URL}/auth/forgot-password"
    payload = {"email": email}
    logger.info(f"Requesting password reset for email: {email}")
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        # Successfully sent request (e.g., 200 OK)
        # err["error"] = f"hihiPassword reset request failed: {url}"
        return True, resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("Forgot password request failed: %s", e)
        err = {}
        if e.response is not None:
            try:
                # Try to get specific error detail from backend
                detail = e.response.json().get("detail", str(e))
                err["error"] = f"Password reset request failed: {detail}"
            except Exception:
                # Fallback if response isn't JSON
                err["error"] = f"Password reset request failed: {e.response.status_code} - {e.response.reason}"
        else:
            # Network or other connection error
            err["error"] = f"Password reset request failed: {e}"
        return False, err
    except Exception as e:
        logger.error("Unexpected error in forgot password: %s", e)
        return False, {"error": f"Unexpected error: {e}"}
    
def logout():
    st.session_state.update({
        "logged_in": False,
        "user_token": None,
        "username": None,
        "openai_api_key": None,
        "current_page": "intro",
    })
    st.rerun()
    logger.info("User logged out.")
