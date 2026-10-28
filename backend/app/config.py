import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "AarogyaConnect AI"
    HOSPITAL_NAME: str = "Aarogya Multispeciality Hospital"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./aarogya_hospital.db"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Sarvam AI Official Configuration
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"
    SARVAM_MODEL: str = "sarvam-105b"

    # Generic LLM Configuration (fallback / compatibility)
    LLM_BASE_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None

    # Operator Authentication Credentials (Configured via Environment Variables)
    OPERATOR_USERNAME: str = "operator@aarogya.org"
    OPERATOR_PASSWORD: str = "AarogyaOp@2026"
    OPERATOR_SECRET_KEY: str = "aarogya-hospital-operations-secret-key-2026-prototype"
    OPERATOR_TOKEN_EXPIRE_HOURS: int = 12

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def active_llm_api_key(self) -> Optional[str]:
        return self.SARVAM_API_KEY or self.LLM_API_KEY

    @property
    def active_llm_base_url(self) -> str:
        if self.SARVAM_API_KEY:
            return self.SARVAM_BASE_URL.rstrip("/")
        if self.LLM_BASE_URL:
            return self.LLM_BASE_URL.rstrip("/")
        return self.SARVAM_BASE_URL.rstrip("/")

    @property
    def active_llm_model(self) -> str:
        if self.SARVAM_API_KEY:
            return self.SARVAM_MODEL
        if self.LLM_MODEL:
            return self.LLM_MODEL
        return self.SARVAM_MODEL

    @property
    def is_ai_configured(self) -> bool:
        key = self.active_llm_api_key
        return bool(key and key.strip())

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
