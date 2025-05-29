from fastapi import APIRouter, HTTPException
from typing import List

from app.models import RepairRequest, StatusResponse, StatusUpdate
from app.database import db
from app.config import settings

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("/", response_model=dict)
async def create_request(request: RepairRequest):
    """Создание новой заявки на ремонт"""
    request_id = db.create_request(request)
    return {
        "id": request_id,
        "message": "Заявка успешно создана"
    }


@router.get("/{request_id}/status", response_model=StatusResponse)
async def get_request_status(request_id: str):
    """Получение статуса заявки по ID"""
    request_data = db.get_request(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return StatusResponse(**request_data)


@router.get("/", response_model=List[dict])
async def get_all_requests():
    """Получение всех заявок (для администрирования)"""
    return db.get_all_requests()


@router.put("/{request_id}/status")
async def update_request_status(request_id: str, status_update: StatusUpdate):
    """Обновление статуса заявки"""
    if status_update.status not in settings.REPAIR_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус. Доступные статусы: {', '.join(settings.REPAIR_STATUSES)}"
        )

    if not db.update_request_status(request_id, status_update.status):
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return {
        "message": "Статус обновлен",
        "new_status": status_update.status
    }


@router.delete("/{request_id}")
async def delete_request(request_id: str):
    """Удаление заявки"""
    if not db.delete_request(request_id):
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return {"message": "Заявка удалена"}