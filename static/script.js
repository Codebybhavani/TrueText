const token = localStorage.getItem('token');
const username = localStorage.getItem('username');
if (!token) window.location.href = '/';
document.getElementById('hello-user').textContent = `Hello, ${username}`;

document.getElementById('logout-btn').onclick = () => { localStorage.clear(); window.location.href = '/'; };

function authHeaders(json = true) {
  const h = { 'Authorization': `Bearer ${token}` };
  if (json) h['Content-Type'] = 'application/json';
  return h;
}
async function apiCall(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401) { localStorage.clear(); window.location.href = '/'; return null; }
  return res;
}

/* ---------- Theme toggle (light beige default, dark alternate) ---------- */
const themeBtn = document.getElementById('theme-toggle');
function applyTheme(t) {
  if (t === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  themeBtn.textContent = t === 'dark' ? '☀️' : '🌙';
  localStorage.setItem('theme', t);
}
applyTheme(localStorage.getItem('theme') || 'light');
themeBtn.onclick = () => {
  const current = localStorage.getItem('theme') === 'dark' ? 'light' : 'dark';
  applyTheme(current);
};

/* ---------- Mode tabs ---------- */
const tabDetector = document.getElementById('tab-detector');
const tabInstructor = document.getElementById('tab-instructor');
const viewDetector = document.getElementById('view-detector');
const viewInstructor = document.getElementById('view-instructor');
tabDetector.onclick = () => {
  tabDetector.classList.add('active'); tabInstructor.classList.remove('active');
  viewDetector.classList.remove('hidden'); viewInstructor.classList.add('hidden');
};
tabInstructor.onclick = () => {
  tabInstructor.classList.add('active'); tabDetector.classList.remove('active');
  viewInstructor.classList.remove('hidden'); viewDetector.classList.add('hidden');
};

/* ---------- History / stats ---------- */
async function loadHistory() {
  const res = await apiCall('/api/history', { headers: authHeaders() });
  if (!res) return;
  const data = await res.json();
  document.getElementById('stat-total').textContent = data.total_scans;
  document.getElementById('stat-avg').textContent = data.average_ai_score + '%';
  document.getElementById('stat-last').textContent = data.items[0] ? data.items[0].label : '–';

  const list = document.getElementById('history-list');
  list.innerHTML = '';
  if (data.items.length === 0) {
    list.innerHTML = '<p class="hint">No scans yet. Run your first detection above.</p>';
    return;
  }
  data.items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'history-row';
    const isAI = item.label.includes('AI');
    row.innerHTML = `
      <span class="history-text">${escapeHtml(item.text)}</span>
      <span class="badge ${isAI ? 'ai' : 'human'}">${item.label} (${isAI ? item.ai_probability : item.human_probability}%)</span>
      <button class="small-btn" data-id="${item.id}">PDF</button>
    `;
    row.querySelector('button').onclick = () => downloadReport(item.id);
    list.appendChild(row);
  });
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function downloadReport(id) {
  fetch(`/api/report/${id}`, { headers: authHeaders(false) })
    .then(res => res.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `report_${id}.pdf`; a.click();
    });
}
document.getElementById('download-pdf-btn').onclick = () => {
  if (window.lastDetectionId) downloadReport(window.lastDetectionId);
};

/* ---------- Ring gauge animation ---------- */
const RING_CIRCUMFERENCE = 2 * Math.PI * 70; // r=70
function animateRing(pct) {
  const fg = document.getElementById('ring-fg');
  const offset = RING_CIRCUMFERENCE - (pct / 100) * RING_CIRCUMFERENCE;
  fg.style.stroke = pct >= 50 ? 'var(--ai)' : 'var(--human)';
  requestAnimationFrame(() => { fg.style.strokeDashoffset = offset; });

  const percentEl = document.getElementById('ring-percent');
  let start = null;
  const from = parseFloat(percentEl.dataset.value || '0');
  const duration = 800;
  function step(ts) {
    if (!start) start = ts;
    const t = Math.min((ts - start) / duration, 1);
    const val = Math.round(from + (pct - from) * t);
    percentEl.textContent = val + '%';
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
  percentEl.dataset.value = pct;
}

/* ---------- Word count ---------- */
const inputText = document.getElementById('input-text');
const wordCountEl = document.getElementById('word-count');
inputText.addEventListener('input', () => {
  const n = inputText.value.trim() ? inputText.value.trim().split(/\s+/).length : 0;
  wordCountEl.textContent = `${n} word${n === 1 ? '' : 's'}`;
  maybeLiveCheck();
});

/* ---------- Live check (debounced auto-detect while typing) ---------- */
const liveToggle = document.getElementById('live-toggle');
const liveStatus = document.getElementById('live-status');
let liveTimer = null;
function maybeLiveCheck() {
  if (!liveToggle.checked) return;
  const text = inputText.value.trim();
  clearTimeout(liveTimer);
  if (text.split(/\s+/).length < 5) { liveStatus.classList.add('hidden'); return; }
  liveStatus.classList.remove('hidden');
  liveTimer = setTimeout(() => runDetection(text, true), 1000);
}

/* ---------- Inline word highlighting (Grammarly-style) ---------- */
function renderInlineHighlight(text, words) {
  const box = document.getElementById('inline-highlight');
  let html = escapeHtml(text);
  // sort by length desc so longer matches replace first, avoid partial overlap issues
  const sorted = [...words].sort((a, b) => b.word.length - a.word.length);
  sorted.forEach(w => {
    const safeWord = w.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`\\b(${safeWord})\\b`, 'gi');
    const intensity = Math.min(Math.abs(w.weight) * 4, 1);
    const color = w.weight > 0
      ? `rgba(161,81,47,${0.14 + intensity * 0.32})`
      : `rgba(75,109,84,${0.14 + intensity * 0.32})`;
    html = html.replace(re, `<span class="tag" title="LIME weight: ${w.weight}" style="background:${color}">$1</span>`);
  });
  box.innerHTML = html;
}

/* ---------- Shared result rendering (used by both typed text and uploaded files) ---------- */
function renderDetectionResult(data) {
  window.lastDetectionId = data.id;
  document.getElementById('result-panel').classList.remove('hidden');
  document.getElementById('ai-prob').textContent = data.ai_probability + '%';
  document.getElementById('human-prob').textContent = data.human_probability + '%';

  const badge = document.getElementById('verdict-badge');
  const isAI = data.label.includes('AI');
  badge.textContent = data.label;
  badge.className = 'verdict-badge ' + (isAI ? 'ai' : 'human');

  animateRing(data.ai_probability);
  renderLimeBars(data.highlighted_words || []);
  renderInlineHighlight(data.text, data.highlighted_words || []);

  const styleBox = document.getElementById('style-stats');
  styleBox.innerHTML = '';
  Object.entries(data.style || {}).forEach(([k, v]) => {
    const div = document.createElement('div');
    div.className = 'style-item';
    div.innerHTML = `<b>${k.replace(/_/g, ' ')}</b>: ${v}`;
    styleBox.appendChild(div);
  });
}

/* ---------- Real LIME horizontal bar chart (actual word weights, not summary stats) ---------- */
function renderLimeBars(words) {
  const box = document.getElementById('lime-bars');
  box.innerHTML = '';
  if (!words.length) {
    box.innerHTML = '<p class="hint">No LIME weights returned for this text.</p>';
    return;
  }
  const legend = document.createElement('div');
  legend.className = 'lime-legend';
  legend.innerHTML = `
    <span><span class="legend-dot" style="background:var(--ai)"></span>Supports AI</span>
    <span><span class="legend-dot" style="background:var(--human)"></span>Supports Human</span>
  `;
  box.appendChild(legend);

  const sorted = [...words].sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight));
  const maxAbs = Math.max(...sorted.map(w => Math.abs(w.weight)), 0.0001);

  sorted.forEach(w => {
    const row = document.createElement('div');
    row.className = 'lime-bar-row';
    const pct = Math.min((Math.abs(w.weight) / maxAbs) * 50, 50); // half-width max, grows from center
    const isAI = w.weight > 0;
    const fillStyle = isAI ? `width:${pct}%` : `width:${pct}%`;
    row.innerHTML = `
      <div class="lime-bar-word">${escapeHtml(w.word)}</div>
      <div class="lime-bar-track">
        <div class="lime-bar-mid"></div>
        <div class="lime-bar-fill ${isAI ? 'ai' : 'human'}" style="${fillStyle}"></div>
      </div>
      <div class="lime-bar-weight">${w.weight > 0 ? '+' : ''}${w.weight}</div>
    `;
    box.appendChild(row);
  });
}

/* ---------- Run single detection (typed/pasted text) ---------- */
async function runDetection(text, isLive = false) {
  const errorBox = document.getElementById('detect-error');
  const btn = document.getElementById('detect-btn');
  if (!isLive) { errorBox.textContent = ''; btn.disabled = true; btn.textContent = 'Analyzing…'; }

  const res = await apiCall('/api/detect', { method: 'POST', headers: authHeaders(), body: JSON.stringify({ text }) });
  if (isLive) liveStatus.classList.add('hidden');
  if (!isLive) { btn.disabled = false; btn.textContent = 'Run Detection'; }
  if (!res) return;
  const data = await res.json();
  if (!res.ok) { if (!isLive) errorBox.textContent = data.error || 'Detection failed'; return; }

  renderDetectionResult(data);
  if (!isLive) loadHistory();
}

document.getElementById('detect-btn').onclick = () => {
  const text = inputText.value.trim();
  const errorBox = document.getElementById('detect-error');
  errorBox.textContent = '';
  if (text.split(/\s+/).length < 5) { errorBox.textContent = 'Please enter at least 5 words.'; return; }
  runDetection(text, false);
};

/* ---------- Single file upload (PDF / DOCX / TXT) in Detector panel ---------- */
const singleDropzone = document.getElementById('single-dropzone');
const singleFileInput = document.getElementById('single-file-input');
const singleFileNameEl = document.getElementById('single-file-name');

singleDropzone.onclick = () => singleFileInput.click();
singleDropzone.ondragover = (e) => { e.preventDefault(); singleDropzone.classList.add('dragover'); };
singleDropzone.ondragleave = () => singleDropzone.classList.remove('dragover');
singleDropzone.ondrop = (e) => {
  e.preventDefault();
  singleDropzone.classList.remove('dragover');
  if (e.dataTransfer.files.length) runFileDetection(e.dataTransfer.files[0]);
};
singleFileInput.onchange = () => {
  if (singleFileInput.files.length) runFileDetection(singleFileInput.files[0]);
};

async function runFileDetection(file) {
  const errorBox = document.getElementById('file-detect-error');
  errorBox.textContent = '';
  singleFileNameEl.textContent = `Selected: ${file.name}`;

  const formData = new FormData();
  formData.append('file', file);

  const res = await apiCall('/api/detect-file', { method: 'POST', headers: authHeaders(false), body: formData });
  if (!res) return;
  const data = await res.json();
  if (!res.ok) { errorBox.textContent = data.error || 'Could not process this file.'; return; }

  inputText.value = data.text; // so the textarea reflects what was actually analyzed
  wordCountEl.textContent = `${data.text.trim().split(/\s+/).length} words (from ${file.name})`;
  renderDetectionResult(data);
  loadHistory();
}

/* ================= INSTRUCTOR BATCH MODE ================= */
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const fileListEl = document.getElementById('file-list');
let selectedFiles = [];

dropzone.onclick = () => fileInput.click();
dropzone.ondragover = (e) => { e.preventDefault(); dropzone.classList.add('dragover'); };
dropzone.ondragleave = () => dropzone.classList.remove('dragover');
dropzone.ondrop = (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  setFiles([...e.dataTransfer.files].filter(f => f.name.endsWith('.txt')));
};
fileInput.onchange = () => setFiles([...fileInput.files]);

function setFiles(files) {
  selectedFiles = files;
  fileListEl.textContent = files.length
    ? `${files.length} file(s) selected: ${files.map(f => f.name).join(', ')}`
    : '';
}

const thresholdSlider = document.getElementById('threshold-slider');
const thresholdValue = document.getElementById('threshold-value');
thresholdSlider.oninput = () => { thresholdValue.textContent = thresholdSlider.value + '%'; };

const simThresholdSlider = document.getElementById('sim-threshold-slider');
const simThresholdValue = document.getElementById('sim-threshold-value');
simThresholdSlider.oninput = () => { simThresholdValue.textContent = simThresholdSlider.value + '%'; };

let lastBatchResults = [];
let sortKey = 'ai_probability';
let sortAsc = false;

document.getElementById('batch-btn').onclick = async () => {
  const errorBox = document.getElementById('batch-error');
  errorBox.textContent = '';
  if (selectedFiles.length === 0) { errorBox.textContent = 'Please select at least one .txt file.'; return; }

  const btn = document.getElementById('batch-btn');
  btn.disabled = true; btn.textContent = 'Analyzing…';

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append('files', f));
  formData.append('threshold', thresholdSlider.value);
  formData.append('similarity_threshold', simThresholdSlider.value);

  const res = await apiCall('/api/batch-detect', { method: 'POST', headers: authHeaders(false), body: formData });
  btn.disabled = false; btn.textContent = 'Analyze All';
  if (!res) return;
  const data = await res.json();
  if (!res.ok) { errorBox.textContent = data.error || 'Batch analysis failed'; return; }

  lastBatchResults = data.results;
  document.getElementById('batch-result-panel').classList.remove('hidden');
  document.getElementById('batch-total').textContent = data.total;
  document.getElementById('batch-avg').textContent = data.class_average_ai + '%';
  document.getElementById('batch-flagged').textContent = data.flagged_count;
  renderBatchTable();
  renderPlagiarismTable(data.similarity_pairs || []);
};

function renderPlagiarismTable(pairs) {
  const panel = document.getElementById('plagiarism-panel');
  const tbody = document.getElementById('plagiarism-tbody');
  const emptyMsg = document.getElementById('plagiarism-empty');
  const tableWrap = document.getElementById('plagiarism-table-wrap');
  panel.classList.remove('hidden');
  tbody.innerHTML = '';

  if (pairs.length === 0) {
    emptyMsg.classList.remove('hidden');
    tableWrap.classList.add('hidden');
    return;
  }
  emptyMsg.classList.add('hidden');
  tableWrap.classList.remove('hidden');

  pairs.forEach(p => {
    const tr = document.createElement('tr');
    if (p.similarity >= 85) tr.classList.add('flagged');
    tr.innerHTML = `
      <td>${escapeHtml(p.file_a)}</td>
      <td>${escapeHtml(p.file_b)}</td>
      <td>
        <div class="bar-cell">
          <div class="bar-track"><div class="bar-fill" style="width:${p.similarity}%; background:${p.similarity >= 85 ? 'var(--ai)' : 'var(--accent)'}"></div></div>
          <span>${p.similarity}%</span>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderBatchTable() {
  const tbody = document.getElementById('batch-tbody');
  const rows = [...lastBatchResults].sort((a, b) => {
    let av = a[sortKey], bv = b[sortKey];
    if (av == null) av = -1;
    if (bv == null) bv = -1;
    if (typeof av === 'string') { av = av.toLowerCase(); bv = bv.toLowerCase(); }
    if (av < bv) return sortAsc ? -1 : 1;
    if (av > bv) return sortAsc ? 1 : -1;
    return 0;
  });

  tbody.innerHTML = '';
  rows.forEach(r => {
    const tr = document.createElement('tr');
    if (r.flagged) tr.classList.add('flagged');
    if (r.error) {
      tr.innerHTML = `<td>${escapeHtml(r.filename)}</td><td colspan="3" class="hint">${r.error}</td>`;
    } else {
      const isAI = r.label.includes('AI');
      tr.innerHTML = `
        <td>${r.flagged ? '🚩 ' : ''}${escapeHtml(r.filename)}</td>
        <td>${r.word_count}</td>
        <td>
          <div class="bar-cell">
            <div class="bar-track"><div class="bar-fill" style="width:${r.ai_probability}%; background:${isAI ? 'var(--ai)' : 'var(--human)'}"></div></div>
            <span>${r.ai_probability}%</span>
          </div>
        </td>
        <td><span class="badge ${isAI ? 'ai' : 'human'}">${r.label}</span></td>
      `;
    }
    tbody.appendChild(tr);
  });
}

document.querySelectorAll('table.batch-table th').forEach(th => {
  th.onclick = () => {
    const key = th.dataset.key;
    if (sortKey === key) sortAsc = !sortAsc; else { sortKey = key; sortAsc = false; }
    renderBatchTable();
  };
});

document.getElementById('export-csv-btn').onclick = () => {
  const header = 'Filename,Words,AI %,Human %,Verdict,Flagged\n';
  const lines = lastBatchResults.map(r => {
    if (r.error) return `${r.filename},,,,${r.error},`;
    return `${r.filename},${r.word_count},${r.ai_probability},${r.human_probability},${r.label},${r.flagged}`;
  });
  const csv = header + lines.join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'class_report.csv'; a.click();
};

loadHistory();
