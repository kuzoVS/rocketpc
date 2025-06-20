// Глобальные переменные
let allClients = [];
let filteredClients = [];
let currentPage = 1;
let itemsPerPage = 12;
let sortField = 'name';
let sortOrder = 'asc';
let currentClientId = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    console.log('👥 Инициализация страницы клиентов...');

    // Загружаем информацию о пользователе
    await loadUserInfo();

    // Загружаем клиентов
    await loadClients();

    // Загружаем статистику
    await loadClientStatistics();

    // Настраиваем обработчики форм
    setupFormHandlers();

    // Настраиваем обработчики для выхода
    setupLogoutHandlers();

    // Проверяем предзаполненные данные клиента из localStorage
    checkPreselectedClient();

    console.log('✅ Страница клиентов готова к работе');
});

// Загрузка информации о пользователе
async function loadUserInfo() {
    try {
        const res = await fetch("/auth/profile", {
            credentials: "include"
        });

        if (res.status === 401) {
            window.location.href = "/auth/login";
            return;
        }

        if (!res.ok) throw new Error("Ошибка загрузки профиля");

        const user = await res.json();

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

        // Показываем пункт "Пользователи" для админов/директоров
        if (user.role === 'admin' || user.role === 'director') {
            const usersMenuItem = document.getElementById('usersMenuItem');
            if (usersMenuItem) usersMenuItem.style.display = 'block';
        }

    } catch (err) {
        console.error("❌ Ошибка загрузки профиля:", err);
        window.location.href = "/auth/login";
    }
}

// Загрузка клиентов
async function loadClients(force = false) {
    try {
        console.log('👥 Загружаем клиентов...');

        const response = await fetch('/api/clients', {
            credentials: 'include'
        });

        if (response.status === 401) {
            console.log('❌ 401 - перенаправляем на login');
            window.location.href = "/auth/login";
            return;
        }

        if (response.ok) {
            allClients = await response.json();
            console.log(`✅ Загружено ${allClients.length} клиентов`);

            // Применяем фильтры и отображаем
            filterAndDisplayClients();
        } else {
            console.log('❌ Ошибка загрузки:', response.status);
            showNotification('Ошибка загрузки клиентов', 'error');
            showEmptyState('Ошибка загрузки данных');
        }
    } catch (error) {
        console.error('❌ Ошибка:', error);
        showNotification('Ошибка подключения к серверу', 'error');
        showEmptyState('Ошибка загрузки данных');
    }
}

// Загрузка статистики клиентов
async function loadClientStatistics() {
    try {
        console.log('📊 Загружаем статистику клиентов...');

        const response = await fetch('/api/clients/statistics', {
            method: 'GET',
            credentials: 'include'
        });

        if (response.ok) {
            const stats = await response.json();
            console.log('✅ Статистика загружена:', stats);

            // Обновляем элементы статистики
            updateStatElement('totalClientsCount', stats.total_clients || 0);
            updateStatElement('vipClientsCount', stats.vip_clients || 0);
            updateStatElement('newClientsMonth', stats.new_clients_month || 0);
            updateStatElement('avgRepairsPerClient', (stats.avg_repairs_per_client || 0).toFixed(1));
        } else {
            console.log('⚠️ Не удалось загрузить статистику');
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки статистики:', error);
    }
}

function updateStatElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

// Фильтрация и отображение клиентов
function filterAndDisplayClients() {
    // Применяем поиск
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const filterBy = document.getElementById('filterBy').value;

    filteredClients = allClients.filter(client => {
        // Поиск по тексту
        if (searchTerm) {
            const searchMatch =
                client.full_name.toLowerCase().includes(searchTerm) ||
                client.phone.toLowerCase().includes(searchTerm) ||
                (client.email && client.email.toLowerCase().includes(searchTerm));

            if (!searchMatch) return false;
        }

        // Фильтр по типу
        switch (filterBy) {
            case 'vip':
                return client.is_vip;
            case 'active':
                return (client.active_requests || 0) > 0;
            case 'new':
                const createdDate = new Date(client.created_at);
                const monthAgo = new Date();
                monthAgo.setMonth(monthAgo.getMonth() - 1);
                return createdDate > monthAgo;
            default:
                return true;
        }
    });

    // Сортируем
    sortFilteredClients(); // Изменено название функции

    // Отображаем
    currentPage = 1;
    displayClients();

    // Обновляем счетчик
    document.getElementById('clientsCount').textContent = `${filteredClients.length} клиентов`;
}

// Сортировка клиентов
function sortFilteredClients() {
    const sortBy = document.getElementById('sortBy').value;

    filteredClients.sort((a, b) => {
        let valueA, valueB;

        switch (sortBy) {
            case 'name':
                valueA = a.full_name.toLowerCase();
                valueB = b.full_name.toLowerCase();
                break;
            case 'date':
                valueA = new Date(a.created_at);
                valueB = new Date(b.created_at);
                break;
            case 'repairs':
                valueA = a.total_requests || 0;
                valueB = b.total_requests || 0;
                break;
            case 'spending':
                valueA = a.total_spent || 0;
                valueB = b.total_spent || 0;
                break;
            default:
                valueA = a.full_name.toLowerCase();
                valueB = b.full_name.toLowerCase();
        }

        if (valueA < valueB) return sortOrder === 'asc' ? -1 : 1;
        if (valueA > valueB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
    });
}

// Отображение клиентов
function displayClients() {
    const container = document.getElementById('clientsGrid');

    if (filteredClients.length === 0) {
        showEmptyState();
        return;
    }

    // Расчет пагинации
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageClients = filteredClients.slice(startIndex, endIndex);

    // Генерация HTML карточек
    container.innerHTML = pageClients.map(client => createClientCard(client)).join('');

    // Обновляем пагинацию
    updatePagination();
}

// Создание карточки клиента
function createClientCard(client) {
    const avatar = client.full_name.charAt(0).toUpperCase();
    const vipBadge = client.is_vip ? '<div class="vip-badge">VIP</div>' : '';
    const totalSpent = client.total_spent || 0;
    const totalRequests = client.total_requests || 0;
    const activeRequests = client.active_requests || 0;

    return `
        <div class="client-card" onclick="openClientDetail(${client.id})">
            ${vipBadge}
            <div class="client-avatar">${avatar}</div>
            <div class="client-name">${client.full_name}</div>
            <div class="client-info">
                <span>📞</span> ${client.phone}
            </div>
            ${client.email ? `
                <div class="client-info">
                    <span>📧</span> ${client.email}
                </div>
            ` : ''}
            <div class="client-info">
                <span>📅</span> ${formatDate(client.created_at)}
            </div>
            <div class="client-stats">
                <div class="client-stat">
                    <div class="client-stat-value">${totalRequests}</div>
                    <div class="client-stat-label">Заявок</div>
                </div>
                <div class="client-stat">
                    <div class="client-stat-value">${activeRequests}</div>
                    <div class="client-stat-label">Активных</div>
                </div>
                <div class="client-stat">
                    <div class="client-stat-value">₽${totalSpent.toLocaleString('ru-RU')}</div>
                    <div class="client-stat-label">Потрачено</div>
                </div>
            </div>
            <div class="client-actions">
                <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); openClientDetail(${client.id})">
                    👁️ Подробнее
                </button>
            </div>
        </div>
    `;
}

// Пустое состояние
function showEmptyState(message = 'Клиенты не найдены') {
    const container = document.getElementById('clientsGrid');
    container.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
            <div class="empty-state-icon">👥</div>
            <h3 style="color: #00ffff; margin-bottom: 1rem;">${message}</h3>
            <p style="color: rgba(255,255,255,0.6);">
                ${message === 'Клиенты не найдены' ? 'Попробуйте изменить параметры поиска или добавить нового клиента' : ''}
            </p>
            ${message === 'Клиенты не найдены' ? `
                <button class="btn" onclick="openNewClientModal()" style="margin-top: 1rem;">
                    ➕ Добавить первого клиента
                </button>
            ` : ''}
        </div>
    `;

    // Скрываем пагинацию
    document.getElementById('pagination').innerHTML = '';
}

// Пагинация
function updatePagination() {
    const totalPages = Math.ceil(filteredClients.length / itemsPerPage);
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

function changePage(page) {
    const totalPages = Math.ceil(filteredClients.length / itemsPerPage);
    if (page < 1 || page > totalPages) return;

    currentPage = page;
    displayClients();
}

// Обработчики поиска и фильтров
function searchClients() {
    filterAndDisplayClients();
}

function filterClients() {
    filterAndDisplayClients();
}

function sortClients() {
    // Эта функция вызывается из HTML при изменении select
    filterAndDisplayClients();
}

function changeItemsPerPage() {
    itemsPerPage = parseInt(document.getElementById('itemsPerPage').value);
    currentPage = 1;
    displayClients();
}

// Открытие модального окна нового клиента
function openNewClientModal() {
    document.getElementById('newClientForm').reset();
    document.getElementById('newClientVip').value = 'false';

    // Проверяем предзаполненные данные
    checkPreselectedClient();

    openModal('newClientModal');
}

// Проверка предзаполненного клиента из localStorage
function checkPreselectedClient() {
    const preselectedClient = localStorage.getItem('preselectedClient');
    if (preselectedClient) {
        try {
            const clientData = JSON.parse(preselectedClient);

            // Заполняем форму, если модальное окно открыто
            const nameField = document.getElementById('newClientName');
            const phoneField = document.getElementById('newClientPhone');
            const emailField = document.getElementById('newClientEmail');

            if (nameField && clientData.name) {
                nameField.value = clientData.name;
            }
            if (phoneField && clientData.phone) {
                phoneField.value = clientData.phone;
            }
            if (emailField && clientData.email) {
                emailField.value = clientData.email;
            }

            // Очищаем данные
            localStorage.removeItem('preselectedClient');
        } catch (error) {
            console.error('❌ Ошибка парсинга предзаполненного клиента:', error);
            localStorage.removeItem('preselectedClient');
        }
    }
}

// Открытие детальной информации о клиенте
async function openClientDetail(clientId) {
    try {
        console.log('👤 Открываем детали клиента:', clientId);
        currentClientId = clientId;

        // Загружаем полную информацию о клиенте
        const response = await fetch(`/api/clients/${clientId}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            showNotification('Ошибка загрузки данных клиента', 'error');
            return;
        }

        const client = await response.json();
        console.log('✅ Данные клиента загружены:', client);

        // Заполняем основную информацию
        document.getElementById('detailClientName').textContent = client.full_name;
        document.getElementById('detailClientPhone').textContent = client.phone;
        document.getElementById('detailClientEmail').textContent = client.email || 'Не указан';
        document.getElementById('detailClientCreated').textContent = formatDate(client.created_at);
        document.getElementById('detailClientTotalRequests').textContent = client.total_requests || 0;
        document.getElementById('detailClientTotalSpent').textContent = `₽${(client.total_spent || 0).toLocaleString('ru-RU')}`;
        document.getElementById('detailClientAddress').textContent = client.address || 'Не указан';
        document.getElementById('detailClientNotes').textContent = client.notes || 'Нет заметок';

        // Заполняем форму редактирования
        document.getElementById('editClientName').value = client.full_name;
        document.getElementById('editClientPhone').value = client.phone;
        document.getElementById('editClientEmail').value = client.email || '';
        document.getElementById('editClientVip').value = client.is_vip ? 'true' : 'false';
        document.getElementById('editClientAddress').value = client.address || '';
        document.getElementById('editClientNotes').value = client.notes || '';

        // Загружаем историю заявок
        await loadClientRequests(clientId);

        // Загружаем информацию об устройствах
        await loadClientDevices(clientId);

        // Переключаемся на первую вкладку
        switchDetailTab('info');

        // Открываем модальное окно
        openModal('clientDetailModal');

    } catch (error) {
        console.error('❌ Ошибка открытия деталей клиента:', error);
        showNotification('Ошибка загрузки данных клиента', 'error');
    }
}

// Загрузка заявок клиента
async function loadClientRequests(clientId) {
    try {
        const response = await fetch(`/api/clients/${clientId}/requests`, {
            credentials: 'include'
        });

        if (response.ok) {
            const requests = await response.json();
            renderClientRequests(requests);
        } else {
            document.getElementById('clientRequestsList').innerHTML = `
                <div style="text-align: center; padding: 2rem; color: rgba(255,255,255,0.6);">
                    Ошибка загрузки заявок
                </div>
            `;
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки заявок клиента:', error);
        document.getElementById('clientRequestsList').innerHTML = `
            <div style="text-align: center; padding: 2rem; color: rgba(255,255,255,0.6);">
                Ошибка загрузки заявок
            </div>
        `;
    }
}

// Отображение заявок клиента
function renderClientRequests(requests) {
    const container = document.getElementById('clientRequestsList');

    if (!requests.length) {
        container.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: rgba(255,255,255,0.6);">
                <h4>У этого клиента пока нет заявок</h4>
                <button class="btn" onclick="createRequestForClient(${currentClientId})" style="margin-top: 1rem;">
                    📝 Создать первую заявку
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = requests.map(request => `
        <div class="request-item">
            <div class="request-header">
                <div class="request-id">#${request.request_id}</div>
                <div class="request-date">${formatDate(request.created_at)}</div>
            </div>
            <div class="request-device">
                <strong>${request.device_type}</strong>
                ${request.brand ? ` ${request.brand}` : ''}
                ${request.model ? ` ${request.model}` : ''}
            </div>
            <div class="request-problem">${truncateText(request.problem_description, 100)}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
                <span class="status-badge ${getStatusClass(request.status)}">${request.status}</span>
                ${request.final_cost ? `<span style="color: #00ff00;">₽${request.final_cost.toLocaleString('ru-RU')}</span>` : ''}
            </div>
            ${request.master_name ? `
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7); margin-top: 0.25rem;">
                    🔧 Мастер: ${request.master_name}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Загрузка устройств клиента
async function loadClientDevices(clientId) {
    try {
        const response = await fetch(`/api/clients/${clientId}`, {
            credentials: 'include'
        });

        if (response.ok) {
            const client = await response.json();
            renderClientDevices(client.device_types || []);
        } else {
            document.getElementById('clientDevicesList').innerHTML = `
                <div style="text-align: center; padding: 2rem; color: rgba(255,255,255,0.6);">
                    Ошибка загрузки информации об устройствах
                </div>
            `;
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки устройств клиента:', error);
        document.getElementById('clientDevicesList').innerHTML = `
            <div style="text-align: center; padding: 2rem; color: rgba(255,255,255,0.6);">
                Ошибка загрузки данных
            </div>
        `;
    }
}

// Отображение устройств клиента
function renderClientDevices(devices) {
    const container = document.getElementById('clientDevicesList');

    if (!devices.length) {
        container.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: rgba(255,255,255,0.6);">
                <h4>Информация об устройствах отсутствует</h4>
                <p>Данные появятся после создания заявок</p>
            </div>
        `;
        return;
    }

    const deviceIcons = {
        'Настольный ПК': '🖥️',
        'Ноутбук': '💻',
        'Моноблок': '🖥️',
        'Сервер': '🗄️',
        'Другое': '📱'
    };

    container.innerHTML = devices.map(device => `
        <div style="background: rgba(0, 255, 255, 0.05); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; border: 1px solid rgba(0, 255, 255, 0.1);">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2rem;">${deviceIcons[device.device_type] || '📱'}</div>
                <div>
                    <div style="font-weight: 600; color: #00ffff; margin-bottom: 0.25rem;">
                        ${device.device_type}
                    </div>
                    <div style="font-size: 0.9rem; color: rgba(255,255,255,0.8);">
                        Обслуживался: ${device.count} раз
                    </div>
                    <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">
                        Последний ремонт: ${formatDate(device.last_repair)}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// Переключение вкладок в детальном окне
function switchDetailTab(tabName) {
    // Скрываем все вкладки
    document.querySelectorAll('.detail-tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Убираем активный класс со всех кнопок
    document.querySelectorAll('.detail-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Показываем нужную вкладку
    const targetContent = document.getElementById(tabName + 'DetailTab');
    if (targetContent) {
        targetContent.classList.add('active');
    }

    // Активируем соответствующую кнопку
    const targetTab = Array.from(document.querySelectorAll('.detail-tab')).find(tab =>
        tab.getAttribute('onclick') && tab.getAttribute('onclick').includes(tabName)
    );
    if (targetTab) {
        targetTab.classList.add('active');
    }
}

// Настройка обработчиков форм
function setupFormHandlers() {
    // Форма создания клиента
    const newClientForm = document.getElementById('newClientForm');
    if (newClientForm) {
        newClientForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitButton = e.target.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Создание...';

            try {
                const clientData = {
                    full_name: document.getElementById('newClientName').value.trim(),
                    phone: document.getElementById('newClientPhone').value.trim(),
                    email: document.getElementById('newClientEmail').value.trim() || null,
                    address: document.getElementById('newClientAddress').value.trim() || null,
                    is_vip: document.getElementById('newClientVip').value === 'true',
                    notes: document.getElementById('newClientNotes').value.trim() || null
                };

                const success = await createClient(clientData);
                if (success) {
                    closeModal('newClientModal');
                    await loadClients();
                    await loadClientStatistics();
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }

    // Форма редактирования клиента
    const editClientForm = document.getElementById('editClientForm');
    if (editClientForm) {
        editClientForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitButton = e.target.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Сохранение...';

            try {
                const clientData = {
                    full_name: document.getElementById('editClientName').value.trim(),
                    phone: document.getElementById('editClientPhone').value.trim(),
                    email: document.getElementById('editClientEmail').value.trim() || null,
                    address: document.getElementById('editClientAddress').value.trim() || null,
                    is_vip: document.getElementById('editClientVip').value === 'true',
                    notes: document.getElementById('editClientNotes').value.trim() || null
                };

                const success = await updateClient(currentClientId, clientData);
                if (success) {
                    closeModal('clientDetailModal');
                    await loadClients();
                    await loadClientStatistics();
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }
}

// API функции
async function createClient(clientData) {
    try {
        console.log('👤 Создание клиента:', clientData);

        const response = await fetch('/api/clients', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(clientData)
        });

        if (response.ok) {
            const result = await response.json();
            showNotification(`Клиент создан! ID: ${result.id}`, 'success');
            return true;
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Ошибка создания клиента', 'error');
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка создания клиента:', error);
        showNotification('Ошибка подключения к серверу', 'error');
        return false;
    }
}

async function updateClient(clientId, clientData) {
    try {
        console.log('🔄 Обновление клиента:', clientId, clientData);

        const response = await fetch(`/api/clients/${clientId}`, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(clientData)
        });

        if (response.ok) {
            showNotification('Клиент успешно обновлен', 'success');
            return true;
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Ошибка обновления клиента', 'error');
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка обновления клиента:', error);
        showNotification('Ошибка подключения к серверу', 'error');
        return false;
    }
}

async function deleteClient() {
    if (!confirm('Вы уверены, что хотите удалить этого клиента? Это действие нельзя отменить.')) return;

    try {
        console.log('🗑️ Удаление клиента:', currentClientId);

        const response = await fetch(`/api/clients/${currentClientId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.ok) {
            showNotification('Клиент удален', 'success');
            closeModal('clientDetailModal');
            await loadClients();
            await loadClientStatistics();
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Ошибка удаления клиента', 'error');
        }
    } catch (error) {
        console.error('❌ Ошибка удаления клиента:', error);
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

// Создание заявки для клиента
function createRequestForClient(clientId) {
    const client = allClients.find(c => c.id === clientId);
    if (client) {
        localStorage.setItem('preselectedClient', JSON.stringify({
            id: client.id,
            name: client.full_name,
            phone: client.phone,
            email: client.email
        }));

        window.location.href = '/dashboard/requests';
    }
}

// Экспорт клиентов
function exportClients() {
    if (filteredClients.length === 0) {
        showNotification('Нет данных для экспорта', 'error');
        return;
    }

    const csvContent = [
        ['ID', 'Имя', 'Телефон', 'Email', 'Адрес', 'VIP', 'Всего заявок', 'Потрачено', 'Дата регистрации'],
        ...filteredClients.map(c => [
            c.id,
            c.full_name,
            c.phone,
            c.email || '',
            c.address || '',
            c.is_vip ? 'Да' : 'Нет',
            c.total_requests || 0,
            c.total_spent || 0,
            formatDate(c.created_at)
        ])
    ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `клиенты_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();

    showNotification(`Экспортировано ${filteredClients.length} клиентов`, 'success');
}

// Вспомогательные функции
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
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

// Управление модальными окнами
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Предотвращаем прокрутку фона
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto'; // Восстанавливаем прокрутку
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
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.4s ease-out';
        setTimeout(() => notification.remove(), 400);
    }, 4000);
}

// Переключение sidebar для мобильных
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
}

// Выход из системы
function logout() {
    console.log('🚪 Выход из системы');
    window.location.href = '/logout';
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
        document.body.style.overflow = 'auto';
    }
}

// Обработка клавиши Escape для закрытия модальных окон
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal[style*="flex"]');
        openModals.forEach(modal => {
            modal.style.display = 'none';
        });
        document.body.style.overflow = 'auto';
    }
});

// Добавим стили для анимации уведомлений
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    /* Дополнительные стили для карточек клиентов */
    .client-card {
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .client-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 40px rgba(0, 255, 255, 0.3);
    }

    .client-actions button {
        transition: all 0.3s ease;
    }

    .client-actions button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 255, 255, 0.3);
    }

    /* Стили для формы */
    .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .info-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .info-item {
        padding: 1rem;
        background: rgba(0, 255, 255, 0.05);
        border-radius: 8px;
        border: 1px solid rgba(0, 255, 255, 0.1);
    }

    .info-label {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 0.25rem;
    }

    .info-value {
        font-size: 1.1rem;
        color: #00ffff;
        word-break: break-all;
    }

    /* Адаптивность */
    @media (max-width: 768px) {
        .clients-grid {
            grid-template-columns: 1fr;
        }

        .filters-section > div {
            grid-template-columns: 1fr;
        }

        .form-row {
            grid-template-columns: 1fr;
        }

        .info-grid {
            grid-template-columns: 1fr;
        }

        .client-stats {
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }
    }

    @media (max-width: 480px) {
        .modal-content {
            padding: 1rem;
            margin: 0.5rem;
        }

        .client-card {
            padding: 1rem;
        }

        .client-actions {
            flex-direction: column;
        }
    }

    /* Стили для загрузки */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }

    .loading-content {
        background: rgba(26, 26, 46, 0.9);
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid rgba(0, 255, 255, 0.3);
        text-align: center;
        backdrop-filter: blur(10px);
    }

    .loading-spinner {
        width: 40px;
        height: 40px;
        border: 3px solid rgba(0, 255, 255, 0.3);
        border-top: 3px solid #00ffff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 1rem;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

console.log('✅ Полный скрипт управления клиентами загружен и готов к работе');