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
from app.auth import verify_token_from_cookie, require_role_cookie, clear_auth_cookie
from app.middleware import AuthenticationMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Запуск приложения ROCKET PC...")

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

    try:
        await db.connect()
        print("✅ Успешно подключились к PostgreSQL")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")

    yield

    print("👋 Завершение работы приложения...")
    await db.disconnect()

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthenticationMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(main.router)
app.include_router(requests.router, prefix="/api")
app.include_router(auth.router)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard/dashboard.html", {"request": request, "page": "dashboard"})

@app.get("/dashboard/requests", response_class=HTMLResponse)
async def dashboard_requests(request: Request):
    return templates.TemplateResponse("dashboard/requests.html", {"request": request, "page": "requests"})

@app.get("/dashboard/users", response_class=HTMLResponse)
async def dashboard_users(request: Request):
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard/statistics", response_class=HTMLResponse)
async def dashboard_statistics(request: Request):
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard/api/masters/available")
async def get_available_masters_api(token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        masters = await db.get_available_masters()
        for master in masters:
            master["skills"] = await db.get_master_skills(master["id"])
        return masters
    except Exception as e:
        print(f"❌ Ошибка получения мастеров: {e}")
        return []

@app.post("/dashboard/api/requests/{request_id}/assign-master")
async def assign_master_api(request_id: str, assignment_data: dict, token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
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

@app.delete("/dashboard/api/requests/{request_id}/unassign-master")
async def unassign_master_api(request_id: str, token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
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

@app.get("/dashboard/api/masters/{master_id}/workload")
async def get_master_workload_api(master_id: int, token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        workload = await db.get_master_workload(master_id)
        return workload
    except Exception as e:
        print(f"❌ Ошибка получения загруженности: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")

@app.get("/dashboard/api/masters/dashboard")
async def get_masters_dashboard_api(token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
    try:
        dashboard_data = await db.get_masters_dashboard()
        return dashboard_data
    except Exception as e:
        print(f"❌ Ошибка получения dashboard: {e}")
        return []

@app.post("/dashboard/api/requests")
async def create_request_dashboard_api(request_data: dict, token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        client_data = {
            "full_name": request_data.get("client_name"),
            "phone": request_data.get("phone"),
            "email": request_data.get("email", "")
        }
        device_data = {
            "device_type": request_data.get("device_type"),
            "brand": request_data.get("brand", ""),
            "model": request_data.get("model", ""),
            "problem_description": request_data.get("problem_description"),
            "priority": request_data.get("priority", "Обычная")
        }
        request_id = await db.create_repair_request(client_data, device_data, int(token_data["sub"]))

        if request_data.get("assigned_master_id"):
            await db.assign_master_to_request(request_id, request_data["assigned_master_id"], int(token_data["sub"]))

        return {
            "id": request_id,
            "message": "Заявка создана",
            "status": "success"
        }
    except Exception as e:
        print(f"❌ Ошибка создания заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания заявки")

@app.get("/dashboard/api/requests")
async def get_dashboard_requests(token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        all_requests = await db.get_all_repair_requests()
        recent_requests = sorted(all_requests, key=lambda r: r['created_at'], reverse=True)
        return recent_requests[:5]
    except Exception as e:
        print(f"❌ Ошибка получения последних заявок: {e}")
        raise HTTPException(status_code=500, detail="Не удалось загрузить заявки")


@app.get("/dashboard/api/stats")
async def dashboard_api_stats(token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        print(f"📊 Запрос статистики от пользователя: {token_data.get('username')}")
        stats = await db.get_statistics()
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
async def update_request_status_api(request_id: str, status_data: dict, token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        print(f"🔄 Обновление статуса заявки {request_id} пользователем {token_data.get('username')}")

        # Обновляем статус
        success = await db.update_request_status(
            request_id=request_id,
            new_status=status_data["status"],
            user_id=int(token_data["sub"]),
            comment=status_data.get("comment")
        )

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # 🆕 Обновляем описание проблемы, если передано
        if "problem_description" in status_data and status_data["problem_description"]:
            await db.update_problem_description(request_id, status_data["problem_description"])

        return {"message": "Статус и описание проблемы обновлены"}

    except Exception as e:
        print(f"❌ Ошибка обновления статуса: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@app.post("/dashboard/api/requests/{request_id}/archive")
async def archive_request_api(request_id: str, token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
    try:
        print(f"💄 Архивирование заявки {request_id} пользователем {token_data.get('username')}")
        success = await db.archive_request(request_id)
        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        return {"message": "Заявка архивирована"}
    except Exception as e:
        print(f"❌ Ошибка архивирования: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")

app.include_router(dashboard.router)

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    clear_auth_cookie(response)
    return response

@app.get("/api")
async def api_root():
    return {
        "message": "ROCKET PC Service Center API",
        "version": settings.APP_VERSION,
        "status": "online"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if db.pool else "disconnected"
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/auth/login", status_code=302)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})
    html_content = """..."""  # unchanged for brevity
    return HTMLResponse(content=html_content, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    print(f"💥 Внутренняя ошибка сервера: {exc}")
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    html_content = """..."""  # unchanged for brevity
    return HTMLResponse(content=html_content, status_code=500)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
