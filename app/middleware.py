# app/middleware.py
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re
from app.auth import verify_token
from fastapi.security import HTTPAuthorizationCredentials


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки аутентификации на защищенных маршрутах"""

    def __init__(self, app):
        super().__init__(app)
        # Маршруты, которые требуют аутентификации
        self.protected_paths = [
            r'^/dashboard.*',  # Все пути, начинающиеся с /dashboard
        ]

        # Маршруты, которые не требуют аутентификации
        self.public_paths = [
            r'^/$',  # Главная страница
            r'^/auth/.*',  # Все пути аутентификации
            r'^/api/requests$',  # Публичное создание заявок
            r'^/api/requests/.*/status$',  # Публичная проверка статуса
            r'^/static/.*',  # Статические файлы
            r'^/health$',  # Healthcheck
            r'^/api$',  # API root
            r'^/logout$',  # Выход из системы
        ]

    async def dispatch(self, request: Request, call_next):
        # Проверяем, является ли путь защищенным
        if self.is_protected_path(request.url.path):
            # Для HTML страниц проверяем через JavaScript (клиентская проверка)
            if self.is_html_request(request):
                # Пропускаем HTML страницы - проверка будет на клиенте
                response = await call_next(request)
                return response
            else:
                # Для API запросов проверяем токен на сервере
                if not await self.verify_token_from_request(request):
                    raise HTTPException(status_code=401, detail="Authentication required")

        response = await call_next(request)
        return response

    def is_protected_path(self, path: str) -> bool:
        """Проверяет, является ли путь защищенным"""
        # Сначала проверяем публичные пути
        for pattern in self.public_paths:
            if re.match(pattern, path):
                return False

        # Затем проверяем защищенные пути
        for pattern in self.protected_paths:
            if re.match(pattern, path):
                return True

        return False

    def is_html_request(self, request: Request) -> bool:
        """Определяет, является ли запрос запросом HTML страницы"""
        accept_header = request.headers.get("accept", "")
        return "text/html" in accept_header or request.url.path.endswith(".html")

    async def verify_token_from_request(self, request: Request) -> bool:
        """Проверяет токен из заголовка Authorization"""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return False

            token = auth_header.split(" ")[1]

            # Создаем объект для verify_token
            class MockCredentials:
                def __init__(self, token):
                    self.credentials = token

            credentials = MockCredentials(token)
            verify_token(credentials)
            return True
        except:
            return False