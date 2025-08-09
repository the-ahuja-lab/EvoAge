# app/database.py

import redis.asyncio as redis
from neo4j import GraphDatabase

from app.utils.environment import CONFIG


class Neo4jConnection:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()

    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]


# Global instance (Singleton) for the Neo4j connection
neo4j_connection = Neo4jConnection(
    uri=CONFIG.NEO4J.URI,
    user=CONFIG.NEO4J.USERNAME,
    password=CONFIG.NEO4J.PASSWORD,
)


# Dependency injection function for FastAPI routes
def get_neo4j_connection():
    return neo4j_connection


# --- Redis Connection ---
# This class manages the Redis connection pool and provides a method to get a connection.
# It also includes a method to close the connection pool when needed.
class RedisConnection:
    def __init__(
        self, host: str, port: int, db: int, username: str = None, password: str = None
    ):
        self.host = host
        self.port = port
        self.db = db
        self.username = username
        self.password = password
        self.pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            username=self.username,
            password=self.password,
            decode_responses=True,  # Decode responses to strings
        )

    async def get_connection(self):
        """Get an async Redis connection from the pool."""
        return redis.Redis(connection_pool=self.pool)

    async def close(self):
        """Close the Redis connection pool."""
        if self.pool:
            await self.pool.disconnect()


# Global instance (Singleton) for the Redis connection
redis_connection = RedisConnection(
    host=CONFIG.REDIS.HOST,
    port=CONFIG.REDIS.PORT,
    db=CONFIG.REDIS.DB,
    username=CONFIG.REDIS.USERNAME,
    password=CONFIG.REDIS.PASSWORD,
)


# Dependency injection function for FastAPI routes
async def get_redis_connection():
    """Dependency to get an async Redis connection."""
    return await redis_connection.get_connection()


# See FastAPI documentation for lifespan events
