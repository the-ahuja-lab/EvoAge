import openai
from fastapi import APIRouter, Body, HTTPException

from app.models.utils_models import OpenAIKeyRequest, OpenAIKeyValidationResponse

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post("/validate_openai_key", response_model=OpenAIKeyValidationResponse)
async def validate_openai_key(request_body: OpenAIKeyRequest = Body(...)):
    """
    Validates an OpenAI API key by attempting a simple API call.
    """
    try:
        client = openai.OpenAI(api_key=request_body.api_key)
        # Attempt a lightweight API call, e.g., listing models
        client.models.list()
        return OpenAIKeyValidationResponse(is_valid=True)
    except openai.AuthenticationError:
        return OpenAIKeyValidationResponse(is_valid=False)
    except Exception:
        # Catch any other exceptions during the API call
        # You might want to log the error e for debugging
        # For security, don't return the specific error message to the client
        raise HTTPException(
            status_code=500, detail="An error occurred while validating the key."
        )
