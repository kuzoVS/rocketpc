from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from pydantic import BaseModel, Field
from datetime import datetime

from app.models import RepairRequest, StatusResponse, StatusUpdate
from app.database_pg import db
from app.config import settings
from app.auth import verify_token, require_role

router = APIRouter(prefix="/requests", tags=["requests"])


# Модель для создания заявки через API
class CreateRequestModel(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: str = Field(default="", max_length=100)
    device_type: str = Field(..., min_length=2, max_length=50)
    brand: str = Field(default="", max_length=50)
    model: str = Field(default="", max_length=100)
    problem_description: str = Field(..., min_length=10, max_length=1000)
    priority: str = Field(default="Обычная")

    class Config:
        json_schema_extra = {
            "example": {
                "client_name": "Иван Иванов",
                "phone": "+7 (999) 123-45-67",
                "email": "ivan@example.com",
                "device_type": "Ноутбук",
                "brand": "ASUS",
                "model": "VivoBook 15",
                "problem_description": "Не включается, нет реакции на кнопку питания",
                "priority": "Обычная"
            }
        }


@router.post("/", response_model=dict)
async def create_request(request: CreateRequestModel):
    """
    Создание новой заявки на ремонт (открытый эндпоинт).

    Доступно всем пользователям без авторизации.
    """
    try:
        # Подготавливаем данные клиента
        client_data = {
            "full_name": request.client_name,
            "phone": request.phone,
            "email": request.email
        }

        # Подготавливаем данные устройства
        device_data = {
            "device_type": request.device_type,
            "brand": request.brand,
            "model": request.model,
            "problem_description": request.problem_description,
            "priority": request.priority
        }

        # Создаем заявку в базе данных
        request_id = await db.create_repair_request(client_data, device_data)

        return {
            "id": request_id,
            "message": "Заявка успешно создана",
            "status": "success"
        }

    except Exception as e:
        print(f"❌ Ошибка создания заявки: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ошибка при создании заявки. Попробуйте позже."
        )


@router.get("/{request_id}/status", response_model=StatusResponse)
async def get_request_status(request_id: str):
    """
    Получение статуса заявки по ID (открытый эндпоинт).

    Доступно всем для проверки статуса своей заявки.
    """
    request_data = await db.get_repair_request(request_id)

    if not request_data:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return StatusResponse(
        id=request_data["request_id"],
        client_name=request_data["client_name"],
        device_type=request_data["device_type"],
        problem_description=request_data["problem_description"],
        status=request_data["status"],
        created_at=request_data["created_at"]
    )


@router.get("/", response_model=List[dict])
async def get_all_requests(token_data: Dict = Depends(verify_token)):
    """
    Получение всех заявок (требует авторизации).

    Доступно только авторизованным сотрудникам.
    """
    try:
        requests = await db.get_all_repair_requests()
        return requests
    except Exception as e:
        print(f"❌ Ошибка получения заявок: {e}")
        return []


@router.put("/{request_id}/status")
async def update_request_status(
        request_id: str,
        status_update: StatusUpdate,
        token_data: Dict = Depends(verify_token)
):
    """
    Обновление статуса заявки (требует авторизации).

    Доступно только авторизованным сотрудникам.
    """
    if status_update.status not in settings.REPAIR_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус. Доступные статусы: {', '.join(settings.REPAIR_STATUSES)}"
        )

    success = await db.update_request_status(
        request_id=request_id,
        new_status=status_update.status,
        user_id=int(token_data["sub"]),
        comment=None
    )

    if not success:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return {
        "message": "Статус обновлен",
        "new_status": status_update.status
    }


@router.delete("/{request_id}")
async def delete_request(
        request_id: str,
        token_data: Dict = Depends(require_role(["admin", "director"]))
):
    """
    Удаление заявки (требует роль admin или director).

    Доступно только администраторам и директорам.
    """
    success = await db.archive_request(request_id)

    if not success:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return {"message": "Заявка удалена"}


@router.get("/stats/summary")
async def get_requests_stats(token_data: Dict = Depends(verify_token)):
    """
    Получение статистики по заявкам (требует авторизации).
    """
    try:
        stats = await db.get_statistics()
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")