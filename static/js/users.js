// Глобальные переменные
let allUsers = [];
let currentEditUserId = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    console.log('👤 Инициализация страницы пользователей...');

    // Загружаем информацию о текущем пользователе
    await loadCurrentUserInfo();

    // Загружаем список пользователей
    await loadUsers();

    // Загружаем статистику
    await loadUserStatistics();

    // Настраиваем обработчики форм
    setupFormHandlers();

    // Проверяем URL параметры для уведомлений
    checkURLParams();

    console.log('✅ Страница пользователей готова к работе');
});

// Загрузка информации о текущем пользователе
async function loadCurrentUserInfo() {
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

        console.log('✅ Профиль текущего пользователя загружен:', user.full_name);

    } catch (err) {
        console.error("❌ Ошибка загрузки профиля:", err);
        window.location.href = "/auth/login";
    }
}

// Загрузка всех пользователей через API
async function loadUsers() {
    try {
        console.log('👥 Загружаем пользователей через API...');

        const response = await fetch('/dashboard/users/api/list', {
            credentials: 'include'
        });

        if (response.status === 401) {
            console.log('❌ 401 - перенаправляем на login');
            window.location.href = "/auth/login";
            return;
        }

        if (response.ok) {
            const data = await response.json();
            allUsers = data.users;
            console.log(`✅ Загружено ${allUsers.length} пользователей через API`);

            // Обновляем отображение
            renderUsers(allUsers);
            updateUsersCount(allUsers.length);
        } else {
            console.log('❌ Ошибка загрузки:', response.status);
            showNotification('Ошибка загрузки пользователей', 'error');
        }
    } catch (error) {
        console.error('❌ Ошибка:', error);
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

// Загрузка статистики пользователей
async function loadUserStatistics() {
    try {
        console.log('📊 Загружаем статистику пользователей...');

        const response = await fetch('/dashboard/users/api/statistics', {
            credentials: 'include'
        });

        if (response.ok) {
            const stats = await response.json();
            console.log('✅ Статистика загружена:', stats);

            // Обновляем элементы статистики
            updateStatCard('totalUsers', stats.total_users || 0);
            updateStatCard('adminUsers', stats.admin_users || 0);
            updateStatCard('masterUsers', stats.master_users || 0);
            updateStatCard('recentUsers', stats.recent_users || 0);
        } else {
            console.log('⚠️ Не удалось загрузить статистику');
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки статистики:', error);
    }
}

// Отображение пользователей
function renderUsers(users) {
    const container = document.querySelector('.users-grid');

    if (!container) {
        console.warn('⚠️ Контейнер для пользователей не найден');
        return;
    }

    if (!users.length) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="empty-state-icon">👥</div>
                <h3>Пользователи не найдены</h3>
                <p>Нет пользователей, соответствующих критериям поиска</p>
                <button class="btn" onclick="openModal('addUserModal')">
                    ➕ Добавить пользователя
                </button>
            </div>
        `;
        return;
    }

    container.innerHTML = users.map(user => createUserCard(user)).join('');

    // Добавляем анимацию появления
    const cards = container.querySelectorAll('.user-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Создание карточки пользователя
function createUserCard(user) {
    const avatar = user.full_name ? user.full_name.charAt(0).toUpperCase() : user.username.charAt(0).toUpperCase();
    const roleMap = {
        'admin': { name: '🔐 Администратор', class: 'role-admin' },
        'director': { name: '👔 Директор', class: 'role-director' },
        'manager': { name: '📋 Менеджер', class: 'role-manager' },
        'master': { name: '🔧 Мастер', class: 'role-master' }
    };

    const roleInfo = roleMap[user.role] || { name: user.role, class: 'role-other' };
    const statusClass = user.is_active ? 'status-active' : 'status-inactive';
    const statusText = user.is_active ? 'Активен' : 'Неактивен';

    return `
        <div class="user-card">
            <div class="user-header">
                <div class="user-avatar-large">${avatar}</div>
                <div class="user-basic-info">
                    <h3 class="user-name">${user.full_name || user.username}</h3>
                    <p class="user-username">@${user.username}</p>
                    <div class="user-role-badge ${roleInfo.class}">
                        ${roleInfo.name}
                    </div>
                </div>
                <div class="user-status">
                    <span class="status-badge ${statusClass}">${statusText}</span>
                </div>
            </div>

            <div class="user-details">
                <div class="user-info-grid">
                    <div class="info-item">
                        <span class="info-label">Email:</span>
                        <span class="info-value">${user.email}</span>
                    </div>
                    ${user.phone ? `
                        <div class="info-item">
                            <span class="info-label">Телефон:</span>
                            <span class="info-value">${user.phone}</span>
                        </div>
                    ` : ''}
                    <div class="info-item">
                        <span class="info-label">Регистрация:</span>
                        <span class="info-value">${formatDate(user.created_at)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Последний вход:</span>
                        <span class="info-value">${user.last_login ? formatDate(user.last_login) : 'Никогда'}</span>
                    </div>
                </div>

                ${user.role === 'master' && user.specialization ? `
                    <div class="master-specialization">
                        <span class="spec-label">Специализация:</span>
                        <span class="spec-value">${user.specialization}</span>
                    </div>
                ` : ''}
            </div>

            <div class="user-actions">
                <button class="btn btn-outline btn-sm" onclick="openEditModal(${user.id}, '${user.username}', '${user.email}', '${user.full_name}', '${user.role}', ${user.is_active}, '${user.phone || ''}')">
                    ✏️ Редактировать
                </button>
                ${user.is_active ? `
                    <button class="btn btn-outline btn-sm btn-warning" onclick="toggleUserStatus(${user.id}, false, '${user.username}')">
                        🚫 Деактивировать
                    </button>
                ` : `
                    <button class="btn btn-outline btn-sm btn-success" onclick="toggleUserStatus(${user.id}, true, '${user.username}')">
                        ✅ Активировать
                    </button>
                `}
            </div>
        </div>
    `;
}

// Переключение статуса пользователя
async function toggleUserStatus(userId, activate, username) {
    const action = activate ? 'активировать' : 'деактивировать';
    const confirmMessage = `Вы уверены, что хотите ${action} пользователя ${username}?`;

    if (!confirm(confirmMessage)) return;

    try {
        const endpoint = activate ? 'activate' : 'deactivate';
        const response = await fetch(`/dashboard/users/${userId}/${endpoint}`, {
            method: 'POST',
            credentials: 'include'
        });

        if (response.ok) {
            showNotification(`Пользователь ${activate ? 'активирован' : 'деактивирован'}`, 'success');
            await loadUsers(); // Перезагружаем список
        } else {
            showNotification(`Ошибка ${action}ции пользователя`, 'error');
        }
    } catch (error) {
        console.error(`❌ Ошибка ${action}ции:`, error);
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

// Настройка обработчиков форм
function setupFormHandlers() {
    // Форма создания пользователя
    const addUserForm = document.getElementById('addUserModal')?.querySelector('form');
    if (addUserForm) {
        addUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitButton = e.target.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Создание...';

            try {
                const formData = new FormData(e.target);
                const response = await fetch('/dashboard/users', {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (response.ok) {
                    showNotification('Пользователь создан успешно', 'success');
                    closeModal('addUserModal');
                    await loadUsers();
                    e.target.reset();
                } else {
                    const error = await response.text();
                    showNotification('Ошибка создания пользователя', 'error');
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }

    // Форма редактирования пользователя
    const editUserForm = document.getElementById('editUserForm');
    if (editUserForm) {
        editUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitButton = e.target.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Сохранение...';

            try {
                const formData = new FormData(e.target);
                const response = await fetch(e.target.action, {
                    method: 'POST',
                    credentials: 'include',
                    body: formData
                });

                if (response.ok) {
                    showNotification('Пользователь обновлен успешно', 'success');
                    closeModal('editUserModal');
                    await loadUsers();
                } else {
                    showNotification('Ошибка обновления пользователя', 'error');
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }
}

// Открытие модального окна редактирования
function openEditModal(id, username, email, fullName, role, isActive, phone) {
    const form = document.getElementById('editUserForm');
    if (!form) return;

    form.action = `/dashboard/users/${id}`;
    document.getElementById('edit_username').value = username;
    document.getElementById('edit_email').value = email;
    document.getElementById('edit_full_name').value = fullName;
    document.getElementById('edit_role').value = role;
    document.getElementById('edit_is_active').value = isActive ? 'true' : 'false';
    document.getElementById('edit_phone').value = phone || '';
    document.getElementById('edit_password').value = '';

    currentEditUserId = id;
    openModal('editUserModal');
}

// Проверка URL параметров для уведомлений
function checkURLParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const success = urlParams.get('success');
    const error = urlParams.get('error');

    if (success) {
        const messages = {
            'created': 'Пользователь создан успешно',
            'updated': 'Пользователь обновлен успешно',
            'activated': 'Пользователь активирован',
            'deactivated': 'Пользователь деактивирован',
            'deleted': 'Пользователь удален'
        };
        showNotification(messages[success] || 'Операция выполнена успешно', 'success');
    }

    if (error) {
        const messages = {
            'username_exists': 'Имя пользователя уже существует',
            'email_exists': 'Email уже используется',
            'cannot_deactivate_self': 'Нельзя деактивировать самого себя',
            'cannot_delete_self': 'Нельзя удалить самого себя',
            'activation_failed': 'Ошибка активации пользователя',
            'deactivation_failed': 'Ошибка деактивации пользователя',
            'deletion_failed': 'Ошибка удаления пользователя'
        };
        showNotification(messages[error] || 'Произошла ошибка', 'error');
    }

    // Очищаем URL параметры
    if (success || error) {
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }
}

// Обновление счетчика пользователей
function updateUsersCount(count) {
    const element = document.querySelector('.users-count');
    if (element) {
        element.textContent = `${count} пользователей`;
    }
}

// Обновление карточек статистики
function updateStatCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

// Форматирование даты
function formatDate(dateString) {
    if (!dateString) return 'Неизвестно';

    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return 'Неизвестно';
    }
}

// Управление модальными окнами
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
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

// Фильтрация и поиск пользователей
function filterUsers() {
    const searchInput = document.querySelector('input[name="search"]');
    const roleSelect = document.querySelector('select[name="role"]');
    const statusSelect = document.querySelector('select[name="status"]');

    if (!searchInput) return;

    const searchTerm = searchInput.value.toLowerCase();
    const roleFilter = roleSelect?.value || '';
    const statusFilter = statusSelect?.value || '';

    let filteredUsers = allUsers.filter(user => {
        // Поиск по тексту
        if (searchTerm) {
            const searchMatch =
                user.full_name.toLowerCase().includes(searchTerm) ||
                user.username.toLowerCase().includes(searchTerm) ||
                user.email.toLowerCase().includes(searchTerm) ||
                user.role.toLowerCase().includes(searchTerm);

            if (!searchMatch) return false;
        }

        // Фильтр по роли
        if (roleFilter && user.role !== roleFilter) return false;

        // Фильтр по статусу
        if (statusFilter) {
            const isActive = statusFilter === 'active';
            if (user.is_active !== isActive) return false;
        }

        return true;
    });

    renderUsers(filteredUsers);
    updateUsersCount(filteredUsers.length);
}

// Экспорт пользователей в CSV
function exportUsers() {
    if (!allUsers.length) {
        showNotification('Нет данных для экспорта', 'error');
        return;
    }

    const csvContent = [
        ['ID', 'Имя пользователя', 'Email', 'Полное имя', 'Роль', 'Статус', 'Телефон', 'Дата создания', 'Последний вход'],
        ...allUsers.map(u => [
            u.id,
            u.username,
            u.email,
            u.full_name || '',
            u.role,
            u.is_active ? 'Активен' : 'Неактивен',
            u.phone || '',
            formatDate(u.created_at),
            formatDate(u.last_login)
        ])
    ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `пользователи_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();

    showNotification(`Экспортировано ${allUsers.length} пользователей`, 'success');
}

// Обновление статистики в реальном времени
async function refreshStatistics() {
    await loadUserStatistics();
    showNotification('Статистика обновлена', 'success');
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

// Валидация форм
function validateUserForm(formData, isEdit = false) {
    const errors = [];

    // Проверка имени пользователя
    if (!isEdit && !formData.get('username')) {
        errors.push('Имя пользователя обязательно');
    } else if (!isEdit && !/^[a-zA-Z0-9_]+$/.test(formData.get('username'))) {
        errors.push('Имя пользователя может содержать только латинские буквы, цифры и подчеркивания');
    }

    // Проверка email
    if (!formData.get('email')) {
        errors.push('Email обязателен');
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.get('email'))) {
        errors.push('Неверный формат email');
    }

    // Проверка полного имени
    if (!formData.get('full_name')) {
        errors.push('Полное имя обязательно');
    }

    // Проверка роли
    if (!formData.get('role')) {
        errors.push('Роль обязательна');
    }

    // Проверка пароля (только при создании или если указан)
    const password = formData.get('password');
    if (!isEdit && !password) {
        errors.push('Пароль обязателен');
    } else if (password && password.length < 6) {
        errors.push('Пароль должен содержать минимум 6 символов');
    }

    return errors;
}

// Добавляем стили для анимации уведомлений
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

    /* Улучшенные стили для модальных окон */
    .modal {
        backdrop-filter: blur(10px);
    }

    .modal-content {
        animation: modalSlideIn 0.4s ease-out;
    }

    @keyframes modalSlideIn {
        from {
            opacity: 0;
            transform: scale(0.9) translateY(-50px);
        }
        to {
            opacity: 1;
            transform: scale(1) translateY(0);
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

console.log('✅ JavaScript для управления пользователями загружен и готов к работе');