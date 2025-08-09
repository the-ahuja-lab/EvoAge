from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.utils.database import get_redis_connection

router = APIRouter()


@router.get(
    "/hello_world",
    tags=["Testing"],
    description="A simple test endpoint that returns 'Hello, World!'",
    summary="Hello World Test Endpoint",
    response_description="Returns a simple greeting message",
    operation_id="hello_world",
)
async def hello_world():
    return {"message": "Hello, World!"}


@router.get(
    "/test_redis",
    tags=["Testing"],
    summary="Test Redis Connection",
    description="Pings the Redis server to check the connection.",
    response_description="Returns 'PONG' if successful, otherwise raises an error.",
    operation_id="test_redis_connection",
)
async def test_redis(redis_client: Redis = Depends(get_redis_connection)):
    try:
        pong = await redis_client.ping()
        return {"status": "success", "response": pong}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        # Note: With connection pooling, explicitly closing the client
        # after each request might not be necessary or even desirable.
        # The pool manages the connections.
        # await redis_client.close() # Usually not needed here
        pass
