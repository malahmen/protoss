from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Set
import ast
from pylon import output_messages

class ApiSettings(BaseSettings):
    WATCH_FOLDER: str = Field(..., env="WATCH_FOLDER")
    #PROCESSED_FOLDER: str = Field(..., env="PROCESSED_FOLDER")
    #CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")
    SUPPORTED_EXTENSIONS: str = Field(..., env="SUPPORTED_EXTENSIONS")

    API_TITLE: str = Field(..., env="API_TITLE")
    API_DESCRIPTION: str = Field(..., env="API_DESCRIPTION")
    API_VERSION: str = Field(..., env="API_VERSION")
    API_URL: str = Field(..., env="API_URL")
    API_TIMEOUT: str = Field(..., env="API_TIMEOUT")


    PROMPT_RULES: str = Field(..., env="PROMPT_RULES")
    PROMPT_RESPONSE_FIELD: str = Field(..., env="PROMPT_RESPONSE_FIELD") # "response"

    ALLOW_ORIGINS: str = Field(..., env="ALLOW_ORIGINS")
    ALLOW_CREDENTIALS: bool = Field(..., env="ALLOW_CREDENTIALS")
    ALLOW_METHODS: str = Field(..., env="ALLOW_METHODS")
    ALLOW_HEADERS: str = Field(..., env="ALLOW_HEADERS")
    
    LOG_LEVEL: str = Field(..., env="LOG_LEVEL")
    LOG_FORMAT: str = Field(..., env="LOG_FORMAT")

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
        extra = "allow" # Allow extra fields from environment variables

api_settings = ApiSettings()