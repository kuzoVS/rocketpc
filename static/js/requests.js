// Глобальные переменные
let allRequests = [];
let filteredRequests = [];
let currentPage = 1;
let itemsPerPage = 10;
let sortField = 'date';
let sortOrder = 'desc';
let currentEditRequestId = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    console.log('📄 Инициализация страницы заявок...');

    // Показываем страницу
    document.getElementById('pageBody').style.display = 'block';

    // Загружаем информацию о пользователе
    loadUserInfo();

    // Загружаем заявки
    await loadRequests();

    // Настраиваем обработчики форм
    setupFormHandlers();

    // Настраиваем обработчики для выхода
    setupLogoutHandlers();
});

// Загрузка информации о пользователе
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

// Загрузка заявок с использованием существующего API
async function loadRequests() {
    console.log('📋 Загружаем заявки...');

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/dashboard/api/requests', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            console.log('❌ 401 - перенаправляем на login');
            logout();
            return;
        }

        if (response.ok) {
            allRequests = await response.json();
            console.log(`✅ Загружено ${allRequests.length} заявок`);

            // Применяем фильтры
            filterRequests();
        } else {
            console.log('❌ Ошибка загрузки:', response.status);
            showNotification('Ошибка загрузки заявок', 'error');
        }
    } catch (error) {
        console.error('❌ Ошибка:', error);
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

// Создание новой заявки через существующий API
async function createRequest(requestData) {
    try {
        console.log('📝 Отправка данных:', requestData);

        // Используем открытый эндпоинт /api/requests для создания заявки
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const responseText = await response.text();
        console.log('📡 Ответ сервера:', response.status, responseText);

        let result;
        try {
            result = JSON.parse(responseText);
        } catch (e) {
            console.error('❌ Ошибка парсинга JSON:', e);
            showNotification('Ошибка сервера: неверный формат ответа', 'error');
            return;
        }

        if (response.ok) {
            showNotification(`Заявка создана! ID: ${result.id}`, 'success');
            closeModal('newRequestModal');
            await loadRequests(); // Перезагружаем список
            return result;
        } else {
            // Обрабатываем разные типы ошибок
            let errorMessage = 'Ошибка создания заявки';

            if (result.detail) {
                if (typeof result.detail === 'string') {
                    errorMessage = result.detail;
                } else if (Array.isArray(result.detail)) {
                    // Если это массив ошибок валидации от FastAPI
                    errorMessage = result.detail.map(err => err.msg).join(', ');
                } else if (typeof result.detail === 'object') {
                    errorMessage = JSON.stringify(result.detail);
                }
            } else if (result.message) {
                errorMessage = result.message;
            }

            console.error('❌ Ошибка от сервера:', errorMessage);
            showNotification(errorMessage, 'error');
        }
    } catch (error) {
        console.error('❌ Ошибка создания заявки:', error);
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

// Обновление статуса заявки через API
async function updateRequestStatus(requestId, newStatus, comment = '') {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/dashboard/api/requests/${requestId}/status`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: newStatus,
                comment: comment
            })
        });

        if (response.ok) {
            showNotification('Статус обновлен', 'success');
            closeModal('editRequestModal');
            await loadRequests();
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Ошибка обновления', 'error');
        }
    } catch (error) {
        console.error('❌ Ошибка обновления:', error);
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

// Архивирование заявки
async function archiveRequest(requestId) {
    if (!confirm('Вы уверены, что хотите архивировать эту заявку?')) return;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/dashboard/api/requests/${requestId}/archive`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            showNotification('Заявка архивирована', 'success');
            await loadRequests();
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Ошибка архивирования', 'error');
        }
    } catch (error) {
        console.error('❌ Ошибка архивирования:', error);
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

// Настройка обработчиков форм
function setupFormHandlers() {
    // Форма создания заявки
    const newRequestForm = document.getElementById('newRequestForm');
    if (newRequestForm) {
        newRequestForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Собираем данные из формы
            const clientName = document.getElementById('clientName').value.trim();
            const clientPhone = document.getElementById('clientPhone').value.trim();
            const clientEmail = document.getElementById('clientEmail').value.trim();
            const deviceType = document.getElementById('deviceType').value;
            const deviceBrand = document.getElementById('deviceBrand').value.trim();
            const deviceModel = document.getElementById('deviceModel').value.trim();
            const problemDescription = document.getElementById('problemDescription').value.trim();
            const priority = document.getElementById('priority').value || 'Обычная';

            // Базовая валидация
            if (!clientName || clientName.length < 2) {
                showNotification('Имя клиента должно содержать минимум 2 символа', 'error');
                return;
            }

            if (!clientPhone || clientPhone.length < 10) {
                showNotification('Телефон должен содержать минимум 10 символов', 'error');
                return;
            }

            if (!deviceType) {
                showNotification('Выберите тип устройства', 'error');
                return;
            }

            if (!problemDescription || problemDescription.length < 10) {
                showNotification('Описание проблемы должно содержать минимум 10 символов', 'error');
                return;
            }

            const requestData = {
                client_name: clientName,
                phone: clientPhone,
                email: clientEmail || '',
                device_type: deviceType,
                problem_description: problemDescription,
                priority: priority
            };

            // Добавляем дополнительные поля если они заполнены
            if (deviceBrand) requestData.brand = deviceBrand;
            if (deviceModel) requestData.model = deviceModel;

            // Показываем индикатор загрузки
            const submitButton = e.target.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Создание...';

            try {
                await createRequest(requestData);
            } finally {
                // Восстанавливаем кнопку
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }
}
    // Форма редактирования заявки
    // Форма редактирования заявки
const editRequestForm = document.getElementById('editRequestForm');
if (editRequestForm) {
    editRequestForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const newStatus = document.getElementById('editStatus').value;
        const comment = document.getElementById('editComment').value;
        const masterId = document.getElementById('editMaster').value; // Добавить
        const estimatedCost = document.getElementById('editEstimatedCost').value; // Добавить

        // Показываем индикатор загрузки
        const submitButton = e.target.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Сохранение...';

        try {
            // Обновляем статус
            await updateRequestStatus(currentEditRequestId, newStatus, comment);

            // Если изменился мастер, обновляем назначение
            if (masterId !== undefined) {
                await updateMasterAssignment(currentEditRequestId, masterId);
            }

            // Если изменилась стоимость, обновляем её
            if (estimatedCost) {
                await updateEstimatedCost(currentEditRequestId, estimatedCost);
            }

        } finally {
            // Восстанавливаем кнопку
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    });
}

// Обновление назначения мастера
async function updateMasterAssignment(requestId, masterId) {
    try {
        const token = localStorage.getItem('access_token');

        if (masterId) {
            // Назначаем мастера
            await fetch(`/dashboard/api/requests/${requestId}/assign-master`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ master_id: parseInt(masterId) })
            });
        } else {
            // Снимаем мастера
            await fetch(`/dashboard/api/requests/${requestId}/unassign-master`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
        }
    } catch (error) {
        console.error('❌ Ошибка обновления мастера:', error);
    }
}

// Фильтрация заявок
function filterRequests() {
    const searchValue = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const priorityFilter = document.getElementById('priorityFilter').value;
    const periodFilter = document.getElementById('periodFilter').value;

    filteredRequests = allRequests.filter(request => {
        // Поиск по тексту
        if (searchValue) {
            const searchMatch =
                request.request_id.toLowerCase().includes(searchValue) ||
                request.client_name.toLowerCase().includes(searchValue) ||
                request.device_type.toLowerCase().includes(searchValue) ||
                (request.problem_description || '').toLowerCase().includes(searchValue);

            if (!searchMatch) return false;
        }

        // Фильтр по статусу
        if (statusFilter && request.status !== statusFilter) return false;

        // Фильтр по приоритету
        if (priorityFilter && request.priority !== priorityFilter) return false;

        // Фильтр по периоду
        if (periodFilter) {
            const requestDate = new Date(request.created_at);
            const now = new Date();

            switch (periodFilter) {
                case 'today':
                    if (requestDate.toDateString() !== now.toDateString()) return false;
                    break;
                case 'week':
                    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    if (requestDate < weekAgo) return false;
                    break;
                case 'month':
                    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                    if (requestDate < monthAgo) return false;
                    break;
            }
        }

        return true;
    });

    // Сортируем и отображаем
    sortRequests();
    currentPage = 1;
    displayRequests();
}

// Сортировка заявок
function sortTable(field) {
    if (sortField === field) {
        sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        sortField = field;
        sortOrder = 'asc';
    }

    sortRequests();
    displayRequests();
}

function sortRequests() {
    filteredRequests.sort((a, b) => {
        let valueA, valueB;

        switch (sortField) {
            case 'id':
                valueA = a.request_id;
                valueB = b.request_id;
                break;
            case 'client':
                valueA = a.client_name;
                valueB = b.client_name;
                break;
            case 'device':
                valueA = a.device_type;
                valueB = b.device_type;
                break;
            case 'status':
                valueA = a.status;
                valueB = b.status;
                break;
            case 'priority':
                const priorityOrder = { 'Критическая': 4, 'Высокая': 3, 'Обычная': 2, 'Низкая': 1 };
                valueA = priorityOrder[a.priority] || 2;
                valueB = priorityOrder[b.priority] || 2;
                break;
            case 'date':
                valueA = new Date(a.created_at);
                valueB = new Date(b.created_at);
                break;
            default:
                valueA = a[sortField];
                valueB = b[sortField];
        }

        if (valueA < valueB) return sortOrder === 'asc' ? -1 : 1;
        if (valueA > valueB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
    });
}

// Отображение заявок в таблице
function displayRequests() {
    const tbody = document.getElementById('requestsTableBody');

    if (filteredRequests.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 3rem; color: rgba(255,255,255,0.6);">Заявки не найдены</td></tr>';
        document.getElementById('pagination').innerHTML = '';
        return;
    }

    // Расчет пагинации
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageRequests = filteredRequests.slice(startIndex, endIndex);

    // Генерация HTML таблицы
    tbody.innerHTML = pageRequests.map(request => {
        const statusClass = getStatusClass(request.status);
        const priorityClass = getPriorityClass(request.priority);

        return `
            <tr>
                <td style="color: #00ffff; font-weight: bold;">#${request.request_id}</td>
                <td>${request.client_name}</td>
                <td>${request.device_type} ${request.brand ? `(${request.brand})` : ''}</td>
                <td title="${request.problem_description}">${truncateText(request.problem_description, 50)}</td>
                <td><span class="status-badge ${statusClass}">${request.status}</span></td>
                <td><span class="priority-badge ${priorityClass}">${request.priority || 'Обычная'}</span></td>
                <td>${request.master_name || '-'}</td>
                <td>${formatDate(request.created_at)}</td>
                <td>
                    <div class="table-actions">
                        <button class="btn btn-icon btn-edit" onclick="openEditModal('${request.request_id}')" title="Редактировать">
                            ✏️
                        </button>
                        <button class="btn btn-icon btn-delete" onclick="archiveRequest('${request.request_id}')" title="Архивировать">
                            📁
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    // Обновляем пагинацию
    updatePagination();
}

// Обновление пагинации
function updatePagination() {
    const totalPages = Math.ceil(filteredRequests.length / itemsPerPage);
    const pagination = document.getElementById('pagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';

    // Кнопка "Назад"
    html += `<button class="page-btn" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
        ← Назад
    </button>`;

    // Номера страниц
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">
                ${i}
            </button>`;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += '<span style="color: rgba(255,255,255,0.5);">...</span>';
        }
    }

    // Кнопка "Вперед"
    html += `<button class="page-btn" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
        Вперед →
    </button>`;

    pagination.innerHTML = html;
}

// Изменение страницы
function changePage(page) {
    const totalPages = Math.ceil(filteredRequests.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;

    currentPage = page;
    displayRequests();
}

// Открытие модального окна создания заявки
function openNewRequestModal() {
    document.getElementById('newRequestForm').reset();
    document.getElementById('priority').value = 'Обычная';
    document.querySelectorAll('.status-option').forEach(btn => {
        btn.classList.toggle('active', btn.textContent === 'Обычная');
    });
    openModal('newRequestModal');
}

// Открытие модального окна редактирования

// Открытие модального окна редактирования
async function openEditModal(requestId) {
    const request = allRequests.find(r => r.request_id === requestId);
    if (!request) return;

    currentEditRequestId = requestId;

    // Заполняем информацию о заявке
    document.getElementById('editRequestId').textContent = `#${request.request_id}`;
    document.getElementById('editCreatedAt').textContent = formatDate(request.created_at);
    document.getElementById('editClientInfo').textContent = `${request.client_name} (${request.client_phone})`;
    document.getElementById('editDeviceInfo').textContent = `${request.device_type} ${request.brand || ''} ${request.model || ''}`;
    document.getElementById('editProblemDescription').value = request.problem_description;
    document.getElementById('editStatus').value = request.status;
    document.getElementById('editPriority').value = request.priority || 'Обычная';

    // Загружаем список мастеров
    await loadMasters();

    // Устанавливаем текущего мастера
    const masterSelect = document.getElementById('editMaster');
    if (masterSelect && request.assigned_master_id) {
        masterSelect.value = request.assigned_master_id;
    }

    // Сбрасываем комментарий
    document.getElementById('editComment').value = '';

    openModal('editRequestModal');
}

async function loadMasters() {
    try {
        console.log('🔄 Загружаем мастеров...');
        const token = localStorage.getItem('access_token');
        const response = await fetch('/dashboard/api/masters/available', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        console.log('📡 Ответ API:', response.status);
        if (response.ok) {
            const masters = await response.json();
            const masterSelect = document.getElementById('editMaster');
            console.log('🎯 Select элемент:', masterSelect);

            if (masterSelect) {
                masterSelect.innerHTML = '<option value="">Не назначен</option>';

                masters.forEach(master => {
                    const option = document.createElement('option');
                    option.value = master.id;
                    option.textContent = `${master.full_name} (Активных: ${master.active_repairs}/${master.max_concurrent_repairs})`;

                    // Добавляем специализацию если есть
                    if (master.specialization) {
                        option.textContent += ` - ${master.specialization}`;
                    }

                    // Отключаем если мастер перегружен
                    if (!master.is_available || master.active_repairs >= master.max_concurrent_repairs) {
                        option.disabled = true;
                        option.textContent += ' (Недоступен)';
                    }

                    masterSelect.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки мастеров:', error);
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
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// Управление модальными окнами
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Установка приоритета
function setPriority(button, priority) {
    document.querySelectorAll('.status-option').forEach(btn => {
        btn.classList.remove('active');
    });
    button.classList.add('active');
    document.getElementById('priority').value = priority;
}

// Показ уведомлений
function showNotification(message, type = 'success') {
    // Удаляем старые уведомления
    document.querySelectorAll('.notification').forEach(el => el.remove());

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? 'rgba(255, 0, 0, 0.2)' : 'rgba(0, 255, 0, 0.2)'};
        border: 1px solid ${type === 'error' ? 'rgba(255, 0, 0, 0.3)' : 'rgba(0, 255, 0, 0.3)'};
        color: ${type === 'error' ? '#ff4444' : '#00ff00'};
        border-radius: 12px;
        z-index: 3000;
        animation: slideInRight 0.4s ease-out;
        max-width: 400px;
        word-wrap: break-word;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.4s ease-out';
        setTimeout(() => notification.remove(), 400);
    }, 4000);
}

// Экспорт заявок
function exportRequests() {
    const csvContent = [
        ['ID', 'Клиент', 'Телефон', 'Устройство', 'Проблема', 'Статус', 'Приоритет', 'Дата'],
        ...filteredRequests.map(r => [
            r.request_id,
            r.client_name,
            r.client_phone || '',
            `${r.device_type} ${r.brand || ''} ${r.model || ''}`,
            r.problem_description,
            r.status,
            r.priority || 'Обычная',
            formatDate(r.created_at)
        ])
    ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `заявки_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
}

// Переключение sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('active');
}

// Выход из системы
function logout() {
    console.log('🚪 Выход из системы');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.replace('/auth/login');
}

// Настройка обработчиков выхода
function setupLogoutHandlers() {
    document.querySelectorAll('a[href="#logout"]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    });
}

// Закрытие модальных окон по клику вне их
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

console.log('✅ Скрипт управления заявками загружен');