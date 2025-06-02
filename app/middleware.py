# app/middleware.py - Упрощенная версия
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re
from app.auth import verify_token, verify_token_from_cookie, decode_token_from_cookie


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Отладочная версия middleware"""

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
            return await call_next(request)

        # Все остальные пути требуют авторизации
        print(f"🔒 Защищенный путь: {path}")
        authenticated = await self.check_cookie_auth(request)

        if not authenticated:
            # HTML страницы - редирект
            if not path.startswith('/api/') and not path.startswith('/dashboard/api/'):
                print(f"🔁 Редирект на login для HTML: {path}")
                return RedirectResponse(url="/auth/login")
            # API - 401
            else:
                print(f"🚫 401 для API: {path}")
                return Response(status_code=401, content="Authentication required")

        print(f"✅ Доступ разрешен для: {path}")
        return await call_next(request)

    async def check_cookie_auth(self, request: Request) -> bool:
        """Проверка авторизации через cookie"""
        try:
            token_data = decode_token_from_cookie(request)
            username = token_data.get('username', 'unknown')
            print(f"✅ Авторизован пользователь: {username}")
            return True
        except Exception as e:
            print(f"❌ Ошибка авторизации: {str(e)[:100]}")
            return False