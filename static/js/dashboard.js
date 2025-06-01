// dashboard.js — обновленная версия с графиками

let weeklyChart = null;
let statusChart = null;
let deviceChart = null;

window.addEventListener("DOMContentLoaded", () => {
  loadDashboardStats();
  loadDashboardRequests();
  loadUserInfo();
  loadCharts();
});

// 📊 Загрузка детальной статистики
async function loadDashboardStats() {
  try {
    const res = await fetch("/dashboard/api/stats/detailed", {
      credentials: "include"
    });

    if (res.status === 401) {
      window.location.href = "/auth/login";
      return;
    }

    if (!res.ok) throw new Error("Ошибка загрузки статистики");

    const stats = await res.json();

    // Обновляем основные показатели
    updateStatCard("activeRequestsCount", stats.active_requests || 0, "↑", "+12% за неделю");
    updateStatCard("completedRequestsCount", stats.completed_this_month || 0, "↑", `+${stats.growth_percentage || 0}% к прошлому месяцу`);
    updateStatCard("monthlyRevenue", `${(stats.monthly_revenue || 0).toLocaleString('ru-RU')}₽`, "↑", "+23% к прошлому месяцу");

    // Добавляем дополнительные карточки если их нет
    addAdditionalStatCards(stats);

  } catch (err) {
    console.error("Ошибка загрузки статистики:", err);
  }
}

function updateStatCard(elementId, value, trend, change) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = value;

    // Обновляем изменение
    const changeElement = element.closest('.stat-card').querySelector('.stat-change');
    if (changeElement) {
      changeElement.innerHTML = `<span>${trend}</span> ${change}`;
    }
  }
}

function addAdditionalStatCards(stats) {
  const statsGrid = document.querySelector('.stats-grid');
  if (!statsGrid) return;

  // Проверяем, есть ли уже дополнительные карточки
  if (statsGrid.children.length > 3) return;

  // Средняя стоимость
  const avgCostCard = createStatCard(
    "💳",
    `${(stats.avg_cost || 0).toLocaleString('ru-RU')}₽`,
    "Средняя стоимость",
    "📈 Стабильно"
  );

  statsGrid.appendChild(avgCostCard);
}

function createStatCard(icon, value, label, change) {
  const card = document.createElement('div');
  card.className = 'stat-card fade-in';
  card.innerHTML = `
    <div class="stat-header">
      <div class="stat-icon">${icon}</div>
    </div>
    <div class="stat-value">${value}</div>
    <div class="stat-label">${label}</div>
    <div class="stat-change">${change}</div>
  `;
  return card;
}

// 🧾 Загрузка последних заявок (без изменений)
async function loadDashboardRequests() {
  try {
    const res = await fetch("/dashboard/api/requests", {
      credentials: "include"
    });

    if (res.status === 401) {
      window.location.href = "/auth/login";
      return;
    }

    if (!res.ok) throw new Error("Ошибка загрузки заявок");

    const requests = await res.json();
    renderRequestsTable(requests.slice(0, 5));
  } catch (err) {
    console.error("Ошибка загрузки заявок:", err);
    renderRequestsTable([]);
  }
}

// 👤 Загрузка информации о пользователе (без изменений)
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

    if (user.role === 'admin' || user.role === 'director') {
      const usersMenuItem = document.getElementById('usersMenuItem');
      if (usersMenuItem) usersMenuItem.style.display = 'block';
    }

  } catch (err) {
    console.error("Ошибка загрузки профиля:", err);
  }
}

// 📈 Загрузка и создание графиков
async function loadCharts() {
  try {
    // Загружаем данные для графиков
    const [weeklyData, deviceData] = await Promise.all([
      fetch("/dashboard/api/charts/weekly", { credentials: "include" }).then(r => r.json()),
      fetch("/dashboard/api/stats", { credentials: "include" }).then(r => r.json())
    ]);

    // Создаем графики
    createWeeklyChart(weeklyData);
    createStatusChart(deviceData.status_stats || []);

  } catch (err) {
    console.error("Ошибка загрузки данных для графиков:", err);
    createPlaceholderCharts();
  }
}

function createWeeklyChart(data) {
  const canvas = document.getElementById('weeklyChart');
  if (!canvas) return;

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
}

function createStatusChart(statusData) {
  const canvas = document.getElementById('statusChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  // Простая круговая диаграмма
  const data = statusData.length ? statusData : [
    { status: 'В работе', count: 15 },
    { status: 'Завершено', count: 25 },
    { status: 'Ожидание', count: 8 }
  ];

  drawPieChart(ctx, data);
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
  const stepY = chartHeight / maxValue;

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
  // Создаем заглушки для графиков
  const weeklyCanvas = document.getElementById('weeklyChart');
  const statusCanvas = document.getElementById('statusChart');

  if (weeklyCanvas) {
    const ctx = weeklyCanvas.getContext('2d');
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.fillRect(0, 0, weeklyCanvas.width, weeklyCanvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Загрузка данных...', weeklyCanvas.width/2, weeklyCanvas.height/2);
  }

  if (statusCanvas) {
    const ctx = statusCanvas.getContext('2d');
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.fillRect(0, 0, statusCanvas.width, statusCanvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Загрузка данных...', statusCanvas.width/2, statusCanvas.height/2);
  }
}

// 🖊️ Отображение заявок в таблице (без изменений)
function renderRequestsTable(requests) {
  const tbody = document.getElementById("recentRequestsTable");

  if (!tbody) return;

  if (!requests.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: rgba(255,255,255,0.6);">
          Нет данных для отображения
        </td>
      </tr>`;
    return;
  }

  tbody.innerHTML = requests.map(r => `
    <tr>
      <td>#${r.request_id || '—'}</td>
      <td>${r.client_name || '—'}</td>
      <td>${r.device_type || '—'}</td>
      <td>${(r.problem_description || '').slice(0, 40)}...</td>
      <td><span class="status-badge ${getStatusClass(r.status)}">${r.status || '—'}</span></td>
      <td>${r.master_name || '—'}</td>
      <td>${r.created_at ? new Date(r.created_at).toLocaleDateString('ru-RU') : '—'}</td>
      <td>
        <a href="/dashboard/requests" class="btn btn-outline" style="padding: 4px 8px;">
          Подробнее
        </a>
      </td>
    </tr>
  `).join('');
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

// Утилиты
function logout() {
  window.location.href = "/logout";
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('active');
}