from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import Set
import ast
from pylon import output_messages


class WatcherSettings(BaseSettings):
    watch_folder: str = Field(..., env="WATCH_FOLDER")
    processed_folder: str = Field(..., env="PROCESSED_FOLDER")
    check_interval: int = Field(..., env="CHECK_INTERVAL")
    supported_extensions: str = Field(..., env="SUPPORTED_EXTENSIONS")
    
    #LOG_LEVEL: str = Field(..., env="LOG_LEVEL")
    #LOG_FORMAT: str = Field(..., env="LOG_FORMAT")

    @property
    def supported_extensions(self) -> Set[str]:
        """Get the supported extensions as a set."""
        try:
            return ast.literal_eval(self.supported_extensions.strip())
        except (ValueError, SyntaxError) as e:
            raise ValueError(f"{output_messages.UNSUPPORTED_EXTENSIONS}: {self.supported_extensions}. {output_messages.EXPECTED_EXTENSIONS}") from e
    
    model_config = SettingsConfigDict(
        env_file = Path(__file__).resolve().parent / ".env",
        case_sensitive = False,
        extra = "allow"
    )

watcher_settings = WatcherSettings()