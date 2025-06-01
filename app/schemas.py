from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    DIRECTOR = "director"
    MANAGER = "manager"
    MASTER = "master"


class RepairStatus(str, Enum):
    ACCEPTED = "Принята"
    DIAGNOSTICS = "Диагностика"
    WAITING_PARTS = "Ожидание запчастей"
    IN_REPAIR = "В ремонте"
    TESTING = "Тестирование"
    READY = "Готова к выдаче"
    COMPLETED = "Выдана"


class Priority(str, Enum):
    LOW = "Низкая"
    NORMAL = "Обычная"
    HIGH = "Высокая"
    CRITICAL = "Критическая"


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    id: int
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserResponse(UserInDB):
    """User response without sensitive data"""
    pass


# Master specific schemas
class MasterSkill(BaseModel):
    skill_name: str
    skill_level: int = Field(..., ge=1, le=5)


class MasterInfo(UserResponse):
    specialization: Optional[str] = None
    is_available: bool = True
    max_concurrent_repairs: int = 5
    current_repairs_count: int = 0
    skills: List[MasterSkill] = []
    active_repairs: int = 0


# Client schemas
class ClientBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientInDB(ClientBase):
    id: int
    created_at: datetime
    total_repairs: int = 0
    is_vip: bool = False
    notes: Optional[str] = None

    class Config:
        orm_mode = True


# Repair request schemas
class RepairRequestBase(BaseModel):
    device_type: str = Field(..., min_length=2, max_length=50)
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=100)
    problem_description: str = Field(..., min_length=10, max_length=1000)
    priority: Priority = Priority.NORMAL


class RepairRequestCreate(RepairRequestBase):
    client_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    assigned_master_id: Optional[int] = None


class RepairRequestUpdate(BaseModel):
    status: Optional[RepairStatus] = None
    priority: Optional[Priority] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    final_cost: Optional[float] = Field(None, ge=0)
    estimated_completion: Optional[datetime] = None
    assigned_master_id: Optional[int] = None
    parts_used: Optional[str] = None
    notes: Optional[str] = None


class RepairRequestInDB(RepairRequestBase):
    id: int
    request_id: str
    client_id: int
    status: RepairStatus = RepairStatus.ACCEPTED
    estimated_cost: Optional[float] = None
    final_cost: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    assigned_master_id: Optional[int] = None
    assigned_by_id: Optional[int] = None
    assigned_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False
    warranty_period: int = 30
    repair_duration_hours: Optional[float] = None
    parts_used: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        orm_mode = True


class RepairRequestResponse(RepairRequestInDB):
    """Full repair request with related data"""
    client_name: str
    client_phone: str
    client_email: Optional[str] = None
    client_is_vip: Optional[bool] = False
    master_name: Optional[str] = None
    master_phone: Optional[str] = None
    master_specialization: Optional[str] = None
    assigned_by_name: Optional[str] = None
    created_by_name: Optional[str] = None


# Status update schemas
class StatusUpdateRequest(BaseModel):
    status: RepairStatus
    comment: Optional[str] = None
    problem_description: Optional[str] = Field(None, min_length=10, max_length=1000)


class AssignMasterRequest(BaseModel):
    master_id: int
    comment: Optional[str] = None


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: str  # user_id as string
    username: str
    role: UserRole
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Statistics schemas
class StatusStatistic(BaseModel):
    status: str
    count: int


class Statistics(BaseModel):
    total_requests: int
    status_stats: List[StatusStatistic]
    active_requests: int = 0
    completed_requests: int = 0
    monthly_revenue: float = 0.0
    avg_repair_time: float = 0.0


# Dashboard schemas
class MasterWorkload(BaseModel):
    active_repairs: List[Dict[str, Any]]
    stats: Dict[str, Any]


class MasterDashboard(BaseModel):
    id: int
    full_name: str
    specialization: Optional[str]
    is_available: bool
    active_repairs: int
    completed_this_week: int
    skills: Optional[str]


# Error schemas
class ErrorResponse(BaseModel):
    detail: str


class ValidationErrorResponse(BaseModel):
    detail: List[Dict[str, Any]]


# Pagination schemas
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    pages: int
    limit: int