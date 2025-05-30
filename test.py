import requests
import json
from datetime import datetime

# Базовый URL вашего сервера
BASE_URL = "http://localhost:8000"


# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'


def test_create_request():
    """Тест создания заявки (открытый эндпоинт)"""
    print(f"\n{Colors.BLUE}=== Тест создания заявки ==={Colors.END}")

    # Данные для создания заявки
    request_data = {
        "client_name": f"Тестовый клиент {datetime.now().strftime('%H:%M:%S')}",
        "phone": "+7 (999) 123-45-67",
        "email": "test@example.com",
        "device_type": "Ноутбук",
        "brand": "ASUS",
        "model": "VivoBook 15",
        "problem_description": "Тестовая заявка: не включается",
        "priority": "Высокая"
    }

    try:
        response = requests.post(f"{BASE_URL}/api/requests", json=request_data)

        if response.status_code == 200:
            result = response.json()
            print(f"{Colors.GREEN}✅ Успешно создана заявка: {result['id']}{Colors.END}")
            print(f"   Сообщение: {result['message']}")
            return result['id']
        else:
            print(f"{Colors.RED}❌ Ошибка: {response.status_code}{Colors.END}")
            print(f"   {response.text}")
            return None
    except Exception as e:
        print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.END}")
        return None


def test_get_request_status(request_id):
    """Тест получения статуса заявки (открытый эндпоинт)"""
    print(f"\n{Colors.BLUE}=== Тест получения статуса заявки ==={Colors.END}")

    try:
        response = requests.get(f"{BASE_URL}/api/requests/{request_id}/status")

        if response.status_code == 200:
            result = response.json()
            print(f"{Colors.GREEN}✅ Статус получен{Colors.END}")
            print(f"   ID: {result['id']}")
            print(f"   Клиент: {result['client_name']}")
            print(f"   Устройство: {result['device_type']}")
            print(f"   Статус: {result['status']}")
        else:
            print(f"{Colors.RED}❌ Ошибка: {response.status_code}{Colors.END}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.END}")


def test_login():
    """Тест авторизации для получения токена"""
    print(f"\n{Colors.BLUE}=== Тест авторизации ==={Colors.END}")

    login_data = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)

        if response.status_code == 200:
            result = response.json()
            print(f"{Colors.GREEN}✅ Авторизация успешна{Colors.END}")
            print(f"   Пользователь: {result['user']['username']}")
            print(f"   Роль: {result['user']['role']}")
            return result['access_token']
        else:
            print(f"{Colors.RED}❌ Ошибка авторизации: {response.status_code}{Colors.END}")
            print(f"   {response.text}")
            return None
    except Exception as e:
        print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.END}")
        return None


def test_get_all_requests(token):
    """Тест получения всех заявок (требует токен)"""
    print(f"\n{Colors.BLUE}=== Тест получения всех заявок ==={Colors.END}")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BASE_URL}/dashboard/api/requests", headers=headers)

        if response.status_code == 200:
            requests_list = response.json()
            print(f"{Colors.GREEN}✅ Получено заявок: {len(requests_list)}{Colors.END}")

            # Показываем первые 3 заявки
            for i, req in enumerate(requests_list[:3]):
                print(f"   #{req['request_id']} - {req['client_name']} - {req['status']}")

            if len(requests_list) > 3:
                print(f"   ... и еще {len(requests_list) - 3} заявок")

            return requests_list[0]['request_id'] if requests_list else None
        else:
            print(f"{Colors.RED}❌ Ошибка: {response.status_code}{Colors.END}")
            print(f"   {response.text}")
            return None
    except Exception as e:
        print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.END}")
        return None


def test_update_status(token, request_id):
    """Тест обновления статуса заявки (требует токен)"""
    print(f"\n{Colors.BLUE}=== Тест обновления статуса заявки ==={Colors.END}")

    headers = {"Authorization": f"Bearer {token}"}
    status_data = {
        "status": "Диагностика",
        "comment": "Начата диагностика устройства"
    }

    try:
        response = requests.put(
            f"{BASE_URL}/dashboard/api/requests/{request_id}/status",
            json=status_data,
            headers=headers
        )

        if response.status_code == 200:
            print(f"{Colors.GREEN}✅ Статус обновлен{Colors.END}")
            print(f"   Новый статус: {status_data['status']}")
        else:
            print(f"{Colors.RED}❌ Ошибка: {response.status_code}{Colors.END}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.END}")


def test_archive_request(token, request_id):
    """Тест архивирования заявки (требует токен и роль)"""
    print(f"\n{Colors.BLUE}=== Тест архивирования заявки ==={Colors.END}")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(
            f"{BASE_URL}/dashboard/api/requests/{request_id}/archive",
            headers=headers
        )

        if response.status_code == 200:
            print(f"{Colors.GREEN}✅ Заявка архивирована{Colors.END}")
        elif response.status_code == 403:
            print(f"{Colors.YELLOW}⚠️  Недостаточно прав для архивирования{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Ошибка: {response.status_code}{Colors.END}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"{Colors.RED}❌ Ошибка подключения: {e}{Colors.END}")


def main():
    """Основная функция тестирования"""
    print(f"{Colors.YELLOW}🚀 Тестирование API ROCKET PC{Colors.END}")
    print(f"Сервер: {BASE_URL}")

    # 1. Тест создания заявки (открытый эндпоинт)
    new_request_id = test_create_request()

    # 2. Тест получения статуса заявки (открытый эндпоинт)
    if new_request_id:
        test_get_request_status(new_request_id)

    # 3. Тест авторизации
    token = test_login()

    if token:
        # 4. Тест получения всех заявок (требует токен)
        existing_request_id = test_get_all_requests(token)

        # 5. Тест обновления статуса (требует токен)
        if existing_request_id:
            test_update_status(token, existing_request_id)

        # 6. Тест архивирования (требует токен и роль)
        if new_request_id:
            test_archive_request(token, new_request_id)

    print(f"\n{Colors.YELLOW}✅ Тестирование завершено{Colors.END}")


if __name__ == "__main__":
    main()