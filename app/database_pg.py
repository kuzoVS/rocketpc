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
                    actual_completion DATE,
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
        """Назначение мастера на заявку"""
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

                # Если был назначен другой мастер, записываем в историю
                if request['assigned_master_id']:
                    await conn.execute('''
                        UPDATE assignment_history 
                        SET unassigned_at = CURRENT_TIMESTAMP
                        WHERE request_id = $1 AND unassigned_at IS NULL
                    ''', request['id'])

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
                    INSERT INTO assignment_history (request_id, master_id, assigned_by)
                    VALUES ($1, $2, $3)
                ''', request['id'], master_id, assigned_by_id)

                # Обновляем счетчик активных ремонтов у мастера
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
        """Снятие мастера с заявки"""
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
                ''', reason, request['id'])

                # Обновляем счетчик активных ремонтов у мастера
                await conn.execute('''
                    UPDATE users 
                    SET current_repairs_count = current_repairs_count - 1
                    WHERE id = $1 AND current_repairs_count > 0
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
            # Базовая статистика
            total_requests = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests WHERE is_archived = FALSE
            ''')

            # Активные заявки (не завершенные)
            active_requests = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests 
                WHERE status NOT IN ('Выдана') AND is_archived = FALSE
            ''')

            # Завершенные за текущий месяц
            completed_this_month = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests 
                WHERE status = 'Выдана' 
                AND EXTRACT(MONTH FROM created_at) = EXTRACT(MONTH FROM CURRENT_DATE)
                AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_DATE)
            ''')

            # Завершенные за прошлый месяц для расчета роста
            completed_last_month = await conn.fetchval('''
                SELECT COUNT(*) FROM repair_requests 
                WHERE status = 'Выдана' 
                AND EXTRACT(MONTH FROM created_at) = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')
                AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '1 month')
            ''')

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

            # Средняя стоимость ремонта
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

            # Топ мастеров по количеству выполненных работ за месяц
            top_masters = await conn.fetch('''
                SELECT 
                    u.full_name,
                    COUNT(rr.id) as completed_repairs,
                    AVG(EXTRACT(EPOCH FROM (rr.actual_completion - rr.created_at))/86400) as avg_days
                FROM users u
                LEFT JOIN repair_requests rr ON u.id = rr.assigned_master_id
                WHERE u.role = 'master' 
                    AND rr.status = 'Выдана'
                    AND rr.actual_completion >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY u.id, u.full_name
                ORDER BY completed_repairs DESC
                LIMIT 5
            ''')

            # Расчет процента роста
            growth_percentage = 0
            if completed_last_month > 0:
                growth_percentage = ((completed_this_month - completed_last_month) / completed_last_month) * 100

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

# Создание глобального экземпляра
db = PostgreSQLDatabase()