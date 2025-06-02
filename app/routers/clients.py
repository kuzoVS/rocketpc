from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.database_pg import db
from app.auth import verify_token_from_cookie, require_role, require_role_cookie

router = APIRouter(prefix="/clients", tags=["clients"])


# Модели для клиентов
class ClientCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    is_vip: bool = False
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    is_vip: Optional[bool] = None
    notes: Optional[str] = None


@router.get("/")
async def get_all_clients(
        search: Optional[str] = Query(None, description="Поиск по имени, телефону или email"),
        include_stats: bool = Query(True, description="Включить статистику"),
        token_data: Dict = Depends(verify_token_from_cookie)
):
    """Получение всех клиентов с опциональным поиском"""
    try:
        if search:
            clients = await db.search_clients(search)
        else:
            clients = await db.get_all_clients(include_stats)
        return clients
    except Exception as e:
        print(f"❌ Ошибка получения клиентов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


@router.get("/statistics")
async def get_client_statistics(token_data: Dict = Depends(verify_token_from_cookie)):
    """Получение общей статистики по клиентам"""
    try:
        stats = await db.get_client_statistics()
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


@router.get("/vip")
async def get_vip_clients(token_data: Dict = Depends(verify_token_from_cookie)):
    """Получение VIP клиентов"""
    try:
        vip_clients = await db.get_vip_clients()
        return vip_clients
    except Exception as e:
        print(f"❌ Ошибка получения VIP клиентов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")

@router.get("/search")
async def search_clients_by_phone(
    phone: str = Query(..., min_length=3),
    token_data: Dict = Depends(verify_token_from_cookie)
):
    """
    🔍 Поиск клиентов по номеру телефона (по части номера)
    """
    try:
        clean_token = ''.join(filter(str.isdigit, phone))

        if not clean_token or len(clean_token) < 3:
            return []

        results = await db.search_clients_by_phone(clean_token)

        return [{
            "id": c["id"],
            "full_name": c["full_name"],
            "phone": c["phone"],
            "email": c.get("email")
        } for c in results]

    except Exception as e:
        print(f"❌ Ошибка поиска клиентов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска клиентов")

@router.get("/{client_id}")
async def get_client(client_id: int, token_data: Dict = Depends(verify_token_from_cookie)):
    """Получение клиента по ID с полной информацией"""
    try:
        client = await db.get_client_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        requests = await db.get_client_requests(client_id)
        client['requests'] = requests

        devices = await db.get_client_device_types(client_id)
        client['device_types'] = devices

        return client
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка получения клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


@router.get("/{client_id}/requests")
async def get_client_requests(
        client_id: int,
        limit: Optional[int] = Query(None, description="Лимит заявок"),
        token_data: Dict = Depends(verify_token_from_cookie)
):
    """Получение заявок клиента"""
    try:
        requests = await db.get_client_requests(client_id, limit)
        return requests
    except Exception as e:
        print(f"❌ Ошибка получения заявок клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


@router.post("/")
async def create_client(
        client_data: ClientCreate,
        token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))
):
    """Создание нового клиента"""
    try:
        client_id = await db.create_client(
            full_name=client_data.full_name,
            phone=client_data.phone,
            email=client_data.email,
            address=client_data.address
        )

        update_data = {}
        if client_data.is_vip:
            update_data['is_vip'] = client_data.is_vip
        if client_data.notes:
            update_data['notes'] = client_data.notes

        if update_data:
            await db.update_client(client_id, update_data)

        return {"id": client_id, "message": "Клиент создан успешно"}
    except Exception as e:
        print(f"❌ Ошибка создания клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания клиента")



@router.put("/{client_id}")
async def update_client(
        client_id: int,
        client_data: ClientUpdate,
        token_data: Dict = Depends(verify_token_from_cookie)
):
    """Обновление информации о клиенте"""
    try:
        existing_client = await db.get_client_by_id(client_id)
        if not existing_client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        update_data = {
            field: value for field, value in client_data.dict(exclude_unset=True).items()
            if value is not None
        }

        if not update_data:
            return {"message": "Нет данных для обновления"}

        success = await db.update_client(client_id, update_data)
        if not success:
            raise HTTPException(status_code=400, detail="Ошибка обновления клиента")

        return {"message": "Клиент обновлен успешно"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка обновления клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления клиента")


@router.delete("/{client_id}")
async def delete_client(
        client_id: int,
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """Удаление клиента (только если нет активных заявок)"""
    try:
        existing_client = await db.get_client_by_id(client_id)
        if not existing_client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        success = await db.delete_client(client_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Невозможно удалить клиента с активными заявками"
            )

        return {"message": "Клиент удален успешно"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка удаления клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления клиента")
