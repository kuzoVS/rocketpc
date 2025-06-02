#!/usr/bin/env python3
"""
Скрипт для тестирования API клиентов
Запустите после входа в систему через браузер
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_with_session():
    """Тестирование API через браузерную сессию"""

    # Создаем сессию для сохранения cookies
    session = requests.Session()

    print("🧪 Тестирование API клиентов через сессию...")

    # 1. Авторизуемся
    print("\n1. Авторизация...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }

    # Используем POST для авторизации через форму
    login_response = session.post(
        f"{BASE_URL}/auth/login",
        data=login_data,
        allow_redirects=False  # Не следуем редиректам автоматически
    )
    print(f"   Статус авторизации: {login_response.status_code}")

    # Проблема: cookie устанавливается для localhost.local, а мы работаем с localhost
    # Исправляем domain cookie вручную
    for cookie in session.cookies:
        if cookie.domain == 'localhost.local':
            cookie.domain = 'localhost'

    print(f"   Cookies после исправления: {session.cookies}")

    if login_response.status_code not in [200, 302]:
        print("❌ Ошибка авторизации")
        return

    # 2. Тестируем получение статистики клиентов
    print("\n2. Получение статистики клиентов...")
    stats_response = session.get(f"{BASE_URL}/api/clients/statistics")
    print(f"   Статус: {stats_response.status_code}")

    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"   ✅ Статистика получена: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    else:
        print(f"   ❌ Ошибка: {stats_response.text}")

    # 3. Тестируем получение всех клиентов
    print("\n3. Получение всех клиентов...")
    clients_response = session.get(f"{BASE_URL}/api/clients")
    print(f"   Статус: {clients_response.status_code}")

    if clients_response.status_code == 200:
        clients = clients_response.json()
        print(f"   ✅ Клиенты получены: {len(clients)} шт.")
        if clients:
            print(f"   Первый клиент: {clients[0]['full_name']}")
    else:
        print(f"   ❌ Ошибка: {clients_response.text}")

    # 4. Тестируем создание клиента
    print("\n4. Создание тестового клиента...")
    new_client_data = {
        "full_name": f"Тестовый Клиент {len(clients) + 1}",
        "phone": f"+7 (999) 123-45-{67 + len(clients)}",
        "email": f"test{len(clients)}@example.com",
        "is_vip": False,
        "notes": "Создан через API тест"
    }

    create_response = session.post(
        f"{BASE_URL}/api/clients",
        json=new_client_data
    )
    print(f"   Статус: {create_response.status_code}")

    if create_response.status_code == 200:
        result = create_response.json()
        print(f"   ✅ Клиент создан с ID: {result['id']}")

        # 5. Тестируем получение созданного клиента
        print(f"\n5. Получение клиента {result['id']}...")
        client_response = session.get(f"{BASE_URL}/api/clients/{result['id']}")
        print(f"   Статус: {client_response.status_code}")

        if client_response.status_code == 200:
            client = client_response.json()
            print(f"   ✅ Клиент получен: {client['full_name']}")
        else:
            print(f"   ❌ Ошибка: {client_response.text}")

    else:
        print(f"   ❌ Ошибка создания: {create_response.text}")


def test_without_auth():
    """Тестирование без авторизации (должно вернуть 401)"""
    print("\n🧪 Тестирование без авторизации...")

    response = requests.get(f"{BASE_URL}/api/clients/statistics")
    print(f"   Статус без авторизации: {response.status_code}")

    if response.status_code == 401:
        print("   ✅ Правильно возвращает 401 без авторизации")
    else:
        print(f"   ❌ Неожиданный статус: {response.status_code}")


if __name__ == "__main__":
    print("🚀 Запуск тестов API клиентов...")

    # Тест без авторизации
    test_without_auth()

    # Тест с авторизацией
    test_with_session()

    print("\n✅ Тестирование завершено!")