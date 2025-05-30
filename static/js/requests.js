// Простые функции для тестирования
console.log('📄 Скрипт requests загружен');

async function loadRequests() {
    console.log('📋 Загружаем заявки...');
    const container = document.getElementById('requestsContainer');

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
            const requests = await response.json();
            console.log(`✅ Загружено ${requests.length} заявок`);

            if (requests.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: rgba(255,255,255,0.6); padding: 2rem;">📝 Заявки не найдены</p>';
                return;
            }

            // Простая таблица
            container.innerHTML = `
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: rgba(0, 255, 255, 0.1);">
                                <th style="padding: 1rem; color: #00ffff; border-bottom: 2px solid rgba(0, 255, 255, 0.3);">ID</th>
                                <th style="padding: 1rem; color: #00ffff; border-bottom: 2px solid rgba(0, 255, 255, 0.3);">Клиент</th>
                                <th style="padding: 1rem; color: #00ffff; border-bottom: 2px solid rgba(0, 255, 255, 0.3);">Устройство</th>
                                <th style="padding: 1rem; color: #00ffff; border-bottom: 2px solid rgba(0, 255, 255, 0.3);">Статус</th>
                                <th style="padding: 1rem; color: #00ffff; border-bottom: 2px solid rgba(0, 255, 255, 0.3);">Дата</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${requests.map(req => `
                                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                                    <td style="padding: 1rem; color: #00ffff; font-weight: bold;">#${req.request_id}</td>
                                    <td style="padding: 1rem;">${req.client_name || 'Не указано'}</td>
                                    <td style="padding: 1rem;">${req.device_type || 'Не указано'}</td>
                                    <td style="padding: 1rem;">
                                        <span style="
                                            background: rgba(0, 255, 255, 0.2);
                                            color: #00ffff;
                                            padding: 0.25rem 0.75rem;
                                            border-radius: 20px;
                                            font-size: 0.85rem;
                                        ">${req.status}</span>
                                    </td>
                                    <td style="padding: 1rem;">${new Date(req.created_at).toLocaleDateString('ru-RU')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            console.log('❌ Ошибка загрузки:', response.status);
            container.innerHTML = '<p style="text-align: center; color: #ff4444; padding: 2rem;">❌ Ошибка загрузки заявок</p>';
        }
    } catch (error) {
        console.error('❌ Ошибка:', error);
        container.innerHTML = '<p style="text-align: center; color: #ff4444; padding: 2rem;">❌ Ошибка подключения</p>';
    }
}

async function testCreateRequest() {
    console.log('🧪 Тест создания заявки...');

    const testData = {
        client_name: 'Тестовый Клиент',
        phone: '+7 (999) 123-45-67',
        email: 'test@example.com',
        device_type: 'Ноутбук',
        problem_description: 'Тестовая заявка созданная через веб-интерфейс'
    };

    try {
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(testData)
        });

        if (response.ok) {
            const result = await response.json();
            alert(`✅ Заявка создана! ID: ${result.id}`);
            loadRequests(); // Обновляем список
        } else {
            const error = await response.json();
            alert(`❌ Ошибка: ${error.detail}`);
        }
    } catch (error) {
        console.error('❌ Ошибка создания:', error);
        alert('❌ Ошибка подключения');
    }
}

function logout() {
    console.log('🚪 Выход');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.replace('/auth/login');
}

// Автозагрузка при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(loadRequests, 500);
});

console.log('✅ Простая страница заявок готова');