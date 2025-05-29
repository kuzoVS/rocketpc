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

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Вызываем проверку при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    checkLogo();

    // Close modal when clicking outside
    window.onclick = function(event) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    };

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
});

// Handle request form submission
async function handleRequestSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        client_name: formData.get('clientName'),
        phone: formData.get('phone'),
        email: formData.get('email') || '',
        device_type: formData.get('deviceType'),
        problem_description: formData.get('problemDescription')
    };

    try {
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            alert(`Заявка успешно создана! Номер заявки: ${result.id}\nСохраните этот номер для отслеживания статуса.`);
            closeModal('requestModal');
            e.target.reset();
        } else {
            alert('Ошибка при создании заявки. Попробуйте еще раз.');
        }
    } catch (error) {
        alert('Ошибка подключения. Проверьте интернет-соединение.');
    }
}

// Handle status form submission
async function handleStatusSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const requestId = formData.get('requestId');

    try {
        const response = await fetch(`/api/requests/${requestId}/status`);
        const resultDiv = document.getElementById('statusResult');

        if (response.ok) {
            const data = await response.json();
            const statusClass = getStatusClass(data.status);

            resultDiv.innerHTML = `
                <div class="status-result">
                    <h3>Информация о заявке</h3>
                    <p><strong>Номер заявки:</strong> ${data.id}</p>
                    <p><strong>Клиент:</strong> ${data.client_name}</p>
                    <p><strong>Устройство:</strong> ${data.device_type}</p>
                    <p><strong>Описание:</strong> ${data.problem_description}</p>
                    <p><strong>Дата создания:</strong> ${new Date(data.created_at).toLocaleString('ru-RU')}</p>
                    <p><strong>Статус:</strong> <span class="status-badge ${statusClass}">${data.status}</span></p>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div style="color: #ff6b6b; padding: 20px; border: 1px solid #ff6b6b; border-radius: 10px; margin-top: 20px;">
                    Заявка с номером ${requestId} не найдена. Проверьте правильность номера.
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('statusResult').innerHTML = `
            <div style="color: #ff6b6b; padding: 20px; border: 1px solid #ff6b6b; border-radius: 10px; margin-top: 20px;">
                Ошибка при проверке статуса. Попробуйте позже.
            </div>
        `;
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