from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from datetime import date
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
    problem_description: Optional[str] = Field(None, min_length=10, max_length=1000)


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

        # 🔧 Обновление описания проблемы
        if update_data.problem_description:
            await db.update_problem_description(request_id, update_data.problem_description)

        # TODO: Добавить обновление приоритета, стоимости и т.д.

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


class UpdateRequestFullModel(BaseModel):
    # Основная информация об устройстве
    device_type: Optional[str] = Field(None, min_length=2, max_length=50)
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)

    # Описание проблемы
    problem_description: Optional[str] = Field(None, min_length=10, max_length=1000)

    # Статус и приоритет
    status: Optional[str] = None
    priority: Optional[str] = None

    # Финансовая информация
    estimated_cost: Optional[float] = Field(None, ge=0)
    final_cost: Optional[float] = Field(None, ge=0)

    # Временные рамки
    estimated_completion: Optional[date] = None
    repair_duration_hours: Optional[float] = Field(None, ge=0)

    # Дополнительная информация
    warranty_period: Optional[int] = Field(None, ge=0, le=365)
    parts_used: Optional[str] = None
    notes: Optional[str] = None

    # Комментарий к изменению
    comment: Optional[str] = None


# Модель для обновления информации о клиенте
class UpdateClientModel(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None


@router.get("/{request_id}/full")
async def get_request_full(
        request_id: str,
        token_data: Dict = Depends(verify_token)
):
    """
    Получение полной информации о заявке для редактирования
    """
    try:
        request_data = await db.get_repair_request_full(request_id)

        if not request_data:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # Получаем историю изменений
        status_history = await db.get_status_history(request_id)
        request_data['status_history'] = status_history

        return request_data

    except Exception as e:
        print(f"❌ Ошибка получения заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.put("/{request_id}/full")
async def update_request_full(
        request_id: str,
        update_data: UpdateRequestFullModel,
        token_data: Dict = Depends(verify_token)
):
    """
    Полное обновление заявки на ремонт
    """
    try:
        # Проверяем статус если он указан
        if update_data.status:
            valid_statuses = [
                'Принята', 'Диагностика', 'Ожидание запчастей',
                'В ремонте', 'Тестирование', 'Готова к выдаче', 'Выдана'
            ]
            if update_data.status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недопустимый статус. Доступные: {', '.join(valid_statuses)}"
                )

        # Проверяем приоритет если он указан
        if update_data.priority:
            valid_priorities = ['Низкая', 'Обычная', 'Высокая', 'Критическая']
            if update_data.priority not in valid_priorities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недопустимый приоритет. Доступные: {', '.join(valid_priorities)}"
                )

        # Подготавливаем данные для обновления
        update_dict = {}
        for field, value in update_data.dict(exclude_unset=True).items():
            if value is not None and field != 'comment':
                update_dict[field] = value

        # Добавляем комментарий если есть
        if update_data.comment:
            update_dict['comment'] = update_data.comment

        # Обновляем заявку
        success = await db.update_repair_request_full(
            request_id=request_id,
            update_data=update_dict,
            user_id=int(token_data["sub"])
        )

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        return {"message": "Заявка успешно обновлена", "updated_fields": list(update_dict.keys())}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка обновления заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления заявки")


@router.put("/{request_id}/client")
async def update_request_client(
        request_id: str,
        client_data: UpdateClientModel,
        token_data: Dict = Depends(verify_token)
):
    """
    Обновление информации о клиенте заявки
    """
    try:
        # Получаем заявку чтобы найти клиента
        request_info = await db.get_repair_request(request_id)
        if not request_info:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # Подготавливаем данные клиента для обновления
        client_update = {}
        for field, value in client_data.dict(exclude_unset=True).items():
            if value is not None:
                client_update[field] = value

        if not client_update:
            return {"message": "Нет данных для обновления"}

        # Обновляем информацию о клиенте
        # Нужно получить client_id из заявки
        success = await db.update_client_info(
            client_id=request_info['client_id'],
            client_data=client_update
        )

        if not success:
            raise HTTPException(status_code=400, detail="Ошибка обновления клиента")

        return {"message": "Информация о клиенте обновлена"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка обновления клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@router.get("/{request_id}/history")
async def get_request_history(
        request_id: str,
        token_data: Dict = Depends(verify_token)
):
    """
    Получение истории изменений заявки
    """
    try:
        history = await db.get_status_history(request_id)
        return history
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")