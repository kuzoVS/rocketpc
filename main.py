from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import Dict

from app.routers import main, requests, auth, dashboard
from app.config import settings
from app.database_pg import db
from app.auth import verify_token


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

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")


# Функция для проверки аутентификации через HTML страницы
async def get_current_user_from_request(request: Request) -> Dict:
    """Получение текущего пользователя из запроса (для HTML страниц)"""
    try:
        # Пытаемся получить токен из заголовка Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token required")

        token = auth_header.split(" ")[1]

        # Создаем объект для verify_token
        class MockCredentials:
            def __init__(self, token):
                self.credentials = token

        credentials = MockCredentials(token)
        return verify_token(credentials)
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


# Подключение роутеров
app.include_router(main.router)
app.include_router(requests.router, prefix="/api")
app.include_router(auth.router)


# Dashboard роуты с проверкой аутентификации
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Главная страница dashboard (требует аутентификации)"""
    return templates.TemplateResponse("dashboard/dashboard.html", {"request": request})


@app.get("/dashboard/requests", response_class=HTMLResponse)
async def dashboard_requests(request: Request):
    """Страница заявок (требует аутентификации)"""
    return templates.TemplateResponse("dashboard/requests.html", {"request": request})


@app.get("/dashboard/users", response_class=HTMLResponse)
async def dashboard_users(request: Request):
    """Страница пользователей (требует аутентификации)"""
    return templates.TemplateResponse("dashboard/users.html", {"request": request})


@app.get("/dashboard/statistics", response_class=HTMLResponse)
async def dashboard_statistics(request: Request):
    """Страница статистики (требует аутентификации)"""
    return templates.TemplateResponse("dashboard/statistics.html", {"request": request})


# Включаем API роуты dashboard
app.include_router(dashboard.router)


# Страница входа (открытая)
@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


# Выход из системы
@app.get("/logout", response_class=HTMLResponse)
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/auth/login", status_code=302)
    return response


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