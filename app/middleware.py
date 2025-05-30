# app/middleware.py
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re
from app.auth import verify_token


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

        # Игнорируем Chrome DevTools запросы
        if path.startswith('/.well-known/'):
            response = Response(status_code=404)
            response.headers["content-type"] = "text/plain"
            return response

        # Логируем важные запросы
        if not path.startswith('/static/'):
            print(f"📡 {method} {path}")

        # Проверяем только API эндпоинты dashboard
        if self.is_protected_path(path):
            print(f"🔒 Проверяем API эндпоинт: {path}")

            # Строго проверяем токен для API
            if not await self.verify_api_token(request):
                print(f"🚫 401 - нет валидного токена для API")
                raise HTTPException(status_code=401, detail="Authentication required")

        response = await call_next(request)
        return response

    def is_protected_path(self, path: str) -> bool:
        """Проверяет, является ли путь защищенным (только API)"""
        for pattern in self.protected_paths:
            if re.match(pattern, path):
                return True
        return False

    async def verify_api_token(self, request: Request) -> bool:
        """Строгая проверка токена для API запросов"""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return False

            token = auth_header.split(" ")[1]

            class MockCredentials:
                def __init__(self, token):
                    self.credentials = token

            credentials = MockCredentials(token)
            verify_token(credentials)
            return True

        except Exception as e:
            print(f"❌ Ошибка проверки API токена: {e}")
            return False