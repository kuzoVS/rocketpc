// ПРОВЕРКА ТОКЕНА ДО ЗАГРУЗКИ DOM
console.log('🚀 Dashboard JS загружен');

// Немедленная проверка токена
const token = localStorage.getItem('access_token');
console.log('🔑 Токен при загрузке:', token ? 'ЕСТЬ' : 'НЕТ');

if (!token) {
    console.log('❌ Токена нет, немедленный редирект на login');
    window.location.replace('/auth/login');
    // Останавливаем выполнение скрипта
    throw new Error('No token, redirecting to login');
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM загружен');

    // Сразу скрываем loader и показываем контент
    hideLoaderAndShowContent();

    // Загружаем базовую информацию
    loadBasicInfo();

    // Простая проверка аутентификации в фоне
    checkAuthInBackground();
});

function hideLoaderAndShowContent() {
    console.log('👁️ Скрываем loader...');

    const loader = document.getElementById('authCheckLoader');
    if (loader) {
        loader.style.display = 'none';
        console.log('✅ Loader скрыт');
    } else {
        console.log('⚠️ Loader не найден');
    }

    const content = document.getElementById('dashboardContent');
    if (content) {
        content.style.display = 'block';
        console.log('✅ Dashboard контент показан');
    } else {
        console.log('⚠️ dashboardContent не найден, показываем body');
        document.body.style.visibility = 'visible';
        document.body.style.opacity = '1';
    }
}

function loadBasicInfo() {
    console.log('📊 Загружаем базовую информацию...');

    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        console.log('👤 Пользователь:', user);

        // Обновляем имя пользователя
        const userName = document.getElementById('userName') || document.querySelector('.user-name');
        if (userName && user.full_name) {
            userName.textContent = user.full_name;
            console.log('✅ Имя пользователя обновлено');
        }

        // Обновляем роль
        const userRole = document.getElementById('userRole') || document.querySelector('.user-role');
        if (userRole && user.role) {
            userRole.textContent = getRoleDisplayName(user.role);
            console.log('✅ Роль пользователя обновлена');
        }

        // Обновляем аватар
        const userAvatar = document.getElementById('userAvatar') || document.querySelector('.user-avatar');
        if (userAvatar && user.full_name) {
            userAvatar.textContent = user.full_name.charAt(0).toUpperCase();
            console.log('✅ Аватар обновлен');
        }

        // Показываем пункт меню для админов
        if (user.role === 'admin' || user.role === 'director') {
            const usersMenuItem = document.getElementById('usersMenuItem');
            if (usersMenuItem) {
                usersMenuItem.style.display = 'block';
                console.log('✅ Пункт "Пользователи" показан');
            }
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки базовой информации:', error);
    }

    // Устанавливаем значения по умолчанию для статистики
    setDefaultStats();

    // Показываем заглушку в таблице
    showTablePlaceholder();
}

function setDefaultStats() {
    console.log('📈 Устанавливаем статистику по умолчанию...');

    const stats = {
        'activeRequestsCount': '12',
        'completedRequestsCount': '85',
        'monthlyRevenue': '₽425 000',
        'avgRepairTime': '3ч'
    };

    Object.entries(stats).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            console.log(`✅ ${id} = ${value}`);
        } else {
            console.log(`⚠️ Элемент ${id} не найден`);
        }
    });
}

function showTablePlaceholder() {
    console.log('📋 Показываем заглушку таблицы...');

    const tbody = document.getElementById('recentRequestsTable') || document.querySelector('table tbody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td>#RQ2A4F</td>
                <td>Иван Петров</td>
                <td>Ноутбук ASUS</td>
                <td>Не включается</td>
                <td><span class="status-badge status-new">Принята</span></td>
                <td>-</td>
                <td>30.05.2025</td>
                <td><button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;">Подробнее</button></td>
            </tr>
            <tr>
                <td>#RQ1B3E</td>
                <td>Мария Сидорова</td>
                <td>ПК</td>
                <td>Перегревается</td>
                <td><span class="status-badge status-in-progress">В ремонте</span></td>
                <td>Алексей</td>
                <td>29.05.2025</td>
                <td><button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;">Подробнее</button></td>
            </tr>
        `;
        console.log('✅ Таблица заполнена тестовыми данными');
    } else {
        console.log('⚠️ Таблица не найдена');
    }
}

function checkAuthInBackground() {
    console.log('🔍 Фоновая проверка аутентификации...');

    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('❌ Токена нет, редирект');
        redirectToLogin();
        return;
    }

    fetch('/auth/profile', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('📡 Ответ сервера на /auth/profile:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Аутентификация подтверждена:', data.username);
        // Попробуем загрузить реальные данные
        loadRealData();
    })
    .catch(error => {
        console.error('❌ Ошибка аутентификации:', error);
        console.log('🚪 Токен недействителен, редирект на login');
        clearTokensAndRedirect();
    });
}

function clearTokensAndRedirect() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    redirectToLogin();
}

function redirectToLogin() {
    console.log('🚪 Перенаправление на login...');
    window.location.replace('/auth/login');
}

function loadRealData() {
    console.log('📊 Попытка загрузки реальных данных...');

    const token = localStorage.getItem('access_token');

    fetch('/dashboard/api/requests', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('📡 Ответ на /dashboard/api/requests:', response.status);
        if (response.status === 401) {
            throw new Error('Unauthorized');
        }
        if (response.ok) {
            return response.json();
        }
        throw new Error(`HTTP ${response.status}`);
    })
    .then(data => {
        console.log('✅ Реальные данные получены:', data.length, 'заявок');
        updateWithRealData(data);
    })
    .catch(error => {
        if (error.message === 'Unauthorized') {
            console.log('❌ Не авторизован, редирект');
            clearTokensAndRedirect();
        } else {
            console.log('⚠️ Не удалось загрузить реальные данные:', error.message);
            console.log('📊 Продолжаем с тестовыми данными');
        }
    });
}

function updateWithRealData(requests) {
    // Обновляем статистику
    const activeCount = requests.filter(r => r.status !== 'Выдана').length;
    const completedCount = requests.filter(r => r.status === 'Выдана').length;

    const activeElement = document.getElementById('activeRequestsCount');
    const completedElement = document.getElementById('completedRequestsCount');

    if (activeElement) activeElement.textContent = activeCount;
    if (completedElement) completedElement.textContent = completedCount;

    // Обновляем таблицу
    const tbody = document.getElementById('recentRequestsTable') || document.querySelector('table tbody');
    if (tbody && requests.length > 0) {
        tbody.innerHTML = requests.slice(0, 5).map(request => `
            <tr>
                <td>#${request.request_id || 'N/A'}</td>
                <td>${request.client_name || 'Не указано'}</td>
                <td>${request.device_type || 'Не указано'}</td>
                <td>${(request.problem_description || 'Не указано').substring(0, 30)}...</td>
                <td><span class="status-badge status-new">${request.status || 'Принята'}</span></td>
                <td>${request.master_name || '-'}</td>
                <td>${formatDate(request.created_at)}</td>
                <td><button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;">Подробнее</button></td>
            </tr>
        `).join('');
        console.log('✅ Таблица обновлена реальными данными');
    }
}

function getRoleDisplayName(role) {
    const roleMap = {
        'admin': 'Администратор',
        'director': 'Директор',
        'manager': 'Менеджер',
        'master': 'Мастер'
    };
    return roleMap[role] || role;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        return new Date(dateString).toLocaleDateString('ru-RU');
    } catch {
        return 'N/A';
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
}

// Простой обработчик выхода
function logout() {
    console.log('🚪 Выход из системы');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.replace('/auth/login');
}

// Привязываем обработчики выхода
document.addEventListener('DOMContentLoaded', function() {
    const logoutLinks = document.querySelectorAll('a[href="/logout"], a[href="#logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    });
});

// Простые графики
function drawWeeklyChart() {
    const canvas = document.getElementById('weeklyChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    ctx.fillStyle = "#00ffff";
    ctx.font = "16px Arial";
    ctx.fillText("График заявок за неделю", 20, 30);
    ctx.fillText("(демо-данные)", 20, 60);
}

function drawStatusChart() {
    const canvas = document.getElementById('statusChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    ctx.fillStyle = "#00ffff";
    ctx.font = "16px Arial";
    ctx.fillText("Статистика по статусам", 20, 30);
    ctx.fillText("(демо-данные)", 20, 60);
}

// Рисуем графики через секунду после загрузки
setTimeout(() => {
    drawWeeklyChart();
    drawStatusChart();
}, 1000);

// Обработка потери токена во время работы
window.addEventListener('storage', function(e) {
    if (e.key === 'access_token' && !e.newValue) {
        console.log('🔑 Токен был удален, редирект');
        redirectToLogin();
    }
});

console.log('✅ Dashboard JS инициализирован');