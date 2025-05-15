# pylon/immortal.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class ApplicationSettings(BaseSettings):
    # Mothership
    model_name: str = Field(..., env="MODEL_NAME")
    model_api: str = Field(..., env="MODEL_API")
    model_health: str = Field(..., env="MODEL_HEALTH")
    model_embeddings: str = Field(..., env="MODEL_EMBEDDINGS")
    embed_field: str = Field(..., env="EMBED_FIELD")
    model_generate: str = Field(..., env="MODEL_GENERATE")
    max_chunks: int = Field(..., env="MAX_CHUNKS")
    model_score: float = Field(..., env="MODEL_SCORE")
    model_hnsw: int = Field(..., env="MODEL_HNSW")
    base_url: str = Field(..., env="BASE_URL")

    # Qdrant
    db_version: str = Field(..., env="DB_VERSION")
    db_host: str = Field(..., env="DB_HOST")
    db_port: int = Field(..., env="DB_PORT")
    db_volume: str = Field(..., env="DB_VOLUME")
    db_timeout: int = Field(..., env="DB_TIMEOUT")
    collection_name: str = Field(..., env="COLLECTION_NAME")
    vector_dimension: int = Field(..., env="VECTOR_DIMENSION")
    index_field: str = Field(..., env="INDEX_FIELD")

    # Redis
    redis_host: str = Field(..., env="REDIS_HOST")
    redis_port: int = Field(..., env="REDIS_PORT")
    redis_db: int = Field(..., env="REDIS_DB")
    redis_timeout: int = Field(..., env="REDIS_TIMEOUT")
    redis_retry: bool = Field(..., env="REDIS_RETRY")
    redis_retry_delay: int = Field(..., env="REDIS_RETRY_DELAY")
    redis_health_check_interval: int = Field(..., env="REDIS_HEALTH_CHECK_INTERVAL")
    redis_queue: str = Field(..., env="REDIS_QUEUE")
    redis_queue_files: str = Field(..., env="REDIS_QUEUE_FILES")
    redis_queue_documents: str = Field(..., env="REDIS_QUEUE_DOCUMENTS")
    redis_queue_pages: str = Field(..., env="REDIS_QUEUE_PAGES")
    redis_queue_scout: str = Field(..., env="REDIS_QUEUE_SCOUT")
    redis_queue_spied: str = Field(..., env="REDIS_QUEUE_SPIED")
    redis_content_field: str = Field(..., env="REDIS_CONTENT_FIELD")
    redis_content_type: str = Field(..., env="REDIS_CONTENT_TYPE")
    redis_content_mime: str = Field(..., env="REDIS_CONTENT_MIME")

    # Oracle
    node_image: str = Field(..., env="NODE_IMAGE")
    nginx_image: str = Field(..., env="NGINX_IMAGE")
    oracle_port_in: int = Field(..., env="ORACLE_PORT_IN")
    oracle_port_out: int = Field(..., env="ORACLE_PORT_OUT")

    # General
    encoding: str = Field(..., env="ENCODING")
    async_timeout: int = Field(..., env="ASYNC_TIMEOUT")

    model_config = SettingsConfigDict(
        env_file = Path(__file__).resolve().parents[1] / ".env",
        case_sensitive=False,
        extra="allow"
    )

# self initialize
settings = ApplicationSettings()
