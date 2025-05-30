// Основная функция инициализации
async function initializeDashboard() {
    console.log('🚀 Инициализация dashboard...');

    const token = localStorage.getItem('access_token');
    if (!token) {
        console.log('❌ Токена нет в localStorage');
        redirectToLogin();
        return;
    }

    try {
        // Показываем body
        document.getElementById('pageBody').style.display = 'block';

        // Проверяем валидность токена
        console.log('🔍 Проверка валидности токена...');
        const response = await fetch('/auth/profile', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            console.log('❌ Токен недействителен');
            clearTokensAndRedirect();
            return;
        }

        const userData = await response.json();
        console.log('✅ Токен валидный, пользователь:', userData.username);

        // Загружаем пользовательскую информацию
        loadUserInfo();

        // Скрываем loader и показываем контент
        hideLoaderAndShowContent();

        // Загружаем данные
        await loadDashboardData();

        // Инициализируем графики
        setTimeout(() => {
            drawWeeklyChart();
            drawStatusChart();
        }, 500);

    } catch (error) {
        console.error('❌ Ошибка инициализации:', error);
        clearTokensAndRedirect();
    }
}

function redirectToLogin() {
    console.log('🚪 Перенаправление на login...');
    window.location.replace('/auth/login');
}

function clearTokensAndRedirect() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    redirectToLogin();
}

function hideLoaderAndShowContent() {
    console.log('👁️ Показываем dashboard контент...');

    const loader = document.getElementById('authCheckLoader');
    const content = document.getElementById('dashboardContent');

    if (loader) loader.style.display = 'none';
    if (content) content.style.display = 'block';
}

function loadUserInfo() {
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        console.log('👤 Загрузка информации о пользователе:', user.username);

        const userName = document.getElementById('userName');
        const userRole = document.getElementById('userRole');
        const userAvatar = document.getElementById('userAvatar');

        if (userName && user.full_name) {
            userName.textContent = user.full_name;
        }

        if (userRole && user.role) {
            const roleMap = {
                'admin': 'Администратор',
                'director': 'Директор',
                'manager': 'Менеджер',
                'master': 'Мастер'
            };
            userRole.textContent = roleMap[user.role] || user.role;
        }

        if (userAvatar && user.full_name) {
            userAvatar.textContent = user.full_name.charAt(0).toUpperCase();
        }

        // Показываем пункт "Пользователи" для админов
        if (user.role === 'admin' || user.role === 'director') {
            const usersMenuItem = document.getElementById('usersMenuItem');
            if (usersMenuItem) usersMenuItem.style.display = 'block';
        }

    } catch (error) {
        console.error('❌ Ошибка загрузки информации о пользователе:', error);
    }
}

async function loadDashboardData() {
    console.log('📊 Загрузка данных dashboard...');

    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        // Загружаем заявки
        const response = await fetch('/dashboard/api/requests', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            clearTokensAndRedirect();
            return;
        }

        if (response.ok) {
            const requests = await response.json();
            console.log('✅ Данные загружены:', requests.length, 'заявок');

            // Обновляем статистику
            updateStats(requests);

            // Обновляем таблицу
            updateRequestsTable(requests.slice(0, 5));
        } else {
            console.log('⚠️ Не удалось загрузить данные, показываем demo');
            showDemoData();
        }
    } catch (error) {
        console.log('⚠️ Ошибка загрузки, показываем demo data');
        showDemoData();
    }
}

function updateStats(requests) {
    const activeCount = requests.filter(r => r.status !== 'Выдана').length;
    const completedCount = requests.filter(r => r.status === 'Выдана').length;

    document.getElementById('activeRequestsCount').textContent = activeCount;
    document.getElementById('completedRequestsCount').textContent = completedCount;
    document.getElementById('monthlyRevenue').textContent = `₽${(completedCount * 5000).toLocaleString()}`;
    document.getElementById('avgRepairTime').textContent = '3ч';
}

function updateRequestsTable(requests) {
    const tbody = document.getElementById('recentRequestsTable');
    if (!tbody || !requests.length) {
        showDemoData();
        return;
    }

    tbody.innerHTML = requests.map(request => `
        <tr>
            <td>#${request.request_id || 'N/A'}</td>
            <td>${request.client_name || 'Не указано'}</td>
            <td>${request.device_type || 'Не указано'}</td>
            <td>${(request.problem_description || 'Не указано').substring(0, 30)}...</td>
            <td><span class="status-badge status-new">${request.status || 'Принята'}</span></td>
            <td>${request.master_name || '-'}</td>
            <td>${request.created_at ? new Date(request.created_at).toLocaleDateString('ru-RU') : 'N/A'}</td>
            <td><button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;">Подробнее</button></td>
        </tr>
    `).join('');
}

function showDemoData() {
    // Устанавливаем demo статистику
    document.getElementById('activeRequestsCount').textContent = '12';
    document.getElementById('completedRequestsCount').textContent = '85';
    document.getElementById('monthlyRevenue').textContent = '₽425 000';
    document.getElementById('avgRepairTime').textContent = '3ч';

    // Показываем demo таблицу
    const tbody = document.getElementById('recentRequestsTable');
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
    }
}

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

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('active');
}

function logout() {
    console.log('🚪 Выход из системы');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.replace('/auth/login');
}

// Привязываем обработчики событий
document.addEventListener('DOMContentLoaded', function() {
    const logoutLinks = document.querySelectorAll('a[href="#logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    });
});

// Запускаем инициализацию
document.addEventListener('DOMContentLoaded', initializeDashboard);

console.log('✅ Dashboard скрипт загружен');