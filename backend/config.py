from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # LLM
    GEMINI_API_KEY: str = ""

    # ASR
    DEEPGRAM_API_KEY: str = ""

    # TTS
    SARVAM_API_KEY: str = ""
    SARVAM_TTS_URL: str = "https://api.sarvam.ai/text-to-speech"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./medora_ot.db"

    # Auth
    SECRET_KEY: str = "change_me_to_random_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    def get_cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
