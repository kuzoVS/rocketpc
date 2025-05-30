from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import os
from app.routers import main, requests, auth, dashboard
from app.config import settings
from app.database_pg import db

# Создание lifecycle manager для подключения к БД
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Запуск приложения ROCKET PC...")

    # Создание директорий при запуске
    if not os.path.exists("static"):
        os.makedirs("static")
        os.makedirs("static/images")
        os.makedirs("static/css")
        os.makedirs("static/js")
        os.makedirs("static/uploads")

    if not os.path.exists("templates"):
        os.makedirs("templates")
        os.makedirs("templates/auth")
        os.makedirs("templates/dashboard")

    # Подключение к базе данных
    try:
        await db.connect()
        print("✅ Успешно подключились к PostgreSQL")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")

    yield

    # Shutdown
    print("👋 Завершение работы приложения...")
    await db.disconnect()


# Создание приложения
app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене измените на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключение роутеров
app.include_router(main.router)
app.include_router(requests.router, prefix="/api")
app.include_router(auth.router)
app.include_router(dashboard.router)

templates = Jinja2Templates(directory="templates")

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard/dashboard.html", {"request": request})

# Корневой эндпоинт для проверки API
@app.get("/api")
async def api_root():
    return {
        "message": "ROCKET PC Service Center API",
        "version": settings.APP_VERSION,
        "status": "online"
    }


# Healthcheck endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if db.pool else "disconnected"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )