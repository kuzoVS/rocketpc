from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
import os
from typing import Dict, Optional
from app.routers import clients
from app.routers import main, requests, auth, dashboard
from app.config import settings
from app.database_pg import db
from app.auth import verify_token_from_cookie, require_role_cookie, clear_auth_cookie
from app.middleware import AuthenticationMiddleware
from fastapi import Form

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Запуск приложения ROCKET PC...")

    if not os.path.exists("static"):
        os.makedirs("static")
        os.makedirs("static/images")
        os.makedirs("static/css")
        os.makedirs("static/js")
        os.makedirs("static/uploads")

    if not os.path.exists("templates"):
        os.makedirs("templates")
        os.makedirs("templates/auth")
        os.makedirs("templates/dashboard")

    try:
        await db.connect()
        print("✅ Успешно подключились к PostgreSQL")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")

    yield

    print("👋 Завершение работы приложения...")
    await db.disconnect()

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthenticationMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(main.router)
app.include_router(requests.router, prefix="/api")
app.include_router(auth.router)
app.include_router(clients.router, prefix="/api")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard/dashboard.html", {"request": request, "page": "dashboard"})

@app.get("/dashboard/requests", response_class=HTMLResponse)
async def dashboard_requests(request: Request):
    return templates.TemplateResponse("dashboard/requests.html", {"request": request, "page": "requests"})

@app.get("/dashboard/users", response_class=HTMLResponse)
async def dashboard_users(request: Request):
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard/schedule", response_class=HTMLResponse)
async def dashboard_statistics(request: Request):
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/dashboard/clients", response_class=HTMLResponse)
async def dashboard_statistics(request: Request):
    return templates.TemplateResponse("dashboard/clients.html", {"request": request, "page": "clients"})


@app.get("/dashboard/api/masters/available")
async def get_available_masters_api(token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        masters = await db.get_available_masters()
        for master in masters:
            master["skills"] = await db.get_master_skills(master["id"])
        return masters
    except Exception as e:
        print(f"❌ Ошибка получения мастеров: {e}")
        return []

@app.post("/dashboard/api/requests/{request_id}/assign-master")
async def assign_master_api(request_id: str, assignment_data: dict, token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
    try:
        success = await db.assign_master_to_request(
            request_id=request_id,
            master_id=assignment_data.get("master_id"),
            assigned_by_id=int(token_data["sub"])
        )
        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        return {"message": "Мастер назначен"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка назначения мастера: {e}")
        raise HTTPException(status_code=500, detail="Ошибка назначения мастера")

@app.delete("/dashboard/api/requests/{request_id}/unassign-master")
async def unassign_master_api(request_id: str, token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
    try:
        success = await db.unassign_master_from_request(request_id)
        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена или мастер не назначен")
        return {"message": "Мастер снят с заявки"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка снятия мастера: {e}")
        raise HTTPException(status_code=500, detail="Ошибка снятия мастера")

@app.get("/dashboard/api/masters/{master_id}/workload")
async def get_master_workload_api(master_id: int, token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        workload = await db.get_master_workload(master_id)
        return workload
    except Exception as e:
        print(f"❌ Ошибка получения загруженности: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")

@app.get("/dashboard/api/masters/dashboard")
async def get_masters_dashboard_api(token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
    try:
        dashboard_data = await db.get_masters_dashboard()
        return dashboard_data
    except Exception as e:
        print(f"❌ Ошибка получения dashboard: {e}")
        return []

@app.post("/dashboard/api/requests")
async def create_request_dashboard_api(request_data: dict, token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        client_data = {
            "full_name": request_data.get("client_name"),
            "phone": request_data.get("phone"),
            "email": request_data.get("email", "")
        }
        device_data = {
            "device_type": request_data.get("device_type"),
            "brand": request_data.get("brand", ""),
            "model": request_data.get("model", ""),
            "problem_description": request_data.get("problem_description"),
            "priority": request_data.get("priority", "Обычная")
        }
        request_id = await db.create_repair_request(client_data, device_data, int(token_data["sub"]))

        if request_data.get("assigned_master_id"):
            await db.assign_master_to_request(request_id, request_data["assigned_master_id"], int(token_data["sub"]))

        return {
            "id": request_id,
            "message": "Заявка создана",
            "status": "success"
        }
    except Exception as e:
        print(f"❌ Ошибка создания заявки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания заявки")

@app.get("/dashboard/api/requests")
async def get_dashboard_requests(token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        all_requests = await db.get_all_repair_requests()
        recent_requests = sorted(all_requests, key=lambda r: r['created_at'], reverse=True)
        return recent_requests[:5]
    except Exception as e:
        print(f"❌ Ошибка получения последних заявок: {e}")
        raise HTTPException(status_code=500, detail="Не удалось загрузить заявки")


@app.get("/dashboard/api/stats")
async def dashboard_api_stats(token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        print(f"📊 Запрос статистики от пользователя: {token_data.get('username')}")
        stats = await db.get_statistics()
        all_requests = await db.get_all_repair_requests()
        active_requests = len([r for r in all_requests if r['status'] != 'Выдана' and not r['is_archived']])
        completed_requests = len([r for r in all_requests if r['status'] == 'Выдана'])
        stats.update({
            'active_requests': active_requests,
            'completed_requests': completed_requests,
            'monthly_revenue': completed_requests * 5000,
            'avg_repair_time': 3
        })
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {
            'active_requests': 0,
            'completed_requests': 0,
            'monthly_revenue': 0,
            'avg_repair_time': 0
        }


# Добавьте эти роуты в main.py после существующих роутов

from app.routers import clients

# Подключаем роуты клиентов
app.include_router(clients.router, prefix="/api")

# Или если роуты clients еще не импортированы, добавьте эти API методы напрямую:

@app.get("/api/clients")
async def get_clients_api(token_data: Dict = Depends(verify_token_from_cookie)):
    """API для получения всех клиентов"""
    try:
        print(f"👥 Запрос клиентов от пользователя: {token_data.get('username')}")
        clients = await db.get_all_clients(include_stats=True)
        print(f"✅ Возвращено {len(clients)} клиентов")
        return clients
    except Exception as e:
        print(f"❌ Ошибка получения клиентов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")

@app.get("/api/clients/statistics")
async def get_clients_statistics_api(token_data: Dict = Depends(verify_token_from_cookie)):
    """API для получения статистики клиентов"""
    try:
        print(f"📊 Запрос статистики клиентов от пользователя: {token_data.get('username')}")
        stats = await db.get_client_statistics()
        print(f"✅ Статистика клиентов получена: {stats}")
        return stats
    except Exception as e:
        print("⚠️ Ошибка при получении статистики:", repr(e))  # Добавили repr
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@app.get("/api/clients/{client_id}")
async def get_client_api(client_id: int, token_data: Dict = Depends(verify_token_from_cookie)):
    """API для получения клиента по ID"""
    try:
        print(f"👤 Запрос клиента {client_id} от пользователя: {token_data.get('username')}")
        client = await db.get_client_by_id(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        # Получаем заявки клиента
        requests = await db.get_client_requests(client_id)
        client['requests'] = requests

        # Получаем типы устройств
        devices = await db.get_client_device_types(client_id)
        client['device_types'] = devices

        print(f"✅ Клиент {client_id} найден: {client['full_name']}")
        return client
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка получения клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


@app.get("/api/clients/{client_id}/requests")
async def get_client_requests_api(
        client_id: int,
        limit: Optional[int] = Query(None, description="Лимит заявок"),
        token_data: Dict = Depends(verify_token_from_cookie)
):
    """API для получения заявок клиента"""
    try:
        print(f"📋 Запрос заявок клиента {client_id} от пользователя: {token_data.get('username')}")
        requests = await db.get_client_requests(client_id, limit)
        print(f"✅ Найдено {len(requests)} заявок для клиента {client_id}")
        return requests
    except Exception as e:
        print(f"❌ Ошибка получения заявок клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных")


@app.post("/api/clients")
async def create_client_api(
        client_data: dict,
        token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))
):
    """API для создания нового клиента"""
    try:
        print(f"➕ Создание клиента пользователем: {token_data.get('username')}")
        print(f"📝 Данные клиента: {client_data}")

        # Валидация данных
        if not client_data.get('full_name') or len(client_data['full_name'].strip()) < 2:
            raise HTTPException(status_code=400, detail="Имя клиента должно содержать минимум 2 символа")

        if not client_data.get('phone') or len(client_data['phone'].strip()) < 10:
            raise HTTPException(status_code=400, detail="Телефон должен содержать минимум 10 символов")

        client_id = await db.create_client(
            full_name=client_data['full_name'].strip(),
            phone=client_data['phone'].strip(),
            email=client_data.get('email', '').strip() or None,
            address=client_data.get('address', '').strip() or None
        )

        # Обновляем дополнительные поля если есть
        if client_data.get('is_vip') or client_data.get('notes'):
            update_data = {}
            if client_data.get('is_vip'):
                update_data['is_vip'] = bool(client_data['is_vip'])
            if client_data.get('notes'):
                update_data['notes'] = client_data['notes'].strip()

            if update_data:
                await db.update_client(client_id, update_data)

        print(f"✅ Клиент создан с ID: {client_id}")
        return {"id": client_id, "message": "Клиент создан успешно"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка создания клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания клиента")


@app.put("/api/clients/{client_id}")
async def update_client_api(
        client_id: int,
        client_data: dict,
        token_data: Dict = Depends(verify_token_from_cookie)
):
    """API для обновления информации о клиенте"""
    try:
        print(f"🔄 Обновление клиента {client_id} пользователем: {token_data.get('username')}")
        print(f"📝 Данные для обновления: {client_data}")

        # Проверяем существование клиента
        existing_client = await db.get_client_by_id(client_id)
        if not existing_client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        # Подготавливаем данные для обновления
        update_data = {}
        for field, value in client_data.items():
            if value is not None and str(value).strip():
                if field in ['full_name', 'phone', 'email', 'address', 'notes']:
                    update_data[field] = str(value).strip()
                elif field == 'is_vip':
                    update_data[field] = bool(value)

        if not update_data:
            return {"message": "Нет данных для обновления"}

        success = await db.update_client(client_id, update_data)
        if not success:
            raise HTTPException(status_code=400, detail="Ошибка обновления клиента")

        print(f"✅ Клиент {client_id} обновлен")
        return {"message": "Клиент обновлен успешно"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка обновления клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления клиента")


@app.delete("/api/clients/{client_id}")
async def delete_client_api(
        client_id: int,
        token_data: Dict = Depends(require_role_cookie(["admin", "director"]))
):
    """API для удаления клиента"""
    try:
        print(f"🗑️ Удаление клиента {client_id} пользователем: {token_data.get('username')}")

        # Проверяем существование клиента
        existing_client = await db.get_client_by_id(client_id)
        if not existing_client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        success = await db.delete_client(client_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Невозможно удалить клиента с активными заявками"
            )

        print(f"✅ Клиент {client_id} удален")
        return {"message": "Клиент удален успешно"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка удаления клиента: {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления клиента")

@app.put("/dashboard/api/requests/{request_id}/status")
async def update_request_status_api(request_id: str, status_data: dict, token_data: Dict = Depends(verify_token_from_cookie)):
    try:
        print(f"🔄 Обновление статуса заявки {request_id} пользователем {token_data.get('username')}")

        # Обновляем статус
        success = await db.update_request_status(
            request_id=request_id,
            new_status=status_data["status"],
            user_id=int(token_data["sub"]),
            comment=status_data.get("comment")
        )

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # 🆕 Обновляем описание проблемы, если передано
        if "problem_description" in status_data and status_data["problem_description"]:
            await db.update_problem_description(request_id, status_data["problem_description"])

        return {"message": "Статус и описание проблемы обновлены"}

    except Exception as e:
        print(f"❌ Ошибка обновления статуса: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


@app.post("/dashboard/api/requests/{request_id}/archive")
async def archive_request_api(request_id: str, token_data: Dict = Depends(require_role_cookie(["admin", "director", "manager"]))):
    try:
        print(f"💄 Архивирование заявки {request_id} пользователем {token_data.get('username')}")
        success = await db.archive_request(request_id)
        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        return {"message": "Заявка архивирована"}
    except Exception as e:
        print(f"❌ Ошибка архивирования: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")

app.include_router(dashboard.router)

@app.get("/dashboard/api/stats/detailed")
async def get_detailed_stats(token_data: Dict = Depends(verify_token_from_cookie)):
    """Детальная статистика для главной страницы"""
    try:
        print(f"📊 Запрос детальной статистики от пользователя: {token_data.get('username')}")
        stats = await db.get_detailed_statistics()
        return stats
    except Exception as e:
        print(f"❌ Ошибка получения детальной статистики: {e}")
        return {
            'total_requests': 0,
            'active_requests': 0,
            'completed_this_month': 0,
            'completed_last_month': 0,
            'growth_percentage': 0,
            'avg_cost': 0,
            'avg_repair_time': 0,
            'status_stats': [],
            'priority_stats': [],
            'top_masters': [],
            'monthly_revenue': 0
        }

@app.get("/dashboard/api/charts/weekly")
async def get_weekly_chart(token_data: Dict = Depends(verify_token_from_cookie)):
    """Данные для графика за неделю"""
    try:
        chart_data = await db.get_weekly_chart_data()
        return chart_data
    except Exception as e:
        print(f"❌ Ошибка получения данных графика: {e}")
        return {
            'labels': [],
            'requests': [],
            'completed': []
        }

@app.get("/dashboard/api/charts/monthly")
async def get_monthly_chart(token_data: Dict = Depends(verify_token_from_cookie)):
    """Данные для графика за месяц"""
    try:
        chart_data = await db.get_monthly_chart_data()
        return chart_data
    except Exception as e:
        print(f"❌ Ошибка получения месячных данных: {e}")
        return {
            'labels': [],
            'requests': [],
            'completed': []
        }

@app.get("/dashboard/api/stats/devices")
async def get_device_stats(token_data: Dict = Depends(verify_token_from_cookie)):
    """Статистика по типам устройств"""
    try:
        device_stats = await db.get_device_type_stats()
        return device_stats
    except Exception as e:
        print(f"❌ Ошибка получения статистики устройств: {e}")
        return []

@app.get("/dashboard/api/stats/masters")
async def get_masters_performance(token_data: Dict = Depends(verify_token_from_cookie)):
    """Производительность мастеров"""
    try:
        masters_data = await db.get_masters_dashboard()
        return masters_data
    except Exception as e:
        print(f"❌ Ошибка получения данных мастеров: {e}")
        return []

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    clear_auth_cookie(response)
    return response

@app.get("/api")
async def api_root():
    return {
        "message": "ROCKET PC Service Center API",
        "version": settings.APP_VERSION,
        "status": "online"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if db.pool else "disconnected"
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/auth/login", status_code=302)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})
    html_content = """..."""  # unchanged for brevity
    return HTMLResponse(content=html_content, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    print(f"💥 Внутренняя ошибка сервера: {exc}")
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    html_content = """..."""  # unchanged for brevity
    return HTMLResponse(content=html_content, status_code=500)


@app.get("/dashboard/api/requests/{request_id}/full")
async def get_request_full_api(request_id: str, token_data: Dict = Depends(verify_token_from_cookie)):
    """API для получения полной информации о заявке"""
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


@app.put("/dashboard/api/requests/{request_id}/full")
async def update_request_full_api(request_id: str, update_data: dict,
                                  token_data: Dict = Depends(verify_token_from_cookie)):
    """API для полного обновления заявки"""
    from datetime import datetime, date

    try:
        print(f"🔄 Полное обновление заявки {request_id} пользователем {token_data.get('username')}")
        print(f"📝 Данные для обновления: {update_data}")

        # Проверяем статус если он указан
        if 'status' in update_data and update_data['status']:
            valid_statuses = [
                'Принята', 'Диагностика', 'Ожидание запчастей',
                'В ремонте', 'Тестирование', 'Готова к выдаче', 'Выдана'
            ]
            if update_data['status'] not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недопустимый статус. Доступные: {', '.join(valid_statuses)}"
                )

        # Проверяем приоритет если он указан
        if 'priority' in update_data and update_data['priority']:
            valid_priorities = ['Низкая', 'Обычная', 'Высокая', 'Критическая']
            if update_data['priority'] not in valid_priorities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недопустимый приоритет. Доступные: {', '.join(valid_priorities)}"
                )

        # Очищаем пустые значения и обрабатываем типы данных
        clean_data = {}
        for key, value in update_data.items():
            if value is not None and value != '':
                # Преобразуем строковые числа в числа
                if key in ['estimated_cost', 'final_cost', 'repair_duration_hours'] and isinstance(value, str):
                    try:
                        clean_data[key] = float(value) if value else None
                    except ValueError:
                        continue
                elif key == 'warranty_period' and isinstance(value, str):
                    try:
                        clean_data[key] = int(value) if value else None
                    except ValueError:
                        continue
                # 🆕 Специальная обработка для даты estimated_completion
                elif key == 'estimated_completion' and isinstance(value, str):
                    try:
                        # Проверяем, что дата в правильном формате YYYY-MM-DD
                        datetime.strptime(value, '%Y-%m-%d')
                        clean_data[key] = value  # Оставляем как строку, обработка в БД
                    except ValueError:
                        print(f"❌ Неправильный формат даты: {value}")
                        continue
                else:
                    clean_data[key] = value

        print(f"🧹 Очищенные данные: {clean_data}")

        # Обновляем заявку
        success = await db.update_repair_request_full(
            request_id=request_id,
            update_data=clean_data,
            user_id=int(token_data["sub"])
        )

        if not success:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        return {
            "message": "Заявка успешно обновлена",
            "updated_fields": list(clean_data.keys())
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка обновления заявки: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Ошибка обновления заявки")


@app.put("/dashboard/api/requests/{request_id}/client")
async def update_request_client_api(request_id: str, client_data: dict,
                                    token_data: Dict = Depends(verify_token_from_cookie)):
    """API для обновления информации о клиенте"""
    try:
        print(f"👤 Обновление клиента для заявки {request_id}")
        print(f"📝 Данные клиента: {client_data}")

        # Получаем заявку чтобы найти клиента
        request_info = await db.get_repair_request(request_id)
        if not request_info:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # Подготавливаем данные клиента для обновления
        client_update = {}
        for field, value in client_data.items():
            if value is not None and value != '':
                client_update[field] = value

        if not client_update:
            return {"message": "Нет данных для обновления"}

        # Обновляем информацию о клиенте
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


@app.get("/dashboard/api/requests/{request_id}/history")
async def get_request_history_api(request_id: str, token_data: Dict = Depends(verify_token_from_cookie)):
    """API для получения истории изменений заявки"""
    try:
        history = await db.get_status_history(request_id)
        return history
    except Exception as e:
        print(f"❌ Ошибка получения истории: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
