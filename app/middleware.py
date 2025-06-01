# app/middleware.py
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re
from app.auth import verify_token, verify_token_from_cookie, decode_token_from_cookie


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Строгий middleware для server-side проверки аутентификации"""

    def __init__(self, app):
        super().__init__(app)
        # Маршруты, которые требуют аутентификации
        self.protected_paths = [
            r'^/dashboard/api/.*',  # Только API dashboard требует токен
        ]

        # Публичные маршруты (включая HTML страницы dashboard)
        self.public_paths = [
            r'^/$',
            r'^/auth/.*',
            r'^/api/requests$',
            r'^/api/requests/.*/status$',
            r'^/static/.*',
            r'^/health$',
            r'^/api$',
            r'^/logout$',
            r'^/.well-known/.*',
            r'^/dashboard$',  # HTML страница dashboard
            r'^/dashboard/requests$',  # HTML страница
            r'^/dashboard/users$',  # HTML страница
            r'^/dashboard/statistics$',  # HTML страница
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if path.startswith('/.well-known/'):
            return Response(status_code=404, content="Not Found")

        if not path.startswith('/static/'):
            print(f"📡 {method} {path}")

        # Проверка токена
        authenticated = await self.verify_api_token(request)

        # API — только возврат 401
        if self.is_protected_path(path):
            print(f"🔒 Проверяем API эндпоинт: {path}")
            if not authenticated:
                print(f"🚫 401 - нет валидного токена для API")
                return Response(status_code=401, content="Authentication required")

        # Страницы — редирект
        if not self.is_public_path(path):
            if not authenticated:
                print(f"🔁 Неавторизованный доступ к {path} — редирект на /auth/login")
                return RedirectResponse(url="/auth/login")

        return await call_next(request)

    def is_public_path(self, path: str) -> bool:
        """Проверяет, является ли путь публичным (без авторизации)"""
        for pattern in self.public_paths:
            if re.match(pattern, path):
                return True
        return False

    def is_protected_path(self, path: str) -> bool:
        """Проверяет, является ли путь защищенным (только API)"""
        for pattern in self.protected_paths:
            if re.match(pattern, path):
                return True
        return False

    async def verify_api_token(self, request: Request) -> bool:
        try:
            token_data = decode_token_from_cookie(request)
            print(f"✅ Авторизован через cookie: {token_data['username']}")
            return True
        except Exception as e:
            print(f"❌ Ошибка проверки токена из cookie: {e}")
            return False