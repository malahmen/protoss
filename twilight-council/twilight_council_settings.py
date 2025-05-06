from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Set
from pylon import output_messages
import ast

class ChunkerSettings(BaseSettings):
    CHECK_INTERVAL: int = Field(..., env="CHECK_INTERVAL")
    SUPPORTED_EXTENSIONS: str = Field(..., env="SUPPORTED_EXTENSIONS")
    
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
        extra = "allow"  # Allow extra fields from environment variables

chunker_settings = ChunkerSettings()