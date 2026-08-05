# Packages and functions for loading environment variables
import os
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
    URI: str = "bolt://localhost:3333"
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

# Root of the model artifacts. Defaults to where the Dockerfile places
# Backend/, so a container needs no path variables at all; a host checkout
# overrides it from .env, where the paths are absolute host paths.
# Override the whole tree at once with DGL_BASE_DIR.
DGL_BASE = os.getenv("DGL_BASE_DIR", "/app/backend/DGL-EvoKG")


class DGLConfig(BaseSettings):
    # Defaults resolve inside the container; .env overrides them on a host.
    NODE_MAPPINGS_PATH: str = f"{DGL_BASE}/Node_Mapping/node_id_mapping_EvoAge_121_12M.pkl"
    MODEL_PATH: str = f"{DGL_BASE}/Model/RESCAL_Evoage_121_12M_0"
    ENT_DICT_PATH: str = f"{DGL_BASE}/Model/entities_final_Ntype_updated.dict"
    REL_DICT_PATH: str = f"{DGL_BASE}/Model/relation_final.dict"
    DGLKE_INPUT_DIR: str = f"{DGL_BASE}/Input"
    DGLKE_DUMMY_HEAD_LIST: str = f"{DGL_BASE}/Dummy_Input/head.list"
    DGLKE_DUMMY_REL_LIST: str = f"{DGL_BASE}/Dummy_Input/rel.list"

    # Optional (recommended)
    DGLKE_DEVICE: int = 0
    DGLKE_SFUNC: str = "logsigmoid"

    class Config:
        env_prefix = ""   # read env vars exactly as named in .env
        # extra = "ignore"  # (optional) ignore unexpected vars

class HypothesisConfig(BaseSettings):
    # Same convention as DGLConfig: defaults resolve inside the container,
    # .env overrides them on a host checkout.
    INPUT_DIR_HYPOTHESIS: str = f"{DGL_BASE}/HypothesisTesting/InputHypothesis"
    API_BASE: str = "http://localhost:1026"
    DEFAULT_ENTITY_PROP: str = "id"
    CUTOFF_FILE_NAME: str = f"{DGL_BASE}/HypothesisTesting/Cutoff/relation_cutoff_summary.csv"
    HYPOTHESIS_ENT_DICT_PATH: str = f"{DGL_BASE}/HypothesisTesting/Model/entities_final_Ntype_updated.dict"
    HYPOTHESIS_TRIPLE_OUTPUT_DIR: str = f"{DGL_BASE}/HypothesisTesting/JSONResult"
    EDGE_TENSOR_PATH: str = f"{DGL_BASE}/HypothesisTesting/Model/EvoAge_121_12M_to_many_KG.pt"
    # Single-row CSV of RESCAL score percentiles (p0..p100) over ALL ground-truth
    # triples in the graph -- not per-relation like CUTOFF_FILE_NAME. Lives
    # alongside relation_cutoff_summary.csv in the same Cutoff/ dir.
    GLOBAL_SCORE_PERCENTILES_FILE: str = (
        f"{DGL_BASE}/HypothesisTesting/Cutoff/GLOBAL_GT_score_percentiles.csv"
    )
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

    # LLM backend switch for the hypothesis pipeline: "gemini" (default) or
    # "medgemma" -- routes every filter/agent/judge call to whichever is set.
    USE: str = "gemini"
    MEDGEMMA_BASE_URL: str = "http://localhost:30001/v1"
    MEDGEMMA_MODEL: str = "medgemma-27b-local"

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