// Управление заявками - requests.js
console.log('🚀 Requests JS загружен');

let allRequests = [];
let filteredRequests = [];
let currentPage = 1;
const itemsPerPage = 10;

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', async function() {
    console.log('📄 DOM загружен');

    try {
        // Показываем body
        document.getElementById('pageBody').style.display = 'block';

        // Проверяем аутентификацию
        await checkAuthentication();

        // Загружаем пользовательскую информацию
        loadUserInfo();

        // Скрываем loader и показываем контент
        hideLoaderAndShowContent();

        // Загружаем заявки
        await loadRequests();

        // Инициализируем обработчики событий
        initializeEventHandlers();

    } catch (error) {
        console.error('❌ Ошибка загрузки информации о пользователе:', error);
    }
}

function hideLoaderAndShowContent() {
    const loader = document.getElementById('authCheckLoader');
    const content = document.getElementById('dashboardContent');

    if (loader) loader.style.display = 'none';
    if (content) content.style.display = 'block';
}

function redirectToLogin() {
    window.location.replace('/auth/login');
}

// Загрузка заявок
async function loadRequests() {
    console.log('📋 Загрузка заявок...');

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/dashboard/api/requests', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            redirectToLogin();
            return;
        }

        if (response.ok) {
            allRequests = await response.json();
            filteredRequests = [...allRequests];
            console.log(`✅ Загружено ${allRequests.length} заявок`);

            updateRequestsTable();
            updateTableInfo();
        } else {
            showError('Не удалось загрузить заявки');
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки заявок:', error);
        showError('Ошибка подключения к серверу');
    }
}

// Обновление таблицы заявок
function updateRequestsTable() {
    const tbody = document.getElementById('requestsTableBody');
    if (!tbody) return;

    if (filteredRequests.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 3rem; color: rgba(255,255,255,0.6);">
                    📝 Заявки не найдены
                </td>
            </tr>
        `;
        return;
    }

    // Пагинация
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageRequests = filteredRequests.slice(startIndex, endIndex);

    tbody.innerHTML = pageRequests.map(request => `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1);" onmouseover="this.style.background='rgba(0, 255, 255, 0.05)'" onmouseout="this.style.background='transparent'">
            <td style="padding: 1rem; font-weight: bold; color: #00ffff;">#${request.request_id}</td>
            <td style="padding: 1rem;">
                <div style="font-weight: 600;">${request.client_name || 'Не указано'}</div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">${request.client_phone || ''}</div>
            </td>
            <td style="padding: 1rem;">
                <div>${request.device_type || 'Не указано'}</div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">${request.brand ? `${request.brand} ${request.model || ''}` : ''}</div>
            </td>
            <td style="padding: 1rem; max-width: 200px;">
                <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${request.problem_description || ''}">
                    ${truncateText(request.problem_description || 'Не указано', 50)}
                </div>
            </td>
            <td style="padding: 1rem;">
                <span class="status-badge ${getStatusClass(request.status)}" style="
                    display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px;
                    font-size: 0.85rem; font-weight: 600;
                ">${request.status}</span>
            </td>
            <td style="padding: 1rem;">
                <span class="priority-badge ${getPriorityClass(request.priority)}" style="
                    display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px;
                    font-size: 0.8rem; font-weight: 600;
                ">${request.priority || 'Обычная'}</span>
            </td>
            <td style="padding: 1rem;">
                <div>${request.estimated_cost ? `₽${formatMoney(request.estimated_cost)}` : '-'}</div>
                ${request.final_cost ? `<div style="font-size: 0.85rem; color: #00ff00;">Итого: ₽${formatMoney(request.final_cost)}</div>` : ''}
            </td>
            <td style="padding: 1rem;">
                <div>${formatDate(request.created_at)}</div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">${formatTime(request.created_at)}</div>
            </td>
            <td style="padding: 1rem; text-align: center;">
                <div style="display: flex; gap: 0.5rem; justify-content: center;">
                    <button onclick="editRequest('${request.request_id}')" class="btn btn-outline" style="
                        padding: 0.5rem; font-size: 0.8rem; min-width: auto;
                    " title="Редактировать">
                        ✏️
                    </button>
                    <button onclick="viewRequestDetails('${request.request_id}')" class="btn btn-outline" style="
                        padding: 0.5rem; font-size: 0.8rem; min-width: auto;
                    " title="Подробности">
                        👁️
                    </button>
                </div>
            </td>
        </tr>
    `).join('');

    updatePagination();
}

// Фильтрация
function applyFilters() {
    const statusFilter = document.getElementById('statusFilter').value;
    const deviceTypeFilter = document.getElementById('deviceTypeFilter').value;
    const searchFilter = document.getElementById('searchFilter').value.toLowerCase();

    filteredRequests = allRequests.filter(request => {
        const matchesStatus = !statusFilter || request.status === statusFilter;
        const matchesDeviceType = !deviceTypeFilter || request.device_type === deviceTypeFilter;
        const matchesSearch = !searchFilter ||
            request.request_id.toLowerCase().includes(searchFilter) ||
            (request.client_name && request.client_name.toLowerCase().includes(searchFilter)) ||
            (request.problem_description && request.problem_description.toLowerCase().includes(searchFilter));

        return matchesStatus && matchesDeviceType && matchesSearch;
    });

    currentPage = 1;
    updateRequestsTable();
    updateTableInfo();
}

function resetFilters() {
    document.getElementById('statusFilter').value = '';
    document.getElementById('deviceTypeFilter').value = '';
    document.getElementById('searchFilter').value = '';
    filteredRequests = [...allRequests];
    currentPage = 1;
    updateRequestsTable();
    updateTableInfo();
}

// Пагинация
function updatePagination() {
    const totalPages = Math.ceil(filteredRequests.length / itemsPerPage);
    const pagination = document.getElementById('pagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let paginationHTML = '';

    // Предыдущая страница
    if (currentPage > 1) {
        paginationHTML += `<button onclick="changePage(${currentPage - 1})" class="btn btn-outline">← Предыдущая</button>`;
    }

    // Номера страниц
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        const activeClass = i === currentPage ? 'btn' : 'btn btn-outline';
        paginationHTML += `<button onclick="changePage(${i})" class="${activeClass}">${i}</button>`;
    }

    // Следующая страница
    if (currentPage < totalPages) {
        paginationHTML += `<button onclick="changePage(${currentPage + 1})" class="btn btn-outline">Следующая →</button>`;
    }

    pagination.innerHTML = paginationHTML;
}

function changePage(page) {
    currentPage = page;
    updateRequestsTable();
}

function updateTableInfo() {
    const tableInfo = document.getElementById('tableInfo');
    if (tableInfo) {
        const total = allRequests.length;
        const filtered = filteredRequests.length;
        const showing = Math.min(itemsPerPage, filtered - (currentPage - 1) * itemsPerPage);

        if (total === filtered) {
            tableInfo.textContent = `Показано ${showing} из ${total} заявок`;
        } else {
            tableInfo.textContent = `Показано ${showing} из ${filtered} (всего ${total}) заявок`;
        }
    }
}

// Редактирование заявки
function editRequest(requestId) {
    const request = allRequests.find(r => r.request_id === requestId);
    if (!request) return;

    // Заполняем форму редактирования
    document.getElementById('editRequestId').value = request.request_id;
    document.getElementById('editStatus').value = request.status;
    document.getElementById('editPriority').value = request.priority || 'Обычная';
    document.getElementById('editEstimatedCost').value = request.estimated_cost || '';
    document.getElementById('editComment').value = '';

    // Показываем модальное окно
    document.getElementById('editRequestModal').style.display = 'block';
}

function closeEditRequestModal() {
    document.getElementById('editRequestModal').style.display = 'none';
}

// Создание новой заявки
function openCreateRequestModal() {
    document.getElementById('createRequestModal').style.display = 'block';
}

function closeCreateRequestModal() {
    document.getElementById('createRequestModal').style.display = 'none';
    document.getElementById('createRequestForm').reset();
}

// Обработчики событий
function initializeEventHandlers() {
    // Форма редактирования
    document.getElementById('editRequestForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await updateRequest();
    });

    // Форма создания
    document.getElementById('createRequestForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createRequest();
    });

    // Закрытие модальных окон при клике вне их
    window.onclick = function(event) {
        const editModal = document.getElementById('editRequestModal');
        const createModal = document.getElementById('createRequestModal');

        if (event.target === editModal) {
            closeEditRequestModal();
        }
        if (event.target === createModal) {
            closeCreateRequestModal();
        }
    };

    // Обработчики logout
    const logoutLinks = document.querySelectorAll('a[href="#logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    });
}

// Обновление заявки
async function updateRequest() {
    const requestId = document.getElementById('editRequestId').value;
    const status = document.getElementById('editStatus').value;
    const comment = document.getElementById('editComment').value;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/dashboard/api/requests/${requestId}/status`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status, comment })
        });

        if (response.ok) {
            showSuccess('Заявка успешно обновлена');
            closeEditRequestModal();
            await loadRequests(); // Перезагружаем список
        } else {
            const error = await response.json();
            showError(error.detail || 'Ошибка при обновлении заявки');
        }
    } catch (error) {
        console.error('❌ Ошибка обновления заявки:', error);
        showError('Ошибка подключения к серверу');
    }
}

// Создание заявки
async function createRequest() {
    const formData = {
        client_name: document.getElementById('createClientName').value,
        phone: document.getElementById('createClientPhone').value,
        email: document.getElementById('createClientEmail').value,
        device_type: document.getElementById('createDeviceType').value,
        brand: document.getElementById('createBrand').value,
        model: document.getElementById('createModel').value,
        problem_description: document.getElementById('createProblemDescription').value,
        priority: document.getElementById('createPriority').value
    };

    try {
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            const result = await response.json();
            showSuccess(`Заявка успешно создана! Номер: ${result.id}`);
            closeCreateRequestModal();
            await loadRequests(); // Перезагружаем список
        } else {
            const error = await response.json();
            showError(error.detail || 'Ошибка при создании заявки');
        }
    } catch (error) {
        console.error('❌ Ошибка создания заявки:', error);
        showError('Ошибка подключения к серверу');
    }
}

// Вспомогательные функции
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

function getPriorityClass(priority) {
    const priorityMap = {
        'Низкая': 'priority-low',
        'Обычная': 'priority-normal',
        'Высокая': 'priority-high',
        'Критическая': 'priority-critical'
    };
    return priorityMap[priority] || 'priority-normal';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('ru-RU');
}

function formatTime(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function formatMoney(amount) {
    return new Intl.NumberFormat('ru-RU').format(amount);
}

function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('active');
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.replace('/auth/login');
}

function viewRequestDetails(requestId) {
    // Пока просто показываем alert, позже можно сделать детальное модальное окно
    const request = allRequests.find(r => r.request_id === requestId);
    if (request) {
        alert(`Детали заявки ${requestId}:\n\nКлиент: ${request.client_name}\nУстройство: ${request.device_type}\nПроблема: ${request.problem_description}\nСтатус: ${request.status}`);
    }
}

// Уведомления
function showSuccess(message) {
    // Простое уведомление, можно заменить на более красивое
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 10000;
        background: linear-gradient(45deg, #00ff00, #00cc00);
        color: #000; padding: 1rem 2rem; border-radius: 8px;
        font-weight: 600; animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = `✅ ${message}`;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function showError(message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 10000;
        background: linear-gradient(45deg, #ff4444, #cc0000);
        color: #fff; padding: 1rem 2rem; border-radius: 8px;
        font-weight: 600; animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = `❌ ${message}`;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

console.log('✅ Requests JS инициализирован');error) {
        console.error('❌ Ошибка инициализации:', error);
        redirectToLogin();
    }
});

async function checkAuthentication() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        throw new Error('No token found');
    }

    const response = await fetch('/auth/profile', {
        headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        throw new Error('Token validation failed');
    }

    return await response.json();
}

function loadUserInfo() {
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');

        const userName = document.getElementById('userName');
        const userRole = document.getElementById('userRole');
        const userAvatar = document.getElementById('userAvatar');

        if (userName && user.full_name) userName.textContent = user.full_name;
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
    } catch (