/* ИИ-помощник Directum Targets — фронтенд логика */

// Состояние приложения
const state = {
  goalsMap: null,
  docxContent: null,
  goalsList: [],
  mapSummary: '',
  sessionId: null,
  currentCaseId: null,
  chatMessages: [],
  jsonFile: null,
  docxFile: null,
  caseAbortController: null,
};

// Инициализация сессии
function initSession() {
  let sid = sessionStorage.getItem('targets_session_id');
  if (!sid) {
    sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2);
    sessionStorage.setItem('targets_session_id', sid);
  }
  state.sessionId = sid;

  // Восстановление чата
  const savedMessages = sessionStorage.getItem('targets_chat');
  if (savedMessages) {
    try {
      state.chatMessages = JSON.parse(savedMessages);
      restoreChatMessages();
    } catch (e) {
      // Игнорируем ошибки восстановления
    }
  }
}

// ===== ЗАГРУЗКА ДАННЫХ =====

async function loadTestData() {
  const btn = document.getElementById('btn-load-test');
  btn.disabled = true;
  btn.textContent = 'Загрузка...';
  showGlobalAlert('info', 'Загружаю тестовую карту целей Ario 2026...');

  try {
    const resp = await fetch('/api/data/test');
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Ошибка загрузки');
    }
    const data = await resp.json();
    applyLoadedData(data);
    hideGlobalAlert();
  } catch (e) {
    showGlobalAlert('error', 'Ошибка загрузки тестовых данных: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Использовать тестовую карту целей: Карта целей Ario 2026';
  }
}

async function uploadUserData() {
  const jsonText = document.getElementById('json-text-input').value.trim();
  const jsonFile = state.jsonFile;
  const docxFile = state.docxFile;

  if (!jsonText && !jsonFile) {
    showGlobalAlert('error', 'Необходимо загрузить JSON-файл карты целей или вставить JSON-текст');
    return;
  }

  const formData = new FormData();
  if (jsonFile) {
    formData.append('json_file', jsonFile);
  } else {
    formData.append('json_text', jsonText);
  }
  if (docxFile) {
    formData.append('docx_file', docxFile);
  }

  showGlobalAlert('info', 'Загружаю и парсю карту целей...');

  try {
    const resp = await fetch('/api/data/upload', { method: 'POST', body: formData });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Ошибка загрузки');
    }
    const data = await resp.json();
    applyLoadedData(data);
    hideGlobalAlert();
  } catch (e) {
    showGlobalAlert('error', 'Ошибка: ' + e.message);
  }
}

function applyLoadedData(data) {
  state.goalsMap = data.goals_map;
  state.docxContent = data.docx_content;
  state.goalsList = data.goals_list;
  state.mapSummary = data.map_summary;

  // Заполняем dropdown список целей
  const select = document.getElementById('goal-select');
  select.innerHTML = '<option value="">— выберите цель для кейсов 1-4 и 6 —</option>';
  for (const goal of data.goals_list) {
    const opt = document.createElement('option');
    opt.value = goal.id;
    opt.textContent = `${goal.code}: ${goal.name} (${goal.progress.toFixed(0)}%)`;
    select.appendChild(opt);
  }

  // Обновляем инфо о карте
  document.getElementById('map-info').textContent = data.map_summary;

  // Переключаемся на основной экран
  showSection('section-main');
}

function resetApp() {
  state.goalsMap = null;
  state.docxContent = null;
  state.goalsList = [];
  state.jsonFile = null;
  state.docxFile = null;

  // Сбрасываем форму
  document.getElementById('json-text-input').value = '';
  document.getElementById('json-zone').classList.remove('has-file');
  document.getElementById('json-zone-title').textContent = 'Перетащите JSON-файл';
  document.getElementById('docx-zone').classList.remove('has-file');
  document.getElementById('docx-zone-title').textContent = 'Перетащите DOCX-файл';

  hideResult();
  showSection('section-upload');
  hideGlobalAlert();
}

// ===== УПРАВЛЕНИЕ ФАЙЛАМИ =====

function handleFileSelect(event, type) {
  const file = event.target.files[0];
  if (!file) return;
  setFile(type, file);
}

function handleFileDrop(event, type) {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (!file) return;
  setFile(type, file);
  event.target.classList.remove('drag-over');
}

function handleDragOver(event) {
  event.preventDefault();
  event.target.closest('.upload-zone')?.classList.add('drag-over');
}

function handleDragLeave(event) {
  event.target.closest('.upload-zone')?.classList.remove('drag-over');
}

function setFile(type, file) {
  if (type === 'json') {
    state.jsonFile = file;
    document.getElementById('json-zone').classList.add('has-file');
    document.getElementById('json-zone-title').textContent = file.name;
  } else {
    state.docxFile = file;
    document.getElementById('docx-zone').classList.add('has-file');
    document.getElementById('docx-zone-title').textContent = file.name;
  }
}

// ===== КЕЙСЫ =====

async function runCase(caseId) {
  if (!state.goalsMap) {
    showGlobalAlert('error', 'Сначала загрузите карту целей');
    return;
  }

  // Для кейсов 1-4, 6 нужна выбранная цель
  const needsGoal = [1, 2, 3, 4, 6].includes(caseId);
  const selectedGoalId = document.getElementById('goal-select').value;

  if (needsGoal && !selectedGoalId) {
    showGlobalAlert('error', `Кейс ${caseId} требует выбора конкретной цели. Выберите цель из списка выше.`);
    return;
  }

  hideGlobalAlert();

  // Отменяем предыдущий запрос если он ещё идёт
  if (state.caseAbortController) {
    state.caseAbortController.abort();
  }
  state.caseAbortController = new AbortController();
  const signal = state.caseAbortController.signal;

  state.currentCaseId = caseId;
  const caseNames = {
    1: 'Кейс 1: Формулировка описания цели',
    2: 'Кейс 2: Формулировка ключевых результатов',
    3: 'Кейс 3: Декомпозиция на квартальные цели',
    4: 'Кейс 4: Верификация по ожиданиям руководства',
    5: 'Кейс 5: Конфликты и слепые зоны стратегии',
    6: 'Кейс 6: Риски достижения цели',
    7: 'Кейс 7: Экспресс-отчёт по целям',
  };

  showResult(caseNames[caseId]);

  const body = {
    goals_map: state.goalsMap,
    selected_goal_id: selectedGoalId || null,
    docx_content: state.docxContent || null,
  };

  try {
    const resp = await fetch(`/api/cases/${caseId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Ошибка запроса');
    }

    await readSSEStream(resp, 'result-content', signal);
    if (!signal.aborted) showFeedbackBar();
  } catch (e) {
    if (e.name === 'AbortError') return; // Запрос отменён — тихо игнорируем
    document.getElementById('result-content').textContent = 'Ошибка: ' + e.message;
    hideLoading();
  }
}

// ===== ЧАТ =====

function handleChatKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendChatMessage();
  }
}

async function sendChatMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;
  if (!state.goalsMap) {
    showGlobalAlert('error', 'Сначала загрузите карту целей');
    return;
  }

  input.value = '';
  input.style.height = 'auto';

  // Добавляем сообщение пользователя
  state.chatMessages.push({ role: 'user', content: text });
  appendChatMessage('user', text);

  const btn = document.getElementById('btn-chat-send');
  btn.disabled = true;
  input.disabled = true;

  // Добавляем сообщение-заглушку для ответа
  const assistantDiv = appendChatMessage('assistant', '');
  assistantDiv.classList.add('loading-msg');
  assistantDiv.innerHTML = '<span class="spinner"></span>';

  const body = {
    goals_map: state.goalsMap,
    docx_content: state.docxContent || null,
    messages: state.chatMessages,
  };

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Ошибка запроса');
    }

    let fullText = '';
    assistantDiv.innerHTML = '';
    assistantDiv.classList.remove('loading-msg');
    await readSSEStreamToElement(resp, (chunk) => {
      fullText += chunk;
      assistantDiv.innerHTML = renderMarkdown(fullText);
      scrollChatToBottom();
    });

    state.chatMessages.push({ role: 'assistant', content: fullText });
    saveChatToSession();
  } catch (e) {
    assistantDiv.textContent = 'Ошибка: ' + e.message;
  } finally {
    btn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

function appendChatMessage(role, text) {
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  div.textContent = text;
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
  // Оставляем только приветствие
  const welcome = container.firstChild;
  container.innerHTML = '';
  if (welcome) container.appendChild(welcome);
  for (const msg of state.chatMessages) {
    appendChatMessage(msg.role, msg.content);
  }
}

function saveChatToSession() {
  sessionStorage.setItem('targets_chat', JSON.stringify(state.chatMessages));
}

// ===== ОЦЕНКА (FEEDBACK) =====

async function sendFeedback(vote) {
  if (!state.currentCaseId) return;

  const btnUp = document.getElementById('btn-thumbs-up');
  const btnDown = document.getElementById('btn-thumbs-down');
  const sentLabel = document.getElementById('feedback-sent');

  btnUp.classList.remove('active-pos');
  btnDown.classList.remove('active-neg');

  if (vote === 1) {
    btnUp.classList.add('active-pos');
  } else {
    btnDown.classList.add('active-neg');
  }

  try {
    await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: state.currentCaseId,
        session_id: state.sessionId,
        vote: vote,
      }),
    });
    sentLabel.classList.remove('hidden');
    setTimeout(() => sentLabel.classList.add('hidden'), 2000);
  } catch (e) {
    // Не блокируем UI при ошибке сохранения оценки
  }
}

// ===== MARKDOWN РЕНДЕРЕР =====

function renderMarkdown(text) {
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const lines = text.split('\n');
  let html = '';
  let inList = false;
  let inOrderedList = false;

  const closeList = () => {
    if (inList)        { html += '</ul>'; inList = false; }
    if (inOrderedList) { html += '</ol>'; inOrderedList = false; }
  };

  const inlineFormat = (s) => {
    // Экранируем HTML
    s = esc(s);
    // Жирный + курсив: ***text***
    s = s.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    // Жирный: **text**
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Курсив: *text*
    s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Инлайн-код: `code`
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    return s;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Заголовки
    if (/^### /.test(line)) { closeList(); html += `<h3>${inlineFormat(line.slice(4))}</h3>`; continue; }
    if (/^## /.test(line))  { closeList(); html += `<h2>${inlineFormat(line.slice(3))}</h2>`; continue; }
    if (/^# /.test(line))   { closeList(); html += `<h1>${inlineFormat(line.slice(2))}</h1>`; continue; }

    // Горизонтальная линия
    if (/^---+$/.test(line.trim())) { closeList(); html += '<hr>'; continue; }

    // Маркированный список
    if (/^[-*] /.test(line)) {
      if (inOrderedList) { html += '</ol>'; inOrderedList = false; }
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${inlineFormat(line.slice(2))}</li>`;
      continue;
    }

    // Нумерованный список
    if (/^\d+\. /.test(line)) {
      if (inList) { html += '</ul>'; inList = false; }
      if (!inOrderedList) { html += '<ol>'; inOrderedList = true; }
      html += `<li>${inlineFormat(line.replace(/^\d+\. /, ''))}</li>`;
      continue;
    }

    // Blockquote
    if (/^> /.test(line)) {
      closeList();
      html += `<blockquote>${inlineFormat(line.slice(2))}</blockquote>`;
      continue;
    }

    // Пустая строка
    if (line.trim() === '') {
      closeList();
      html += '<br>';
      continue;
    }

    // Обычный абзац
    closeList();
    html += `<p>${inlineFormat(line)}</p>`;
  }

  closeList();
  return html;
}

// ===== SSE УТИЛИТЫ =====

async function readSSEStream(resp, targetElementId, signal) {
  const element = document.getElementById(targetElementId);
  const loading = document.getElementById('result-loading');
  let started = false;
  let fullText = '';

  await readSSEStreamToElement(resp, (chunk) => {
    if (signal && signal.aborted) return;
    if (!started) {
      if (loading) loading.classList.add('hidden');
      started = true;
    }
    if (chunk.startsWith('[ERROR]')) {
      fullText = chunk.replace('[ERROR] ', 'Ошибка: ');
    } else {
      fullText += chunk;
    }
    element.innerHTML = renderMarkdown(fullText);
  }, signal);
}

async function readSSEStreamToElement(resp, onChunk, signal) {
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  // Отменяем чтение потока при abort
  if (signal) {
    signal.addEventListener('abort', () => reader.cancel(), { once: true });
  }

  while (true) {
    const { done, value } = await reader.read();
    if (done || (signal && signal.aborted)) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Последняя неполная строка

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') {
          hideLoading();
          return;
        }
        try {
          const text = JSON.parse(data);
          onChunk(text);
        } catch (e) {
          // Пропускаем невалидный JSON
        }
      }
    }
  }
  hideLoading();
}

// ===== UI УТИЛИТЫ =====

function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function switchTab(tabName, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tab-' + tabName).classList.add('active');
}

function showResult(caseName) {
  const area = document.getElementById('result-area');
  area.classList.remove('hidden');

  document.getElementById('result-case-label').textContent = caseName;
  document.getElementById('result-content').textContent = '';
  document.getElementById('result-loading').classList.remove('hidden');
  hideFeedbackBar();

  // Прокрутка к результату
  area.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideResult() {
  document.getElementById('result-area')?.classList.add('hidden');
}

function hideLoading() {
  const loading = document.getElementById('result-loading');
  if (loading) loading.classList.add('hidden');
}

function showFeedbackBar() {
  const bar = document.getElementById('feedback-bar');
  if (bar) {
    bar.classList.remove('hidden');
    // Сбрасываем предыдущее состояние
    document.getElementById('btn-thumbs-up').classList.remove('active-pos');
    document.getElementById('btn-thumbs-down').classList.remove('active-neg');
    document.getElementById('feedback-sent').classList.add('hidden');
  }
}

function hideFeedbackBar() {
  document.getElementById('feedback-bar')?.classList.add('hidden');
}

function showGlobalAlert(type, message) {
  const alert = document.getElementById('global-alert');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  alert.classList.remove('hidden');
}

function hideGlobalAlert() {
  document.getElementById('global-alert').classList.add('hidden');
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', () => {
  initSession();
});
