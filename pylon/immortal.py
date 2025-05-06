from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # AI Configuration
    AI_MODEL: str = Field(..., env="MODEL_NAME")
    AI_MODEL_API: str = Field(..., env="MODEL_API")
    AI_MODEL_HEALTH: str = Field(..., env="MODEL_HEALTH")
    AI_MODEL_EMBEDDINGS: str = Field(..., env="MODEL_EMBEDDINGS")
    AI_MODEL_GENERATE: str = Field(..., env="MODEL_GENERATE")
    AI_MODEL_MAX_CHUNKS: str = Field(..., env="MAX_CHUNKS")
    AI_MODEL_SCORE: str = Field(..., env="MODEL_SCORE")
    AI_MODEL_HNSW: str = Field(..., env="AI_MODEL_HNSW")
    AI_BASE_URL: str = Field(..., env="BASE_URL")
    AI_EMBED_FIELD: str = Field(..., env="EMBED_FIELD")

    # Vector Database Configuration
    QDRANT_HOST: str = Field(..., env="DB_HOST")
    QDRANT_PORT: int = Field(..., env="DB_PORT")
    QDRANT_TIMEOUT: int = Field(..., env="DB_TIMEOUT")
    COLLECTION_NAME: str = Field(..., env="COLLECTION_NAME")
    VECTOR_DIMENSION: int = Field(..., env="VECTOR_DIMENSION")
    QDRANT_INDEX_FIELD: str = Field(..., env="INDEX_FIELD") # text

    # Redis Configuration
    REDIS_HOST: str = Field(..., env="REDIS_HOST")
    REDIS_PORT: int = Field(..., env="REDIS_PORT")
    REDIS_DB: int = Field(..., env="REDIS_DB")
    REDIS_RETRY: bool = Field(..., env="REDIS_RETRY")
    REDIS_HEALTH_CHECK_INTERVAL: int = Field(..., env="REDIS_HEALTH_CHECK_INTERVAL")
    REDIS_QUEUE: str = Field(..., env="REDIS_QUEUE") 
    REDIS_QUEUE_FILES: str = Field(..., env="REDIS_QUEUE_FILES")
    REDIS_QUEUE_DOCUMENTS: str = Field(..., env="REDIS_QUEUE_DOCUMENTS")
    REDIS_QUEUE_PAGES: str = Field(..., env="REDIS_QUEUE_PAGES")
    REDIS_QUEUE_SCOUT: str = Field(..., env="REDIS_QUEUE_SCOUT")
    REDIS_QUEUE_SPIED: str = Field(..., env="REDIS_QUEUE_SPIED")
    REDIS_CONTENT_FIELD: str = Field(..., env="REDIS_CONTENT_FIELD")
    REDIS_CONTENT_TYPE: str = Field(..., env="REDIS_CONTENT_TYPE")
    REDIS_CONTENT_MIME: str = Field(..., env="REDIS_CONTENT_MIME")

    # General
    ENCODING: str = Field(..., env="ENCODING")
    CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")
    MAX_CHUNKS: int = Field(..., env="MAX_CHUNKS")

    # Timeout Configuration
    REDIS_TIMEOUT: int = Field(..., env="REDIS_TIMEOUT")
    #API_TIMEOUT: int = Field(..., env="API_TIMEOUT") # in api_settings
    ASYNC_TIMEOUT: int = Field(..., env="ASYNC_TIMEOUT")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment variables

# self initialize
settings = Settings()