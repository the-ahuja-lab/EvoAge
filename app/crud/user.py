import logging

from pydantic import EmailStr
from redis.asyncio import Redis

from app.models.user import UserCreate, UserInDB
from app.utils.security import get_password_hash

# Key for the Redis set storing all registered emails
EMAIL_SET_KEY = "registered_emails"
logger = logging.getLogger(__name__)


async def get_user_by_username(db: Redis, username: str) -> UserInDB | None:
    """Fetches a user from Redis by username."""
    user_data = await db.hgetall(f"user:{username}")
    if not user_data:
        return None
    # Ensure id is set correctly, using username as the key identifier
    return UserInDB(id=username, **user_data)


async def check_email_exists(db: Redis, email: EmailStr) -> bool:
    """Checks if an email already exists in the registered emails set."""
    return await db.sismember(EMAIL_SET_KEY, email)


async def create_user(db: Redis, user: UserCreate) -> UserInDB:
    """Creates a new user in Redis and adds email to the tracking set."""
    hashed_password = get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "organization": user.organization,
        "OPENAI_API_KEY": user.OPENAI_API_KEY,
        "hashed_password": hashed_password,
    }
    # Use hset to store the hash, as hmset is deprecated in newer redis-py versions
    await db.hset(f"user:{user.username}", mapping=user_data)
    # Add the email to the set for quick existence checks
    await db.sadd(EMAIL_SET_KEY, user.email)
    logger.info(f"User {user.username} created successfully.")
    # Return the created user data, ensuring id is set
    return UserInDB(id=user.username, **user_data)


async def update_user_query_limit_data(
    db: Redis, username: str, query_limits: int, last_query_reset: str
) -> bool:
    """Updates the query limits and last reset time for a user in Redis."""
    user_key = f"user:{username}"
    if not await db.exists(user_key):
        logger.warning(
            f"Attempted to update query limit for non-existent user: {username}"
        )
        return False  # User not found
    await db.hset(
        user_key,
        mapping={"query_limits": query_limits, "last_query_reset": last_query_reset},
    )
    logger.info(f"Query limit data updated for user: {username}.")
    return True


async def update_user_openai_key(db: Redis, username: str, openai_api_key: str) -> bool:
    """Updates the OpenAI API key for a user in Redis."""
    user_key = f"user:{username}"
    if not await db.exists(user_key):
        logger.warning(
            f"Attempted to update OpenAI key for non-existent user: {username}"
        )
        return False  # User not found
    await db.hset(user_key, mapping={"OPENAI_API_KEY": openai_api_key})
    logger.info(f"OpenAI API key updated for user: {username}.")
    return True
