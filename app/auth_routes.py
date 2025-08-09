from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import (
    RateLimiter,
)
from redis.asyncio import Redis

from app.crud.user import check_email_exists, create_user, get_user_by_username
from app.models.user import Token, UserCreate, UserPublic
from app.models.utils_models import OpenAIKeyRequest
from app.utils.email_utils import (
    send_new_user_notification,
    send_welcome_email,
)
from app.utils.environment import CONFIG
from app.utils.redis_utils import get_redis_connection
from app.utils.security import create_access_token, verify_password
from app.utils_routes import validate_openai_key

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Define common free email domains to disallow
DISALLOWED_FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "yahoo.com",
    "aol.com",
    "msn.com",
    "live.com",
    "mail.com",
    "gmx.com",
    "gmx.us",
    "icloud.com",
    "yandex.com",
    "zoho.com",
    "protonmail.com",
    # Add more free email providers as needed
}


@router.post(
    "/signup",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)
async def signup_new_user(user: UserCreate, db: Redis = Depends(get_redis_connection)):
    """Registers a new user after validating email domain and existence."""
    # 0. Validate OpenAI API Key
    key_validation_response = await validate_openai_key(
        OpenAIKeyRequest(api_key=user.OPENAI_API_KEY)
    )
    if not key_validation_response.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OpenAI API Key.",
        )

    # 1. Check if email domain is from a disallowed free provider
    try:
        email_domain = user.email.split("@")[1].lower()
        print(f"Email domain extracted: {email_domain}")
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )

    if email_domain in DISALLOWED_FREE_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signups using common free email providers are not allowed. Please use an organizational email.",
        )

    # 2. Check if username already exists
    db_user = await get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # 3. Check if email already exists
    email_exists = await check_email_exists(db, user.email)
    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 4. Create the user
    created_user_db = await create_user(db=db, user=user)
    # Convert DB model to Pydantic model for response and email
    created_user_public = UserPublic.model_validate(created_user_db)

    # 5. Send notification email to admin
    await send_new_user_notification(created_user_public)

    # 6. Send welcome email to the new user
    await send_welcome_email(email_to=created_user_public.email)

    # Return UserPublic model which doesn't include the password
    return created_user_public


@router.post(
    "/login",
    response_model=Token,
    dependencies=[
        Depends(RateLimiter(times=10, minutes=1))
    ],  # Changed to 10 per minute
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Redis = Depends(get_redis_connection),
):
    """Authenticates a user and returns a JWT access token."""
    user = await get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=CONFIG.JWT.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
