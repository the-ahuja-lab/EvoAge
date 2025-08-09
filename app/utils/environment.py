# Packages and functions for loading environment variables
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from pydantic import EmailStr
from pydantic_settings import BaseSettings

# Load environment from disk first, then apply any defaults
load_dotenv(find_dotenv(".env"))


class UvicornConfig(BaseSettings):
    PORT: int = 1026
    HOST: str = "0.0.0.0"

    WORKERS: int = 4
    RELOAD_ON_CHANGE: bool = False

    class Config:
        env_prefix = "UVICORN_"


class Neo4jConfig(BaseSettings):
    URI: str = "bolt://localhost:7687"
    USERNAME: str
    PASSWORD: str

    class Config:
        env_prefix = "NEO4J_"


class RedisConfig(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 6379
    DB: int = 0

    USERNAME: Optional[str] = None
    PASSWORD: Optional[str] = None

    class Config:
        env_prefix = "REDIS_"


class JWTSettings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_prefix = "JWT_"


class MailConfig(BaseSettings):
    # Email settings
    USERNAME: Optional[str] = None
    PASSWORD: Optional[str] = None
    FROM: Optional[EmailStr] = None
    PORT: int = 587
    SERVER: Optional[str] = None
    FROM_NAME: Optional[str] = "Evo-KG Admin"
    STARTTLS: bool = True
    SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    ADMIN_EMAIL: Optional[EmailStr] = None  # Admin email to receive notifications

    class Config:
        env_prefix = "MAIL_"


class AdminSettings(BaseSettings):
    PASSWORD: str  # For the admin user/operations

    class Config:
        env_prefix = "ADMIN_"


class CONFIG:
    UVICORN = UvicornConfig()
    NEO4J = Neo4jConfig()
    REDIS = RedisConfig()
    JWT = JWTSettings()
    MAIL = MailConfig()
    ADMIN = AdminSettings()
