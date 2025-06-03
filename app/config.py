# app/config.py

from pydantic_settings import BaseSettings
from typing import List
from pydantic import Field


class Settings(BaseSettings):
    # App info
    APP_TITLE: str = "ROCKET PC Service Center API"
    APP_DESCRIPTION: str = "API для сервисного центра ROCKET PC"
    APP_VERSION: str = "1.0.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # CORS
    ALLOWED_ORIGINS: List[str]

    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    FROM_EMAIL: str

    # Uploads
    UPLOAD_FOLDER: str
    MAX_UPLOAD_SIZE: int

    # Timezone
    TIMEZONE: str

    # Repair statuses
    REPAIR_STATUSES: List[str] = [
        "Принята",
        "Диагностика",
        "Ожидание запчастей",
        "В ремонте",
        "Тестирование",
        "Готова к выдаче",
        "Выдана"
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "forbid"  # запрет "лишних" переменных в .env

settings = Settings()
