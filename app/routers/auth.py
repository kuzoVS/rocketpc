from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict
from datetime import timedelta

from app.database_pg import db
from app.auth import create_access_token, verify_token, require_role

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(login_data: LoginRequest):
    """Авторизация пользователя"""
    user = await db.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Неверное имя пользователя или пароль"
        )

    access_token_expires = timedelta(minutes=480)
    access_token = create_access_token(
        data={"sub": str(user["id"]), "username": user["username"], "role": user["role"]},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }


@router.get("/profile")
async def get_profile(token_data: Dict = Depends(verify_token)):
    """Получение профиля текущего пользователя"""
    user = await db.get_user(int(token_data["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return user


@router.post("/users")
async def create_user(
        user_data: UserCreateRequest,
        token_data: Dict = Depends(require_role(["admin", "director"]))
):
    """Создание нового пользователя (только для админов и директоров)"""
    try:
        user_id = await db.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            role=user_data.role
        )
        return {"id": user_id, "message": "Пользователь создан успешно"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users")
async def get_all_users(token_data: Dict = Depends(require_role(["admin", "director"]))):
    """Получение всех пользователей"""
    users = await db.get_all_users()
    return users