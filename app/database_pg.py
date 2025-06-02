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

    def normalize_phone(self, phone: str) -> str:
        """Нормализация телефона: удаляет все символы кроме цифр и приводит к формату 7XXXXXXXXXX"""
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 11 and digits.startswith('8'):
            digits = '7' + digits[1:]
        elif len(digits) == 10:
            digits = '7' + digits
        return digits

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
        """Создание таблиц в БД с улучшенной структурой"""
        async with self.pool.acquire() as conn:
            # Таблица пользователей (сотрудников) с расширенными полями
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    password_plain VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('director', 'manager', 'master', 'admin')),
                    phone VARCHAR(20),
                    specialization VARCHAR(100), -- Специализация для мастеров
                    hire_date DATE DEFAULT CURRENT_DATE,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_available BOOLEAN DEFAULT TRUE, -- Доступен ли мастер для новых заявок
                    max_concurrent_repairs INTEGER DEFAULT 5, -- Макс. количество одновременных ремонтов
                    current_repairs_count INTEGER DEFAULT 0, -- Текущее количество активных ремонтов
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    notes TEXT
                )
            ''')

            # Таблица навыков мастеров
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS master_skills (
                    id SERIAL PRIMARY KEY,
                    master_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    skill_name VARCHAR(100) NOT NULL,
                    skill_level INTEGER CHECK (skill_level >= 1 AND skill_level <= 5),
                    UNIQUE(master_id, skill_name)
                )
            ''')

            # Таблица клиентов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    phone VARCHAR(20) NOT NULL UNIQUE,
                    email VARCHAR(100),
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_repairs INTEGER DEFAULT 0,
                    is_vip BOOLEAN DEFAULT FALSE,
                    notes TEXT
                )
            ''')

            # Обновленная таблица заявок на ремонт
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
                    actual_completion DATE, -- Автоматически при статусе Готова к выдаче
                    assigned_master_id INTEGER REFERENCES users(id),
                    assigned_by_id INTEGER REFERENCES users(id), -- Кто назначил мастера
                    assigned_at TIMESTAMP, -- Когда был назначен мастер
                    created_by_id INTEGER REFERENCES users(id), -- Кто создал заявку
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_archived BOOLEAN DEFAULT FALSE,
                    warranty_period INTEGER DEFAULT 30,
                    repair_duration_hours DECIMAL(5, 2), -- Время ремонта в часах
                    parts_used TEXT, -- Использованные запчасти
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

            # Таблица назначений мастеров (история)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS assignment_history (
                    id SERIAL PRIMARY KEY,
                    request_id INTEGER REFERENCES repair_requests(id),
                    master_id INTEGER REFERENCES users(id),
                    assigned_by INTEGER REFERENCES users(id),
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    unassigned_at TIMESTAMP,
                    reason VARCHAR(255)
                )
            ''')

            # Таблица рабочего времени мастеров
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS master_schedule (
                    id SERIAL PRIMARY KEY,
                    master_id INTEGER REFERENCES users(id),
                    day_of_week INTEGER CHECK (day_of_week >= 0 AND day_of_week <= 6),
                    start_time TIME,
                    end_time TIME,
                    is_working_day BOOLEAN DEFAULT TRUE,
                    UNIQUE(master_id, day_of_week)
                )
            ''')

            # Создание индексов
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_status ON repair_requests(status)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_created_at ON repair_requests(created_at)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_client_id ON repair_requests(client_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_requests_master_id ON repair_requests(assigned_master_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_master_skills_master_id ON master_skills(master_id)')

            # Создание администратора и тестовых пользователей
            await self.create_default_users()

    async def create_default_users(self):
        """Создание пользователей по умолчанию"""
        async with self.pool.acquire() as conn:
            try:
                # Проверяем, есть ли уже пользователи
                users_count = await conn.fetchval('SELECT COUNT(*) FROM users')
                if users_count == 0:
                    # Администратор
                    admin_password = "admin123"
                    admin_hash = self.hash_password(admin_password)
                    admin_id = await conn.fetchval('''
                        INSERT INTO users (username, email, password_hash, password_plain, full_name, role, phone)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id
                    ''', 'admin', 'admin@rocketpc.ru', admin_hash, admin_password, 'Администратор', 'admin', '+7 (999) 000-00-01')

                    # Директор
                    director_password = "director123"
                    director_hash = self.hash_password(director_password)
                    await conn.execute('''
                        INSERT INTO users (username, email, password_hash, password_plain, full_name, role, phone)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ''', 'director', 'director@rocketpc.ru', director_hash, director_password, 'Иван Директоров', 'director', '+7 (999) 000-00-02')

                    # Менеджер
                    manager_password = "manager123"
                    manager_hash = self.hash_password(manager_password)
                    await conn.execute('''
                        INSERT INTO users (username, email, password_hash, password_plain, full_name, role, phone)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ''', 'manager', 'manager@rocketpc.ru', manager_hash, manager_password, 'Анна Менеджерова', 'manager', '+7 (999) 000-00-03')

                    # Мастера
                    masters = [
                        ('master1', 'master123', 'Алексей Мастеров', 'Ноутбуки и ПК', '+7 (999) 000-00-04'),
                        ('master2', 'master123', 'Максим Ремонтов', 'Материнские платы', '+7 (999) 000-00-05'),
                        ('master3', 'master123', 'Дмитрий Сервисов', 'Блоки питания', '+7 (999) 000-00-06')
                    ]

                    for username, password, full_name, spec, phone in masters:
                        password_hash = self.hash_password(password)
                        master_id = await conn.fetchval('''
                            INSERT INTO users (username, email, password_hash, password_plain, full_name, role, phone, specialization)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            RETURNING id
                        ''', username, f'{username}@rocketpc.ru', password_hash, password, full_name, 'master', phone, spec)

                        # Добавляем навыки мастерам
                        if 'Ноутбуки' in spec:
                            skills = [('Ремонт ноутбуков', 5), ('Диагностика', 4), ('Замена матриц', 4)]
                        elif 'Материнские' in spec:
                            skills = [('Ремонт материнских плат', 5), ('Пайка BGA', 4), ('Диагностика', 3)]
                        else:
                            skills = [('Ремонт БП', 5), ('Электроника', 4), ('Диагностика', 3)]

                        for skill_name, level in skills:
                            await conn.execute('''
                                INSERT INTO master_skills (master_id, skill_name, skill_level)
                                VALUES ($1, $2, $3)
                            ''', master_id, skill_name, level)

                    print("✅ Созданы пользователи по умолчанию:")
                    print("   admin / admin123")
                    print("   director / director123")
                    print("   manager / manager123")
                    print("   master1 / master123")
                    print("   master2 / master123")
                    print("   master3 / master123")

            except Exception as e:
                print(f"Ошибка создания пользователей: {e}")

    # Добавьте эти методы в app/database_pg.py в класс PostgreSQLDatabase
    async def get_all_clients(self, include_stats: bool = True) -> List[Dict]:
        """Получение всех клиентов с полной статистикой"""
        async with self.pool.acquire() as conn:
            if include_stats:
                clients = await conn.fetch('''
                    SELECT 
                        c.id,
                        c.full_name,
                        c.phone,
                        c.email,
                        c.address,
                        c.created_at,
                        c.total_repairs,
                        c.is_vip,
                        c.notes,
                        COUNT(rr.id) FILTER (WHERE rr.is_archived = FALSE) as total_requests,
                        COUNT(rr.id) FILTER (WHERE rr.status != 'Выдана' AND rr.is_archived = FALSE) as active_requests,
                        COUNT(rr.id) FILTER (WHERE rr.status = 'Выдана' AND rr.is_archived = FALSE) as completed_requests,
                        SUM(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost ELSE 0 END) as total_spent,
                        MAX(rr.created_at) as last_request_date,
                        AVG(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost END) as avg_cost
                    FROM clients c
                    LEFT JOIN repair_requests rr ON c.id = rr.client_id
                    GROUP BY c.id
                    ORDER BY c.created_at DESC
                ''')
            else:
                clients = await conn.fetch('''
                    SELECT id, full_name, phone, email, address, created_at, total_repairs, is_vip, notes
                    FROM clients 
                    ORDER BY created_at DESC
                ''')

            return [dict(client) for client in clients]

    async def get_client_by_id(self, client_id: int) -> Optional[Dict]:
        """Получение клиента по ID с полной статистикой"""
        async with self.pool.acquire() as conn:
            client = await conn.fetchrow('''
                SELECT 
                    c.*,
                    COUNT(rr.id) FILTER (WHERE rr.is_archived = FALSE) as total_requests,
                    COUNT(rr.id) FILTER (WHERE rr.status != 'Выдана' AND rr.is_archived = FALSE) as active_requests,
                    COUNT(rr.id) FILTER (WHERE rr.status = 'Выдана' AND rr.is_archived = FALSE) as completed_requests,
                    SUM(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost ELSE 0 END) as total_spent,
                    AVG(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost END) as avg_cost,
                    MAX(rr.created_at) as last_request_date,
                    MIN(rr.created_at) as first_request_date
                FROM clients c
                LEFT JOIN repair_requests rr ON c.id = rr.client_id
                WHERE c.id = $1
                GROUP BY c.id
            ''', client_id)

            return dict(client) if client else None

    async def get_client_requests(self, client_id: int, limit: int = None) -> List[Dict]:
        """Получение всех заявок клиента"""
        async with self.pool.acquire() as conn:
            limit_clause = f"LIMIT {limit}" if limit else ""

            requests = await conn.fetch(f'''
                SELECT 
                    rr.*,
                    u.full_name as master_name,
                    u.specialization as master_specialization
                FROM repair_requests rr
                LEFT JOIN users u ON rr.assigned_master_id = u.id
                WHERE rr.client_id = $1 AND rr.is_archived = FALSE
                ORDER BY rr.created_at DESC
                {limit_clause}
            ''', client_id)

            return [dict(request) for request in requests]

    async def search_clients(self, search_term: str) -> List[Dict]:
        """Поиск клиентов по имени, телефону или email с полной статистикой"""
        async with self.pool.acquire() as conn:
            clients = await conn.fetch('''
                SELECT 
                    c.id,
                    c.full_name,
                    c.phone,
                    c.email,
                    c.address,
                    c.created_at,
                    c.total_repairs,
                    c.is_vip,
                    c.notes,
                    COUNT(rr.id) FILTER (WHERE rr.is_archived = FALSE) as total_requests,
                    COUNT(rr.id) FILTER (WHERE rr.status != 'Выдана' AND rr.is_archived = FALSE) as active_requests,
                    COUNT(rr.id) FILTER (WHERE rr.status = 'Выдана' AND rr.is_archived = FALSE) as completed_requests
                FROM clients c
                LEFT JOIN repair_requests rr ON c.id = rr.client_id
                WHERE 
                    c.full_name ILIKE $1 OR 
                    c.phone ILIKE $1 OR 
                    c.email ILIKE $1
                GROUP BY c.id
                ORDER BY c.full_name
            ''', f'%{search_term}%')

            return [dict(client) for client in clients]


    async def update_client(self, client_id: int, client_data: dict) -> bool:
        """Обновление информации о клиенте"""
        async with self.pool.acquire() as conn:
            try:
                set_clauses = []
                values = []
                param_count = 1

                updatable_fields = {
                    'full_name': 'full_name',
                    'phone': 'phone',
                    'email': 'email',
                    'address': 'address',
                    'is_vip': 'is_vip',
                    'notes': 'notes'
                }

                for field_name, db_field in updatable_fields.items():
                    if field_name in client_data and client_data[field_name] is not None:
                        set_clauses.append(f"{db_field} = ${param_count}")
                        values.append(client_data[field_name])
                        param_count += 1

                if not set_clauses:
                    return True

                query = f'''
                    UPDATE clients 
                    SET {', '.join(set_clauses)}
                    WHERE id = ${param_count}
                '''
                values.append(client_id)

                await conn.execute(query, *values)
                return True

            except Exception as e:
                print(f"❌ Ошибка обновления клиента: {e}")
                return False

    async def delete_client(self, client_id: int) -> bool:
        """Удаление клиента (только если нет активных заявок)"""
        async with self.pool.acquire() as conn:
            try:
                # Проверяем, есть ли активные заявки
                active_requests = await conn.fetchval('''
                    SELECT COUNT(*) FROM repair_requests 
                    WHERE client_id = $1 AND status != 'Выдана' AND is_archived = FALSE
                ''', client_id)

                if active_requests > 0:
                    return False

                # Архивируем все заявки клиента
                await conn.execute('''
                    UPDATE repair_requests 
                    SET is_archived = TRUE 
                    WHERE client_id = $1
                ''', client_id)

                # Удаляем клиента
                await conn.execute('DELETE FROM clients WHERE id = $1', client_id)
                return True

            except Exception as e:
                print(f"❌ Ошибка удаления клиента: {e}")
                return False

    async def get_client_device_types(self, client_id: int) -> List[Dict]:
        """Получение типов устройств, которые ремонтировал клиент"""
        async with self.pool.acquire() as conn:
            devices = await conn.fetch('''
                SELECT 
                    device_type,
                    COUNT(*) as count,
                    MAX(created_at) as last_repair
                FROM repair_requests 
                WHERE client_id = $1 AND is_archived = FALSE
                GROUP BY device_type
                ORDER BY count DESC
            ''', client_id)

            return [dict(device) for device in devices]

    async def get_vip_clients(self) -> List[Dict]:
        """Получение VIP клиентов"""
        async with self.pool.acquire() as conn:
            clients = await conn.fetch('''
                SELECT 
                    c.*,
                    COUNT(rr.id) as total_requests,
                    SUM(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost ELSE 0 END) as total_spent
                FROM clients c
                LEFT JOIN repair_requests rr ON c.id = rr.client_id AND rr.is_archived = FALSE
                WHERE c.is_vip = TRUE
                GROUP BY c.id
                ORDER BY total_spent DESC
            ''')

            return [dict(client) for client in clients]

    async def get_client_statistics(self) -> Dict:
        """Общая статистика по клиентам"""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_clients,
                    COUNT(CASE WHEN is_vip = TRUE THEN 1 END) as vip_clients,
                    COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as new_clients_month,
                    AVG(total_repairs::float) as avg_repairs_per_client
                FROM clients
            ''')

            # Топ клиенты по тратам
            top_clients = await conn.fetch('''
                SELECT 
                    c.full_name,
                    SUM(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost ELSE 0 END) as total_spent,
                    COUNT(rr.id) as total_requests
                FROM clients c
                LEFT JOIN repair_requests rr ON c.id = rr.client_id AND rr.is_archived = FALSE
                GROUP BY c.id, c.full_name
                HAVING SUM(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost ELSE 0 END) > 0
                ORDER BY total_spent DESC
                LIMIT 5
            ''')

            return {
                'total_clients': stats['total_clients'] or 0,
                'vip_clients': stats['vip_clients'] or 0,
                'new_clients_month': stats['new_clients_month'] or 0,
                'avg_repairs_per_client': float(stats['avg_repairs_per_client'] or 0),
                'top_clients': [dict(client) for client in top_clients]
            }


    # Методы для работы с мастерами
    async def get_available_masters(self) -> List[Dict]:
        """Получение списка доступных мастеров"""
        async with self.pool.acquire() as conn:
            masters = await conn.fetch('''
                SELECT 
                    u.id, u.username, u.full_name, u.phone, u.specialization,
                    u.current_repairs_count, u.max_concurrent_repairs,
                    u.is_available,
                    COUNT(rr.id) as active_repairs
                FROM users u
                LEFT JOIN repair_requests rr ON u.id = rr.assigned_master_id 
                    AND rr.status NOT IN ('Выдана', 'Готова к выдаче')
                    AND rr.is_archived = FALSE
                WHERE u.role = 'master' AND u.is_active = TRUE
                GROUP BY u.id
                ORDER BY active_repairs ASC, u.full_name ASC
            ''')

            return [dict(master) for master in masters]

    async def get_master_skills(self, master_id: int) -> List[Dict]:
        """Получение навыков мастера"""
        async with self.pool.acquire() as conn:
            skills = await conn.fetch('''
                SELECT skill_name, skill_level
                FROM master_skills
                WHERE master_id = $1
                ORDER BY skill_level DESC
            ''', master_id)

            return [dict(skill) for skill in skills]

    async def assign_master_to_request(self, request_id: str, master_id: int, assigned_by_id: int) -> bool:
        """Назначение мастера на заявку с улучшенной историей"""
        async with self.pool.acquire() as conn:
            try:
                # Проверяем существование заявки
                request = await conn.fetchrow('''
                    SELECT id, assigned_master_id 
                    FROM repair_requests 
                    WHERE request_id = $1 AND is_archived = FALSE
                ''', request_id)

                if not request:
                    return False

                # Если был назначен другой мастер, сначала снимаем его
                if request['assigned_master_id'] and request['assigned_master_id'] != master_id:
                    await conn.execute('''
                        UPDATE assignment_history 
                        SET unassigned_at = CURRENT_TIMESTAMP,
                            reason = 'Переназначение на другого мастера'
                        WHERE request_id = $1 AND unassigned_at IS NULL
                    ''', request['id'])

                    # Обновляем счетчик у предыдущего мастера
                    await conn.execute('''
                        UPDATE users 
                        SET current_repairs_count = GREATEST(current_repairs_count - 1, 0)
                        WHERE id = $1
                    ''', request['assigned_master_id'])

                # Назначаем нового мастера
                await conn.execute('''
                    UPDATE repair_requests 
                    SET assigned_master_id = $1, 
                        assigned_by_id = $2,
                        assigned_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE request_id = $3
                ''', master_id, assigned_by_id, request_id)

                # Добавляем запись в историю назначений
                await conn.execute('''
                    INSERT INTO assignment_history (request_id, master_id, assigned_by, assigned_at)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ''', request['id'], master_id, assigned_by_id)

                # Обновляем счетчик активных ремонтов у нового мастера
                await conn.execute('''
                    UPDATE users 
                    SET current_repairs_count = (
                        SELECT COUNT(*) 
                        FROM repair_requests 
                        WHERE assigned_master_id = $1 
                            AND status NOT IN ('Выдана', 'Готова к выдаче')
                            AND is_archived = FALSE
                    )
                    WHERE id = $1
                ''', master_id)

                return True

            except Exception as e:
                print(f"Ошибка назначения мастера: {e}")
                return False

    async def unassign_master_from_request(self, request_id: str, reason: str = None) -> bool:
        """Снятие мастера с заявки с улучшенной историей"""
        async with self.pool.acquire() as conn:
            try:
                # Получаем информацию о заявке
                request = await conn.fetchrow('''
                    SELECT id, assigned_master_id 
                    FROM repair_requests 
                    WHERE request_id = $1 AND is_archived = FALSE
                ''', request_id)

                if not request or not request['assigned_master_id']:
                    return False

                old_master_id = request['assigned_master_id']

                # Обновляем заявку
                await conn.execute('''
                    UPDATE repair_requests 
                    SET assigned_master_id = NULL,
                        assigned_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE request_id = $1
                ''', request_id)

                # Обновляем историю назначений
                await conn.execute('''
                    UPDATE assignment_history 
                    SET unassigned_at = CURRENT_TIMESTAMP,
                        reason = $1
                    WHERE request_id = $2 AND unassigned_at IS NULL
                ''', reason or 'Мастер снят с заявки', request['id'])

                # Обновляем счетчик активных ремонтов у мастера
                await conn.execute('''
                    UPDATE users 
                    SET current_repairs_count = GREATEST(current_repairs_count - 1, 0)
                    WHERE id = $1
                ''', old_master_id)

                return True

            except Exception as e:
                print(f"Ошибка снятия мастера: {e}")
                return False


    async def get_master_workload(self, master_id: int) -> Dict:
        """Получение загруженности мастера"""
        async with self.pool.acquire() as conn:
            # Активные заявки
            active_repairs = await conn.fetch('''
                SELECT 
                    rr.request_id, rr.status, rr.priority,
                    c.full_name as client_name,
                    rr.device_type, rr.created_at
                FROM repair_requests rr
                JOIN clients c ON rr.client_id = c.id
                WHERE rr.assigned_master_id = $1 
                    AND rr.status NOT IN ('Выдана', 'Готова к выдаче')
                    AND rr.is_archived = FALSE
                ORDER BY 
                    CASE rr.priority
                        WHEN 'Критическая' THEN 1
                        WHEN 'Высокая' THEN 2
                        WHEN 'Обычная' THEN 3
                        WHEN 'Низкая' THEN 4
                    END,
                    rr.created_at
            ''', master_id)

            # Статистика за последние 30 дней
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_repairs,
                    COUNT(CASE WHEN rr.status = 'Выдана' THEN 1 END) as completed_repairs,
                    AVG(EXTRACT(EPOCH FROM (rr.actual_completion - rr.created_at))/3600)::numeric(10,2) as avg_repair_hours
                FROM repair_requests rr
                WHERE rr.assigned_master_id = $1
                    AND rr.created_at >= CURRENT_DATE - INTERVAL '30 days'
            ''', master_id)

            return {
                'active_repairs': [dict(r) for r in active_repairs],
                'stats': dict(stats) if stats else {}
            }

    async def get_masters_dashboard(self) -> List[Dict]:
        """Получение dashboard для менеджера с информацией о всех мастерах"""
        async with self.pool.acquire() as conn:
            masters = await conn.fetch('''
                SELECT 
                    u.id, u.full_name, u.specialization, u.is_available,
                    COUNT(DISTINCT CASE WHEN rr.status NOT IN ('Выдана', 'Готова к выдаче') 
                        AND rr.is_archived = FALSE THEN rr.id END) as active_repairs,
                    COUNT(DISTINCT CASE WHEN rr.status = 'Выдана' 
                        AND rr.created_at >= CURRENT_DATE - INTERVAL '7 days' THEN rr.id END) as completed_this_week,
                    STRING_AGG(DISTINCT ms.skill_name || ' (' || ms.skill_level || ')', ', ') as skills
                FROM users u
                LEFT JOIN repair_requests rr ON u.id = rr.assigned_master_id
                LEFT JOIN master_skills ms ON u.id = ms.master_id
                WHERE u.role = 'master' AND u.is_active = TRUE
                GROUP BY u.id
                ORDER BY active_repairs DESC
            ''')

            return [dict(master) for master in masters]

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

    async def create_user(self, username: str, email: str, password: str, full_name: str, role: str,
                          phone: str = None) -> int:
        """Создание нового пользователя с поддержкой телефона"""
        password_hash = self.hash_password(password)

        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval('''
                INSERT INTO users (username, email, password_hash, password_plain, full_name, role, phone)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            ''', username, email, password_hash, password, full_name, role, phone)

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
        """Получение всех пользователей с телефонами"""
        async with self.pool.acquire() as conn:
            users = await conn.fetch('''
                SELECT 
                    id, 
                    username, 
                    email, 
                    password_plain, 
                    full_name, 
                    role, 
                    phone,
                    is_active, 
                    created_at, 
                    last_login,
                    specialization
                FROM users 
                ORDER BY created_at DESC
            ''')

            result = []
            for user in users:
                user_dict = dict(user)
                # Убеждаемся, что phone всегда присутствует
                if user_dict.get('phone') is None:
                    user_dict['phone'] = None
                result.append(user_dict)

            return result

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
        """Создание нового клиента с нормализацией телефона"""
        normalized_phone = self.normalize_phone(phone)

        async with self.pool.acquire() as conn:
            # Проверяем, не существует ли уже клиент с таким телефоном
            existing_client = await conn.fetchval('''
                SELECT id FROM clients WHERE phone = $1
            ''', normalized_phone)

            if existing_client:
                print(f"⚠️ Клиент с телефоном {normalized_phone} уже существует (ID: {existing_client})")
                # Можно обновить информацию или вернуть существующего
                await conn.execute('''
                    UPDATE clients 
                    SET full_name = $1, email = COALESCE($2, email), address = COALESCE($3, address)
                    WHERE id = $4
                ''', full_name, email, address, existing_client)
                return existing_client

            client_id = await conn.fetchval('''
                INSERT INTO clients (full_name, phone, email, address)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', full_name, normalized_phone, email, address)

            print(f"✅ Создан новый клиент ID: {client_id} с телефоном: {normalized_phone}")
            return client_id

    async def search_clients_by_phone(self, phone_token: str):
        """Поиск клиентов по номеру телефона (по части номера)"""
        # Нормализуем поисковый запрос
        clean_token = ''.join(filter(str.isdigit, phone_token))

        query = """
            SELECT id, full_name, phone, email
            FROM clients
            WHERE phone LIKE '%' || $1 || '%'
            ORDER BY id DESC
            LIMIT 10;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, clean_token)
            print(f"🔍 Поиск клиентов по телефону '{clean_token}': найдено {len(rows)}")
            return [dict(row) for row in rows]

    async def get_or_create_client(self, full_name: str, phone: str, email: str = None) -> int:
        """Получение или создание клиента с нормализацией телефона"""
        normalized_phone = self.normalize_phone(phone)

        async with self.pool.acquire() as conn:
            # Ищем клиента по нормализованному телефону
            client_id = await conn.fetchval('''
                SELECT id FROM clients
                WHERE phone = $1
            ''', normalized_phone)

            if client_id:
                print(f"👤 Найден существующий клиент ID: {client_id} для телефона: {normalized_phone}")

                # Обновляем информацию если она изменилась
                await conn.execute('''
                    UPDATE clients 
                    SET full_name = $1, email = COALESCE($2, email), total_repairs = total_repairs + 1
                    WHERE id = $3
                ''', full_name, email, client_id)

                return client_id

            # Создаём нового клиента с нормализованным телефоном
            client_id = await conn.fetchval('''
                INSERT INTO clients (full_name, phone, email, total_repairs)
                VALUES ($1, $2, $3, 1)
                RETURNING id
            ''', full_name, normalized_phone, email)

            print(f"➕ Создан новый клиент ID: {client_id} для телефона: {normalized_phone}")
            return client_id

    # Методы для работы с заявками
    async def create_repair_request(self, client_data: Dict, device_data: Dict, created_by_id: int = None) -> str:
        """Создание новой заявки на ремонт с указанием создателя"""
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
                    problem_description, priority, status, created_by_id, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_TIMESTAMP)
            ''', request_id, client_id, device_data['device_type'],
                               device_data.get('brand', ''),
                               device_data.get('model', ''),
                               device_data['problem_description'],
                               device_data.get('priority', 'Обычная'),
                               'Принята',
                               created_by_id)  # ID пользователя, создавшего заявку

            # Обновляем счетчик ремонтов у клиента
            await conn.execute('''
                UPDATE clients 
                SET total_repairs = total_repairs + 1
                WHERE id = $1
            ''', client_id)

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
        """Получение всех заявок с расширенной информацией"""
        async with self.pool.acquire() as conn:
            where_clause = "" if include_archived else "WHERE rr.is_archived = FALSE"

            requests = await conn.fetch(f'''
                SELECT 
                    rr.*, 
                    c.full_name as client_name, 
                    c.phone as client_phone,
                    c.email as client_email,
                    c.is_vip as client_is_vip,
                    master.full_name as master_name,
                    master.phone as master_phone,
                    master.specialization as master_specialization,
                    assigned_by.full_name as assigned_by_name,
                    created_by.full_name as created_by_name
                FROM repair_requests rr
                LEFT JOIN clients c ON rr.client_id = c.id
                LEFT JOIN users master ON rr.assigned_master_id = master.id
                LEFT JOIN users assigned_by ON rr.assigned_by_id = assigned_by.id
                LEFT JOIN users created_by ON rr.created_by_id = created_by.id
                {where_clause}
                ORDER BY 
                    CASE rr.priority
                        WHEN 'Критическая' THEN 1
                        WHEN 'Высокая' THEN 2
                        WHEN 'Обычная' THEN 3
                        WHEN 'Низкая' THEN 4
                    END,
                    rr.created_at DESC
            ''')

            return [dict(request) for request in requests]

    async def update_problem_description(self, request_id: str, new_description: str) -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    UPDATE repair_requests
                    SET problem_description = $1, updated_at = NOW()
                    WHERE request_id = $2
                """, new_description, request_id)
                return True
            except Exception as e:
                print(f"❌ Ошибка обновления описания проблемы: {e}")
                return False

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

    # Добавьте эти методы в класс PostgreSQLDatabase в файле app/database_pg.py

    async def get_detailed_statistics(self) -> Dict:
        """Получение детальной статистики для dashboard"""
        async with self.pool.acquire() as conn:
            # Общее количество заявок
            total_requests = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests WHERE is_archived = FALSE
            ''')

            # Активные заявки
            active_requests = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests 
                WHERE status != 'Выдана' AND is_archived = FALSE
            ''')

            # Завершенные заявки за текущий месяц
            completed_this_month = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests 
                WHERE status = 'Выдана' 
                  AND DATE_TRUNC('month', actual_completion) = DATE_TRUNC('month', CURRENT_DATE)
            ''')

            # Завершенные заявки за прошлый месяц
            completed_last_month = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests 
                WHERE status = 'Выдана' 
                  AND DATE_TRUNC('month', actual_completion) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
            ''')

            # Расчет процента роста
            growth_percentage = (
                ((completed_this_month - completed_last_month) / completed_last_month * 100)
                if completed_last_month > 0 else 0
            )

            # Средняя стоимость завершенного ремонта
            avg_cost = await conn.fetchval('''
                SELECT AVG(final_cost) FROM repair_requests 
                WHERE final_cost IS NOT NULL AND status = 'Выдана'
            ''') or 0

            # Среднее время ремонта в днях
            avg_repair_time = await conn.fetchval('''
                SELECT AVG(EXTRACT(EPOCH FROM (actual_completion - created_at))/86400)
                FROM repair_requests 
                WHERE actual_completion IS NOT NULL
            ''') or 0

            # Статистика по статусам
            status_stats = await conn.fetch('''
                SELECT status, COUNT(*) as count
                FROM repair_requests 
                WHERE is_archived = FALSE
                GROUP BY status
                ORDER BY count DESC
            ''')

            # Статистика по приоритетам
            priority_stats = await conn.fetch('''
                SELECT priority, COUNT(*) as count
                FROM repair_requests 
                WHERE is_archived = FALSE
                GROUP BY priority
                ORDER BY 
                    CASE priority
                        WHEN 'Критическая' THEN 1
                        WHEN 'Высокая' THEN 2
                        WHEN 'Обычная' THEN 3
                        WHEN 'Низкая' THEN 4
                    END
            ''')

            # Топ-5 мастеров по завершенным ремонтам за последние 30 дней
            top_masters = await conn.fetch('''
                SELECT 
                    u.full_name,
                    COUNT(rr.id) as completed_repairs,
                    AVG(EXTRACT(EPOCH FROM (rr.actual_completion - rr.created_at))/86400) as avg_days
                FROM users u
                JOIN repair_requests rr ON rr.assigned_master_id = u.id
                WHERE u.role = 'master'
                  AND rr.status = 'Выдана'
                  AND rr.actual_completion >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY u.full_name
                ORDER BY completed_repairs DESC
                LIMIT 5
            ''')

            return {
                'total_requests': total_requests,
                'active_requests': active_requests,
                'completed_this_month': completed_this_month,
                'completed_last_month': completed_last_month,
                'growth_percentage': round(growth_percentage, 1),
                'avg_cost': round(float(avg_cost), 2),
                'avg_repair_time': round(float(avg_repair_time), 1),
                'status_stats': [dict(row) for row in status_stats],
                'priority_stats': [dict(row) for row in priority_stats],
                'top_masters': [dict(row) for row in top_masters],
                'monthly_revenue': round(float(avg_cost) * completed_this_month, 2) if avg_cost else 0
            }

    async def get_weekly_chart_data(self) -> Dict:
        """Получение данных для графика заявок за неделю"""
        async with self.pool.acquire() as conn:
            weekly_data = await conn.fetch('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as requests_count,
                    COUNT(CASE WHEN status = 'Выдана' THEN 1 END) as completed_count
                FROM repair_requests 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                    AND is_archived = FALSE
                GROUP BY DATE(created_at)
                ORDER BY date
            ''')

            return {
                'labels': [row['date'].strftime('%d.%m') for row in weekly_data],
                'requests': [row['requests_count'] for row in weekly_data],
                'completed': [row['completed_count'] for row in weekly_data]
            }

    async def get_monthly_chart_data(self) -> Dict:
        """Получение данных для графика заявок за месяц"""
        async with self.pool.acquire() as conn:
            monthly_data = await conn.fetch('''
                SELECT 
                    DATE_TRUNC('week', created_at) as week_start,
                    COUNT(*) as requests_count,
                    COUNT(CASE WHEN status = 'Выдана' THEN 1 END) as completed_count
                FROM repair_requests 
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    AND is_archived = FALSE
                GROUP BY DATE_TRUNC('week', created_at)
                ORDER BY week_start
            ''')

            return {
                'labels': [f"Неделя {i + 1}" for i in range(len(monthly_data))],
                'requests': [row['requests_count'] for row in monthly_data],
                'completed': [row['completed_count'] for row in monthly_data]
            }

    async def get_device_type_stats(self) -> List[Dict]:
        """Статистика по типам устройств"""
        async with self.pool.acquire() as conn:
            device_stats = await conn.fetch('''
                SELECT 
                    device_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN status = 'Выдана' THEN 1 END) as completed,
                    AVG(CASE WHEN final_cost IS NOT NULL THEN final_cost END) as avg_cost
                FROM repair_requests 
                WHERE is_archived = FALSE
                    AND created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY device_type
                ORDER BY count DESC
            ''')

            return [dict(row) for row in device_stats]

    # Добавьте эти методы в класс PostgreSQLDatabase в app/database_pg.py

    async def update_repair_request_full(self, request_id: str, update_data: dict, user_id: int) -> bool:
        """Полное обновление заявки на ремонт"""
        from datetime import datetime, date

        async with self.pool.acquire() as conn:
            try:
                # Получаем текущие данные заявки
                current_request = await conn.fetchrow('''
                    SELECT * FROM repair_requests WHERE request_id = $1 AND is_archived = FALSE
                ''', request_id)

                if not current_request:
                    return False

                # Подготавливаем список полей для обновления
                set_clauses = []
                values = []
                param_count = 1

                # Мапинг полей для обновления
                updatable_fields = {
                    'device_type': 'device_type',
                    'brand': 'brand',
                    'model': 'model',
                    'serial_number': 'serial_number',
                    'problem_description': 'problem_description',
                    'status': 'status',
                    'priority': 'priority',
                    'estimated_cost': 'estimated_cost',
                    'final_cost': 'final_cost',
                    'estimated_completion': 'estimated_completion',
                    'warranty_period': 'warranty_period',
                    'repair_duration_hours': 'repair_duration_hours',
                    'parts_used': 'parts_used',
                    'notes': 'notes'
                }

                # Обрабатываем каждое поле
                for field_name, db_field in updatable_fields.items():
                    if field_name in update_data and update_data[field_name] is not None:
                        value = update_data[field_name]

                        # 🆕 Специальная обработка для дат
                        if field_name == 'estimated_completion' and isinstance(value, str):
                            try:
                                # Конвертируем строку вида '2025-06-02' в объект date
                                value = datetime.strptime(value, '%Y-%m-%d').date()
                            except ValueError as e:
                                print(f"❌ Ошибка парсинга даты: {value}, ошибка: {e}")
                                continue

                        set_clauses.append(f"{db_field} = ${param_count}")
                        values.append(value)
                        param_count += 1

                # Автоматическое заполнение actual_completion при статусе "Выдана"
                if 'status' in update_data and update_data['status'] == 'Выдана':
                    if not current_request['actual_completion']:
                        set_clauses.append(f"actual_completion = ${param_count}")
                        values.append(datetime.now())
                        param_count += 1

                # Добавляем updated_at
                set_clauses.append(f"updated_at = ${param_count}")
                values.append(datetime.now())
                param_count += 1

                if not set_clauses:
                    return True  # Нет изменений

                # Выполняем обновление
                query = f'''
                    UPDATE repair_requests 
                    SET {', '.join(set_clauses)}
                    WHERE request_id = ${param_count}
                '''
                values.append(request_id)

                print(f"🔍 SQL запрос: {query}")
                print(f"🔍 Значения: {values}")

                await conn.execute(query, *values)

                # Записываем изменения в историю если изменился статус
                if 'status' in update_data:
                    old_status = current_request['status']
                    new_status = update_data['status']

                    if old_status != new_status:
                        comment = update_data.get('comment', f'Статус изменен с "{old_status}" на "{new_status}"')

                        await conn.execute('''
                            INSERT INTO status_history (request_id, old_status, new_status, changed_by, comment)
                            VALUES (
                                (SELECT id FROM repair_requests WHERE request_id = $1),
                                $2, $3, $4, $5
                            )
                        ''', request_id, old_status, new_status, user_id, comment)

                return True

            except Exception as e:
                print(f"❌ Ошибка обновления заявки: {e}")
                import traceback
                traceback.print_exc()
                return False

    async def get_repair_request_full(self, request_id: str) -> Optional[Dict]:
        """Получение полной информации о заявке для редактирования"""
        async with self.pool.acquire() as conn:
            request = await conn.fetchrow('''
                SELECT 
                    rr.*,
                    c.full_name as client_name, 
                    c.phone as client_phone,
                    c.email as client_email,
                    c.address as client_address,
                    c.is_vip as client_is_vip,
                    c.id as client_id,
                    master.full_name as master_name,
                    master.phone as master_phone,
                    master.specialization as master_specialization,
                    assigned_by.full_name as assigned_by_name,
                    created_by.full_name as created_by_name
                FROM repair_requests rr
                LEFT JOIN clients c ON rr.client_id = c.id
                LEFT JOIN users master ON rr.assigned_master_id = master.id
                LEFT JOIN users assigned_by ON rr.assigned_by_id = assigned_by.id
                LEFT JOIN users created_by ON rr.created_by_id = created_by.id
                WHERE rr.request_id = $1 AND rr.is_archived = FALSE
            ''', request_id)

            if request:
                result = dict(request)
                # Форматируем даты для JSON
                if result.get('estimated_completion'):
                    result['estimated_completion'] = result['estimated_completion'].isoformat()
                if result.get('actual_completion'):
                    result['actual_completion'] = result['actual_completion'].isoformat()
                if result.get('created_at'):
                    result['created_at'] = result['created_at'].isoformat()
                if result.get('updated_at'):
                    result['updated_at'] = result['updated_at'].isoformat()

                return result
            return None

    async def get_status_history(self, request_id: str) -> List[Dict]:
        """Получение истории изменений статуса заявки и назначений мастеров"""
        async with self.pool.acquire() as conn:
            # Получаем ID заявки
            request_row = await conn.fetchrow('SELECT id FROM repair_requests WHERE request_id = $1', request_id)
            if not request_row:
                return []

            internal_id = request_row['id']

            # Получаем историю изменений статусов
            status_history = await conn.fetch('''
                SELECT 
                    sh.id,
                    sh.old_status,
                    sh.new_status,
                    sh.changed_at,
                    sh.comment,
                    u.full_name as changed_by_name,
                    u.role as changed_by_role,
                    'status_change' as action_type
                FROM status_history sh
                LEFT JOIN users u ON sh.changed_by = u.id
                WHERE sh.request_id = $1
                ORDER BY sh.changed_at DESC
            ''', internal_id)

            # Получаем историю назначений мастеров
            assignment_history = await conn.fetch('''
                SELECT 
                    ah.id,
                    ah.assigned_at as changed_at,
                    ah.unassigned_at,
                    ah.reason as comment,
                    master.full_name as master_name,
                    master.specialization as master_specialization,
                    assigned_by.full_name as changed_by_name,
                    assigned_by.role as changed_by_role,
                    'master_assignment' as action_type
                FROM assignment_history ah
                LEFT JOIN users master ON ah.master_id = master.id
                LEFT JOIN users assigned_by ON ah.assigned_by = assigned_by.id
                WHERE ah.request_id = $1
                ORDER BY ah.assigned_at DESC
            ''', internal_id)

            # Объединяем и сортируем все события
            all_events = []

            # Добавляем изменения статусов
            for record in status_history:
                all_events.append({
                    'id': f"status_{record['id']}",
                    'action_type': 'status_change',
                    'old_status': record['old_status'],
                    'new_status': record['new_status'],
                    'changed_at': record['changed_at'],
                    'changed_by_name': record['changed_by_name'],
                    'changed_by_role': record['changed_by_role'],
                    'comment': record['comment']
                })

            # Добавляем назначения мастеров
            for record in assignment_history:
                # Событие назначения
                all_events.append({
                    'id': f"assign_{record['id']}",
                    'action_type': 'master_assignment',
                    'master_name': record['master_name'],
                    'master_specialization': record['master_specialization'],
                    'changed_at': record['changed_at'],
                    'changed_by_name': record['changed_by_name'],
                    'changed_by_role': record['changed_by_role'],
                    'comment': f"Назначен мастер: {record['master_name']}" + (
                        f" ({record['master_specialization']})" if record['master_specialization'] else "")
                })

                # Событие снятия мастера (если есть)
                if record['unassigned_at']:
                    all_events.append({
                        'id': f"unassign_{record['id']}",
                        'action_type': 'master_unassignment',
                        'master_name': record['master_name'],
                        'changed_at': record['unassigned_at'],
                        'changed_by_name': record['changed_by_name'],
                        'changed_by_role': record['changed_by_role'],
                        'comment': f"Снят мастер: {record['master_name']}" + (
                            f" - {record['comment']}" if record['comment'] else "")
                    })

            # Сортируем по времени (новые сверху)
            all_events.sort(key=lambda x: x['changed_at'], reverse=True)

            return all_events

    async def update_client_info(self, client_id: int, client_data: dict) -> bool:
        """Обновление информации о клиенте (алиас для update_client)"""
        return await self.update_client(client_id, client_data)

    # Добавьте эти методы в класс PostgreSQLDatabase в файл app/database_pg.py

    async def update_user_info(self, user_id: int, email: str, full_name: str, role: str, is_active: bool,
                               phone: str = None) -> bool:
        """Обновление информации о пользователе"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE users 
                    SET email = $1, full_name = $2, role = $3, is_active = $4, phone = $5
                    WHERE id = $6
                ''', email, full_name, role, is_active, phone, user_id)
                return True
            except Exception as e:
                print(f"❌ Ошибка обновления пользователя: {e}")
                return False

    async def update_user_status(self, user_id: int, is_active: bool) -> bool:
        """Обновление статуса пользователя (активен/неактивен)"""
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute('''
                    UPDATE users 
                    SET is_active = $1
                    WHERE id = $2
                ''', is_active, user_id)
                return result == 'UPDATE 1'
            except Exception as e:
                print(f"❌ Ошибка обновления статуса пользователя: {e}")
                return False

    async def get_user_statistics(self) -> Dict:
        """ИСПРАВЛЕННОЕ получение статистики пользователей"""
        async with self.pool.acquire() as conn:
            try:
                print("📊 Получение статистики пользователей из БД...")

                # Общее количество пользователей
                total_users = await conn.fetchval('SELECT COUNT(*) FROM users WHERE is_active = TRUE')
                print(f"   Всего пользователей: {total_users}")

                # Количество администраторов и директоров
                admin_users = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE role IN ('admin', 'director') AND is_active = TRUE
                ''')
                print(f"   Администраторов: {admin_users}")

                # Количество мастеров
                master_users = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE role = 'master' AND is_active = TRUE
                ''')
                print(f"   Мастеров: {master_users}")

                # Новые пользователи за последние 30 дней
                recent_users = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    AND is_active = TRUE
                ''')
                print(f"   Новых за месяц: {recent_users}")

                stats = {
                    'total_users': total_users or 0,
                    'admin_users': admin_users or 0,
                    'master_users': master_users or 0,
                    'recent_users': recent_users or 0
                }

                print(f"✅ Статистика пользователей сформирована: {stats}")
                return stats

            except Exception as e:
                print(f"❌ Ошибка получения статистики пользователей: {e}")
                import traceback
                traceback.print_exc()

                # Возвращаем нулевую статистику при ошибке
                return {
                    'total_users': 0,
                    'admin_users': 0,
                    'master_users': 0,
                    'recent_users': 0
                }

    async def check_username_exists(self, username: str, exclude_user_id: int = None) -> bool:
        """Проверка существования имени пользователя"""
        async with self.pool.acquire() as conn:
            try:
                if exclude_user_id:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE username = $1 AND id != $2
                    ''', username, exclude_user_id)
                else:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE username = $1
                    ''', username)
                return result is not None
            except Exception as e:
                print(f"❌ Ошибка проверки имени пользователя: {e}")
                return False

    async def check_email_exists(self, email: str, exclude_user_id: int = None) -> bool:
        """Проверка существования email"""
        async with self.pool.acquire() as conn:
            try:
                if exclude_user_id:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE email = $1 AND id != $2
                    ''', email, exclude_user_id)
                else:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE email = $1
                    ''', email)
                return result is not None
            except Exception as e:
                print(f"❌ Ошибка проверки email: {e}")
                return False

    # Добавьте эти методы в класс PostgreSQLDatabase в файле app/database_pg.py

    async def get_user_statistics(self) -> Dict:
        """Получение статистики пользователей"""
        async with self.pool.acquire() as conn:
            try:
                # Общее количество пользователей
                total_users = await conn.fetchval('SELECT COUNT(*) FROM users WHERE is_active = TRUE')

                # Количество по ролям
                admin_users = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE role IN ('admin', 'director') AND is_active = TRUE
                ''')

                master_users = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE role = 'master' AND is_active = TRUE
                ''')

                # Новые пользователи за последние 30 дней
                recent_users = await conn.fetchval('''
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    AND is_active = TRUE
                ''')

                return {
                    'total_users': total_users or 0,
                    'admin_users': admin_users or 0,
                    'master_users': master_users or 0,
                    'recent_users': recent_users or 0
                }

            except Exception as e:
                print(f"❌ Ошибка получения статистики пользователей: {e}")
                return {
                    'total_users': 0,
                    'admin_users': 0,
                    'master_users': 0,
                    'recent_users': 0
                }

    async def check_username_exists(self, username: str, exclude_user_id: int = None) -> bool:
        """Проверка существования имени пользователя"""
        async with self.pool.acquire() as conn:
            try:
                if exclude_user_id:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE username = $1 AND id != $2
                    ''', username, exclude_user_id)
                else:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE username = $1
                    ''', username)
                return result is not None
            except Exception as e:
                print(f"❌ Ошибка проверки имени пользователя: {e}")
                return False

    async def check_email_exists(self, email: str, exclude_user_id: int = None) -> bool:
        """Проверка существования email"""
        async with self.pool.acquire() as conn:
            try:
                if exclude_user_id:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE email = $1 AND id != $2
                    ''', email, exclude_user_id)
                else:
                    result = await conn.fetchval('''
                        SELECT id FROM users 
                        WHERE email = $1
                    ''', email)
                return result is not None
            except Exception as e:
                print(f"❌ Ошибка проверки email: {e}")
                return False

    async def update_user_info(self, user_id: int, email: str, full_name: str, role: str, is_active: bool,
                               phone: str = None) -> bool:
        """Обновление информации о пользователе"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE users 
                    SET email = $1, full_name = $2, role = $3, is_active = $4, phone = $5
                    WHERE id = $6
                ''', email, full_name, role, is_active, phone, user_id)
                return True
            except Exception as e:
                print(f"❌ Ошибка обновления пользователя: {e}")
                return False

    async def update_user_status(self, user_id: int, is_active: bool) -> bool:
        """Обновление статуса пользователя (активен/неактивен)"""
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute('''
                    UPDATE users 
                    SET is_active = $1
                    WHERE id = $2
                ''', is_active, user_id)
                return result == 'UPDATE 1'
            except Exception as e:
                print(f"❌ Ошибка обновления статуса пользователя: {e}")
                return False

    async def delete_user(self, user_id: int) -> bool:
        """ПОЛНОЕ удаление пользователя из базы данных"""
        async with self.pool.acquire() as conn:
            try:
                print(f"🗑️ Полное удаление пользователя {user_id} из БД")

                # Проверяем существование пользователя
                user_exists = await conn.fetchval('SELECT id FROM users WHERE id = $1', user_id)
                if not user_exists:
                    print(f"❌ Пользователь {user_id} не найден в БД")
                    return False

                # Начинаем транзакцию для безопасного удаления
                async with conn.transaction():
                    # 1. Обновляем связанные таблицы, устанавливая NULL для внешних ключей

                    # Обновляем repair_requests - убираем ссылки на удаляемого пользователя
                    await conn.execute('''
                        UPDATE repair_requests 
                        SET assigned_master_id = NULL 
                        WHERE assigned_master_id = $1
                    ''', user_id)

                    await conn.execute('''
                        UPDATE repair_requests 
                        SET assigned_by_id = NULL 
                        WHERE assigned_by_id = $1
                    ''', user_id)

                    await conn.execute('''
                        UPDATE repair_requests 
                        SET created_by_id = NULL 
                        WHERE created_by_id = $1
                    ''', user_id)

                    # Обновляем status_history - убираем ссылки на пользователя
                    await conn.execute('''
                        UPDATE status_history 
                        SET changed_by = NULL 
                        WHERE changed_by = $1
                    ''', user_id)

                    # Обновляем assignment_history - убираем ссылки на пользователя
                    await conn.execute('''
                        UPDATE assignment_history 
                        SET master_id = NULL 
                        WHERE master_id = $1
                    ''', user_id)

                    await conn.execute('''
                        UPDATE assignment_history 
                        SET assigned_by = NULL 
                        WHERE assigned_by = $1
                    ''', user_id)

                    # 2. Удаляем связанные записи где пользователь является владельцем

                    # Удаляем навыки мастера (если это мастер)
                    await conn.execute('''
                        DELETE FROM master_skills 
                        WHERE master_id = $1
                    ''', user_id)

                    # Удаляем расписание мастера (если есть такая таблица)
                    await conn.execute('''
                        DELETE FROM master_schedule 
                        WHERE master_id = $1
                    ''', user_id)

                    # 3. Наконец, удаляем самого пользователя
                    result = await conn.execute('''
                        DELETE FROM users 
                        WHERE id = $1
                    ''', user_id)

                    print(f"📝 Результат SQL: {result}")

                    # Проверяем результат
                    if result == 'DELETE 1':
                        print(f"✅ Пользователь {user_id} полностью удален из БД")
                        return True
                    else:
                        print(f"❌ Не удалось удалить пользователя {user_id}")
                        return False

            except Exception as e:
                print(f"❌ Ошибка полного удаления пользователя из БД: {e}")
                import traceback
                traceback.print_exc()
                return False

    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Получение пользователя по имени пользователя"""
        async with self.pool.acquire() as conn:
            try:
                user = await conn.fetchrow('''
                    SELECT id, username, email, full_name, role, is_active, created_at, last_login, phone
                    FROM users 
                    WHERE username = $1
                ''', username)
                return dict(user) if user else None
            except Exception as e:
                print(f"❌ Ошибка получения пользователя по username: {e}")
                return None

    async def get_users_by_role(self, role: str) -> List[Dict]:
        """Получение пользователей по роли"""
        async with self.pool.acquire() as conn:
            try:
                users = await conn.fetch('''
                    SELECT id, username, email, full_name, role, is_active, created_at, last_login, phone
                    FROM users 
                    WHERE role = $1 AND is_active = TRUE
                    ORDER BY full_name
                ''', role)
                return [dict(user) for user in users]
            except Exception as e:
                print(f"❌ Ошибка получения пользователей по роли: {e}")
                return []

    async def get_active_masters(self) -> List[Dict]:
        """Получение списка активных мастеров"""
        async with self.pool.acquire() as conn:
            try:
                masters = await conn.fetch('''
                    SELECT 
                        u.id, u.username, u.full_name, u.phone, u.specialization,
                        u.current_repairs_count, u.max_concurrent_repairs,
                        u.is_available,
                        COUNT(rr.id) as active_repairs
                    FROM users u
                    LEFT JOIN repair_requests rr ON u.id = rr.assigned_master_id 
                        AND rr.status NOT IN ('Выдана', 'Готова к выдаче')
                        AND rr.is_archived = FALSE
                    WHERE u.role = 'master' AND u.is_active = TRUE
                    GROUP BY u.id
                    ORDER BY active_repairs ASC, u.full_name ASC
                ''')
                return [dict(master) for master in masters]
            except Exception as e:
                print(f"❌ Ошибка получения активных мастеров: {e}")
                return []

    async def get_user_activity_stats(self, user_id: int) -> Dict:
        """Получение статистики активности пользователя"""
        async with self.pool.acquire() as conn:
            try:
                # Для мастеров - статистика по ремонтам
                if await self.is_user_master(user_id):
                    stats = await conn.fetchrow('''
                        SELECT 
                            COUNT(*) as total_repairs,
                            COUNT(CASE WHEN rr.status = 'Выдана' THEN 1 END) as completed_repairs,
                            COUNT(CASE WHEN rr.status NOT IN ('Выдана', 'Готова к выдаче') THEN 1 END) as active_repairs,
                            AVG(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost END) as avg_repair_cost,
                            AVG(EXTRACT(EPOCH FROM (rr.actual_completion - rr.created_at))/3600)::numeric(10,2) as avg_repair_hours
                        FROM repair_requests rr
                        WHERE rr.assigned_master_id = $1
                            AND rr.created_at >= CURRENT_DATE - INTERVAL '30 days'
                    ''', user_id)
                else:
                    # Для менеджеров/администраторов - статистика по созданным заявкам
                    stats = await conn.fetchrow('''
                        SELECT 
                            COUNT(*) as total_created,
                            COUNT(CASE WHEN rr.status = 'Выдана' THEN 1 END) as completed_created,
                            0 as active_repairs,
                            AVG(CASE WHEN rr.final_cost IS NOT NULL THEN rr.final_cost END) as avg_repair_cost,
                            0 as avg_repair_hours
                        FROM repair_requests rr
                        WHERE rr.created_by_id = $1
                            AND rr.created_at >= CURRENT_DATE - INTERVAL '30 days'
                    ''', user_id)

                return dict(stats) if stats else {}
            except Exception as e:
                print(f"❌ Ошибка получения статистики активности: {e}")
                return {}

    async def is_user_master(self, user_id: int) -> bool:
        """Проверка, является ли пользователь мастером"""
        async with self.pool.acquire() as conn:
            try:
                role = await conn.fetchval('SELECT role FROM users WHERE id = $1', user_id)
                return role == 'master'
            except Exception as e:
                print(f"❌ Ошибка проверки роли пользователя: {e}")
                return False

    async def update_user_last_login(self, user_id: int) -> bool:
        """Обновление времени последнего входа"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = $1
                ''', user_id)
                return True
            except Exception as e:
                print(f"❌ Ошибка обновления времени входа: {e}")
                return False

    async def search_users(self, search_term: str) -> List[Dict]:
        """Поиск пользователей по имени, email или username"""
        async with self.pool.acquire() as conn:
            try:
                users = await conn.fetch('''
                    SELECT id, username, email, full_name, role, is_active, created_at, last_login, phone
                    FROM users 
                    WHERE 
                        (full_name ILIKE $1 OR 
                         username ILIKE $1 OR 
                         email ILIKE $1 OR
                         role ILIKE $1)
                        AND is_active = TRUE
                    ORDER BY full_name
                ''', f'%{search_term}%')
                return [dict(user) for user in users]
            except Exception as e:
                print(f"❌ Ошибка поиска пользователей: {e}")
                return []

    async def get_users_count_by_role(self) -> Dict:
        """Получение количества пользователей по ролям"""
        async with self.pool.acquire() as conn:
            try:
                roles_stats = await conn.fetch('''
                    SELECT role, COUNT(*) as count
                    FROM users 
                    WHERE is_active = TRUE
                    GROUP BY role
                    ORDER BY count DESC
                ''')

                result = {role['role']: role['count'] for role in roles_stats}
                return result
            except Exception as e:
                print(f"❌ Ошибка получения статистики по ролям: {e}")
                return {}

    async def bulk_update_user_status(self, user_ids: List[int], is_active: bool) -> int:
        """Массовое обновление статуса пользователей"""
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute('''
                    UPDATE users 
                    SET is_active = $1
                    WHERE id = ANY($2)
                ''', is_active, user_ids)

                # Извлекаем количество обновленных записей
                updated_count = int(result.split()[-1]) if result else 0
                return updated_count
            except Exception as e:
                print(f"❌ Ошибка массового обновления статуса: {e}")
                return 0

    async def get_users_count_by_role(self) -> Dict:

        """Получение количества пользователей по ролям"""

        async with self.pool.acquire() as conn:

            try:

                roles_stats = await conn.fetch('''

                    SELECT role, COUNT(*) as count

                    FROM users 

                    WHERE is_active = TRUE

                    GROUP BY role

                    ORDER BY count DESC

                ''')

                result = {role['role']: role['count'] for role in roles_stats}

                return result

            except Exception as e:

                print(f"❌ Ошибка получения статистики по ролям: {e}")

                return {}

# Создание глобального экземпляра
db = PostgreSQLDatabase()