from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class RepairRequest(BaseModel):
    """Модель заявки на ремонт"""
    client_name: str = Field(..., description="Имя клиента")
    phone: str = Field(..., description="Телефон клиента")
    email: Optional[str] = Field("", description="Email клиента")
    device_type: str = Field(..., description="Тип устройства")
    problem_description: str = Field(..., description="Описание проблемы")
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="Принята", description="Статус заявки")
    id: Optional[str] = Field(default=None, description="ID заявки")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StatusResponse(BaseModel):
    """Модель ответа о статусе заявки"""
    id: str
    client_name: str
    device_type: str
    problem_description: str
    status: str
    created_at: datetime


class StatusUpdate(BaseModel):
    """Модель для обновления статуса"""
    status: str