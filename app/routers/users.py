from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Optional, List
from datetime import datetime

from app.database_pg import db
from app.auth import verify_token_from_cookie, require_role_cookie
from app.config import settings

router = APIRouter(prefix="/dashboard/users", tags=["users"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def users_page(
        request: Request,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        sort: Optional[str] = "name",
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """Страница управления пользователями"""
    try:
        # Получаем всех пользователей (фильтрация теперь на клиенте)
        all_users = await db.get_all_users()

        return templates.TemplateResponse("dashboard/users.html", {
            "request": request,
            "users": all_users,  # Передаем всех пользователей
            "page": "users"
        })

    except Exception as e:
        print(f"❌ Ошибка загрузки страницы пользователей: {e}")
        return templates.TemplateResponse("dashboard/users.html", {
            "request": request,
            "users": [],
            "page": "users",
            "error": "Ошибка загрузки данных"
        })


@router.post("", response_class=HTMLResponse)
async def create_user(
        request: Request,
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        full_name: str = Form(...),
        role: str = Form(...),
        phone: Optional[str] = Form(None),
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """Создание нового пользователя"""
    try:
        # Валидация
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")

        if role not in ['admin', 'director', 'manager', 'master']:
            raise HTTPException(status_code=400, detail="Неверная роль пользователя")

        # Проверяем существование username и email
        if await db.check_username_exists(username):
            return RedirectResponse(url="/dashboard/users?error=username_exists", status_code=302)

        if await db.check_email_exists(email):
            return RedirectResponse(url="/dashboard/users?error=email_exists", status_code=302)

        # Создаем пользователя
        user_id = await db.create_user(
            username=username.strip(),
            email=email.strip(),
            password=password,
            full_name=full_name.strip(),
            role=role,
            phone=phone.strip() if phone else None
        )

        print(f"✅ Создан пользователь с ID: {user_id}")

        return RedirectResponse(url="/dashboard/users?success=created", status_code=302)

    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        error_msg = str(e) if "уже существует" in str(e) or "duplicate" in str(
            e).lower() else "Ошибка создания пользователя"
        return RedirectResponse(url=f"/dashboard/users?error={error_msg}", status_code=302)


@router.post("/{user_id}", response_class=HTMLResponse)
async def update_user(
        request: Request,
        user_id: int,
        username: str = Form(...),
        email: str = Form(...),
        full_name: str = Form(...),
        role: str = Form(...),
        is_active: str = Form(...),
        phone: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """Обновление пользователя"""
    try:
        # Валидация
        if role not in ['admin', 'director', 'manager', 'master']:
            raise HTTPException(status_code=400, detail="Неверная роль пользователя")

        active_status = is_active.lower() == 'true'

        # Проверяем существование email (исключая текущего пользователя)
        if await db.check_email_exists(email, exclude_user_id=user_id):
            return RedirectResponse(url="/dashboard/users?error=email_exists", status_code=302)

        # Обновляем основную информацию пользователя
        success = await db.update_user_info(
            user_id=user_id,
            email=email.strip(),
            full_name=full_name.strip(),
            role=role,
            is_active=active_status,
            phone=phone.strip() if phone else None
        )

        if not success:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Обновляем пароль если указан
        if password and password.strip() and len(password.strip()) >= 6:
            await db.update_user_password(user_id, password.strip())

        print(f"✅ Обновлен пользователь с ID: {user_id}")
        return RedirectResponse(url="/dashboard/users?success=updated", status_code=302)

    except Exception as e:
        print(f"❌ Ошибка обновления пользователя: {e}")
        error_msg = str(e) if "не найден" in str(e) else "Ошибка обновления пользователя"
        return RedirectResponse(url=f"/dashboard/users?error={error_msg}", status_code=302)


@router.post("/{user_id}/activate", response_class=HTMLResponse)
async def activate_user(
        user_id: int,
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """Активация пользователя"""
    try:
        success = await db.update_user_status(user_id, True)
        if not success:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        print(f"✅ Активирован пользователь с ID: {user_id}")
        return RedirectResponse(url="/dashboard/users?success=activated", status_code=302)

    except Exception as e:
        print(f"❌ Ошибка активации пользователя: {e}")
        return RedirectResponse(url="/dashboard/users?error=activation_failed", status_code=302)


@router.post("/{user_id}/deactivate", response_class=HTMLResponse)
async def deactivate_user(
        user_id: int,
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """Деактивация пользователя"""
    try:
        # Проверяем, что это не последний администратор
        if token_data.get("sub") == str(user_id):
            return RedirectResponse(url="/dashboard/users?error=cannot_deactivate_self", status_code=302)

        success = await db.update_user_status(user_id, False)
        if not success:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        print(f"✅ Деактивирован пользователь с ID: {user_id}")
        return RedirectResponse(url="/dashboard/users?success=deactivated", status_code=302)

    except Exception as e:
        print(f"❌ Ошибка деактивации пользователя: {e}")
        return RedirectResponse(url="/dashboard/users?error=deactivation_failed", status_code=302)


@router.post("/{user_id}/delete", response_class=HTMLResponse)
async def delete_user(
        user_id: int,
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """ПОЛНОЕ удаление пользователя из базы данных"""
    try:
        print(f"🗑️ Попытка полного удаления пользователя {user_id}")

        # Проверяем, что это не текущий пользователь
        current_user_id = int(token_data.get("sub"))
        if current_user_id == user_id:
            print(f"❌ Попытка удалить самого себя: {current_user_id}")
            return RedirectResponse(url="/dashboard/users?error=cannot_delete_self", status_code=302)

        # Проверяем существование пользователя
        user = await db.get_user(user_id)
        if not user:
            print(f"❌ Пользователь {user_id} не найден")
            return RedirectResponse(url="/dashboard/users?error=user_not_found", status_code=302)

        # Проверяем, не последний ли это администратор
        if user['role'] in ['admin', 'director']:
            admin_count = await db.get_users_count_by_role()
            total_admins = admin_count.get('admin', 0) + admin_count.get('director', 0)
            print(f"📊 Общее количество админов: {total_admins}")

            if total_admins <= 1:
                print(f"❌ Попытка удаления последнего администратора")
                return RedirectResponse(url="/dashboard/users?error=cannot_delete_last_admin", status_code=302)

        # Показываем предупреждение о связанных данных
        print(f"⚠️ ВНИМАНИЕ: Удаление пользователя {user['full_name']} ({user['username']}) приведет к:")
        print(f"   - Обнулению ссылок на него во всех заявках")
        print(f"   - Удалению его навыков (если мастер)")
        print(f"   - Удалению истории назначений")

        # ПОЛНОСТЬЮ удаляем пользователя
        success = await db.delete_user(user_id)
        if not success:
            print(f"❌ Не удалось удалить пользователя {user_id}")
            return RedirectResponse(url="/dashboard/users?error=deletion_failed", status_code=302)

        print(f"✅ Пользователь {user_id} ({user['username']}) полностью удален")
        return RedirectResponse(url="/dashboard/users?success=deleted", status_code=302)

    except Exception as e:
        print(f"❌ Ошибка полного удаления пользователя: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/dashboard/users?error=deletion_failed", status_code=302)


# API endpoints для AJAX запросов
@router.get("/api/list")
async def get_users_api(
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """API для получения списка пользователей"""
    try:
        users = await db.get_all_users()
        return {
            "users": users,
            "total": len(users)
        }
    except Exception as e:
        print(f"❌ Ошибка получения пользователей через API: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки данных")

@router.get("/api/statistics")
async def get_user_statistics_api(
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    print(token_data)
    """API для получения статистики пользователей"""
    try:
        stats = await db.get_user_statistics()
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики пользователей: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки статистики")


@router.get("/api/{user_id}")
async def get_user_api(
        user_id: int,
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """API для получения информации о пользователе"""
    try:
        user = await db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка получения пользователя через API: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки данных")


