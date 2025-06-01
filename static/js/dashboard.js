// dashboard.js — работа через cookie авторизацию

window.addEventListener("DOMContentLoaded", () => {
  loadDashboardStats();
  loadDashboardRequests();
  loadUserInfo();
});

// 📊 Загрузка статистики
async function loadDashboardStats() {
  try {
    const res = await fetch("/dashboard/api/stats", {
      credentials: "include"
    });

    if (res.status === 401) {
      window.location.href = "/auth/login";
      return;
    }

    if (!res.ok) throw new Error("Ошибка загрузки статистики");

    const stats = await res.json();

    document.getElementById("activeRequestsCount").textContent = stats.active_requests || 0;
    document.getElementById("completedRequestsCount").textContent = stats.completed_requests || 0;
    document.getElementById("monthlyRevenue").textContent = `${stats.monthly_revenue || 0}₽`;
  } catch (err) {
    console.error("Ошибка загрузки статистики:", err);
  }
}

// 🧾 Загрузка последних заявок
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
    renderRequestsTable(requests.slice(0, 5)); // показываем только 5 последних
  } catch (err) {
    console.error("Ошибка загрузки заявок:", err);
    renderRequestsTable([]);
  }
}

// 👤 Загрузка информации о пользователе
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

    // Показываем пункт "Пользователи" для админов
    if (user.role === 'admin' || user.role === 'director') {
      const usersMenuItem = document.getElementById('usersMenuItem');
      if (usersMenuItem) usersMenuItem.style.display = 'block';
    }

  } catch (err) {
    console.error("Ошибка загрузки профиля:", err);
  }
}

// 🖊️ Отображение заявок в таблице
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

// Получение класса для статуса
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

// 🚪 Выход
const logoutLink = document.getElementById("logout-link");
if (logoutLink) {
  logoutLink.addEventListener("click", (e) => {
    e.preventDefault();
    window.location.href = "/logout";
  });
}

// Обработчик выхода для sidebar
function logout() {
  window.location.href = "/logout";
}

// Переключение sidebar на мобильных устройствах
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('active');
}