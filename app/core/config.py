import logging
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    app_name: str = "EPUB to PDF Converter"
    debug: bool = False

    # File upload settings
    max_upload_size_mb: int = 50
    allowed_mime_types: list[str] = ["application/epub+zip", "application/zip"]
    allowed_extensions: list[str] = [".epub"]

    # Server settings
    port: int = 7860

    # Logging
    log_level: str = "INFO"


settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
