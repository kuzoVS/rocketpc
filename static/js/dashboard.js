function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('active');
}

document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.mobile-menu-toggle');
    if (window.innerWidth <= 1024 && !sidebar.contains(event.target) && !toggle.contains(event.target)) {
        sidebar.classList.remove('active');
    }
});

window.addEventListener('DOMContentLoaded', function() {
    drawWeeklyChart();
    drawStatusChart();
});

function drawWeeklyChart() {
    const canvas = document.getElementById('weeklyChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = "#00ffff";
    ctx.fillText("Chart Placeholder", 20, 100);
}

function drawStatusChart() {
    const canvas = document.getElementById('statusChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = "#00ffff";
    ctx.fillText("Status Chart Placeholder", 20, 100);
}