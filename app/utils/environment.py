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

class FEConfig(BaseSettings):
    FRONTEND_URL: str = "http://localhost:8501"

    class Config:
        env_prefix = ""

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


# class AdminSettings(BaseSettings):
#     PASSWORD: str  # For the admin user/operations

#     class Config:
#         env_prefix = "ADMIN_"

class DGLConfig(BaseSettings):
    # Required (no defaults → must be in .env)
    NODE_MAPPINGS_PATH: str
    MODEL_PATH: str
    ENT_DICT_PATH: str
    REL_DICT_PATH: str
    DGLKE_INPUT_DIR: str
    DGLKE_DUMMY_HEAD_LIST: str
    DGLKE_DUMMY_REL_LIST: str

    # Optional (recommended)
    DGLKE_DEVICE: int = 0
    DGLKE_SFUNC: str = "logsigmoid"

    class Config:
        env_prefix = ""   # read env vars exactly as named in .env
        # extra = "ignore"  # (optional) ignore unexpected vars

class HypothesisConfig(BaseSettings):
    INPUT_DIR_HYPOTHESIS: str
    API_BASE: str = "http://localhost:1026"
    DEFAULT_ENTITY_PROP: str = "id"
    CUTOFF_FILE_NAME: str
    HYPOTHESIS_ENT_DICT_PATH: str

    class Config:
        env_prefix = ""   # read env vars exactly as named in .env

# class OpenAIConfig(BaseSettings):
#     OPENAI_API_KEY: str
#     OPENAI_MODEL: str = "gpt-4o-mini"

#     class Config:
#         env_prefix = ""   # read env vars exactly as named in .env
        
class GoogleGeminiConfig(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"

    class Config:
        env_prefix = ""   # read env vars exactly as named in .env

class CONFIG:
    UVICORN = UvicornConfig()
    NEO4J = Neo4jConfig()
    REDIS = RedisConfig()
    JWT = JWTSettings()
    MAIL = MailConfig()
    # ADMIN = AdminSettings()
    DGLCONFIG = DGLConfig()
    # OPENAI = OpenAIConfig()
    GEMINI = GoogleGeminiConfig()
    HYPOTHESIS = HypothesisConfig()
    FE = FEConfig()