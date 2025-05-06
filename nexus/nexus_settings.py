from pydantic_settings import BaseSettings
from pydantic import Field

class EmbedderSettings(BaseSettings):
    CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")
    REDIS_CONTENT_FIELD: str = Field(..., env="REDIS_CONTENT_FIELD")
    REDIS_CONTENT_TYPE: str = Field(..., env="REDIS_CONTENT_TYPE")
    REDIS_CONTENT_MIME: str = Field(..., env="REDIS_CONTENT_MIME")
    
    #LOG_LEVEL: str = Field(..., env="LOG_LEVEL")
    #LOG_FORMAT: str = Field(..., env="LOG_FORMAT")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment variables

embedder_settings = EmbedderSettings()