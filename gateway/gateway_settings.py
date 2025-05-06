from pydantic_settings import BaseSettings
from pydantic import Field

class ExtractorSettings(BaseSettings):
    CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

extractor_settings = ExtractorSettings()