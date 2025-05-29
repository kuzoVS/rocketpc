from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def get_homepage(request: Request):
    """Главная страница"""
    # Если используем шаблоны Jinja2
    if os.path.exists("templates/index.html"):
        return templates.TemplateResponse("index.html", {"request": request})

    # Иначе возвращаем HTML напрямую (временное решение)
    return HTMLResponse(content=get_html_content())


def get_html_content():
    """Временная функция для HTML контента"""
    # Здесь можно вернуть базовый HTML или прочитать из файла
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ROCKET PC - Сервисный центр</title>
        <link rel="stylesheet" href="/static/css/styles.css">
    </head>
    <body>
        <h1>ROCKET PC Service Center</h1>
        <p>Загрузите файлы стилей и скриптов в соответствующие папки</p>
        <script src="/static/js/main.js"></script>
    </body>
    </html>
    """