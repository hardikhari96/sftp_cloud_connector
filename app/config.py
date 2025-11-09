from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    mongodb_uri: str = Field(..., env="MONGODB_URI")
    mongodb_db: str = Field("sftp_cloud_connector", env="MONGODB_DB")
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_exp_hours: int = Field(12, env="JWT_EXP_HOURS")
    admin_default_username: str = Field("admin", env="ADMIN_DEFAULT_USERNAME")
    admin_default_password: str = Field("ChangeMe123!", env="ADMIN_DEFAULT_PASSWORD")
    sftp_root: Path = Field(Path(__file__).resolve().parent.parent / "sftp_root", env="SFTP_ROOT")


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
