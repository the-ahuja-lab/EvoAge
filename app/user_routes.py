from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import (
    RateLimiter,  # Corrected import path if necessary, or ensure it's available
)
from pydantic import EmailStr
from redis.asyncio import Redis

from app.crud.user import (
    get_user_by_username,
    update_user_openai_key,
    update_user_query_limit_data,
)
from app.models.user import (
    AdminUserQueryLimitUpdate,
    UserOpenAIKeyUpdate,
    UserPublic,
    UserQueryLimitUpdate,
)
from app.utils.email_utils import send_welcome_email
from app.utils.environment import CONFIG
from app.utils.redis_utils import get_redis_connection
from app.utils.security import (
    get_current_active_user,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserPublic,
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)  # Changed to 10 per minute
async def read_users_me(
    current_user: UserPublic = Depends(get_current_active_user),
    db: Redis = Depends(get_redis_connection),
):
    """
    Fetch the current logged-in user's details.
    """
    user_in_db = await get_user_by_username(db, username=current_user.username)
    if user_in_db is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic.model_validate(user_in_db)


@router.put(
    "/me/query_limits",
    response_model=UserPublic,
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)  # Changed to 10 per minute
async def update_current_user_query_limits(
    query_limit_data: UserQueryLimitUpdate,
    current_user: UserPublic = Depends(get_current_active_user),
    db: Redis = Depends(get_redis_connection),
):
    """
    Update the query limits for the current logged-in user.
    """
    success = await update_user_query_limit_data(
        db,
        username=current_user.username,
        query_limits=query_limit_data.query_limits,
        last_query_reset=query_limit_data.last_query_reset.isoformat(),
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or update failed",
        )

    updated_user = await get_user_by_username(db, username=current_user.username)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated user details",
        )
    return UserPublic.model_validate(updated_user)


@router.put(
    "/{username}/query_limit_admin",
    response_model=UserPublic,
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)  # Changed to 10 per minute
async def admin_update_user_query_limit(
    username: str,
    update_data: AdminUserQueryLimitUpdate,
    db: Redis = Depends(get_redis_connection),
):
    """
    Admin endpoint to update a user's query limit.
    Requires admin authentication.
    """
    # Verify admin password
    # Ensure ADMIN_PASSWORD is set in your environment configuration
    if not CONFIG.ADMIN.PASSWORD or not verify_password(
        update_data.admin_password, get_password_hash(CONFIG.ADMIN.PASSWORD)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect admin password or not authorized",
        )

    user_to_update = await get_user_by_username(db, username=username)
    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {username} not found"
        )

    success = await update_user_query_limit_data(
        db,
        username=username,
        query_limits=update_data.new_query_limit,
        last_query_reset=datetime.utcnow().isoformat(),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user query limits",
        )

    updated_user = await get_user_by_username(db, username=username)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated user details post-update",
        )
    return UserPublic.model_validate(updated_user)


@router.post(
    "/send_welcome_email", dependencies=[Depends(RateLimiter(times=10, minutes=1))]
)  # Changed to 10 per minute
async def send_welcome_email_route(
    email_to: EmailStr,
):
    """
    Sends a welcome email to the specified email address.
    """
    # Optional: Add admin role check here if only admins should send welcome emails
    # For example, if current_user.role != "admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    try:
        await send_welcome_email(email_to)
        return {"message": f"Welcome email successfully sent to {email_to}"}
    except HTTPException as e:
        # Re-raise HTTPExceptions from send_welcome_email
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.put(
    "/me/openai_api_key",
    response_model=UserPublic,
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)
async def update_openai_api_key(
    openai_key_data: UserOpenAIKeyUpdate,
    current_user: UserPublic = Depends(get_current_active_user),
    db: Redis = Depends(get_redis_connection),
):
    """
    Update the OpenAI API key for the current logged-in user.
    """
    success = await update_user_openai_key(
        db,
        username=current_user.username,
        openai_api_key=openai_key_data.OPENAI_API_KEY,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or update failed",
        )

    updated_user = await get_user_by_username(db, username=current_user.username)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated user details",
        )
    return UserPublic.model_validate(updated_user)
