from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, List
from datetime import datetime

from app.database_pg import db
from app.auth import verify_token, require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, token_data: Dict = Depends(verify_token)):
    """Главная страница dashboard"""
    # Получаем статистику
    stats = await db.get_statistics()

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": token_data,
        "stats": stats
    })


@router.get("/requests", response_class=HTMLResponse)
async def requests_page(request: Request, token_data: Dict = Depends(verify_token)):
    """Страница управления заявками"""
    requests = await db.get_all_repair_requests()

    return templates.TemplateResponse("dashboard/requests.html", {
        "request": request,
        "user": token_data,
        "requests": requests
    })


@router.get("/requests/archived", response_class=HTMLResponse)
async def archived_requests_page(request: Request, token_data: Dict = Depends(verify_token)):
    """Страница архивных заявок"""
    requests = await db.get_all_repair_requests(include_archived=True)
    archived_requests = [r for r in requests if r['is_archived']]

    return templates.TemplateResponse("dashboard/archived.html", {
        "request": request,
        "user": token_data,
        "requests": archived_requests
    })


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, token_data: Dict = Depends(require_role(["admin", "director"]))):
    """Страница управления пользователями"""
    users = await db.get_all_users()

    return templates.TemplateResponse("dashboard/users.html", {
        "request": request,
        "user": token_data,
        "users": users
    })


@router.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request, token_data: Dict = Depends(verify_token)):
    """Страница статистики"""
    stats = await db.get_statistics()

    return templates.TemplateResponse("dashboard/statistics.html", {
        "request": request,
        "user": token_data,
        "stats": stats
    })


# API методы для dashboard
@router.get("/api/requests")
async def get_requests_api(token_data: Dict = Depends(verify_token)):
    """API для получения заявок"""
    requests = await db.get_all_repair_requests()
    return requests


@router.put("/api/requests/{request_id}/status")
async def update_request_status_api(
        request_id: str,
        status_data: dict,
        token_data: Dict = Depends(verify_token)
):
    """API для обновления статуса заявки"""
    success = await db.update_request_status(
        request_id=request_id,
        new_status=status_data["status"],
        user_id=int(token_data["sub"]),
        comment=status_data.get("comment")
    )

    if not success:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return {"message": "Статус обновлен"}


@router.post("/api/requests/{request_id}/archive")
async def archive_request_api(
        request_id: str,
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """API для архивирования заявки"""
    success = await db.archive_request(request_id)

    if not success:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return {"message": "Заявка архивирована"}