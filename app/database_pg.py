# app/database_pg.py
import asyncpg
from typing import List, Dict, Optional
import os
from datetime import datetime
import hashlib
import secrets


class PostgreSQLDatabase:
    def __init__(self):
        self.pool = None
        self.DATABASE_URL = os.getenv("DATABASE_URL",
                                      "postgresql://postgres.ymombwsrvuzuaalctmfm:BJpbYaLB1mBKAHgn@aws-0-eu-west-2.pooler.supabase.com:5432/postgres")

    def hash_password(self, password: str) -> str:
        """Простое хеширование пароля"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex() + ':' + salt

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверка пароля"""
        try:
            if ':' not in hashed_password:
                # Простое сравнение для обратной совместимости
                return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

            hash_part, salt = hashed_password.rsplit(':', 1)
            password_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000)
            return password_hash.hex() == hash_part
        except Exception as e:
            print(f"Ошибка проверки пароля: {e}")
            return False

    async def connect(self):
        """Создание пула соединений с БД"""
        try:
            self.pool = await asyncpg.create_pool(self.DATABASE_URL)
            await self.create_tables()
            print("✅ Успешно подключились к PostgreSQL")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            raise

    async def disconnect(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        """Создание таблиц в БД"""
        async with self.pool.acquire() as conn:
            # Таблица пользователей (сотрудников)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    password_plain VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('director', 'manager', 'master', 'admin')),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')

            # Таблица клиентов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    email VARCHAR(100),
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            ''')

            # Таблица заявок на ремонт
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS repair_requests (
                    id SERIAL PRIMARY KEY,
                    request_id VARCHAR(20) UNIQUE NOT NULL,
                    client_id INTEGER REFERENCES clients(id),
                    device_type VARCHAR(50) NOT NULL,
                    brand VARCHAR(50),
                    model VARCHAR(100),
                    serial_number VARCHAR(100),
                    problem_description TEXT NOT NULL,
                    status VARCHAR(30) DEFAULT 'Принята' CHECK (status IN (
                        'Принята', 'Диагностика', 'Ожидание запчастей', 
                        'В ремонте', 'Тестирование', 'Готова к выдаче', 'Выдана'
                    )),
                    priority VARCHAR(20) DEFAULT 'Обычная' CHECK (priority IN ('Низкая', 'Обычная', 'Высокая', 'Критическая')),
                    estimated_cost DECIMAL(10, 2),
                    final_cost DECIMAL(10, 2),
                    estimated_completion DATE,
                    actual_completion DATE,
                    assigned_master_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_archived BOOLEAN DEFAULT FALSE,
                    warranty_period INTEGER DEFAULT 30,
                    notes TEXT
                )
            ''')

            # Таблица статусов заявок (история изменений)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS status_history (
                    id SERIAL PRIMARY KEY,
                    request_id INTEGER REFERENCES repair_requests(id),
                    old_status VARCHAR(30),
                    new_status VARCHAR(30) NOT NULL,
                    changed_by INTEGER REFERENCES users(id),
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    comment TEXT
                )
            ''')

            # Создание индексов
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_status ON repair_requests(status)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_created_at ON repair_requests(created_at)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_client_id ON repair_requests(client_id)')

            # Создание администратора по умолчанию
            await self.create_default_admin()

    async def create_default_admin(self):
        """Создание администратора по умолчанию"""
        async with self.pool.acquire() as conn:
            try:
                # Проверяем, есть ли уже пользователи
                users_count = await conn.fetchval('SELECT COUNT(*) FROM users')
                if users_count == 0:
                    default_password = "admin123"
                    password_hash = self.hash_password(default_password)

                    await conn.execute('''
                        INSERT INTO users (username, email, password_hash, password_plain, full_name, role)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    ''', 'admin', 'admin@rocketpc.ru', password_hash, default_password, 'Администратор', 'admin')

                    print(f"✅ Создан администратор по умолчанию: admin / {default_password}")
            except Exception as e:
                print(f"Ошибка создания админа: {e}")

    async def create_user(self, username: str, email: str, password: str, full_name: str, role: str) -> int:
        """Создание нового пользователя"""
        password_hash = self.hash_password(password)

        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval('''
                INSERT INTO users (username, email, password_hash, password_plain, full_name, role)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            ''', username, email, password_hash, password, full_name, role)

            return user_id

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Аутентификация пользователя"""
        async with self.pool.acquire() as conn:
            try:
                user = await conn.fetchrow('''
                    SELECT id, username, email, password_hash, full_name, role, is_active
                    FROM users WHERE username = $1 AND is_active = TRUE
                ''', username)

                if user and self.verify_password(password, user['password_hash']):
                    # Обновляем время последнего входа
                    await conn.execute('''
                        UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1
                    ''', user['id'])

                    return dict(user)
                return None
            except Exception as e:
                print(f"Ошибка аутентификации: {e}")
                return None

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow('''
                SELECT id, username, email, full_name, role, is_active, created_at, last_login
                FROM users WHERE id = $1
            ''', user_id)

            return dict(user) if user else None

    async def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей"""
        async with self.pool.acquire() as conn:
            users = await conn.fetch('''
                SELECT id, username, email, password_plain, full_name, role, is_active, created_at, last_login
                FROM users ORDER BY created_at DESC
            ''')

            return [dict(user) for user in users]

    async def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Обновление пароля пользователя"""
        password_hash = self.hash_password(new_password)

        async with self.pool.acquire() as conn:
            result = await conn.execute('''
                UPDATE users SET password_hash = $1, password_plain = $2 
                WHERE id = $3
            ''', password_hash, new_password, user_id)

            return result == 'UPDATE 1'

    # Методы для работы с клиентами
    async def create_client(self, full_name: str, phone: str, email: str = None, address: str = None) -> int:
        """Создание нового клиента"""
        async with self.pool.acquire() as conn:
            client_id = await conn.fetchval('''
                INSERT INTO clients (full_name, phone, email, address)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', full_name, phone, email, address)

            return client_id

    async def get_or_create_client(self, full_name: str, phone: str, email: str = None) -> int:
        """Получение или создание клиента"""
        async with self.pool.acquire() as conn:
            # Пытаемся найти существующего клиента по телефону
            client_id = await conn.fetchval('''
                SELECT id FROM clients WHERE phone = $1
            ''', phone)

            if client_id:
                return client_id

            # Создаем нового клиента
            client_id = await conn.fetchval('''
                INSERT INTO clients (full_name, phone, email)
                VALUES ($1, $2, $3)
                RETURNING id
            ''', full_name, phone, email)

            return client_id

    # Методы для работы с заявками
    async def create_repair_request(self, client_data: Dict, device_data: Dict) -> str:
        """Создание новой заявки на ремонт"""
        async with self.pool.acquire() as conn:
            # Создаем или получаем клиента
            client_id = await self.get_or_create_client(
                client_data['full_name'],
                client_data['phone'],
                client_data.get('email')
            )

            # Генерируем ID заявки
            request_id = await self.generate_request_id()

            # Создаем заявку
            await conn.execute('''
                INSERT INTO repair_requests (
                    request_id, client_id, device_type, brand, model, 
                    problem_description, priority
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', request_id, client_id, device_data['device_type'],
                               device_data.get('brand'), device_data.get('model'),
                               device_data['problem_description'], device_data.get('priority', 'Обычная'))

            return request_id

    async def generate_request_id(self) -> str:
        """Генерация уникального ID заявки"""
        async with self.pool.acquire() as conn:
            while True:
                request_id = f"RQ{secrets.token_hex(3).upper()}"
                exists = await conn.fetchval('''
                    SELECT 1 FROM repair_requests WHERE request_id = $1
                ''', request_id)

                if not exists:
                    return request_id

    async def get_repair_request(self, request_id: str) -> Optional[Dict]:
        """Получение заявки по ID"""
        async with self.pool.acquire() as conn:
            request = await conn.fetchrow('''
                SELECT rr.*, c.full_name as client_name, c.phone as client_phone, c.email as client_email,
                       u.full_name as master_name
                FROM repair_requests rr
                LEFT JOIN clients c ON rr.client_id = c.id
                LEFT JOIN users u ON rr.assigned_master_id = u.id
                WHERE rr.request_id = $1 AND rr.is_archived = FALSE
            ''', request_id)

            return dict(request) if request else None

    async def get_all_repair_requests(self, include_archived: bool = False) -> List[Dict]:
        """Получение всех заявок"""
        async with self.pool.acquire() as conn:
            where_clause = "" if include_archived else "WHERE rr.is_archived = FALSE"

            requests = await conn.fetch(f'''
                SELECT rr.*, c.full_name as client_name, c.phone as client_phone,
                       u.full_name as master_name
                FROM repair_requests rr
                LEFT JOIN clients c ON rr.client_id = c.id
                LEFT JOIN users u ON rr.assigned_master_id = u.id
                {where_clause}
                ORDER BY rr.created_at DESC
            ''')

            return [dict(request) for request in requests]

    async def update_request_status(self, request_id: str, new_status: str, user_id: int, comment: str = None) -> bool:
        """Обновление статуса заявки"""
        async with self.pool.acquire() as conn:
            # Получаем текущий статус
            current_status = await conn.fetchval('''
                SELECT status FROM repair_requests WHERE request_id = $1
            ''', request_id)

            if not current_status:
                return False

            # Обновляем статус
            await conn.execute('''
                UPDATE repair_requests 
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE request_id = $2
            ''', new_status, request_id)

            # Добавляем запись в историю
            await conn.execute('''
                INSERT INTO status_history (request_id, old_status, new_status, changed_by, comment)
                VALUES (
                    (SELECT id FROM repair_requests WHERE request_id = $1),
                    $2, $3, $4, $5
                )
            ''', request_id, current_status, new_status, user_id, comment)

            return True

    async def archive_request(self, request_id: str) -> bool:
        """Архивирование заявки"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
                UPDATE repair_requests 
                SET is_archived = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE request_id = $1
            ''', request_id)

            return result == 'UPDATE 1'

    # Методы для статистики
    async def get_statistics(self) -> Dict:
        """Получение статистики по заявкам"""
        async with self.pool.acquire() as conn:
            # Общее количество заявок
            total_requests = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests WHERE is_archived = FALSE
            ''')

            # Статистика по статусам
            status_stats = await conn.fetch('''
                SELECT status, COUNT(*) as count
                FROM repair_requests 
                WHERE is_archived = FALSE
                GROUP BY status
                ORDER BY count DESC
            ''')

            return {
                'total_requests': total_requests,
                'status_stats': [dict(row) for row in status_stats]
            }


# Создание глобального экземпляра
db = PostgreSQLDatabase()