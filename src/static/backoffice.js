/* Бэк-офис — логика загрузки и отображения метрик */

const CASE_NAMES = {
  1: 'Формулировка цели',
  2: 'Ключевые результаты',
  3: 'Квартальная декомпозиция',
  4: 'Верификация по руководству',
  5: 'Конфликты и слепые зоны',
  6: 'Риски достижения',
  7: 'Экспресс-отчёт',
};

let timelineChart = null;
let casesChart = null;

async function loadMetrics() {
  const loading = document.getElementById('loading');
  const errorMsg = document.getElementById('error-msg');

  loading.classList.remove('hidden');
  errorMsg.classList.add('hidden');

  try {
    const resp = await fetch('/api/metrics');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    renderMetrics(data);
    loading.classList.add('hidden');
  } catch (e) {
    loading.classList.add('hidden');
    errorMsg.textContent = 'Ошибка загрузки метрик: ' + e.message;
    errorMsg.classList.remove('hidden');
  }
}

function renderMetrics(data) {
  // Сводка
  document.getElementById('stat-requests').textContent = data.total_requests || 0;
  document.getElementById('stat-unique-ip').textContent = data.unique_ips || 0;
  const pct = data.total_positive_pct;
  document.getElementById('stat-positive-pct').textContent = pct != null ? pct + '%' : '—';

  // График по дням
  renderTimelineChart(data.timeline || []);

  // График кейсов
  renderCasesChart(data.case_stats || []);

  // Таблица IP
  renderIpTable(data.ip_stats || []);

  // Таблица кейсов с оценками
  renderCasesTable(data.case_stats || []);
}

function renderTimelineChart(timeline) {
  const canvas = document.getElementById('timeline-chart');
  const noData = document.getElementById('no-timeline');

  if (!timeline.length) {
    canvas.classList.add('hidden');
    noData.classList.remove('hidden');
    return;
  }

  canvas.classList.remove('hidden');
  noData.classList.add('hidden');

  const labels = timeline.map(r => r.date);
  const counts = timeline.map(r => r.count);

  if (timelineChart) timelineChart.destroy();
  timelineChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Запросов в день',
        data: counts,
        borderColor: '#0052CC',
        backgroundColor: 'rgba(0,82,204,0.1)',
        tension: 0.3,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } }
      }
    }
  });
}

function renderCasesChart(caseStats) {
  const canvas = document.getElementById('cases-chart');
  const noData = document.getElementById('no-cases');

  const hasData = caseStats.some(c => c.requests > 0);
  if (!hasData) {
    canvas.classList.add('hidden');
    noData.classList.remove('hidden');
    return;
  }

  canvas.classList.remove('hidden');
  noData.classList.add('hidden');

  const labels = caseStats.map(c => `К${c.case_id}`);
  const counts = caseStats.map(c => c.requests);

  if (casesChart) casesChart.destroy();
  casesChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Запусков',
        data: counts,
        backgroundColor: '#0052CC',
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => CASE_NAMES[parseInt(items[0].label.slice(1))] || items[0].label
          }
        }
      },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } }
      }
    }
  });
}

function renderIpTable(ipStats) {
  const container = document.getElementById('ip-table-container');

  if (!ipStats.length) {
    container.innerHTML = '<div class="no-data">Нет данных</div>';
    return;
  }

  const rows = ipStats.map((item, idx) => `
    <tr>
      <td>${idx + 1}</td>
      <td><code>${item.ip}</code></td>
      <td>${item.count}</td>
    </tr>
  `).join('');

  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>IP-адрес</th>
          <th>Запросов</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderCasesTable(caseStats) {
  const container = document.getElementById('cases-table-container');

  const rows = caseStats.map(c => {
    const pct = c.pct_positive;
    let badge = '<span class="badge badge-gray">—</span>';
    if (pct != null) {
      if (pct >= 70) {
        badge = `<span class="badge badge-green">${pct}% ✓</span>`;
      } else {
        badge = `<span class="badge badge-red">${pct}%</span>`;
      }
    }

    // Цель: каждый кейс использован ≥5 раз
    const reqBadge = c.requests >= 5
      ? `<span class="badge badge-green">${c.requests} ✓</span>`
      : `<span class="badge ${c.requests > 0 ? 'badge-red' : 'badge-gray'}">${c.requests}</span>`;

    return `
      <tr>
        <td>Кейс ${c.case_id}</td>
        <td>${CASE_NAMES[c.case_id] || '—'}</td>
        <td>${reqBadge}</td>
        <td>${c.positive} 👍 / ${c.negative} 👎</td>
        <td>${badge}</td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Кейс</th>
          <th>Название</th>
          <th>Запусков (цель: ≥5)</th>
          <th>Оценки</th>
          <th>% положительных (цель: >70%)</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// Загружаем при открытии страницы
document.addEventListener('DOMContentLoaded', loadMetrics);
