from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class EmbedderSettings(BaseSettings):
    check_interval: int = Field(..., env="CHECK_INTERVAL")

    model_config = SettingsConfigDict(
        env_file = Path(__file__).resolve().parent / ".env",
        case_sensitive = False,
        extra = "allow"
    )

embedder_settings = EmbedderSettings()