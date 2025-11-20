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
    database_url_test: str | None = None
    
    # Security
    secret_key: str = "your-super-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # Environment
    environment: str = "development"
    debug: bool = True

    # Initial admin bootstrap
    initial_admin_email: str = "admin@ambiental.local"
    initial_admin_full_name: str = "Administrador Ambiental"
    initial_admin_password: str = "ChangeMe#123"
    
    # CORS - stored as string, converted to list
    allowed_origins_str: str = "http://localhost:3000,http://localhost:8080,http://localhost:4200"
    
    # N8N Integration
    n8n_webhook_url: str = "https://profound-drum-faithful.ngrok-free.app/webhook/9df28051-1b03-4929-8cf0-d4de53e1ff7f"
    n8n_jwt_token: str = ""
    n8n_signing_secret: str = ""  # For HMAC validation of callbacks from N8N
    
    # Deployment and Storage
    deployment_mode: str = "saas"  # "saas" or "onprem"
    file_storage_backend: str = "local_encrypted"  # "local_encrypted" or "s3_encrypted"
    
    # Encryption
    file_encryption_key: str = ""  # Base64-encoded 256-bit key for file encryption
    
    @computed_field
    @property
    def allowed_origins(self) -> List[str]:
        """Convert comma-separated string to list"""
        if not self.allowed_origins_str:
            return []
        return [origin.strip() for origin in self.allowed_origins_str.split(',') if origin.strip()]


settings = Settings()
