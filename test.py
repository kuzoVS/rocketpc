import requests
import json


# Тест создания заявки с детальным выводом
def debug_create_request():
    url = "http://localhost:8000/api/requests"

    # Минимальные данные для теста
    test_data = {
        "client_name": "Тест Клиент",
        "phone": "+79991234567",
        "email": "test@test.com",
        "device_type": "Ноутбук",
        "problem_description": "Тестовое описание проблемы для отладки"
    }

    print("🔍 Отправляем запрос на:", url)
    print("📝 Данные запроса:", json.dumps(test_data, indent=2, ensure_ascii=False))

    try:
        response = requests.post(url, json=test_data)

        print(f"\n📡 Статус ответа: {response.status_code}")
        print(f"📄 Заголовки ответа: {dict(response.headers)}")

        # Пытаемся получить текст ответа
        response_text = response.text
        print(f"\n📋 Текст ответа:\n{response_text}")

        # Пытаемся распарсить JSON
        try:
            response_json = response.json()
            print(f"\n✅ JSON ответ:\n{json.dumps(response_json, indent=2, ensure_ascii=False)}")
        except:
            print("\n❌ Не удалось распарсить JSON")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


if __name__ == "__main__":
    debug_create_request()