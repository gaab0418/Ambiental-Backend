from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pydantic import computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'  # Ignore extra fields from .env
    )
    
    # Database
    database_url: str = "postgresql://username:password@localhost:5432/ambiental_db"
    
    # Security
    secret_key: str = "your-super-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # CORS - stored as string, converted to list
    allowed_origins_str: str = "http://localhost:3000,http://localhost:8080,http://localhost:4200"
    
    @computed_field
    @property
    def allowed_origins(self) -> List[str]:
        """Convert comma-separated string to list"""
        if not self.allowed_origins_str:
            return []
        return [origin.strip() for origin in self.allowed_origins_str.split(',') if origin.strip()]


settings = Settings()
