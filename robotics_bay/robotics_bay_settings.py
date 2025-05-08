from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class ApiSettings(BaseSettings):
    watch_folder: str = Field(..., env="WATCH_FOLDER")
    #PROCESSED_FOLDER: str = Field(..., env="PROCESSED_FOLDER")
    #CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")

    api_title: str = Field(..., env="API_TITLE")
    api_description: str = Field(..., env="API_DESCRIPTION")
    api_version: str = Field(..., env="API_VERSION")
    api_url: str = Field(..., env="API_URL")
    api_timeout: str = Field(..., env="API_TIMEOUT")

    prompt_rules: str = Field(..., env="PROMPT_RULES")
    prompt_response_field: str = Field(..., env="PROMPT_RESPONSE_FIELD") # "response"

    allow_origins: str = Field(..., env="ALLOW_ORIGINS")
    allow_credentials: bool = Field(..., env="ALLOW_CREDENTIALS")
    allow_methods: str = Field(..., env="ALLOW_METHODS")
    allow_headers: str = Field(..., env="ALLOW_HEADERS")

    model_config = SettingsConfigDict(
        env_file = Path(__file__).resolve().parent / ".env",
        case_sensitive = False,
        extra = "allow"
    )

api_settings = ApiSettings()