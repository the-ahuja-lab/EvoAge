from datetime import datetime  # Added for query limit reset logic

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    organization: str = Field(..., min_length=1, max_length=100)
    OPENAI_API_KEY: str = Field(..., min_length=10)
    query_limits: int = Field(default=5)
    last_query_reset: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserInDBBase(UserBase):
    id: str  # Using username as ID in Redis for simplicity, or generate a UUID

    class Config:
        from_attributes = True  # Replaces orm_mode = True in Pydantic v2


class UserInDB(UserInDBBase):
    hashed_password: str


class UserPublic(UserInDBBase):
    # Model for data returned to the client (omits password)
    pass


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserQueryLimitUpdate(BaseModel):
    query_limits: int
    last_query_reset: datetime


class UserOpenAIKeyUpdate(BaseModel):
    OPENAI_API_KEY: str = Field(..., min_length=10)


class AdminUserQueryLimitUpdate(BaseModel):
    admin_password: str
    new_query_limit: int
