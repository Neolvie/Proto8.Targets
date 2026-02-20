/* Бэк-офис — логика загрузки и отображения метрик */

const CASE_NAMES = {
  1: 'Переформулировать цель',
  2: 'Сгенерировать KR',
  3: 'Декомпозировать',
  5: 'Подсветить конфликты',
  6: 'Выявить риски',
  7: 'Подготовить отчёт',
};

let timelineChart = null;
let casesChart = null;

async function loadMetrics() {
  const loading = document.getElementById('loading');
  const errorMsg = document.getElementById('error-msg');

  loading.classList.remove('hidden');
  errorMsg.classList.add('hidden');

  try {
    const resp = await fetch('/api/metrics', { credentials: 'include' });
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

  // Таблица оценок чата
  renderChatFeedbackTable(data.chat_feedback || [], data.chat_positive_pct, data.chat_total_votes);
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
        borderColor: '#0043A4',
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
        backgroundColor: '#0043A4',
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

function renderChatFeedbackTable(rows, positivePct, totalVotes) {
  const summary = document.getElementById('chat-feedback-summary');
  const container = document.getElementById('chat-feedback-container');

  if (!rows.length) {
    summary.textContent = '';
    container.innerHTML = '<div class="no-data">Нет данных</div>';
    return;
  }

  const pctText = positivePct != null ? `${positivePct}% положительных` : '—';
  summary.textContent = `Всего оценок: ${totalVotes || 0} | ${pctText}`;

  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const tableRows = rows.map(r => {
    const voteIcon = r.vote === 1 ? '👍' : '👎';
    const voteClass = r.vote === 1 ? 'badge-green' : 'badge-red';
    const contextLabel = r.context_type === 'target' ? 'Цель' : 'Карта';
    const ts = r.timestamp ? r.timestamp.slice(0, 16).replace('T', ' ') : '—';

    let messageCell;
    if (r.summary) {
      // Саммари от LLM готово — показываем его + спойлер с полным текстом
      messageCell = `
        ${esc(r.summary)}
        <details style="margin-top:4px;font-size:12px">
          <summary style="cursor:pointer;color:#0043A4">Полный текст</summary>
          <pre style="white-space:pre-wrap;margin-top:4px;background:#F4F5F7;padding:6px;border-radius:4px;font-size:11px">${esc(r.user_message)}</pre>
        </details>
      `;
    } else {
      // Саммари ещё не готово или ошибка — показываем полный текст без спойлера
      messageCell = `<span style="color:#5E6C84">${esc(r.user_message)}</span>`;
    }

    return `
      <tr>
        <td style="white-space:nowrap;font-size:12px;color:#5E6C84">${ts}</td>
        <td><span class="badge ${voteClass}">${voteIcon}</span></td>
        <td style="font-size:12px">${contextLabel}: <strong>${esc(r.context_name)}</strong></td>
        <td>${messageCell}</td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Время</th>
          <th>Оценка</th>
          <th>Контекст</th>
          <th>Запрос пользователя</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

// Загружаем при открытии страницы
document.addEventListener('DOMContentLoaded', loadMetrics);
