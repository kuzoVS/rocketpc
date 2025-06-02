// dashboard.js — обновленная версия с улучшенным выводом статистики

let weeklyChart = null;
let statusChart = null;
let deviceChart = null;

window.addEventListener("DOMContentLoaded", () => {
  console.log('🚀 Инициализация dashboard...');
  loadDashboardStats();
  loadDashboardRequests();
  loadUserInfo();
  loadCharts();
  loadTopMasters();
  loadDeviceStats();
});

// 📊 Загрузка детальной статистики
async function loadDashboardStats() {
  try {
    console.log('📊 Загружаем детальную статистику...');
    const res = await fetch("/dashboard/api/stats/detailed", {
      credentials: "include"
    });

    if (res.status === 401) {
      console.log('❌ 401 - перенаправляем на login');
      window.location.href = "/auth/login";
      return;
    }

    if (!res.ok) throw new Error(`Ошибка загрузки статистики: ${res.status}`);

    const stats = await res.json();
    console.log('✅ Статистика загружена:', stats);

    // Обновляем основные показатели с проверкой существования элементов
    updateStatCard("totalRequestsCount", stats.total_requests || 0, "📊", "За все время");
    updateStatCard("activeRequestsCount", stats.active_requests || 0, "🔥", "В работе сейчас");
    updateStatCard("completedRequestsCount", stats.completed_this_month || 0, "↑",
      `${stats.growth_percentage > 0 ? '+' : ''}${stats.growth_percentage || 0}% к прошлому месяцу`);
    updateStatCard("monthlyRevenue", `${(stats.monthly_revenue || 0).toLocaleString('ru-RU')}₽`, "💵", "Оценочный доход");
    updateStatCard("avgRepairTime", `${stats.avg_repair_time || 0}`, "📈", "дней");
    updateStatCard("avgCost", `${(stats.avg_cost || 0).toLocaleString('ru-RU')}₽`, "📊", "За ремонт");

    console.log('✅ Статистические карточки обновлены');

  } catch (err) {
    console.error("❌ Ошибка загрузки статистики:", err);
    // Устанавливаем значения по умолчанию при ошибке
    updateStatCard("totalRequestsCount", 0, "📊", "Ошибка загрузки");
    updateStatCard("activeRequestsCount", 0, "🔥", "Ошибка загрузки");
    updateStatCard("completedRequestsCount", 0, "↑", "Ошибка загрузки");
    updateStatCard("monthlyRevenue", "₽0", "💵", "Ошибка загрузки");
    updateStatCard("avgRepairTime", "0", "📈", "Ошибка загрузки");
    updateStatCard("avgCost", "₽0", "📊", "Ошибка загрузки");
  }
}

function updateStatCard(elementId, value, icon, change) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = value;
    console.log(`✅ Обновлена карточка ${elementId}: ${value}`);

    // Обновляем изменение
    const changeElement = element.closest('.stat-card').querySelector('.stat-change');
    if (changeElement) {
      changeElement.innerHTML = `<span>${icon}</span> ${change}`;
    }
  } else {
    console.warn(`⚠️ Элемент ${elementId} не найден`);
  }
}

// 🏆 Загрузка топ мастеров
async function loadTopMasters() {
  try {
    console.log('🏆 Загружаем топ мастеров...');
    const res = await fetch("/dashboard/api/stats/detailed", {
      credentials: "include"
    });

    if (!res.ok) throw new Error("Ошибка загрузки данных мастеров");

    const stats = await res.json();
    const topMasters = stats.top_masters || [];

    console.log('✅ Топ мастера загружены:', topMasters);
    renderTopMasters(topMasters);

  } catch (err) {
    console.error("❌ Ошибка загрузки топ мастеров:", err);
    renderTopMasters([]);
  }
}

function renderTopMasters(masters) {
  const container = document.getElementById('topMastersList');
  if (!container) {
    console.warn('⚠️ Контейнер topMastersList не найден');
    return;
  }

  if (!masters.length) {
    container.innerHTML = `
      <div style="text-align: center; color: rgba(255,255,255,0.6);">
        <p>Нет данных о мастерах</p>
      </div>`;
    return;
  }

  container.innerHTML = masters.map((master, index) => `
    <div style="display: flex; justify-content: space-between; align-items: center;
                padding: 0.75rem; background: rgba(0, 255, 255, 0.05);
                border-radius: 8px; margin-bottom: 0.5rem; border: 1px solid rgba(0, 255, 255, 0.1);">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div style="width: 32px; height: 32px; background: linear-gradient(45deg, #00ffff, #0099ff);
                    border-radius: 50%; display: flex; align-items: center; justify-content: center;
                    font-weight: bold; color: #000; font-size: 14px;">
          ${index + 1}
        </div>
        <div>
          <div style="font-weight: 600; color: #00ffff;">${master.full_name}</div>
          <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">
            ${master.completed_repairs || 0} ремонтов за месяц
          </div>
        </div>
      </div>
      <div style="text-align: right; font-size: 0.85rem; color: rgba(255,255,255,0.8);">
        <div>${(master.avg_days || 0).toFixed(1)} дней</div>
        <div style="color: rgba(255,255,255,0.5);">среднее время</div>
      </div>
    </div>
  `).join('');

  console.log('✅ Топ мастера отображены');
}

// 📱 Загрузка статистики по устройствам
async function loadDeviceStats() {
  try {
    console.log('📱 Загружаем статистику по устройствам...');
    const res = await fetch("/dashboard/api/stats/devices", {
      credentials: "include"
    });

    if (!res.ok) throw new Error("Ошибка загрузки статистики устройств");

    const deviceStats = await res.json();
    console.log('✅ Статистика устройств загружена:', deviceStats);
    renderDeviceStats(deviceStats);

  } catch (err) {
    console.error("❌ Ошибка загрузки статистики устройств:", err);
    renderDeviceStats([]);
  }
}

function renderDeviceStats(devices) {
  const container = document.getElementById('deviceStatsList');
  if (!container) {
    console.warn('⚠️ Контейнер deviceStatsList не найден');
    return;
  }

  if (!devices.length) {
    container.innerHTML = `
      <div style="text-align: center; color: rgba(255,255,255,0.6);">
        <p>Нет данных об устройствах</p>
      </div>`;
    return;
  }

  // Определяем иконки для типов устройств
  const deviceIcons = {
    'Настольный ПК': '🖥️',
    'Ноутбук': '💻',
    'Моноблок': '🖥️',
    'Сервер': '🗄️',
    'Другое': '📱'
  };

  container.innerHTML = devices.slice(0, 5).map(device => `
    <div style="display: flex; justify-content: space-between; align-items: center;
                padding: 0.75rem; background: rgba(0, 255, 255, 0.05);
                border-radius: 8px; margin-bottom: 0.5rem; border: 1px solid rgba(0, 255, 255, 0.1);">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div style="font-size: 1.5rem;">
          ${deviceIcons[device.device_type] || '📱'}
        </div>
        <div>
          <div style="font-weight: 600; color: #00ffff;">${device.device_type}</div>
          <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6);">
            ${device.count || 0} заявок за месяц
          </div>
        </div>
      </div>
      <div style="text-align: right; font-size: 0.85rem; color: rgba(255,255,255,0.8);">
        <div style="color: #00ff00;">${device.completed || 0} выполнено</div>
        <div style="color: rgba(255,255,255,0.5);">
          ₽${(device.avg_cost || 0).toLocaleString('ru-RU')}
        </div>
      </div>
    </div>
  `).join('');

  console.log('✅ Статистика устройств отображена');
}

// 🧾 Загрузка последних заявок
async function loadDashboardRequests() {
  try {
    console.log('🧾 Загружаем последние заявки...');
    const res = await fetch("/dashboard/api/requests", {
      credentials: "include"
    });

    if (res.status === 401) {
      console.log('❌ 401 - перенаправляем на login');
      window.location.href = "/auth/login";
      return;
    }

    if (!res.ok) throw new Error(`Ошибка загрузки заявок: ${res.status}`);

    const requests = await res.json();
    console.log('✅ Заявки загружены:', requests.length);
    renderRequestsTable(requests.slice(0, 5));
  } catch (err) {
    console.error("❌ Ошибка загрузки заявок:", err);
    renderRequestsTable([]);
  }
}

// 👤 Загрузка информации о пользователе
async function loadUserInfo() {
  try {
    console.log('👤 Загружаем информацию о пользователе...');
    const res = await fetch("/auth/profile", {
      credentials: "include"
    });

    if (res.status === 401) {
      console.log('❌ 401 - перенаправляем на login');
      window.location.href = "/auth/login";
      return;
    }

    if (!res.ok) throw new Error(`Ошибка загрузки профиля: ${res.status}`);

    const user = await res.json();
    console.log('✅ Профиль пользователя загружен:', user);

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
  }
}

function createWeeklyChart(data) {
    const canvas = document.getElementById('weeklyChart');
    if (!canvas) {
        console.warn('⚠️ Canvas weeklyChart не найден');
        return;
    }

    const ctx = canvas.getContext('2d');

    // Устанавливаем размеры canvas для четкости
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Улучшенный график с анимацией и градиентами
    drawEnhancedLineChart(ctx, {
        labels: data.labels || ['29.05', '30.05', '31.05', '01.06', '02.06', '03.06', '04.06'],
        datasets: [
            {
                label: 'Новые заявки',
                data: data.requests || [5, 8, 12, 7, 15, 10, 6],
                color: '#00ffff',
                fillColor: 'rgba(0, 255, 255, 0.1)'
            },
            {
                label: 'Выполнено',
                data: data.completed || [3, 6, 9, 5, 11, 8, 4],
                color: '#00ff00',
                fillColor: 'rgba(0, 255, 0, 0.1)'
            }
        ]
    }, rect.width, rect.height);

    console.log('✅ Улучшенный график за неделю создан');
}

function createStatusChart(statusData) {
    const canvas = document.getElementById('statusChart');
    if (!canvas) {
        console.warn('⚠️ Canvas statusChart не найден');
        return;
    }

    const ctx = canvas.getContext('2d');

    // Устанавливаем размеры canvas
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Данные по умолчанию или из API
    const data = statusData.length ? statusData : [
        { status: 'Диагностика', count: 2 },
        { status: 'Выдана', count: 1 },
        { status: 'Ожидание запчастей', count: 1 }
    ];

    // Используем правильное название функции
    drawEnhancedPieChart(ctx, data, rect.width, rect.height);

    // Создаем легенду снизу
    createPieChartLegend(data);

    console.log('✅ Улучшенный график статусов создан');
}


function drawEnhancedPieChart(ctx, data, width, height) {
    // Очищаем canvas
    ctx.clearRect(0, 0, width, height);

    // Центрируем диаграмму, оставляя место снизу для легенды
    const centerX = width / 2;
    const centerY = height / 2 - 20; // Немного сдвигаем вверх для легенды
    const radius = Math.min(centerX, centerY) - 40; // Увеличенный радиус

    // Улучшенные цвета для статусов
    const colors = {
        'Принята': '#00ffff',
        'Диагностика': '#0099ff',
        'Ожидание запчастей': '#ffff00',
        'В ремонте': '#ff9800',
        'Тестирование': '#9c27b0',
        'Готова к выдаче': '#4caf50',
        'Выдана': '#00ff00'
    };

    const total = data.reduce((sum, item) => sum + item.count, 0);

    // Если нет данных, показываем заглушку
    if (total === 0) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Нет данных для отображения', width/2, height/2);
        return;
    }

    let currentAngle = -Math.PI / 2; // Начинаем сверху

    data.forEach((item, index) => {
        const sliceAngle = (item.count / total) * 2 * Math.PI;
        const color = colors[item.status] || `hsl(${index * 60}, 70%, 60%)`;

        // Рисуем сегмент с тенью
        ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
        ctx.shadowBlur = 10;
        ctx.shadowOffsetX = 2;
        ctx.shadowOffsetY = 2;

        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
        ctx.lineTo(centerX, centerY);
        ctx.fillStyle = color;
        ctx.fill();

        // Убираем тень для обводки
        ctx.shadowColor = 'transparent';
        ctx.strokeStyle = '#1a1a2e';
        ctx.lineWidth = 3;
        ctx.stroke();

        // Рисуем подпись на сегменте только если сегмент достаточно большой
        if (sliceAngle > 0.2) {
            const labelAngle = currentAngle + sliceAngle / 2;
            const labelRadius = radius * 0.7;
            const labelX = centerX + Math.cos(labelAngle) * labelRadius;
            const labelY = centerY + Math.sin(labelAngle) * labelRadius;

            ctx.fillStyle = '#000';
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(item.count, labelX, labelY + 5);
        }

        currentAngle += sliceAngle;
    });

    // Рисуем центральный круг (больше)
    const innerRadius = radius * 0.45;
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.fillStyle = '#1a1a2e';
    ctx.fill();
    ctx.strokeStyle = '#00ffff';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Общее количество в центре (больший шрифт)
    ctx.fillStyle = '#00ffff';
    ctx.font = 'bold 28px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(total, centerX, centerY - 5);
    ctx.font = '14px Arial';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.fillText('заявок', centerX, centerY + 20);
}

function drawEnhancedLineChart(ctx, chartData, width, height) {
    // Очищаем canvas
    ctx.clearRect(0, 0, width, height);

    const padding = 60;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const labels = chartData.labels;
    const datasets = chartData.datasets;

    if (!labels.length) {
        // Если нет данных, показываем заглушку
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Нет данных для отображения', width/2, height/2);
        return;
    }

    // Находим максимальное значение
    const maxValue = Math.max(...datasets.flatMap(d => d.data)) || 10;
    const stepX = chartWidth / (labels.length - 1);
    const stepY = chartHeight / maxValue;

    // Рисуем сетку
    drawGrid(ctx, padding, chartWidth, chartHeight, maxValue, labels.length);

    // Рисуем линии данных
    datasets.forEach((dataset, index) => {
        drawDataLine(ctx, dataset, padding, stepX, stepY, chartHeight, index);
    });

    // Рисуем подписи осей
    drawAxisLabels(ctx, labels, padding, stepX, chartHeight, maxValue, stepY);

    // НЕ рисуем легенду внутри canvas - она уже есть в HTML снизу
    // Убираем вызов drawBottomLegend
}


function drawGrid(ctx, padding, chartWidth, chartHeight, maxValue, labelCount) {
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;

    // Вертикальные линии
    for (let i = 0; i < labelCount; i++) {
        const x = padding + (i * chartWidth / (labelCount - 1));
        ctx.beginPath();
        ctx.moveTo(x, padding);
        ctx.lineTo(x, padding + chartHeight);
        ctx.stroke();
    }

    // Горизонтальные линии
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const y = padding + (i * chartHeight / gridLines);
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(padding + chartWidth, y);
        ctx.stroke();
    }
}

function drawBottomLegend(ctx, datasets, width, height, padding) {
    const legendY = height - 30;
    const legendStartX = width / 2 - (datasets.length * 100) / 2;

    datasets.forEach((dataset, index) => {
        const x = legendStartX + index * 150;

        // Цветной квадратик
        ctx.fillStyle = dataset.color;
        ctx.fillRect(x, legendY, 15, 15);

        // Подпись
        ctx.fillStyle = '#ffffff';
        ctx.font = '14px Arial';
        ctx.textAlign = 'left';
        ctx.fillText(dataset.label, x + 25, legendY + 12);
    });
}

function drawDataLine(ctx, dataset, padding, stepX, stepY, chartHeight, index) {
    const { data, color, fillColor } = dataset;

    // Создаем градиент для заливки
    if (fillColor) {
        const gradient = ctx.createLinearGradient(0, padding, 0, padding + chartHeight);
        gradient.addColorStop(0, fillColor);
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

        // Рисуем область под линией
        ctx.beginPath();
        ctx.moveTo(padding, padding + chartHeight);

        data.forEach((value, i) => {
            const x = padding + i * stepX;
            const y = padding + chartHeight - (value * stepY);
            if (i === 0) ctx.lineTo(x, y);
            else ctx.lineTo(x, y);
        });

        ctx.lineTo(padding + (data.length - 1) * stepX, padding + chartHeight);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();
    }

    // Рисуем линию
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    data.forEach((value, i) => {
        const x = padding + i * stepX;
        const y = padding + chartHeight - (value * stepY);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    ctx.stroke();

    // Рисуем точки
    data.forEach((value, i) => {
        const x = padding + i * stepX;
        const y = padding + chartHeight - (value * stepY);

        // Внешний круг
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // Внутренний круг
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();

        // Подпись значения
        ctx.fillStyle = color;
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(value, x, y - 12);
    });
}

function drawAxisLabels(ctx, labels, padding, stepX, chartHeight, maxValue, stepY) {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';

    // Подписи X-оси
    labels.forEach((label, i) => {
        const x = padding + i * stepX;
        ctx.fillText(label, x, padding + chartHeight + 20);
    });

    // Подписи Y-оси
    ctx.textAlign = 'right';
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const value = Math.round((maxValue / gridLines) * (gridLines - i));
        const y = padding + (i * chartHeight / gridLines) + 4;
        ctx.fillText(value, padding - 10, y);
    }
}

function drawLegend(ctx, datasets, width, padding) {
    const legendY = 20;
    let legendX = width - 200;

    datasets.forEach((dataset, index) => {
        const y = legendY + index * 25;

        // Цветной квадратик
        ctx.fillStyle = dataset.color;
        ctx.fillRect(legendX, y, 15, 15);

        // Подпись
        ctx.fillStyle = '#ffffff';
        ctx.font = '14px Arial';
        ctx.textAlign = 'left';
        ctx.fillText(dataset.label, legendX + 25, y + 12);
    });
}

function createPieChartLegend(data) {
    const canvas = document.getElementById('statusChart');
    if (!canvas) return;

    const container = canvas.parentElement;

    // Удаляем ВСЕ старые легенды
    const oldLegends = container.querySelectorAll('.bottom-chart-legend, .side-chart-legend');
    oldLegends.forEach(legend => legend.remove());

    // Создаем контейнер для легенды СТРОГО СНИЗУ
    const legendContainer = document.createElement('div');
    legendContainer.className = 'bottom-chart-legend';
    legendContainer.style.cssText = `
        display: flex !important;
        justify-content: center !important;
        gap: 2rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(0, 255, 255, 0.1);
        flex-wrap: wrap;
        position: static !important;
        width: 100% !important;
    `;

    const colors = {
        'Принята': '#00ffff',
        'Диагностика': '#0099ff',
        'Ожидание запчастей': '#ffff00',
        'В ремонте': '#ff9800',
        'Тестирование': '#9c27b0',
        'Готова к выдаче': '#4caf50',
        'Выдана': '#00ff00'
    };

    data.forEach((item, index) => {
        const color = colors[item.status] || `hsl(${index * 60}, 70%, 60%)`;

        const legendItem = document.createElement('div');
        legendItem.style.cssText = `
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.8);
        `;

        legendItem.innerHTML = `
            <div style="
                width: 16px;
                height: 16px;
                background: ${color};
                border-radius: 3px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                flex-shrink: 0;
            "></div>
            <span>${item.status}</span>
        `;

        legendContainer.appendChild(legendItem);
    });

    // Добавляем легенду в конец контейнера (снизу)
    container.appendChild(legendContainer);
}


// Функция для создания анимации появления графиков
function animateCharts() {
    const charts = [
        { id: 'weeklyChart', delay: 0 },
        { id: 'statusChart', delay: 200 }
    ];

    charts.forEach(chart => {
        const canvas = document.getElementById(chart.id);
        if (canvas) {
            canvas.style.opacity = '0';
            canvas.style.transform = 'scale(0.8)';
            canvas.style.transition = 'all 0.6s ease';

            setTimeout(() => {
                canvas.style.opacity = '1';
                canvas.style.transform = 'scale(1)';
            }, chart.delay);
        }
    });
}

// Обновляем функцию loadCharts
async function loadCharts() {
    try {
        console.log('📈 Загружаем данные для графиков...');

        // Загружаем данные для графиков
        const [weeklyData, statsData] = await Promise.all([
            fetch("/dashboard/api/charts/weekly", { credentials: "include" }).then(r => r.json()),
            fetch("/dashboard/api/stats/detailed", { credentials: "include" }).then(r => r.json())
        ]);

        console.log('✅ Данные графиков загружены');

        // Создаем графики
        createWeeklyChart(weeklyData);
        createStatusChart(statsData.status_stats || []);

        // Анимация появления
        animateCharts();

    } catch (err) {
        console.error("❌ Ошибка загрузки данных для графиков:", err);
        createPlaceholderCharts();
    }
}

function createPlaceholderCharts() {
    console.log('⚠️ Создаем заглушки для графиков');

    const weeklyCanvas = document.getElementById('weeklyChart');
    const statusCanvas = document.getElementById('statusChart');

    if (weeklyCanvas) {
        const ctx = weeklyCanvas.getContext('2d');
        const rect = weeklyCanvas.getBoundingClientRect();
        weeklyCanvas.width = rect.width * window.devicePixelRatio;
        weeklyCanvas.height = rect.height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

        ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.fillRect(0, 0, rect.width, rect.height);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Нет данных для отображения', rect.width/2, rect.height/2);
    }

    if (statusCanvas) {
        const ctx = statusCanvas.getContext('2d');
        const rect = statusCanvas.getBoundingClientRect();
        statusCanvas.width = rect.width * window.devicePixelRatio;
        statusCanvas.height = rect.height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

        ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.fillRect(0, 0, rect.width, rect.height);
        ctx.fillStyle = '#ffffff';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Нет данных для отображения', rect.width/2, rect.height/2);
    }
}

// 🖊️ Отображение заявок в таблице
function renderRequestsTable(requests) {
  const tbody = document.getElementById("recentRequestsTable");

  if (!tbody) {
    console.warn('⚠️ Элемент recentRequestsTable не найден');
    return;
  }

  if (!requests.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: rgba(255,255,255,0.6); padding: 2rem;">
          Нет данных для отображения
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = requests.map(r => `
    <tr>
      <td style="color: #00ffff; font-weight: bold;">#${r.request_id || '—'}</td>
      <td>${r.client_name || '—'}</td>
      <td>${r.device_type || '—'}</td>
      <td title="${r.problem_description || ''}">${(r.problem_description || '').slice(0, 40)}${(r.problem_description || '').length > 40 ? '...' : ''}</td>
      <td><span class="status-badge ${getStatusClass(r.status)}">${r.status || '—'}</span></td>
      <td>${r.master_name || '—'}</td>
      <td>${r.created_at ? new Date(r.created_at).toLocaleDateString('ru-RU') : '—'}</td>
      <td>
        <a href="/dashboard/requests" class="btn btn-outline" style="padding: 4px 8px; font-size: 0.85rem;">
          Подробнее
        </a>
      </td>
    </tr>
  `).join('');

  console.log('✅ Таблица заявок обновлена');
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

// Дополнительные функции для переключения графиков
async function loadWeeklyChart() {
  try {
    const data = await fetch("/dashboard/api/charts/weekly", { credentials: "include" }).then(r => r.json());
    createWeeklyChart(data);
    console.log('✅ График за неделю обновлен');
  } catch (err) {
    console.error("❌ Ошибка загрузки недельного графика:", err);
  }
}

async function loadMonthlyChart() {
  try {
    const data = await fetch("/dashboard/api/charts/monthly", { credentials: "include" }).then(r => r.json());
    createWeeklyChart(data); // Используем ту же функцию, но с месячными данными
    console.log('✅ График за месяц обновлен');
  } catch (err) {
    console.error("❌ Ошибка загрузки месячного графика:", err);
  }
}

// Утилиты
function logout() {
  console.log('🚪 Выход из системы');
  window.location.href = "/logout";
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.classList.toggle('active');
    console.log('📱 Sidebar переключен');
  }
}

// Функция для принудительного обновления всех данных
function refreshDashboard() {
  console.log('🔄 Принудительное обновление dashboard...');
  loadDashboardStats();
  loadDashboardRequests();
  loadCharts();
  loadTopMasters();
  loadDeviceStats();
}

function setActiveButton(button) {
    // Убираем активный класс у всех кнопок в той же группе
    const parent = button.parentElement;
    const buttons = parent.querySelectorAll('.btn-chart-toggle');
    buttons.forEach(btn => btn.classList.remove('active'));

    // Добавляем активный класс к нажатой кнопке
    button.classList.add('active');
}
console.log('✅ Dashboard.js загружен и готов к работе');