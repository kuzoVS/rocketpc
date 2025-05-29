from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.routers import main, requests
from app.config import settings

# Создание приложения
app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION
)

# Создание директорий при запуске
if not os.path.exists("static"):
    os.makedirs("static")
    os.makedirs("static/images")
    os.makedirs("static/css")
    os.makedirs("static/js")

if not os.path.exists("templates"):
    os.makedirs("templates")

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключение роутеров
app.include_router(main.router)
app.include_router(requests.router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )