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

// 📈 Загрузка и создание графиков
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

  } catch (err) {
    console.error("❌ Ошибка загрузки данных для графиков:", err);
    createPlaceholderCharts();
  }
}

function createWeeklyChart(data) {
  const canvas = document.getElementById('weeklyChart');
  if (!canvas) {
    console.warn('⚠️ Canvas weeklyChart не найден');
    return;
  }

  const ctx = canvas.getContext('2d');

  // Простой график с Canvas API
  drawLineChart(ctx, {
    labels: data.labels || ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
    datasets: [
      {
        label: 'Новые заявки',
        data: data.requests || [5, 8, 12, 7, 15, 10, 6],
        color: '#00ffff'
      },
      {
        label: 'Выполнено',
        data: data.completed || [3, 6, 9, 5, 11, 8, 4],
        color: '#00ff00'
      }
    ]
  });

  console.log('✅ График за неделю создан');
}

function createStatusChart(statusData) {
  const canvas = document.getElementById('statusChart');
  if (!canvas) {
    console.warn('⚠️ Canvas statusChart не найден');
    return;
  }

  const ctx = canvas.getContext('2d');

  // Простая круговая диаграмма
  const data = statusData.length ? statusData : [
    { status: 'В работе', count: 15 },
    { status: 'Завершено', count: 25 },
    { status: 'Ожидание', count: 8 }
  ];

  drawPieChart(ctx, data);
  console.log('✅ График статусов создан');
}

function drawLineChart(ctx, chartData) {
  const canvas = ctx.canvas;
  const width = canvas.width;
  const height = canvas.height;
  const padding = 40;

  // Очищаем canvas
  ctx.clearRect(0, 0, width, height);

  // Настройка стилей
  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#00ffff';
  ctx.lineWidth = 2;
  ctx.font = '12px Arial';

  // Получаем данные
  const labels = chartData.labels;
  const datasets = chartData.datasets;

  if (!labels.length) return;

  // Расчет размеров
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;
  const stepX = chartWidth / (labels.length - 1);

  // Найдем максимальное значение
  const maxValue = Math.max(...datasets.flatMap(d => d.data));
  const stepY = chartHeight / (maxValue || 1);

  // Рисуем оси
  ctx.beginPath();
  ctx.moveTo(padding, padding);
  ctx.lineTo(padding, height - padding);
  ctx.lineTo(width - padding, height - padding);
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.stroke();

  // Рисуем подписи осей
  ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
  labels.forEach((label, i) => {
    const x = padding + i * stepX;
    ctx.fillText(label, x - 10, height - padding + 20);
  });

  // Рисуем линии данных
  datasets.forEach(dataset => {
    ctx.beginPath();
    ctx.strokeStyle = dataset.color;
    ctx.lineWidth = 3;

    dataset.data.forEach((value, i) => {
      const x = padding + i * stepX;
      const y = height - padding - (value * stepY);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }

      // Рисуем точки
      ctx.fillStyle = dataset.color;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.stroke();
  });

  // Легенда
  let legendY = 20;
  datasets.forEach(dataset => {
    ctx.fillStyle = dataset.color;
    ctx.fillRect(width - 150, legendY, 12, 12);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(dataset.label, width - 130, legendY + 10);
    legendY += 25;
  });
}

function drawPieChart(ctx, data) {
  const canvas = ctx.canvas;
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const radius = Math.min(centerX, centerY) - 40;

  // Очищаем canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Цвета для сегментов
  const colors = ['#00ffff', '#00ff00', '#ffff00', '#ff9800', '#ff4444'];

  const total = data.reduce((sum, item) => sum + item.count, 0);
  if (total === 0) return;

  let startAngle = -Math.PI / 2;

  data.forEach((item, index) => {
    const sliceAngle = (item.count / total) * 2 * Math.PI;

    // Рисуем сегмент
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
    ctx.lineTo(centerX, centerY);
    ctx.fillStyle = colors[index % colors.length];
    ctx.fill();
    ctx.strokeStyle = '#1a1a2e';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Добавляем подпись
    const labelAngle = startAngle + sliceAngle / 2;
    const labelX = centerX + Math.cos(labelAngle) * (radius + 30);
    const labelY = centerY + Math.sin(labelAngle) * (radius + 30);

    ctx.fillStyle = '#ffffff';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(item.status, labelX, labelY);
    ctx.fillText(`${item.count}`, labelX, labelY + 15);

    startAngle += sliceAngle;
  });
}

function createPlaceholderCharts() {
  console.log('⚠️ Создаем заглушки для графиков');

  const weeklyCanvas = document.getElementById('weeklyChart');
  const statusCanvas = document.getElementById('statusChart');

  if (weeklyCanvas) {
    const ctx = weeklyCanvas.getContext('2d');
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.fillRect(0, 0, weeklyCanvas.width, weeklyCanvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Нет данных для отображения', weeklyCanvas.width/2, weeklyCanvas.height/2);
  }

  if (statusCanvas) {
    const ctx = statusCanvas.getContext('2d');
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.fillRect(0, 0, statusCanvas.width, statusCanvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Нет данных для отображения', statusCanvas.width/2, statusCanvas.height/2);
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

console.log('✅ Dashboard.js загружен и готов к работе');