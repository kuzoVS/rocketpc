# app/middleware.py - Исправленная версия для предотвращения TaskGroup ошибок
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException
import re
from app.auth import verify_token, verify_token_from_cookie, decode_token_from_cookie


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Исправленная версия middleware для предотвращения TaskGroup ошибок"""

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

        # Список путей, которые НЕ требуют авторизации
        public_paths = [
            '/',
            '/health',
            '/api',
            '/logout',
            '/api/requests',  # POST создание заявки
        ]

        # Проверяем на точное совпадение или начало пути
        is_public = (
                path in public_paths or
                path.startswith('/static/') or
                path.startswith('/auth/') or
                (path.startswith('/api/requests/') and path.endswith('/status'))
        )

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