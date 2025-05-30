// Проверка аутентификации при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    checkAuthentication();
    loadUserInfo();
    drawWeeklyChart();
    drawStatusChart();
});

function checkAuthentication() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        // Если токена нет, перенаправляем на страницу входа
        window.location.href = '/auth/login';
        return;
    }

    // Проверяем валидность токена
    fetch('/auth/profile', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Token invalid');
        }
        return response.json();
    })
    .catch(error => {
        console.error('Auth error:', error);
        // Удаляем недействительный токен и перенаправляем на вход
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/auth/login';
    });
}

function loadUserInfo() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    // Обновляем информацию о пользователе в интерфейсе
    const userNameElement = document.querySelector('.user-name');
    const userRoleElement = document.querySelector('.user-role');
    const userAvatarElement = document.querySelector('.user-avatar');
    
    if (userNameElement && user.full_name) {
        userNameElement.textContent = user.full_name;
    }
    
    if (userRoleElement && user.role) {
        userRoleElement.textContent = getRoleDisplayName(user.role);
    }
    
    if (userAvatarElement && user.full_name) {
        userAvatarElement.textContent = user.full_name.charAt(0).toUpperCase();
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

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('active');
}

// Закрытие сайдбара при клике вне его области
document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.mobile-menu-toggle');
    if (window.innerWidth <= 1024 && !sidebar.contains(event.target) && !toggle.contains(event.target)) {
        sidebar.classList.remove('active');
    }
});

// Функция для выполнения запросов с авторизацией
async function makeAuthenticatedRequest(url, options = {}) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/auth/login';
        return;
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        if (response.status === 401) {
            // Токен истек или недействителен
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            window.location.href = '/auth/login';
            return;
        }

        return response;
    } catch (error) {
        console.error('Request error:', error);
        throw error;
    }
}

// Обработчик выхода из системы
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/auth/login';
}

// Обновляем все ссылки на выход
document.addEventListener('DOMContentLoaded', function() {
    const logoutLinks = document.querySelectorAll('a[href="/logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    });
});

// Функции для загрузки данных с аутентификацией
async function loadDashboardStats() {
    try {
        const response = await makeAuthenticatedRequest('/dashboard/api/stats');
        if (response && response.ok) {
            const stats = await response.json();
            updateStatsDisplay(stats);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadRecentRequests() {
    try {
        const response = await makeAuthenticatedRequest('/dashboard/api/requests');
        if (response && response.ok) {
            const requests = await response.json();
            updateRequestsTable(requests.slice(0, 5)); // Показываем последние 5
        }
    } catch (error) {
        console.error('Error loading requests:', error);
    }
}

function updateStatsDisplay(stats) {
    // Обновляем статистику на странице
    const statCards = document.querySelectorAll('.stat-card');
    if (statCards.length >= 4 && stats) {
        // Обновляем значения статистики
        const activeRequests = statCards[0].querySelector('.stat-value');
        const completedRequests = statCards[1].querySelector('.stat-value');
        const monthlyRevenue = statCards[2].querySelector('.stat-value');
        const avgTime = statCards[3].querySelector('.stat-value');

        if (activeRequests) activeRequests.textContent = stats.active_requests || '0';
        if (completedRequests) completedRequests.textContent = stats.completed_requests || '0';
        if (monthlyRevenue) monthlyRevenue.textContent = `₽${stats.monthly_revenue || '0'}`;
        if (avgTime) avgTime.textContent = `${stats.avg_repair_time || '0'}ч`;
    }
}

function updateRequestsTable(requests) {
    const tbody = document.querySelector('table tbody');
    if (!tbody || !requests) return;

    tbody.innerHTML = requests.map(request => `
        <tr>
            <td>#${request.request_id}</td>
            <td>${request.client_name || 'Не указано'}</td>
            <td>${request.device_type || 'Не указано'}</td>
            <td>${request.problem_description ? request.problem_description.substring(0, 50) + '...' : 'Не указано'}</td>
            <td><span class="status-badge ${getStatusClass(request.status)}">${request.status}</span></td>
            <td>${request.master_name || '-'}</td>
            <td>${formatDate(request.created_at)}</td>
            <td>
                <button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;" 
                        onclick="viewRequestDetails('${request.request_id}')">
                    Подробнее
                </button>
            </td>
        </tr>
    `).join('');
}

function getStatusClass(status) {
    const statusMap = {
        'Принята': 'status-new',
        'Диагностика': 'status-in-progress',
        'Ожидание запчастей': 'status-pending',
        'В ремонте': 'status-in-progress',
        'Тестирование': 'status-in-progress',
        'Готова к выдаче': 'status-completed',
        'Выдана': 'status-completed'
    };
    return statusMap[status] || 'status-new';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU');
}

function viewRequestDetails(requestId) {
    // Перенаправляем на страницу детальной информации о заявке
    window.location.href = `/dashboard/requests?id=${requestId}`;
}

function drawWeeklyChart() {
    const canvas = document.getElementById('weeklyChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Простой график-заглушка
    ctx.fillStyle = "#00ffff";
    ctx.font = "16px Arial";
    ctx.fillText("График заявок за неделю", 20, 100);
    ctx.fillText("(здесь будет реальный график)", 20, 130);
}

function drawStatusChart() {
    const canvas = document.getElementById('statusChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Простой график-заглушка
    ctx.fillStyle = "#00ffff";
    ctx.font = "16px Arial";
    ctx.fillText("Распределение по статусам", 20, 100);
    ctx.fillText("(здесь будет круговая диаграмма)", 20, 130);
}

// Загружаем данные при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        loadDashboardStats();
        loadRecentRequests();
    }, 500);
});


setInterval(() => {
    loadDashboardStats();
    loadRecentRequests();
}, 30000);