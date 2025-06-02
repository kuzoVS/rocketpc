# app/middleware.py - ИСПРАВЛЕННАЯ ВЕРСИЯ для публичных эндпоинтов

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException
import re
from app.auth import verify_token, verify_token_from_cookie, decode_token_from_cookie


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Исправленная версия middleware с поддержкой публичных эндпоинтов"""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Скрываем .well-known запросы
        if path.startswith('/.well-known/'):
            return Response(status_code=404, content="Not Found")

        if not path.startswith('/static/'):
            print(f"📡 {method} {path}")

        # 🔧 ОБНОВЛЕННЫЙ список публичных путей
        public_paths = [
            '/',
            '/health',
            '/api',
            '/logout',
        ]

        # 🔧 НОВЫЕ паттерны для публичных эндпоинтов
        public_patterns = [
            r'^/static/.*',                    # Статические файлы
            r'^/auth/.*',                      # Авторизация
            r'^/api/requests/$',               # POST создание заявки (ПУБЛИЧНЫЙ)
            r'^/api/requests/[^/]+/status$',   # GET статус заявки (ПУБЛИЧНЫЙ)
        ]

        # Проверяем на точное совпадение
        is_public_exact = path in public_paths

        # Проверяем на совпадение с паттернами
        is_public_pattern = any(re.match(pattern, path) for pattern in public_patterns)

        is_public = is_public_exact or is_public_pattern

        if is_public:
            print(f"🌐 Публичный путь: {path}")
            try:
                return await call_next(request)
            except Exception as e:
                print(f"❌ Ошибка в публичном пути {path}: {e}")
                return Response(status_code=500, content="Internal Server Error")

        # Все остальные пути требуют авторизации
        print(f"🔒 Защищенный путь: {path}")

        try:
            authenticated = await self.check_cookie_auth(request)
        except Exception as e:
            print(f"❌ Ошибка проверки авторизации: {e}")
            authenticated = False

        if not authenticated:
            # HTML страницы - редирект
            if not path.startswith('/api/') and not path.startswith('/dashboard/api/'):
                print(f"🔁 Редирект на login для HTML: {path}")
                return RedirectResponse(url="/auth/login", status_code=302)
            # API - 401
            else:
                print(f"🚫 401 для API: {path}")
                return Response(status_code=401, content="Authentication required")

        print(f"✅ Доступ разрешен для: {path}")

        try:
            return await call_next(request)
        except StarletteHTTPException as e:
            # Перехватываем HTTP исключения и возвращаем корректный ответ
            print(f"⚠️ HTTP исключение: {e.status_code} - {e.detail}")
            return Response(status_code=e.status_code, content=str(e.detail))
        except Exception as e:
            # Перехватываем все остальные исключения
            print(f"❌ Неожиданная ошибка в {path}: {e}")
            import traceback
            traceback.print_exc()

            # Возвращаем разные ответы для API и HTML
            if path.startswith('/api/') or path.startswith('/dashboard/api/'):
                return Response(status_code=500, content="Internal Server Error")
            else:
                return RedirectResponse(url="/auth/login?error=server_error", status_code=302)

    async def check_cookie_auth(self, request: Request) -> bool:
        """Проверка авторизации через cookie"""
        try:
            token_data = decode_token_from_cookie(request)
            username = token_data.get('username', 'unknown')
            print(f"✅ Авторизован пользователь: {username}")
            return True
        except HTTPException:
            return False
        except Exception as e:
            print(f"❌ Ошибка авторизации: {str(e)[:100]}")
            return False