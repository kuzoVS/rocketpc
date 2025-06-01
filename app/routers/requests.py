from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.models import RepairRequest, StatusResponse, StatusUpdate
from app.database_pg import db
from app.config import settings
from app.auth import verify_token, require_role

router = APIRouter(prefix="/requests", tags=["requests"])


# Расширенная модель для создания заявки
class CreateRequestModel(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: str = Field(default="", max_length=100)
    device_type: str = Field(..., min_length=2, max_length=50)
    brand: str = Field(default="", max_length=50)
    model: str = Field(default="", max_length=100)
    problem_description: str = Field(..., min_length=10, max_length=1000)
    priority: str = Field(default="Обычная")
    assigned_master_id: Optional[int] = None  # Опциональное назначение мастера при создании

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


# Модель для назначения мастера
class AssignMasterModel(BaseModel):
    master_id: int
    comment: Optional[str] = None


# Модель для обновления заявки
class UpdateRequestModel(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    estimated_cost: Optional[float] = None
    comment: Optional[str] = None


@router.post("/", response_model=dict)
async def create_request(request: CreateRequestModel, token_data: Optional[Dict] = Depends(verify_token)):
    """
    Создание новой заявки на ремонт.

    Если пользователь авторизован, сохраняется информация о создателе.
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

        # Получаем ID создателя если пользователь авторизован
        created_by_id = None
        if token_data:
            created_by_id = int(token_data.get("sub"))

        # Создаем заявку в базе данных
        request_id = await db.create_repair_request(client_data, device_data, created_by_id)

        # Если указан мастер, назначаем его
        if request.assigned_master_id and token_data:
            await db.assign_master_to_request(
                request_id,
                request.assigned_master_id,
                created_by_id
            )

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
async def get_all_requests(
        token_data: Dict = Depends(verify_token),
        include_archived: bool = False
):
    """
    Получение всех заявок с расширенной информацией.
    """
    try:
        requests = await db.get_all_repair_requests(include_archived)
        return requests
    except Exception as e:
        print(f"❌ Ошибка получения заявок: {e}")
        return []


@router.put("/{request_id}")
async def update_request(
        request_id: str,
        update_data: UpdateRequestModel,
        token_data: Dict = Depends(verify_token)
):
    """
    Обновление заявки (статус, приоритет, стоимость).
    """
    try:
        # Обновляем статус если указан
        if update_data.status:
            if update_data.status not in settings.REPAIR_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недопустимый статус. Доступные: {', '.join(settings.REPAIR_STATUSES)}"
                )

            success = await db.update_request_status(
                request_id=request_id,
                new_status=update_data.status,
                user_id=int(token_data["sub"]),
                comment=update_data.comment
            )

            if not success:
                raise HTTPException(status_code=404, detail="Заявка не найдена")

        # TODO: Добавить обновление других полей (приоритет, стоимость)

        return {"message": "Заявка обновлена"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка обновления заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления заявки")


@router.post("/{request_id}/assign-master")
async def assign_master(
        request_id: str,
        assignment: AssignMasterModel,
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """
    Назначение мастера на заявку.
    """
    try:
        success = await db.assign_master_to_request(
            request_id=request_id,
            master_id=assignment.master_id,
            assigned_by_id=int(token_data["sub"])
        )

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # Если есть комментарий, добавляем его в историю
        if assignment.comment:
            await db.update_request_status(
                request_id=request_id,
                new_status=(await db.get_repair_request(request_id))["status"],
                user_id=int(token_data["sub"]),
                comment=f"Назначен мастер: {assignment.comment}"
            )

        return {"message": "Мастер назначен"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка назначения мастера: {e}")
        raise HTTPException(status_code=500, detail="Ошибка назначения мастера")


@router.delete("/{request_id}/assign-master")
async def unassign_master(
        request_id: str,
        reason: Optional[str] = None,
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """
    Снятие мастера с заявки.
    """
    try:
        success = await db.unassign_master_from_request(request_id, reason)

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена или мастер не назначен")

        return {"message": "Мастер снят с заявки"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка снятия мастера: {e}")
        raise HTTPException(status_code=500, detail="Ошибка снятия мастера")


@router.get("/masters/available")
async def get_available_masters(token_data: Dict = Depends(verify_token)):
    """
    Получение списка доступных мастеров.
    """
    try:
        masters = await db.get_available_masters()

        # Добавляем навыки для каждого мастера
        for master in masters:
            master["skills"] = await db.get_master_skills(master["id"])

        return masters
    except Exception as e:
        print(f"❌ Ошибка получения мастеров: {e}")
        return []


@router.get("/masters/{master_id}/workload")
async def get_master_workload(
        master_id: int,
        token_data: Dict = Depends(verify_token)
):
    """
    Получение загруженности мастера.
    """
    try:
        workload = await db.get_master_workload(master_id)
        return workload
    except Exception as e:
        print(f"❌ Ошибка получения загруженности: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


@router.get("/dashboard/masters")
async def get_masters_dashboard(
        token_data: Dict = Depends(require_role(["admin", "director", "manager"]))
):
    """
    Dashboard информация о всех мастерах.
    """
    try:
        dashboard_data = await db.get_masters_dashboard()
        return dashboard_data
    except Exception as e:
        print(f"❌ Ошибка получения dashboard: {e}")
        return []


@router.delete("/{request_id}")
async def archive_request(
        request_id: str,
        token_data: Dict = Depends(require_role(["admin", "director"]))
):
    """
    Архивирование заявки.
    """
    success = await db.archive_request(request_id)

    if not success:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    return {"message": "Заявка архивирована"}


@router.get("/stats/summary")
async def get_requests_stats(token_data: Dict = Depends(verify_token)):
    """
    Получение статистики по заявкам.
    """
    try:
        stats = await db.get_statistics()
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")