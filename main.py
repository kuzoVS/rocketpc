from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import Dict

from app.routers import main, requests, auth, dashboard
from app.config import settings
from app.database_pg import db
from app.auth import verify_token, require_role
from app.middleware import AuthenticationMiddleware


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

# Добавляем middleware для защиты API
app.add_middleware(AuthenticationMiddleware)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Подключение роутеров
app.include_router(main.router)
app.include_router(requests.router, prefix="/api")
app.include_router(auth.router)


# ПУБЛИЧНЫЕ HTML страницы dashboard (защита через JavaScript)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Главная страница dashboard - защита через JavaScript"""
    return templates.TemplateResponse("dashboard/dashboard.html", {"request": request})


@app.get("/dashboard/requests", response_class=HTMLResponse)
async def dashboard_requests(request: Request):
    """Страница управления заявками"""
    return templates.TemplateResponse("dashboard/requests.html", {"request": request})


@app.get("/dashboard/users", response_class=HTMLResponse)
async def dashboard_users(request: Request):
    """Страница пользователей - пока редирект на главную"""
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard/statistics", response_class=HTMLResponse)
async def dashboard_statistics(request: Request):
    """Страница статистики - пока редирект на главную"""
    return RedirectResponse(url="/dashboard", status_code=302)

# Добавьте эти эндпоинты в main.py после существующих dashboard API

# API для получения доступных мастеров
@app.get("/dashboard/api/masters/available")
async def get_available_masters_api(token_data: Dict = Depends(verify_token)):
    """API для получения списка доступных мастеров"""
    try:
        masters = await db.get_available_masters()

        # Добавляем навыки для каждого мастера
        for master in masters:
            master["skills"] = await db.get_master_skills(master["id"])

        return masters
    except Exception as e:
        print(f"❌ Ошибка получения мастеров: {e}")
        return []


# API для назначения мастера на заявку
@app.post("/dashboard/api/requests/{request_id}/assign-master")
async def assign_master_api(
        request_id: str,
        assignment_data: dict,
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """API для назначения мастера на заявку"""
    try:
        success = await db.assign_master_to_request(
            request_id=request_id,
            master_id=assignment_data.get("master_id"),
            assigned_by_id=int(token_data["sub"])
        )

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        return {"message": "Мастер назначен"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка назначения мастера: {e}")
        raise HTTPException(status_code=500, detail="Ошибка назначения мастера")


# API для снятия мастера с заявки
@app.delete("/dashboard/api/requests/{request_id}/unassign-master")
async def unassign_master_api(
        request_id: str,
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """API для снятия мастера с заявки"""
    try:
        success = await db.unassign_master_from_request(request_id)

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена или мастер не назначен")

        return {"message": "Мастер снят с заявки"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка снятия мастера: {e}")
        raise HTTPException(status_code=500, detail="Ошибка снятия мастера")


# API для получения загруженности мастера
@app.get("/dashboard/api/masters/{master_id}/workload")
async def get_master_workload_api(
        master_id: int,
        token_data: Dict = Depends(verify_token)
):
    """API для получения загруженности мастера"""
    try:
        workload = await db.get_master_workload(master_id)
        return workload
    except Exception as e:
        print(f"❌ Ошибка получения загруженности: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


# API для получения dashboard мастеров
@app.get("/dashboard/api/masters/dashboard")
async def get_masters_dashboard_api(
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """API для получения dashboard информации о всех мастерах"""
    try:
        dashboard_data = await db.get_masters_dashboard()
        return dashboard_data
    except Exception as e:
        print(f"❌ Ошибка получения dashboard: {e}")
        return []


# Обновленный API для создания заявки с поддержкой назначения мастера
@app.post("/dashboard/api/requests")
async def create_request_dashboard_api(
        request_data: dict,
        token_data: Dict = Depends(verify_token)
):
    """API для создания заявки через dashboard с возможностью назначения мастера"""
    try:
        # Подготавливаем данные клиента
        client_data = {
            "full_name": request_data.get("client_name"),
            "phone": request_data.get("phone"),
            "email": request_data.get("email", "")
        }

        # Подготавливаем данные устройства
        device_data = {
            "device_type": request_data.get("device_type"),
            "brand": request_data.get("brand", ""),
            "model": request_data.get("model", ""),
            "problem_description": request_data.get("problem_description"),
            "priority": request_data.get("priority", "Обычная")
        }

        # Создаем заявку
        request_id = await db.create_repair_request(
            client_data,
            device_data,
            int(token_data["sub"])
        )

        # Если указан мастер, назначаем его
        if request_data.get("assigned_master_id"):
            await db.assign_master_to_request(
                request_id,
                request_data["assigned_master_id"],
                int(token_data["sub"])
            )

        return {
            "id": request_id,
            "message": "Заявка создана",
            "status": "success"
        }

    except Exception as e:
        print(f"❌ Ошибка создания заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания заявки")


@app.get("/dashboard/api/stats")
async def dashboard_api_stats(token_data: Dict = Depends(verify_token)):
    """API для получения статистики - требует валидный токен"""
    try:
        print(f"📊 Запрос статистики от пользователя: {token_data.get('username')}")
        stats = await db.get_statistics()

        # Добавляем дополнительную статистику
        all_requests = await db.get_all_repair_requests()
        active_requests = len([r for r in all_requests if r['status'] != 'Выдана' and not r['is_archived']])
        completed_requests = len([r for r in all_requests if r['status'] == 'Выдана'])

        stats.update({
            'active_requests': active_requests,
            'completed_requests': completed_requests,
            'monthly_revenue': completed_requests * 5000,
            'avg_repair_time': 3
        })

        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {
            'active_requests': 0,
            'completed_requests': 0,
            'monthly_revenue': 0,
            'avg_repair_time': 0
        }


@app.put("/dashboard/api/requests/{request_id}/status")
async def update_request_status_api(
        request_id: str,
        status_data: dict,
        token_data: Dict = Depends(verify_token)
):
    """API для обновления статуса заявки - требует валидный токен"""
    try:
        print(f"🔄 Обновление статуса заявки {request_id} пользователем {token_data.get('username')}")
        success = await db.update_request_status(
            request_id=request_id,
            new_status=status_data["status"],
            user_id=int(token_data["sub"]),
            comment=status_data.get("comment")
        )

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        return {"message": "Статус обновлен"}
    except Exception as e:
        print(f"❌ Ошибка обновления статуса: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@app.post("/dashboard/api/requests/{request_id}/archive")
async def archive_request_api(
        request_id: str,
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """API для архивирования заявки - требует роль администратора"""
    try:
        print(f"🗄️ Архивирование заявки {request_id} пользователем {token_data.get('username')}")
        success = await db.archive_request(request_id)

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        return {"message": "Заявка архивирована"}
    except Exception as e:
        print(f"❌ Ошибка архивирования: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


# Включаем оставшиеся API роуты dashboard
app.include_router(dashboard.router)


# Открытые страницы
@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.get("/logout")
async def logout():
    """Выход из системы"""
    return RedirectResponse(url="/auth/login", status_code=302)


@app.get("/api")
async def api_root():
    """Корневой API эндпоинт"""
    return {
        "message": "ROCKET PC Service Center API",
        "version": settings.APP_VERSION,
        "status": "online"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "database": "connected" if db.pool else "disconnected"
    }


@app.get("/", response_class=HTMLResponse)
async def root():
    """Корневая страница - редирект на login"""
    return RedirectResponse(url="/auth/login", status_code=302)


# Обработчики ошибок
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Обработчик 404 ошибок"""
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Endpoint not found"}
        )

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 - Страница не найдена</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; 
                   background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; }
            h1 { color: #00ffff; }
            a { color: #00ffff; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>🚀 ROCKET PC</h1>
        <h2>404 - Страница не найдена</h2>
        <p>Запрашиваемая страница не существует.</p>
        <a href="/auth/login">← Вернуться на главную</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=404)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Обработчик внутренних ошибок сервера"""
    print(f"💥 Внутренняя ошибка сервера: {exc}")

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>500 - Ошибка сервера</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; 
                   background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; }
            h1 { color: #ff4444; }
            a { color: #00ffff; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>🚀 ROCKET PC</h1>
        <h2>500 - Ошибка сервера</h2>
        <p>Произошла внутренняя ошибка сервера.</p>
        <a href="/auth/login">← Вернуться на главную</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=500)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )