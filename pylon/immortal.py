from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Set
from pylon import output_messages
import ast

class Settings(BaseSettings):
    # AI Configuration
    AI_MODEL: str = Field(..., env="AI_MODEL")
    AI_MODEL_API: str = Field(..., env="AI_MODEL_API")
    AI_MODEL_EMBEDDINGS: str = Field(..., env="AI_MODEL_EMBEDDINGS")
    AI_MODEL_GENERATE: str = Field(..., env="AI_MODEL_GENERATE")
    AI_MODEL_SCORE: str = Field(..., env="AI_MODEL_SCORE")
    AI_MODEL_HNSW: str = Field(..., env="AI_MODEL_HNSW")
    AI_BASE_URL: str = Field(..., env="AI_BASE_URL")
    
    # Vector Database Configuration
    QDRANT_HOST: str = Field(..., env="QDRANT_HOST")
    QDRANT_PORT: int = Field(..., env="QDRANT_PORT")
    QDRANT_TIMEOUT: int = Field(..., env="QDRANT_TIMEOUT")
    COLLECTION_NAME: str = Field(..., env="COLLECTION_NAME")
    VECTOR_DIMENSION: int = Field(..., env="VECTOR_DIMENSION")
    
    # Redis Configuration
    REDIS_HOST: str = Field(..., env="REDIS_HOST")
    REDIS_PORT: int = Field(..., env="REDIS_PORT")
    REDIS_DB: int = Field(..., env="REDIS_DB")
    REDIS_QUEUE: str = Field(..., env="REDIS_QUEUE") 
    REDIS_QUEUE_FILES: str = Field(..., env="REDIS_QUEUE_FILES")
    REDIS_QUEUE_DOCUMENTS: str = Field(..., env="REDIS_QUEUE_DOCUMENTS")
    REDIS_QUEUE_PAGES: str = Field(..., env="REDIS_QUEUE_PAGES")
    REDIS_QUEUE_SCOUT: str = Field(..., env="REDIS_QUEUE_SCOUT")
    REDIS_QUEUE_SPIED: str = Field(..., env="REDIS_QUEUE_SPIED")
    
    # API Configuration
    API_URL: str = Field(..., env="API_URL")
    INGEST_URL: str = Field(..., env="INGEST_URL")
    
    # Retry Configuration
    MAX_RETRIES: int = Field(..., env="MAX_RETRIES")
    RETRY_DELAY: int = Field(..., env="RETRY_DELAY")
    
    # Timeout Configuration
    REDIS_TIMEOUT: int = Field(..., env="REDIS_TIMEOUT")
    API_TIMEOUT: int = Field(..., env="API_TIMEOUT")
    
    # Watcher Configuration
    WATCH_DIR: str = Field(..., env="WATCH_DIR")
    CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")
    SUPPORTED_EXTENSIONS: str = Field(..., env="SUPPORTED_EXTENSIONS")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(..., env="LOG_LEVEL")
    LOG_FORMAT: str = Field(..., env="LOG_FORMAT")
    
    NEURON_LANGUAGE_MODEL: str = Field(..., env="NEURON_LANGUAGE_MODEL")
    MAX_CHUNKS: int = Field(..., env="MAX_CHUNKS")

    @property
    def supported_extensions(self) -> Set[str]:
        """Get the supported extensions as a set."""
        try:
            return ast.literal_eval(self.SUPPORTED_EXTENSIONS.strip())
        except (ValueError, SyntaxError) as e:
            raise ValueError(f"{output_messages.UNSUPPORTED_EXTENSIONS}: {self.SUPPORTED_EXTENSIONS}. {output_messages.EXPECTED_EXTENSIONS}") from e
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment variables

settings = Settings()