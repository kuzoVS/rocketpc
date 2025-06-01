// dashboard.js — используем cookie, localStorage больше не нужен

window.addEventListener("DOMContentLoaded", () => {
  loadDashboardStats();
  loadDashboardRequests();
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

    document.getElementById("activeRequestsCount").textContent = stats.active_requests;
    document.getElementById("completedRequestsCount").textContent = stats.completed_requests;
    document.getElementById("monthlyRevenue").textContent = `${stats.monthly_revenue}₽`;
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

// 🖊️ Отображение заявок в таблице
function renderRequestsTable(requests) {
  const tbody = document.getElementById("recentRequestsTable");

  if (!tbody) return;

  if (!requests.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: rgba(255,255,255,0.6);">
          <div class="loading" style="margin: 20px auto;"></div>
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
      <td><span class="status-badge">${r.status || '—'}</span></td>
      <td>${r.master_name || '—'}</td>
      <td>${r.created_at ? new Date(r.created_at).toLocaleDateString('ru-RU') : '—'}</td>
      <td><button class="btn btn-outline" style="padding: 4px 8px;">Подробнее</button></td>
    </tr>
  `).join('');
}

// 🚪 Выход
const logoutLink = document.getElementById("logout-link");
if (logoutLink) {
  logoutLink.addEventListener("click", (e) => {
    e.preventDefault();
    window.location.href = "/logout";
  });
}
