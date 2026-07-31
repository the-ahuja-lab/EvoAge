import dotenv
import logging
import os
import requests

dotenv.load_dotenv()
logger = logging.getLogger(__name__)
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def update_user_query_limits(token: str, query_limits: int, last_query_reset: str):
    """Updates user query limits on the FastAPI backend."""
    url = f"{API_BASE_URL}/users/me/query_limits"  # Assuming this endpoint exists
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"query_limits": query_limits, "last_query_reset": last_query_reset}
    try:
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Query limits updated successfully.")
        return True, response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update query limits: {e}")
        error_message = "Failed to update query limits."
        if e.response is not None:
            try:
                error_detail = e.response.json().get("detail", str(e))
                error_message += f" Server said: {error_detail}"
            except ValueError:  # Handles cases where e.response.json() fails
                error_message += f" Server response: {e.response.text}"
        # st.error(error_message) # Removed: Caller will handle UI feedback
        return False, {"error": error_message}
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating query limits: {e}")
        # st.error("An unexpected error occurred while updating query limits.") # Removed: Caller will handle UI feedback
        return False, {
            "error": "An unexpected error occurred while updating query limits."
        }
    
def update_user_openai_key_api(token: str, new_api_key: str):
    """Updates the user's OpenAI API key on the FastAPI backend after validating it using the backend endpoint."""
    # Step 1: Validate the new API key using the backend endpoint
    validation_url = f"{API_BASE_URL}/utils/validate_openai_key"
    try:
        validation_response = requests.post(
            validation_url, json={"api_key": new_api_key}
        )
        validation_response.raise_for_status()  # Raise an exception for bad status codes
        validation_data = validation_response.json()
        if not validation_data.get("is_valid"):
            logger.error("Invalid OpenAI API key according to backend validation.")
            return (
                False,
                "The provided OpenAI API key is invalid. Please check the key and try again.",
            )
        logger.info("OpenAI API key validated successfully by backend.")
    except requests.exceptions.RequestException as e:
        logger.error(f"API key validation request failed: {e}")
        error_message = "Failed to validate OpenAI API key."
        if e.response is not None:
            try:
                error_detail = e.response.json().get("detail", str(e))
                error_message += f" Server said: {error_detail}"
            except ValueError:
                error_message += f" Server response: {e.response.text}"
        return False, error_message
    except Exception as e:  # Catch any other unexpected errors during validation call
        logger.error(f"An unexpected error occurred during API key validation: {e}")
        return False, "An unexpected error occurred while validating the API key."

    # Step 2: If validated, proceed to update the key
    update_url = f"{API_BASE_URL}/users/me/openai_api_key"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"OPENAI_API_KEY": new_api_key}
    try:
        response = requests.put(update_url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("OpenAI API key updated successfully via API.")
        return (
            True,
            "OpenAI API key updated successfully. Please log out and log back in for the changes to take effect.",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update OpenAI API key via API: {e}")
        error_message = "Failed to update OpenAI API key."
        if e.response is not None:
            try:
                error_detail = e.response.json().get("detail", str(e))
                error_message += f" Server said: {error_detail}"
            except ValueError:  # If response is not JSON
                error_message += f" Server response: {e.response.text}"
        return False, error_message
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while updating OpenAI API key via API: {e}"
        )
        return False, f"An unexpected error occurred: {str(e)}"