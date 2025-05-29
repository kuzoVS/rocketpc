from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Настройки приложения"""
    APP_TITLE: str = "ROCKET PC Service Center API"
    APP_DESCRIPTION: str = "API для сервисного центра ROCKET PC"
    APP_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Статусы ремонта
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


settings = Settings()