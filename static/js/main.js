// Проверка загрузки логотипа
function checkLogo() {
    const logoIcon = document.getElementById('logoIcon');
    const img = new Image();
    img.onload = function() {
        logoIcon.classList.add('has-logo');
    };
    img.onerror = function() {
        logoIcon.classList.remove('has-logo');
    };
    img.src = '/static/images/logo.png';
}

// Нормализация номера телефона
function normalizePhone(phone) {
    // Удаляем все символы кроме цифр
    const digits = phone.replace(/\D/g, '');

    // Приводим к формату 7XXXXXXXXXX
    if (digits.length === 11 && digits.startsWith('8')) {
        return '7' + digits.substring(1);
    } else if (digits.length === 10) {
        return '7' + digits;
    } else if (digits.length === 11 && digits.startsWith('7')) {
        return digits;
    }

    return digits; // Возвращаем как есть, если не можем нормализовать
}

// Форматирование номера телефона для отображения
function formatPhone(phone) {
    const digits = phone.replace(/\D/g, '');
    if (digits.length === 11) {
        return `+${digits[0]} (${digits.substring(1, 4)}) ${digits.substring(4, 7)}-${digits.substring(7, 9)}-${digits.substring(9, 11)}`;
    }
    return phone;
}

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    document.body.style.overflow = 'hidden'; // Предотвращаем прокрутку фона
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto'; // Восстанавливаем прокрутку

    // Очищаем результаты при закрытии
    if (modalId === 'statusModal') {
        const resultDiv = document.getElementById('statusResult');
        if (resultDiv) {
            resultDiv.innerHTML = '';
        }
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
    }, 5000);
}

// Показ индикатора загрузки
function showLoading(message = 'Загрузка...') {
    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <p style="margin-top: 1rem; color: #00ffff;">${message}</p>
        </div>
    `;
    loading.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        backdrop-filter: blur(5px);
    `;

    const loadingContent = loading.querySelector('.loading-content');
    loadingContent.style.cssText = `
        background: rgba(26, 26, 46, 0.9);
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid rgba(0, 255, 255, 0.3);
        text-align: center;
        backdrop-filter: blur(10px);
    `;

    const spinner = loading.querySelector('.loading-spinner');
    spinner.style.cssText = `
        width: 40px;
        height: 40px;
        border: 3px solid rgba(0, 255, 255, 0.3);
        border-top: 3px solid #00ffff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    `;

    document.body.appendChild(loading);
    return loading;
}

// Скрытие индикатора загрузки
function hideLoading() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// Валидация формы заявки
function validateRequestForm(formData) {
    const errors = [];

    if (!formData.client_name || formData.client_name.trim().length < 2) {
        errors.push('Имя должно содержать минимум 2 символа');
    }

    if (!formData.phone || formData.phone.trim().length < 10) {
        errors.push('Телефон должен содержать минимум 10 цифр');
    }

    if (!formData.device_type) {
        errors.push('Выберите тип устройства');
    }

    if (!formData.problem_description || formData.problem_description.trim().length < 10) {
        errors.push('Описание проблемы должно содержать минимум 10 символов');
    }

    return errors;
}

// Handle request form submission
async function handleRequestSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const rawPhone = formData.get('phone');
    const normalizedPhone = normalizePhone(rawPhone);

    const data = {
        client_name: formData.get('clientName').trim(),
        phone: normalizedPhone, // Используем нормализованный номер
        email: formData.get('email').trim() || '',
        device_type: formData.get('deviceType'),
        problem_description: formData.get('problemDescription').trim()
    };

    console.log('📝 Отправка заявки:', data);
    console.log(`📞 Телефон: "${rawPhone}" → "${normalizedPhone}"`);

    // Валидация
    const errors = validateRequestForm(data);
    if (errors.length > 0) {
        showNotification(`Ошибки в форме:\n${errors.join('\n')}`, 'error');
        return;
    }

    const loading = showLoading('Создание заявки...');

    try {
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        hideLoading();

        const responseText = await response.text();
        console.log('📡 Ответ сервера:', response.status, responseText);

        let result;
        try {
            result = JSON.parse(responseText);
        } catch (parseError) {
            console.error('❌ Ошибка парсинга JSON:', parseError);
            showNotification('Ошибка сервера: неверный формат ответа', 'error');
            return;
        }

        if (response.ok) {
            const successMessage = `✅ Заявка успешно создана!

📋 Номер заявки: ${result.id}
📞 Телефон: ${formatPhone(normalizedPhone)}
👤 Клиент: ${data.client_name}

Сохраните номер заявки для отслеживания статуса.`;

            showNotification('Заявка создана! Номер: ' + result.id, 'success');

            // Показываем подробную информацию
            alert(successMessage);

            closeModal('requestModal');
            e.target.reset();

            // Автоматически открываем окно проверки статуса с заполненным номером
            setTimeout(() => {
                document.getElementById('requestId').value = result.id;
                openModal('statusModal');
            }, 1000);

        } else {
            let errorMessage = 'Ошибка при создании заявки';

            if (result.detail) {
                if (typeof result.detail === 'string') {
                    errorMessage = result.detail;
                } else if (Array.isArray(result.detail)) {
                    errorMessage = result.detail.map(err => err.msg || err.message || err).join(', ');
                }
            }

            console.error('❌ Ошибка от сервера:', errorMessage);
            showNotification(errorMessage, 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('❌ Ошибка сети:', error);
        showNotification('Ошибка подключения к серверу. Проверьте интернет-соединение.', 'error');
    }
}

// Handle status form submission
async function handleStatusSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const requestId = formData.get('requestId').trim().toUpperCase();

    if (!requestId) {
        showNotification('Введите номер заявки', 'error');
        return;
    }

    console.log('🔍 Проверка статуса заявки:', requestId);

    const loading = showLoading('Проверка статуса...');

    try {
        const response = await fetch(`/api/requests/${requestId}/status`);

        hideLoading();

        const resultDiv = document.getElementById('statusResult');

        if (response.ok) {
            const data = await response.json();
            console.log('✅ Данные заявки получены:', data);

            const statusClass = getStatusClass(data.status);
            const formattedDate = new Date(data.created_at).toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            resultDiv.innerHTML = `
                <div class="status-result" style="margin-top: 20px;">
                    <h3 style="color: #00ffff; margin-bottom: 1rem;">📋 Информация о заявке</h3>

                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(0, 255, 255, 0.05); border-radius: 8px;">
                            <strong>Номер заявки:</strong>
                            <span style="color: #00ffff;">${data.id}</span>
                        </div>

                        <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(0, 255, 255, 0.05); border-radius: 8px;">
                            <strong>Клиент:</strong>
                            <span>${data.client_name}</span>
                        </div>

                        <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(0, 255, 255, 0.05); border-radius: 8px;">
                            <strong>Устройство:</strong>
                            <span>${data.device_type}</span>
                        </div>

                        <div style="padding: 0.5rem; background: rgba(0, 255, 255, 0.05); border-radius: 8px;">
                            <strong>Описание проблемы:</strong><br>
                            <span style="color: rgba(255,255,255,0.9);">${data.problem_description}</span>
                        </div>

                        <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(0, 255, 255, 0.05); border-radius: 8px;">
                            <strong>Дата создания:</strong>
                            <span>${formattedDate}</span>
                        </div>

                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: rgba(0, 255, 255, 0.05); border-radius: 8px;">
                            <strong>Текущий статус:</strong>
                            <span class="status-badge ${statusClass}" style="margin-left: 1rem;">${data.status}</span>
                        </div>
                    </div>

                    <div style="margin-top: 1rem; padding: 1rem; background: rgba(0, 255, 255, 0.1); border-radius: 8px; border: 1px solid rgba(0, 255, 255, 0.2);">
                        <p style="margin: 0; font-size: 0.9rem; color: rgba(255,255,255,0.8);">
                            💡 <strong>Совет:</strong> Сохраните номер заявки для дальнейшего отслеживания.
                            Вы можете проверить статус в любое время на этой странице.
                        </p>
                    </div>
                </div>
            `;

            showNotification('Статус заявки загружен', 'success');

        } else if (response.status === 404) {
            resultDiv.innerHTML = `
                <div style="color: #ff6b6b; padding: 20px; border: 1px solid #ff6b6b; border-radius: 10px; margin-top: 20px; text-align: center;">
                    <h4 style="margin-top: 0;">❌ Заявка не найдена</h4>
                    <p>Заявка с номером <strong>${requestId}</strong> не найдена в системе.</p>
                    <p style="font-size: 0.9rem; margin-bottom: 0;">Проверьте правильность номера и попробуйте еще раз.</p>
                </div>
            `;
            showNotification('Заявка не найдена', 'error');
        } else {
            resultDiv.innerHTML = `
                <div style="color: #ff6b6b; padding: 20px; border: 1px solid #ff6b6b; border-radius: 10px; margin-top: 20px; text-align: center;">
                    <h4 style="margin-top: 0;">⚠️ Ошибка сервера</h4>
                    <p>Произошла ошибка при проверке статуса заявки.</p>
                    <p style="font-size: 0.9rem; margin-bottom: 0;">Попробуйте позже или обратитесь в службу поддержки.</p>
                </div>
            `;
            showNotification('Ошибка проверки статуса', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('❌ Ошибка сети:', error);

        const resultDiv = document.getElementById('statusResult');
        resultDiv.innerHTML = `
            <div style="color: #ff6b6b; padding: 20px; border: 1px solid #ff6b6b; border-radius: 10px; margin-top: 20px; text-align: center;">
                <h4 style="margin-top: 0;">🌐 Ошибка подключения</h4>
                <p>Не удалось подключиться к серверу.</p>
                <p style="font-size: 0.9rem; margin-bottom: 0;">Проверьте интернет-соединение и попробуйте еще раз.</p>
            </div>
        `;
        showNotification('Ошибка подключения к серверу', 'error');
    }
}

function getStatusClass(status) {
    const statusMap = {
        'Принята': 'status-accepted',
        'Диагностика': 'status-diagnosis',
        'Ожидание запчастей': 'status-waiting',
        'В ремонте': 'status-repair',
        'Тестирование': 'status-testing',
        'Готова к выдаче': 'status-ready',
        'Выдана': 'status-completed'
    };
    return statusMap[status] || 'status-accepted';
}

// Вызываем проверку при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    checkLogo();

    // Close modal when clicking outside
    window.onclick = function(event) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (event.target === modal) {
                const modalId = modal.id;
                closeModal(modalId);
            }
        });
    };

    // Обработка клавиши Escape для закрытия модальных окон
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal[style*="block"]');
            openModals.forEach(modal => {
                closeModal(modal.id);
            });
        }
    });

    // Handle request form submission
    const requestForm = document.getElementById('requestForm');
    if (requestForm) {
        requestForm.addEventListener('submit', handleRequestSubmit);
    }

    // Handle status form submission
    const statusForm = document.getElementById('statusForm');
    if (statusForm) {
        statusForm.addEventListener('submit', handleStatusSubmit);
    }

    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Форматирование телефона при вводе (опционально)
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            // Можно добавить автоформатирование при вводе
            // Но сейчас оставляем простой ввод, нормализация происходит при отправке
        });
    });
});

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

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .status-result {
        animation: fadeIn 0.5s ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

console.log('✅ Обновленный main.js загружен с поддержкой нормализации телефонов');