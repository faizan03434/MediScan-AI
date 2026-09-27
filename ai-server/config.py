from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "MediScan AI Server"
    app_version: str = "1.0.0"
    debug: bool = False
    api_key: str = "internal-dev-key"  # Override in production via env var

    # Models directory
    models_dir: str = "models"

    # Confidence thresholds
    anemia_confidence_threshold: float = 0.5
    skin_confidence_threshold: float = 0.5
    eye_confidence_threshold: float = 0.5
    posture_confidence_threshold: float = 0.4
    wound_confidence_threshold: float = 0.5
    tongue_confidence_threshold: float = 0.5

    # Image settings
    max_image_size_mb: int = 10
    allowed_content_types: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # .NET API (for callbacks if needed)
    dotnet_api_url: str = "http://localhost:5000"

    class Config:
        env_file = ".env"
        env_prefix = "AI_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
