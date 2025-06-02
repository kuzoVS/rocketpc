from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict
from datetime import timedelta, datetime, timezone

from app.database_pg import db
from app.auth import create_access_token, verify_token_from_cookie, require_role_cookie, set_auth_cookie, clear_auth_cookie
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    """Авторизация пользователя через форму и cookie"""
    user = await db.authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Неверное имя пользователя или пароль"
        })

    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"]
    }

    access_token = create_access_token(data=token_data)
    response = RedirectResponse(url="/dashboard", status_code=302)
    set_auth_cookie(response, access_token)
    return response


@router.get("/logout")
async def logout():
    """Выход из системы — удаление cookie"""
    response = RedirectResponse(url="/auth/login", status_code=302)
    clear_auth_cookie(response)
    return response


@router.get("/profile")
async def get_profile(token_data: Dict = Depends(verify_token_from_cookie)):
    """Профиль текущего пользователя"""
    user = await db.get_user(int(token_data["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.post("/users")
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """Создание пользователя (через HTML или форму)"""
    try:
        user_id = await db.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role
        )
        return {"id": user_id, "message": "Пользователь создан успешно"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users")
async def get_all_users(token_data: Dict = Depends(require_role_cookie(["admin", "director"]))):
    """Получение всех пользователей"""
    users = await db.get_all_users()
    return users