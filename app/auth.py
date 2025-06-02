from fastapi import HTTPException, Depends, status, Request, Form, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from app.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена с timezone-aware временем"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Проверка JWT из Authorization заголовка (для API)"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")

def verify_token_from_cookie(request: Request) -> Dict:
    """Проверка JWT токена из cookie (для HTML)"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("🧾 PAYLOAD из cookie:", payload)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")



def require_role(required_roles: list):
    """Проверка ролей для API через Authorization"""
    def role_checker(token_data: Dict = Depends(verify_token)):
        print("🛂 Проверка роли:", token_data.get("role"))
        user_role = token_data.get("role")
        if user_role not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав доступа")
        return token_data
    return role_checker

def require_role_cookie(required_roles: list):
    """Проверка ролей через cookie (для HTML страниц)"""
    def role_checker(token_data: Dict = Depends(verify_token_from_cookie)):
        print("🛂 Проверка роли:", token_data.get("role"))
        user_role = token_data.get("role")
        if user_role not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав доступа")
        return token_data
    return role_checker

def set_auth_cookie(response: Response, token: str):
    """Установка JWT токена в cookie"""
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=False,  # Поставить True в проде для HTTPS
        samesite="lax",
        domain=None,  # Убираем domain, чтобы работало на localhost
        path="/"      # Устанавливаем для всего сайта
    )

def decode_token_from_cookie(request: Request) -> dict:
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="No token in cookies")
    return verify_token_from_str(token)

def verify_token_from_str(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def clear_auth_cookie(response: Response):
    """Удаление токена из cookie при logout"""
    response.delete_cookie("session_token")
