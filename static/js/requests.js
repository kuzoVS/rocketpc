// Глобальные переменные
let allRequests = [];
let filteredRequests = [];
let currentPage = 1;
let itemsPerPage = 10;
let sortField = 'date';
let sortOrder = 'desc';
let currentEditRequestId = null;
let currentActiveTab = 'basic';

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async function() {
    console.log('📄 Инициализация страницы заявок...');
    setupPhoneAutocompleteRemote();
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

    // Настраиваем обработчики вкладок
    setupTabHandlers();
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
        console.error("Ошибка загрузки профиля:", err);
        window.location.href = "/auth/login";
    }
}

// Загрузка заявок с использованием существующего API
async function loadRequests() {
    console.log('📋 Загружаем заявки...');

    try {
        const response = await fetch('/dashboard/api/requests', {
            credentials: 'include'
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

        const response = await fetch('/dashboard/api/requests', {
            method: 'POST',
            credentials: 'include',
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
            let errorMessage = 'Ошибка создания заявки';

            if (result.detail) {
                if (typeof result.detail === 'string') {
                    errorMessage = result.detail;
                } else if (Array.isArray(result.detail)) {
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

// 🆕 Полное обновление заявки
async function updateRequestFull(requestId, updateData) {
    try {
        console.log('🔄 Полное обновление заявки:', requestId, updateData);

        const response = await fetch(`/dashboard/api/requests/${requestId}/full`, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });

        if (response.ok) {
            const result = await response.json();
            showNotification('Заявка успешно обновлена', 'success');
            console.log('✅ Обновленные поля:', result.updated_fields);
            closeModal('editRequestModal');
            await loadRequests();
            return true;
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Ошибка обновления', 'error');
            return false;
        }
    } catch (error) {
        console.error('❌ Ошибка обновления:', error);
        showNotification('Ошибка подключения к серверу', 'error');
        return false;
    }
}

// 🆕 Обновление информации о клиенте
async function updateRequestClient(requestId, clientData) {
    try {
        console.log('👤 Обновление клиента для заявки:', requestId, clientData);

        const response = await fetch(`/dashboard/api/requests/${requestId}/client`, {
            method: 'PUT',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(clientData)
        });

        if (response.ok) {
            showNotification('Информация о клиенте обновлена', 'success');
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

// Архивирование заявки
async function archiveRequest(requestId) {
    if (!confirm('Вы уверены, что хотите архивировать эту заявку?')) return;

    try {
        const response = await fetch(`/dashboard/api/requests/${requestId}/archive`, {
            method: 'POST',
            credentials: 'include'
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

    // 🆕 Обновленная форма редактирования заявки
    const editRequestForm = document.getElementById('editRequestForm');
    if (editRequestForm) {
        editRequestForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitButton = e.target.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Сохранение...';

            try {
                // Собираем данные со всех вкладок
                const updateData = {};
                const clientData = {};

                // Основная информация
                const status = document.getElementById('editStatus').value;
                const priority = document.getElementById('editPriority').value;
                const comment = document.getElementById('editComment').value.trim();

                if (status) updateData.status = status;
                if (priority) updateData.priority = priority;
                if (comment) updateData.comment = comment;

                // Информация о клиенте
                const clientName = document.getElementById('editClientName')?.value.trim();
                const clientPhone = document.getElementById('editClientPhone')?.value.trim();
                const clientEmail = document.getElementById('editClientEmail')?.value.trim();
                const clientAddress = document.getElementById('editClientAddress')?.value.trim();

                if (clientName) clientData.full_name = clientName;
                if (clientPhone) clientData.phone = clientPhone;
                if (clientEmail) clientData.email = clientEmail;
                if (clientAddress) clientData.address = clientAddress;

                // Информация об устройстве
                const deviceType = document.getElementById('editDeviceType')?.value;
                const brand = document.getElementById('editBrand')?.value.trim();
                const model = document.getElementById('editModel')?.value.trim();
                const serialNumber = document.getElementById('editSerialNumber')?.value.trim();
                const problemDescription = document.getElementById('editProblemDescription')?.value.trim();
                const partsUsed = document.getElementById('editPartsUsed')?.value.trim();

                if (deviceType) updateData.device_type = deviceType;
                if (brand) updateData.brand = brand;
                if (model) updateData.model = model;
                if (serialNumber) updateData.serial_number = serialNumber;
                if (problemDescription) updateData.problem_description = problemDescription;
                if (partsUsed) updateData.parts_used = partsUsed;

                // Финансовая информация
                const estimatedCost = document.getElementById('editEstimatedCost')?.value;
                const finalCost = document.getElementById('editFinalCost')?.value;
                const repairDuration = document.getElementById('editRepairDuration')?.value;
                const warrantyPeriod = document.getElementById('editWarrantyPeriod')?.value;
                const estimatedCompletion = document.getElementById('editEstimatedCompletion')?.value;

                if (estimatedCost) updateData.estimated_cost = parseFloat(estimatedCost);
                if (finalCost) updateData.final_cost = parseFloat(finalCost);
                if (repairDuration) updateData.repair_duration_hours = parseFloat(repairDuration);
                if (warrantyPeriod) updateData.warranty_period = parseInt(warrantyPeriod);
                if (estimatedCompletion) updateData.estimated_completion = estimatedCompletion;

                // Заметки
                const notes = document.getElementById('editNotes')?.value.trim();
                if (notes) updateData.notes = notes;

                console.log('📝 Данные для обновления:', updateData);
                console.log('👤 Данные клиента:', clientData);

                // Сначала обновляем заявку
                let success = true;
                if (Object.keys(updateData).length > 0) {
                    success = await updateRequestFull(currentEditRequestId, updateData);
                }

                // Затем обновляем клиента, если есть изменения
                if (success && Object.keys(clientData).length > 0) {
                    await updateRequestClient(currentEditRequestId, clientData);
                }

                // Если есть изменения в назначении мастера
                const masterId = document.getElementById('editMaster')?.value;
                if (masterId !== undefined) {
                    await updateMasterAssignment(currentEditRequestId, masterId);
                }

            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }
}

// Обновление назначения мастера
async function updateMasterAssignment(requestId, masterId) {
    try {
        if (masterId) {
            // Назначаем мастера
            await fetch(`/dashboard/api/requests/${requestId}/assign-master`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ master_id: parseInt(masterId) })
            });
        } else {
            // Снимаем мастера
            await fetch(`/dashboard/api/requests/${requestId}/unassign-master`, {
                method: 'DELETE',
                credentials: 'include'
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

// 🆕 Обновленное открытие модального окна редактирования
async function openEditModal(requestId) {
    try {
        console.log('📝 Открываем редактирование заявки:', requestId);

        currentEditRequestId = requestId;

        // Загружаем полные данные заявки
        const response = await fetch(`/dashboard/api/requests/${requestId}/full`, {
            credentials: 'include'
        });

        if (!response.ok) {
            showNotification('Ошибка загрузки данных заявки', 'error');
            return;
        }

        const request = await response.json();
        console.log('✅ Данные заявки загружены:', request);

        // Заполняем основную информацию
        document.getElementById('editRequestId').textContent = `#${request.request_id}`;
        document.getElementById('editCreatedAt').textContent = formatDate(request.created_at);

        // Заполняем информацию о клиенте
        const editClientName = document.getElementById('editClientName');
        const editClientPhone = document.getElementById('editClientPhone');
        const editClientEmail = document.getElementById('editClientEmail');
        const editClientAddress = document.getElementById('editClientAddress');

        if (editClientName) editClientName.value = request.client_name || '';
        if (editClientPhone) editClientPhone.value = request.client_phone || '';
        if (editClientEmail) editClientEmail.value = request.client_email || '';
        if (editClientAddress) editClientAddress.value = request.client_address || '';

        // Заполняем информацию об устройстве
        const editDeviceType = document.getElementById('editDeviceType');
        const editBrand = document.getElementById('editBrand');
        const editModel = document.getElementById('editModel');
        const editSerialNumber = document.getElementById('editSerialNumber');
        const editProblemDescription = document.getElementById('editProblemDescription');
        const editPartsUsed = document.getElementById('editPartsUsed');

        if (editDeviceType) editDeviceType.value = request.device_type || '';
        if (editBrand) editBrand.value = request.brand || '';
        if (editModel) editModel.value = request.model || '';
        if (editSerialNumber) editSerialNumber.value = request.serial_number || '';
        if (editProblemDescription) editProblemDescription.value = request.problem_description || '';
        if (editPartsUsed) editPartsUsed.value = request.parts_used || '';

        // Заполняем статус и приоритет
        document.getElementById('editStatus').value = request.status || 'Принята';
        document.getElementById('editPriority').value = request.priority || 'Обычная';

        // Заполняем финансовую информацию
        const editEstimatedCost = document.getElementById('editEstimatedCost');
        const editFinalCost = document.getElementById('editFinalCost');
        const editRepairDuration = document.getElementById('editRepairDuration');
        const editWarrantyPeriod = document.getElementById('editWarrantyPeriod');
        const editEstimatedCompletion = document.getElementById('editEstimatedCompletion');

        if (editEstimatedCost) editEstimatedCost.value = request.estimated_cost || '';
        if (editFinalCost) editFinalCost.value = request.final_cost || '';
        if (editRepairDuration) editRepairDuration.value = request.repair_duration_hours || '';
        if (editWarrantyPeriod) editWarrantyPeriod.value = request.warranty_period || 30;
        if (editEstimatedCompletion && request.estimated_completion) {
            const date = new Date(request.estimated_completion);
            editEstimatedCompletion.value = date.toISOString().split('T')[0];
        }

        // Заполняем заметки
        const editNotes = document.getElementById('editNotes');
        if (editNotes) editNotes.value = request.notes || '';

        // Сбрасываем комментарий
        const editComment = document.getElementById('editComment');
        if (editComment) editComment.value = '';

        // Загружаем список мастеров
        await loadMasters();

        // Устанавливаем текущего мастера
        const masterSelect = document.getElementById('editMaster');
        if (masterSelect && request.assigned_master_id) {
            masterSelect.value = request.assigned_master_id;
        }

        // Загружаем историю изменений
        await loadRequestHistory(requestId);

        // Переключаемся на первую вкладку
        switchTab('basic');

        // Открываем модальное окно
        openModal('editRequestModal');

    } catch (error) {
        console.error('❌ Ошибка открытия редактирования:', error);
        showNotification('Ошибка загрузки данных заявки', 'error');
    }
}

// 🆕 Загрузка истории изменений заявки
async function loadRequestHistory(requestId) {
    try {
        const response = await fetch(`/dashboard/api/requests/${requestId}/history`, {
            credentials: 'include'
        });

        if (response.ok) {
            const history = await response.json();
            renderRequestHistory(history);
        } else {
            console.log('⚠️ Не удалось загрузить историю изменений');
            renderRequestHistory([]);
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки истории:', error);
        renderRequestHistory([]);
    }
}

// 🆕 Отображение истории изменений
// 🆕 Обновленное отображение истории изменений с назначениями мастеров
function renderRequestHistory(history) {
    const historyContainer = document.getElementById('editHistory');
    if (!historyContainer) return;

    if (!history.length) {
        historyContainer.innerHTML = `
            <div style="text-align: center; color: rgba(255,255,255,0.6); padding: 1rem;">
                История изменений пуста
            </div>
        `;
        return;
    }

    historyContainer.innerHTML = history.map(item => {
        const date = new Date(item.changed_at).toLocaleString('ru-RU');
        const roleName = {
            'admin': 'Администратор',
            'director': 'Директор',
            'manager': 'Менеджер',
            'master': 'Мастер'
        }[item.changed_by_role] || item.changed_by_role;

        // Определяем тип события и соответствующие стили
        let icon, title, borderColor, bgColor;

        switch (item.action_type) {
            case 'status_change':
                icon = '📋';
                title = `${item.old_status || 'Создание'} → ${item.new_status}`;
                borderColor = '#00ffff';
                bgColor = 'rgba(0, 255, 255, 0.03)';
                break;
            case 'master_assignment':
                icon = '👤';
                title = `Назначен мастер: ${item.master_name}`;
                borderColor = '#00ff00';
                bgColor = 'rgba(0, 255, 0, 0.03)';
                break;
            case 'master_unassignment':
                icon = '❌';
                title = `Снят мастер: ${item.master_name}`;
                borderColor = '#ff9800';
                bgColor = 'rgba(255, 152, 0, 0.03)';
                break;
            default:
                icon = '📝';
                title = 'Изменение';
                borderColor = '#00ffff';
                bgColor = 'rgba(0, 255, 255, 0.03)';
        }

        return `
            <div style="padding: 0.75rem; background: ${bgColor};
                        border-left: 3px solid ${borderColor}; margin-bottom: 0.5rem;
                        border-radius: 0 8px 8px 0; transition: all 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.2rem;">${icon}</span>
                        <div style="font-weight: 600; color: ${borderColor};">
                            ${title}
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">
                        ${date}
                    </div>
                </div>
                <div style="font-size: 0.9rem; color: rgba(255,255,255,0.8); margin-left: 1.7rem;">
                    <strong>${item.changed_by_name || 'Система'}</strong> (${roleName})
                </div>
                ${item.comment && item.action_type === 'status_change' ? `
                    <div style="margin-top: 0.5rem; margin-left: 1.7rem; padding: 0.5rem;
                                background: rgba(255,255,255,0.05); border-radius: 4px;
                                font-size: 0.9rem; color: rgba(255,255,255,0.9);">
                        💬 ${item.comment}
                    </div>
                ` : ''}
                ${item.master_specialization && item.action_type === 'master_assignment' ? `
                    <div style="margin-top: 0.25rem; margin-left: 1.7rem;
                                font-size: 0.85rem; color: rgba(255,255,255,0.7);">
                        🔧 Специализация: ${item.master_specialization}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');

    // Добавляем анимацию появления
    const historyItems = historyContainer.querySelectorAll('div[style*="border-left"]');
    historyItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            item.style.transition = 'all 0.3s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, index * 100);
    });

    console.log('✅ История изменений отображена');
}

async function loadMasters() {
    try {
        console.log('🔄 Загружаем мастеров...');
        const response = await fetch('/dashboard/api/masters/available', {
            credentials: 'include'
        });

        if (response.ok) {
            const masters = await response.json();
            const masterSelect = document.getElementById('editMaster');

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

// 🆕 Настройка обработчиков вкладок
function setupTabHandlers() {
    // Добавляем глобальную функцию для переключения вкладок
    window.switchTab = function(tabName) {
        // Скрываем все вкладки
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Убираем активный класс со всех кнопок
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });

        // Показываем нужную вкладку
        const targetContent = document.getElementById(tabName + 'Tab');
        if (targetContent) {
            targetContent.classList.add('active');
        }

        // Активируем соответствующую кнопку
        const targetTab = Array.from(document.querySelectorAll('.tab')).find(tab =>
            tab.getAttribute('onclick') && tab.getAttribute('onclick').includes(tabName)
        );
        if (targetTab) {
            targetTab.classList.add('active');
        }

        currentActiveTab = tabName;
    };
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
        backdrop-filter: blur(10px);
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.4s ease-out';
        setTimeout(() => notification.remove(), 400);
    }, 4000);
}

function setupPhoneAutocompleteRemote() {
    const phoneInput = document.getElementById('clientPhone');
    const nameInput = document.getElementById('clientName');
    const emailInput = document.getElementById('clientEmail');

    if (!phoneInput || !nameInput || !emailInput) {
        console.warn('⛔ Не найдены input поля для автозаполнения');
        return;
    }

    const suggestionBox = document.createElement('div');
    suggestionBox.id = 'phoneSuggestions';
    suggestionBox.style.cssText = `
        position: absolute;
        z-index: 999;
        background: #222;
        border: 1px solid #555;
        border-radius: 8px;
        color: white;
        padding: 0.5rem;
        max-height: 150px;
        overflow-y: auto;
        display: none;
    `;
    document.body.appendChild(suggestionBox);

    let debounceTimer;

    phoneInput.addEventListener('input', () => {
        const query = phoneInput.value.trim().replace(/\D/g, '');

        if (debounceTimer) clearTimeout(debounceTimer);

        if (query.length < 3) {
            suggestionBox.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/clients/search?phone=${query}`, {
                    credentials: 'include'
                });

                if (!res.ok) {
                    suggestionBox.style.display = 'none';
                    return;
                }

                const clients = await res.json();
                console.log('🔍 Найдено клиентов:', clients);

                if (!Array.isArray(clients) || clients.length === 0) {
                    suggestionBox.style.display = 'none';
                    return;
                }

                suggestionBox.innerHTML = '';
                clients.forEach(c => {
                    const item = document.createElement('div');
                    item.style.padding = '4px 8px';
                    item.style.cursor = 'pointer';
                    item.innerHTML = `<strong>${c.phone}</strong> – ${c.full_name}`;

                    item.addEventListener('mouseenter', () => item.style.background = '#333');
                    item.addEventListener('mouseleave', () => item.style.background = 'transparent');
                    item.addEventListener('click', () => {
                        phoneInput.value = c.phone;
                        nameInput.value = c.full_name;
                        emailInput.value = c.email || '';
                        suggestionBox.style.display = 'none';
                    });

                    suggestionBox.appendChild(item);
                });

                const rect = phoneInput.getBoundingClientRect();
                suggestionBox.style.top = `${rect.bottom + window.scrollY}px`;
                suggestionBox.style.left = `${rect.left + window.scrollX}px`;
                suggestionBox.style.width = `${rect.width}px`;
                suggestionBox.style.display = 'block';

            } catch (err) {
                console.error('❌ Ошибка автоподстановки:', err);
                suggestionBox.style.display = 'none';
            }
        }, 300);
    });

    phoneInput.addEventListener('blur', () => {
        setTimeout(() => suggestionBox.style.display = 'none', 200);
    });
}


// Экспорт заявок
function exportRequests() {
    const csvContent = [
        ['ID', 'Клиент', 'Телефон', 'Устройство', 'Проблема', 'Статус', 'Приоритет', 'Мастер', 'Дата'],
        ...filteredRequests.map(r => [
            r.request_id,
            r.client_name,
            r.client_phone || '',
            `${r.device_type} ${r.brand || ''} ${r.model || ''}`,
            r.problem_description,
            r.status,
            r.priority || 'Обычная',
            r.master_name || '-',
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
    }
}

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
`;
document.head.appendChild(style);

console.log('✅ Обновленный скрипт управления заявками с полным редактированием загружен');