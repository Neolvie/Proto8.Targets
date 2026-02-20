/* ИИ-помощник Directum Targets v2 — фронтенд логика */

// State
const state = {
  selectedMapId: null,
  selectedMapContext: null,
  selectedTargetId: null,
  selectedTargetContext: null,
  mode: null, // 'map' | 'target'
  chatMessages: [],
  currentAbortController: null,
  sessionId: null,
  allMaps: [],
  selectedMapName: '',
  selectedTargetName: '',
};

const CASE_NAMES = {
  1: 'Переформулировать цель',
  2: 'Сгенерировать KR',
  3: 'Декомпозировать',
  5: 'Подсветить конфликты',
  6: 'Выявить риски',
  7: 'Подготовить отчёт',
};

// ===== SESSION =====

function initSession() {
  let sid = sessionStorage.getItem('targets_v2_session_id');
  if (!sid) {
    sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2);
    sessionStorage.setItem('targets_v2_session_id', sid);
  }
  state.sessionId = sid;

  const savedMessages = sessionStorage.getItem('targets_v2_chat');
  if (savedMessages) {
    try {
      state.chatMessages = JSON.parse(savedMessages);
      restoreChatMessages();
    } catch (e) { /* ignore */ }
  }
}

// ===== API: MAPS =====

async function loadMaps() {
  try {
    const resp = await fetch('/api/maps', { headers: { 'X-Session-Id': state.sessionId } });
    if (!resp.ok) throw new Error('Ошибка загрузки карт');

    const data = await resp.json();

    if (data.error) {
      document.getElementById('maps-select').innerHTML =
        `<option value="">${data.error}</option>`;
      return;
    }

    state.allMaps = data.maps;

    // Periods
    const periodFilter = document.getElementById('period-filter');
    periodFilter.innerHTML = '<option value="">— все периоды —</option>';
    for (const period of data.periods) {
      const opt = document.createElement('option');
      opt.value = period;
      opt.textContent = period;
      periodFilter.appendChild(opt);
    }

    populateMapsDropdown(state.allMaps);
  } catch (e) {
    document.getElementById('maps-select').innerHTML =
      `<option value="">Ошибка: ${e.message}</option>`;
  }
}

function populateMapsDropdown(maps) {
  const sel = document.getElementById('maps-select');
  const prevValue = sel.value;
  sel.innerHTML = '<option value="">— выберите карту —</option>';
  for (const map of maps) {
    const opt = document.createElement('option');
    opt.value = map.id;
    opt.textContent = `${map.name} (${map.achievement_percentage.toFixed(0)}%)`;
    sel.appendChild(opt);
  }
  if (prevValue && maps.find(m => String(m.id) === prevValue)) {
    sel.value = prevValue;
  }
}

function filterMapsByPeriod() {
  const period = document.getElementById('period-filter').value;
  const filtered = period ? state.allMaps.filter(m => m.period_label === period) : state.allMaps;
  populateMapsDropdown(filtered);
}

async function onMapSelectChange() {
  const sel = document.getElementById('maps-select');
  const mapId = parseInt(sel.value);
  if (!mapId) {
    state.selectedMapId = null;
    state.selectedMapContext = null;
    state.selectedTargetId = null;
    state.selectedTargetContext = null;
    state.mode = null;
    document.getElementById('goals-section').classList.add('hidden');
    updateContextIndicator();
    updateCaseButtons();
    return;
  }
  const map = state.allMaps.find(m => m.id === mapId);
  await selectMap(mapId, map ? map.name : String(mapId));
}

async function selectMap(mapId, mapName) {
  state.selectedMapId = mapId;
  state.selectedMapName = mapName;
  state.selectedTargetId = null;
  state.selectedTargetContext = null;
  state.mode = 'map';

  document.querySelectorAll('.goal-item').forEach(el => el.classList.remove('active'));

  // Show loading spinner
  const goalsList = document.getElementById('goals-list');
  goalsList.innerHTML = '<div class="goals-loading"><span class="spinner"></span> Загрузка целей...</div>';
  document.getElementById('goals-section').classList.remove('hidden');
  updateCaseButtons();

  try {
    const resp = await fetch(`/api/maps/${mapId}/goals`, {
      headers: { 'X-Session-Id': state.sessionId }
    });
    if (!resp.ok) throw new Error('Ошибка загрузки целей');

    const data = await resp.json();
    state.selectedMapContext = data.map_context ||
      `Карта: ${data.map.name} | Прогресс: ${data.map.progress}%`;

    goalsList.innerHTML = '';
    for (const node of data.nodes) {
      const item = document.createElement('div');
      item.className = 'goal-item';
      item.dataset.targetId = node.target_id;
      item.onclick = () => selectGoal(node.target_id, node.code, node.name);

      const statusKey = node.status_icon ? node.status_icon.toLowerCase() : 'none';
      const dotClass = `goal-status-dot status-${statusKey}`;
      item.innerHTML = `
        <div class="goal-header">
          <span class="goal-code">${node.code}</span>
          <span class="${dotClass}" title="${node.status_icon || ''}"></span>
        </div>
        <div class="goal-name">${node.name}</div>
        <div class="goal-meta">Прогресс: ${node.progress.toFixed(0)}% | КР: ${node.key_result_count}</div>
      `;
      goalsList.appendChild(item);
    }

    updateContextIndicator();
    updateCaseButtons();
  } catch (e) {
    goalsList.innerHTML = `<div style="color:var(--color-danger);font-size:12px;padding:8px 4px">Ошибка: ${e.message}</div>`;
  }
}

async function selectGoal(targetId, code, name) {
  // Повторный клик по активной цели — развыбрать, вернуться в режим карты
  if (state.selectedTargetId === targetId) {
    document.querySelectorAll('.goal-item').forEach(el => el.classList.remove('active'));
    state.selectedTargetId = null;
    state.selectedTargetContext = null;
    state.selectedTargetName = '';
    state.mode = 'map';
    updateContextIndicator();
    updateCaseButtons();
    return;
  }

  document.querySelectorAll('.goal-item').forEach(el => el.classList.remove('active'));
  document.querySelector(`.goal-item[data-target-id="${targetId}"]`)?.classList.add('active');

  state.selectedTargetId = targetId;
  state.selectedTargetName = `[${code}] ${name}`;
  state.mode = 'target';

  try {
    const resp = await fetch(`/api/targets/${targetId}`, {
      headers: { 'X-Session-Id': state.sessionId }
    });
    if (!resp.ok) throw new Error('Ошибка загрузки цели');

    const data = await resp.json();
    state.selectedTargetContext = data.target_context ||
      `Цель: [${data.target.code}] ${data.target.name}\nПрогресс: ${data.target.achievement_percentage}%`;

    updateContextIndicator();
    updateCaseButtons();
  } catch (e) {
    alert('Ошибка загрузки цели: ' + e.message);
  }
}

function updateContextIndicator() {
  const el = document.getElementById('context-text');
  if (state.mode === 'target') {
    el.textContent = state.selectedTargetName;
  } else if (state.mode === 'map') {
    el.textContent = state.selectedMapName;
  } else {
    el.textContent = '— нет выбора —';
  }
}

function updateCaseButtons() {
  const hasTarget = !!state.selectedTargetId;
  const hasMap = !!state.selectedMapId;

  document.querySelectorAll('.case-btn').forEach(btn => {
    const mode = btn.dataset.mode;
    if (hasTarget) {
      // Цель выбрана: активны только кейсы цели, кейсы карты — нет
      btn.disabled = mode !== 'target';
    } else if (hasMap) {
      // Только карта: активны только кейсы карты
      btn.disabled = mode !== 'map';
    } else {
      btn.disabled = true;
    }
  });
}

// ===== CASES IN CHAT =====

async function runCaseInChat(caseId) {
  if (!state.selectedMapId && !state.selectedTargetId) return;

  if (state.currentAbortController) state.currentAbortController.abort();
  state.currentAbortController = new AbortController();
  const signal = state.currentAbortController.signal;

  // Reset conversation history — each case is a fresh request
  state.chatMessages = [];
  sessionStorage.removeItem('targets_v2_chat');
  document.getElementById('chat-messages').innerHTML = '';

  const caseName = CASE_NAMES[caseId];
  const contextName = state.mode === 'target'
    ? state.selectedTargetName
    : state.selectedMapName;
  const userLabel = `▶ Кейс ${caseId}: ${caseName}\n📋 ${contextName}`;

  state.chatMessages.push({ role: 'user', content: userLabel });
  appendChatMessage('user', userLabel);

  const assistantDiv = appendChatMessage('assistant', '');
  assistantDiv.innerHTML = '<span class="spinner"></span>';

  setInputDisabled(true);

  try {
    const resp = await fetch(`/api/cases/${caseId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Id': state.sessionId,
      },
      body: JSON.stringify({
        mode: state.mode,
        map_id: state.selectedMapId,
        target_id: state.selectedTargetId,
      }),
      signal,
    });

    if (!resp.ok) {
      const errText = await resp.text();
      let detail = errText;
      try { detail = JSON.parse(errText).detail; } catch (e) { /* ignore */ }
      throw new Error(detail || `HTTP ${resp.status}`);
    }

    assistantDiv.innerHTML = '';
    const fullText = await readSSEStreamToElement(resp, assistantDiv, signal);
    state.chatMessages.push({ role: 'assistant', content: fullText });
    saveChatToSession();
    appendFeedbackBar(assistantDiv, caseId);

  } catch (e) {
    if (e.name === 'AbortError') {
      assistantDiv.innerHTML = '<em style="color:var(--color-text-muted)">Прервано</em>';
      return;
    }
    assistantDiv.innerHTML = `<p style="color:var(--color-danger)">Ошибка: ${e.message}</p>`;
  } finally {
    setInputDisabled(false);
  }
}

function appendFeedbackBar(afterElement, caseId) {
  const bar = document.createElement('div');
  bar.className = 'feedback-bar';
  bar.innerHTML = `
    <span class="feedback-label">Оцените результат:</span>
    <button class="feedback-btn" onclick="sendFeedback(${caseId}, 1, this.parentElement)">👍</button>
    <button class="feedback-btn" onclick="sendFeedback(${caseId}, -1, this.parentElement)">👎</button>
    <span class="feedback-sent hidden">Оценка сохранена</span>
  `;
  afterElement.parentElement.appendChild(bar);
  scrollChatToBottom();
}

function appendChatFeedbackBar(afterElement, userMessage) {
  const bar = document.createElement('div');
  bar.className = 'feedback-bar';

  const label = document.createElement('span');
  label.className = 'feedback-label';
  label.textContent = 'Оцените ответ:';

  const btnUp = document.createElement('button');
  btnUp.className = 'feedback-btn';
  btnUp.textContent = '👍';

  const btnDown = document.createElement('button');
  btnDown.className = 'feedback-btn';
  btnDown.textContent = '👎';

  const sent = document.createElement('span');
  sent.className = 'feedback-sent hidden';
  sent.textContent = 'Оценка сохранена';

  btnUp.addEventListener('click', () => sendChatFeedback(1, bar, userMessage));
  btnDown.addEventListener('click', () => sendChatFeedback(-1, bar, userMessage));

  bar.appendChild(label);
  bar.appendChild(btnUp);
  bar.appendChild(btnDown);
  bar.appendChild(sent);

  afterElement.parentElement.appendChild(bar);
  scrollChatToBottom();
}

// ===== CHAT =====

function handleChatKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendChatMessage();
  }
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;
  if (!state.selectedMapId && !state.selectedTargetId) {
    alert('Выберите карту или цель слева');
    return;
  }

  if (state.currentAbortController) state.currentAbortController.abort();
  state.currentAbortController = new AbortController();
  const signal = state.currentAbortController.signal;

  input.value = '';
  input.style.height = 'auto';

  // Добавляем контекст к сообщению (как при кейсе)
  const contextName = state.mode === 'target'
    ? state.selectedTargetName
    : state.selectedMapName;
  const displayText = contextName
    ? `${text}\n📋 ${contextName}`
    : text;

  state.chatMessages.push({ role: 'user', content: text });
  appendChatMessage('user', displayText);

  setInputDisabled(true);

  const assistantDiv = appendChatMessage('assistant', '');
  assistantDiv.innerHTML = '<span class="spinner"></span>';

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Id': state.sessionId,
      },
      body: JSON.stringify({
        mode: state.mode,
        map_id: state.selectedMapId,
        target_id: state.selectedTargetId,
        messages: state.chatMessages,
      }),
      signal,
    });

    if (!resp.ok) {
      const errText = await resp.text();
      let detail = errText;
      try { detail = JSON.parse(errText).detail; } catch (e) { /* ignore */ }
      throw new Error(detail || `HTTP ${resp.status}`);
    }

    assistantDiv.innerHTML = '';
    const fullText = await readSSEStreamToElement(resp, assistantDiv, signal);
    state.chatMessages.push({ role: 'assistant', content: fullText });
    saveChatToSession();
    appendChatFeedbackBar(assistantDiv, text);

  } catch (e) {
    if (e.name === 'AbortError') {
      assistantDiv.innerHTML = '<em style="color:var(--color-text-muted)">Прервано</em>';
      return;
    }
    assistantDiv.innerHTML = `<p style="color:var(--color-danger)">Ошибка: ${e.message}</p>`;
  } finally {
    setInputDisabled(false);
    document.getElementById('chat-input').focus();
  }
}

function setInputDisabled(disabled) {
  document.getElementById('btn-chat-send').disabled = disabled;
  document.getElementById('chat-input').disabled = disabled;
}

function appendChatMessage(role, text) {
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  if (text) div.textContent = text;
  messages.appendChild(div);
  scrollChatToBottom();
  return div;
}

function scrollChatToBottom() {
  const messages = document.getElementById('chat-messages');
  messages.scrollTop = messages.scrollHeight;
}

function restoreChatMessages() {
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  for (const msg of state.chatMessages) {
    const div = document.createElement('div');
    div.className = `chat-message ${msg.role}`;
    if (msg.role === 'assistant') {
      div.innerHTML = renderMarkdown(msg.content);
    } else {
      div.textContent = msg.content;
    }
    container.appendChild(div);
  }
}

function saveChatToSession() {
  sessionStorage.setItem('targets_v2_chat', JSON.stringify(state.chatMessages));
}

function resetConversation() {
  state.chatMessages = [];
  sessionStorage.removeItem('targets_v2_chat');
  document.getElementById('chat-messages').innerHTML = `
    <div class="chat-message assistant">
      Здравствуйте! Выберите карту или цель слева, затем задайте вопрос или нажмите кнопку кейса.
    </div>
  `;
}

// ===== FEEDBACK =====

async function sendFeedback(caseId, vote, bar) {
  try {
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: caseId, session_id: state.sessionId, vote }),
    });
    const sent = bar.querySelector('.feedback-sent');
    if (sent) {
      sent.classList.remove('hidden');
      setTimeout(() => sent.classList.add('hidden'), 2000);
    }
  } catch (e) { /* ignore */ }
}

async function sendChatFeedback(vote, bar, userMessage) {
  // Блокируем кнопки сразу
  bar.querySelectorAll('.feedback-btn').forEach(btn => { btn.disabled = true; });

  try {
    const contextType = (state.mode === 'target') ? 'target' : 'map';
    const contextName = (state.mode === 'target')
      ? (state.selectedTargetName || '')
      : (state.selectedMapName || '');

    const saveResp = await fetch('/api/feedback/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: state.sessionId,
        vote,
        user_message: userMessage,
        context_type: contextType,
        context_name: contextName || '',
      }),
    });

    const sent = bar.querySelector('.feedback-sent');
    if (sent) {
      sent.classList.remove('hidden');
      setTimeout(() => sent.classList.add('hidden'), 2000);
    }

    // Асинхронно генерируем саммари — не ждём, не блокируем UI
    if (saveResp.ok) {
      const saveData = await saveResp.json();
      if (saveData.id) {
        fetch('/api/feedback/chat/summarize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: saveData.id, user_message: userMessage }),
        }).catch(() => { /* ignore summarize errors silently */ });
      }
    }
  } catch (e) { /* ignore */ }
}

// ===== MARKDOWN RENDERER =====

function renderMarkdown(text) {
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const lines = text.split('\n');
  let html = '';
  let inList = false;
  let inOrderedList = false;
  let tableBuffer = []; // накапливаем строки таблицы

  const closeList = () => {
    if (inList) { html += '</ul>'; inList = false; }
    if (inOrderedList) { html += '</ol>'; inOrderedList = false; }
  };

  const flushTable = () => {
    if (!tableBuffer.length) return;
    // tableBuffer[0] — заголовок, tableBuffer[1] — разделитель, остальное — строки
    const parseRow = (row) =>
      row.replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());

    const headers = parseRow(tableBuffer[0]);
    const aligns = tableBuffer[1]
      ? parseRow(tableBuffer[1]).map(cell => {
          if (/^:-+:$/.test(cell)) return 'center';
          if (/^-+:$/.test(cell))  return 'right';
          return 'left';
        })
      : [];

    let thtml = '<div class="md-table-wrap"><table class="md-table"><thead><tr>';
    headers.forEach((h, i) => {
      const align = aligns[i] ? ` style="text-align:${aligns[i]}"` : '';
      thtml += `<th${align}>${inlineFormat(h)}</th>`;
    });
    thtml += '</tr></thead><tbody>';

    for (let r = 2; r < tableBuffer.length; r++) {
      const cells = parseRow(tableBuffer[r]);
      thtml += '<tr>';
      headers.forEach((_, i) => {
        const align = aligns[i] ? ` style="text-align:${aligns[i]}"` : '';
        thtml += `<td${align}>${inlineFormat(cells[i] || '')}</td>`;
      });
      thtml += '</tr>';
    }
    thtml += '</tbody></table></div>';
    html += thtml;
    tableBuffer = [];
  };

  const inlineFormat = (s) => {
    s = esc(s);
    s = s.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    return s;
  };

  const isTableRow = (line) => /^\|.+\|/.test(line.trim());

  for (const line of lines) {
    // Таблица
    if (isTableRow(line)) {
      closeList();
      tableBuffer.push(line.trim());
      continue;
    } else if (tableBuffer.length) {
      flushTable();
    }

    if (/^### /.test(line)) { closeList(); html += `<h3>${inlineFormat(line.slice(4))}</h3>`; continue; }
    if (/^## /.test(line))  { closeList(); html += `<h2>${inlineFormat(line.slice(3))}</h2>`; continue; }
    if (/^# /.test(line))   { closeList(); html += `<h1>${inlineFormat(line.slice(2))}</h1>`; continue; }
    if (/^---+$/.test(line.trim())) { closeList(); html += '<hr>'; continue; }

    if (/^[-*] /.test(line)) {
      if (inOrderedList) { html += '</ol>'; inOrderedList = false; }
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${inlineFormat(line.slice(2))}</li>`;
      continue;
    }
    if (/^\d+\. /.test(line)) {
      if (inList) { html += '</ul>'; inList = false; }
      if (!inOrderedList) { html += '<ol>'; inOrderedList = true; }
      html += `<li>${inlineFormat(line.replace(/^\d+\. /, ''))}</li>`;
      continue;
    }
    if (/^> /.test(line)) {
      closeList();
      html += `<blockquote>${inlineFormat(line.slice(2))}</blockquote>`;
      continue;
    }

    if (line.trim() === '') { closeList(); html += '<br>'; continue; }

    closeList();
    html += `<p>${inlineFormat(line)}</p>`;
  }

  flushTable();
  closeList();
  return html;
}

// ===== SSE STREAM READER =====

async function readSSEStreamToElement(resp, targetElement, signal) {
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';

  if (signal) signal.addEventListener('abort', () => reader.cancel());

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = line.slice(6);
      if (data === '[DONE]') return fullText;
      try {
        const chunk = JSON.parse(data);
        if (typeof chunk === 'string' && chunk.startsWith('[ERROR]')) {
          fullText = chunk.replace('[ERROR] ', 'Ошибка: ');
        } else {
          fullText += chunk;
        }
        targetElement.innerHTML = renderMarkdown(fullText);
        scrollChatToBottom();
      } catch (e) { /* skip invalid JSON */ }
    }
  }

  return fullText;
}

// ===== INITIALIZATION =====

document.addEventListener('DOMContentLoaded', () => {
  initSession();
  loadMaps();
});
