import uuid
from typing import Dict, Optional
from app.models import RepairRequest


class Database:
    """Класс для работы с хранилищем данных"""

    def __init__(self):
        # В реальном проекте здесь будет подключение к БД
        self.requests_db: Dict[str, dict] = {}

    def generate_request_id(self) -> str:
        """Генерация уникального ID заявки"""
        return str(uuid.uuid4())[:8].upper()

    def create_request(self, request: RepairRequest) -> str:
        """Создание новой заявки"""
        request_id = self.generate_request_id()
        request.id = request_id
        self.requests_db[request_id] = request.dict()
        return request_id

    def get_request(self, request_id: str) -> Optional[dict]:
        """Получение заявки по ID"""
        return self.requests_db.get(request_id)

    def get_all_requests(self) -> list:
        """Получение всех заявок"""
        return list(self.requests_db.values())

    def update_request_status(self, request_id: str, new_status: str) -> bool:
        """Обновление статуса заявки"""
        if request_id in self.requests_db:
            self.requests_db[request_id]["status"] = new_status
            return True
        return False

    def delete_request(self, request_id: str) -> bool:
        """Удаление заявки"""
        if request_id in self.requests_db:
            del self.requests_db[request_id]
            return True
        return False


# Создаем единственный экземпляр базы данных
db = Database()