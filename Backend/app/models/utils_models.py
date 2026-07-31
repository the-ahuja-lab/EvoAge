from pydantic import BaseModel


class OpenAIKeyRequest(BaseModel):
    api_key: str


class OpenAIKeyValidationResponse(BaseModel):
    is_valid: bool
