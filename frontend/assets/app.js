/* ═══════════════════════════════════════════════════════════════
   MEDORA OT — Frontend Application
   Speech dictation → Gemini structure → Review → Sign → Export
   ═══════════════════════════════════════════════════════════════ */

const API = 'http://localhost:8000';
let authToken = localStorage.getItem('medora_token');
let currentUser = JSON.parse(localStorage.getItem('medora_user') || 'null');
let currentNoteId = null;
let currentNotesFilter = '';
let mediaRecorder = null;
let audioChunks = [];
let recInterval = null;
let recSeconds = 0;
let audioCtx = null;
let analyser = null;
let animRAF = null;

// ─── Signature Pad ────────────────────────────────────────────────
let sigCanvas, sigCtx, sigDrawing = false, sigLastX = 0, sigLastY = 0;

// ═══════════════════════════════════════════════════════════════
// API HELPERS
// ═══════════════════════════════════════════════════════════════
async function api(method, path, body = null, isForm = false) {
  const headers = {};
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  if (!isForm && body) headers['Content-Type'] = 'application/json';

  const opts = { method, headers };
  if (body) opts.body = isForm ? body : JSON.stringify(body);

  const res = await fetch(`${API}${path}`, opts);
  if (res.status === 204) return null;
  const data = res.headers.get('content-type')?.includes('application/json')
    ? await res.json()
    : await res.blob();
  if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`);
  return data;
}

// ═══════════════════════════════════════════════════════════════
// TOAST / LOADER
// ═══════════════════════════════════════════════════════════════
let toastTimer;
function toast(msg, type = 'info', duration = 3500) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type}`;
  el.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), duration);
}

function showLoader(msg = 'Processing…') {
  document.getElementById('loader-msg').textContent = msg;
  document.getElementById('global-loader').classList.remove('hidden');
}
function hideLoader() {
  document.getElementById('global-loader').classList.add('hidden');
}

// ═══════════════════════════════════════════════════════════════
// AUTH
// ═══════════════════════════════════════════════════════════════
document.getElementById('go-register').addEventListener('click', e => {
  e.preventDefault();
  document.getElementById('login-form').classList.remove('active');
  document.getElementById('register-form').classList.add('active');
});
document.getElementById('go-login').addEventListener('click', e => {
  e.preventDefault();
  document.getElementById('register-form').classList.remove('active');
  document.getElementById('login-form').classList.add('active');
});

document.getElementById('login-btn').addEventListener('click', async () => {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');
  if (!email || !password) { errEl.textContent = 'Fill in all fields.'; errEl.classList.remove('hidden'); return; }
  try {
    showLoader('Signing in…');
    const form = new FormData();
    form.append('username', email);
    form.append('password', password);
    const res = await api('POST', '/api/auth/login', form, true);
    authToken = res.access_token;
    currentUser = res.user;
    localStorage.setItem('medora_token', authToken);
    localStorage.setItem('medora_user', JSON.stringify(currentUser));
    hideLoader();
    bootApp();
  } catch (err) {
    hideLoader();
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

document.getElementById('register-btn').addEventListener('click', async () => {
  const errEl = document.getElementById('register-error');
  errEl.classList.add('hidden');
  const body = {
    full_name: document.getElementById('reg-name').value.trim(),
    email: document.getElementById('reg-email').value.trim(),
    password: document.getElementById('reg-password').value,
    role: document.getElementById('reg-role').value,
    designation: document.getElementById('reg-designation').value.trim() || null,
    hospital: document.getElementById('reg-hospital').value.trim() || null,
  };
  if (!body.full_name || !body.email || !body.password) {
    errEl.textContent = 'Name, email and password are required.';
    errEl.classList.remove('hidden'); return;
  }
  try {
    showLoader('Creating account…');
    await api('POST', '/api/auth/register', body);
    hideLoader();
    toast('Account created! Sign in now.', 'success');
    document.getElementById('register-form').classList.remove('active');
    document.getElementById('login-form').classList.add('active');
    document.getElementById('login-email').value = body.email;
  } catch (err) {
    hideLoader();
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

document.getElementById('logout-btn').addEventListener('click', () => {
  authToken = null; currentUser = null;
  localStorage.removeItem('medora_token');
  localStorage.removeItem('medora_user');
  document.getElementById('app').classList.add('hidden');
  document.getElementById('auth-overlay').classList.remove('hidden');
  currentNoteId = null;
});

// ═══════════════════════════════════════════════════════════════
// BOOT
// ═══════════════════════════════════════════════════════════════
function bootApp() {
  document.getElementById('auth-overlay').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');

  // User info
  document.getElementById('sidebar-user-name').textContent = currentUser?.full_name || '—';
  document.getElementById('sidebar-user-role').textContent = currentUser?.role || '—';
  document.getElementById('user-avatar').textContent = (currentUser?.full_name || 'U')[0].toUpperCase();

  navigate('dashboard');
  initSignaturePad();
}

// Auto-boot if token exists
if (authToken && currentUser) bootApp();

// ═══════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`page-${page}`)?.classList.add('active');
  document.getElementById(`nav-${page}`)?.classList.add('active');

  if (page === 'dashboard') loadDashboard();
  if (page === 'notes') loadNotesList();
  if (page === 'patients') loadPatients();
  if (page === 'new-note') resetWizard();
  if (page === 'consultations') loadConsultations();
  if (page === 'new-consultation') resetConsultWizard();
}

document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', e => { e.preventDefault(); navigate(el.dataset.page); });
});

// ═══════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════
async function loadDashboard() {
  document.getElementById('dash-date').textContent =
    new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  try {
    const [stats, notes, consults] = await Promise.all([
      api('GET', '/api/notes/stats'),
      api('GET', '/api/notes?limit=6'),
      api('GET', '/api/consultations?limit=6'),
    ]);
    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-signed').textContent = stats.signed;
    document.getElementById('stat-draft').textContent = stats.drafts;
    document.getElementById('stat-incomplete').textContent = stats.incomplete;
    renderRecentNotes(notes);
    renderRecentConsults(consults);
  } catch (err) {
    toast('Could not load dashboard: ' + err.message, 'error');
  }
}

function renderRecentNotes(notes) {
  const el = document.getElementById('recent-notes-list');
  if (!notes.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-state-icon"></div><p>No OT notes yet. Create your first one!</p></div>';
    return;
  }
  el.innerHTML = notes.map(n => `
    <div class="note-row" onclick="openNoteModal('${n.id}')">
      <div>
        <div class="note-patient">${esc(n.patient_name || 'Unknown Patient')}</div>
        <div class="note-mrn">MRN: ${esc(n.patient_mrn || '—')}</div>
      </div>
      <div class="note-proc">${esc(n.procedure_name || '—')}</div>
      <div class="note-date">${formatDate(n.date_of_surgery || n.created_at)}</div>
      <div>${statusBadge(n.status)}</div>
      <button class="btn-ghost btn-xs" onclick="event.stopPropagation();exportPDF('${n.id}')">PDF</button>
    </div>`).join('');
}

function renderRecentConsults(consults) {
  const el = document.getElementById('recent-consults-list');
  if (!consults.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💬</div><p>No consultations yet. Start a new one!</p></div>';
    return;
  }
  el.innerHTML = consults.map(c => `
    <div class="note-row" onclick="openConsultModal('${c.id}')">
      <div>
        <div class="note-patient">${esc(c.patient_name || 'Unknown Patient')}</div>
        <div class="note-mrn">${esc(c.doctor_name || '—')} · ${esc(c.department || '—')}</div>
      </div>
      <div class="note-proc">${esc(c.diagnosis || 'Pending analysis')}</div>
      <div class="note-date">${formatDate(c.consultation_date || c.created_at)}</div>
      <div>${consultBadge(c.status)}</div>
      <span></span>
    </div>`).join('');
}

// ═══════════════════════════════════════════════════════════════
// NOTES LIST
// ═══════════════════════════════════════════════════════════════
async function loadNotesList(status = '', search = '') {
  const container = document.getElementById('notes-list-container');
  container.innerHTML = '<div class="empty-state">Loading…</div>';
  try {
    let url = `/api/notes?limit=100`;
    if (status) url += `&status=${status}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const notes = await api('GET', url);
    renderNotesTable(notes, container);
  } catch (err) {
    container.innerHTML = `<div class="empty-state">${err.message}</div>`;
  }
}

function renderNotesTable(notes, container) {
  if (!notes.length) {
    container.innerHTML = '<div class="card"><div class="empty-state"><div class="empty-state-icon">🔍</div><p>No notes found.</p></div></div>';
    return;
  }
  container.innerHTML = `
    <div class="card">
      <table class="notes-table">
        <thead>
          <tr>
            <th>Patient</th><th>MRN</th><th>Procedure</th>
            <th>Date</th><th>Surgeon</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${notes.map(n => `
            <tr onclick="openNoteModal('${n.id}')" style="cursor:pointer">
              <td><strong>${esc(n.patient_name || '—')}</strong></td>
              <td style="font-family:var(--font-mono);font-size:0.8rem">${esc(n.patient_mrn || '—')}</td>
              <td>${esc(n.procedure_name || '—')}</td>
              <td>${formatDate(n.date_of_surgery || n.created_at)}</td>
              <td>${esc(n.surgeon_name || '—')}</td>
              <td>${statusBadge(n.status)}</td>
              <td>
                <div style="display:flex;gap:6px">
                  <button class="btn-ghost btn-xs" onclick="event.stopPropagation();exportPDF('${n.id}')">PDF</button>
                  ${n.status !== 'signed' ? `<button class="btn-ghost btn-xs" onclick="event.stopPropagation();deleteNote('${n.id}')">Del</button>` : ''}
                </div>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

// Filter chips — OT Notes (scoped to notes page only)
document.querySelectorAll('[data-status]').forEach(chip => {
  chip.addEventListener('click', () => {
    chip.closest('.filter-chips').querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    currentNotesFilter = chip.dataset.status;
    loadNotesList(currentNotesFilter, document.getElementById('notes-search').value);
  });
});
let searchDebounce;
document.getElementById('notes-search').addEventListener('input', e => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => loadNotesList(currentNotesFilter, e.target.value), 350);
});

// ═══════════════════════════════════════════════════════════════
// NOTE MODAL
// ═══════════════════════════════════════════════════════════════
async function openNoteModal(id) {
  try {
    const note = await api('GET', `/api/notes/${id}`);
    document.getElementById('modal-note-title').textContent =
      `OT Note — ${note.patient_name || 'Unknown'} (${note.patient_mrn || '—'})`;
    document.getElementById('modal-note-body').innerHTML = renderNoteDetail(note);
    document.getElementById('modal-export-pdf').onclick = () => exportPDF(id);
    document.getElementById('modal-export-pdf').style.display = '';  // restore if hidden by consult modal
    document.getElementById('note-modal').classList.remove('hidden');
  } catch (err) { toast(err.message, 'error'); }
}
document.getElementById('close-note-modal').addEventListener('click', () => {
  document.getElementById('note-modal').classList.add('hidden');
});
document.getElementById('note-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('note-modal'))
    document.getElementById('note-modal').classList.add('hidden');
});

function renderNoteDetail(n) {
  const field = (label, val, full = false) => {
    const v = val && val !== 'not_mentioned' ? esc(val) : '<em style="color:var(--text-muted)">—</em>';
    return `<div class="note-detail-field${full ? ' ' : ''}">
      <span class="note-detail-label">${label}</span>
      <span class="note-detail-value">${v}</span>
    </div>`;
  };
  const textBlock = (val) => val
    ? `<div class="note-detail-text">${esc(val)}</div>`
    : `<div style="color:var(--text-muted);font-size:0.82rem;font-style:italic">Not documented</div>`;

  const countBadge = (val) => {
    if (val === 'yes') return '<span class="count-badge count-yes">✓ Correct</span>';
    if (val === 'no') return '<span class="count-badge count-no">✗ Incorrect</span>';
    return '<span class="count-badge count-nm">Not done</span>';
  };

  const missing = n.missing_fields?.length
    ? `<div class="missing-alert" style="margin-bottom:1rem">
        <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
        <div><strong>Missing fields:</strong> ${n.missing_fields.join(', ')}</div>
       </div>` : '';

  const audit = (n.audit_trail || []).map(a => `
    <div class="audit-item">
      <span class="audit-time">${formatDateTime(a.timestamp)}</span>
      <span class="audit-details"><span class="audit-action">${esc(a.action)}</span> by ${esc(a.user)} — ${esc(a.note)}</span>
    </div>`).join('') || '<div class="empty-state" style="padding:1rem">No audit events</div>';

  return `
    ${missing}
    <div class="note-detail-grid">
      <div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Patient</div>
          ${field('Name', n.patient_name)}
          ${field('MRN', n.patient_mrn)}
          ${field('Age/Gender', [n.patient_age, n.patient_gender].filter(Boolean).join(' / '))}
          ${field('Ward / Bed', [n.ward, n.bed_number].filter(Boolean).join(' / '))}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Procedure Timing</div>
          ${field('Date', n.date_of_surgery)}
          ${field('Start / End', [n.time_start, n.time_end].filter(Boolean).join(' – '))}
          ${field('Duration', n.duration_minutes ? n.duration_minutes + ' min' : null)}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Care Team</div>
          ${field('Surgeon', n.surgeon_name)}
          ${field('Assistant', n.assistant_surgeon)}
          ${field('Anesthetist', n.anesthetist)}
          ${field('Scrub Nurse', n.scrub_nurse)}
          ${field('Circ. Nurse', n.circulating_nurse)}
          ${field('Anesthesia', n.type_of_anesthesia)}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Diagnosis</div>
          ${field('Pre-op Dx', n.pre_op_diagnosis)}
          ${field('Post-op Dx', n.post_op_diagnosis)}
          ${field('Procedure', n.procedure_name)}
        </div>
      </div>
      <div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Safety Counts</div>
          <div class="note-detail-field"><span class="note-detail-label">Blood Loss</span><span>${esc(n.blood_loss_ml || '—')}</span></div>
          <div class="note-detail-field"><span class="note-detail-label">Sponge Count</span>${countBadge(n.sponge_count_correct)}</div>
          <div class="note-detail-field"><span class="note-detail-label">Instrument Count</span>${countBadge(n.instrument_count_correct)}</div>
          <div class="note-detail-field"><span class="note-detail-label">Needle Count</span>${countBadge(n.needle_count_correct)}</div>
          ${field('Fluids', n.fluids_given)}
          ${field('Drain', n.drain_placed)}
          ${field('Wound Closure', n.wound_closure)}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Implants / Consumables</div>
          ${field('Implants', n.implants_used)}
          ${field('Consumables', n.consumables)}
          ${field('Specimen', n.specimen_sent)}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Outcome</div>
          ${field('Complications', n.complications)}
          ${field('Disposition', n.disposition)}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Signature</div>
          ${field('Signed by', n.signed_by)}
          ${field('Signed at', n.signed_at ? formatDateTime(n.signed_at) : null)}
          ${field('Status', n.status?.toUpperCase())}
        </div>
      </div>
    </div>
    <div class="note-detail-section">
      <div class="note-detail-heading">Procedure Description</div>
      ${textBlock(n.procedure_description)}
    </div>
    <div class="note-detail-section">
      <div class="note-detail-heading">Intra-operative Findings</div>
      ${textBlock(n.intra_op_findings)}
    </div>
    <div class="note-detail-section">
      <div class="note-detail-heading">Post-operative Instructions</div>
      ${textBlock(n.post_op_instructions)}
    </div>
    <div class="note-detail-section">
      <div class="note-detail-heading">Audit Trail</div>
      <div class="audit-trail">${audit}</div>
    </div>`;
}

// ═══════════════════════════════════════════════════════════════
// WIZARD — NEW NOTE
// ═══════════════════════════════════════════════════════════════
function resetWizard() {
  currentNoteId = null;
  goToStep(1);
  // Clear step 1 inputs
  ['nw-patient-name', 'nw-mrn', 'nw-age', 'nw-ward', 'nw-bed', 'nw-date', 'nw-time-start', 'nw-time-end']
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  document.getElementById('nw-gender').value = '';
  document.getElementById('nw-date').valueAsDate = new Date();
  document.getElementById('transcript-area').value = '';
  document.getElementById('missing-fields-alert').classList.add('hidden');
  clearReviewFields();
  clearCanvas();
}

function goToStep(n) {
  document.querySelectorAll('.wizard-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`wizard-step-${n}`).classList.add('active');

  document.querySelectorAll('.step').forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i + 1 < n) s.classList.add('done');
    if (i + 1 === n) s.classList.add('active');
  });
}

// Step 1 → create draft note
document.getElementById('step1-next-btn').addEventListener('click', async () => {
  const name = document.getElementById('nw-patient-name').value.trim();
  const mrn = document.getElementById('nw-mrn').value.trim();
  if (!name || !mrn) { toast('Patient name and MRN are required.', 'error'); return; }

  try {
    showLoader('Creating draft note…');
    const note = await api('POST', '/api/notes/', {
      patient_name: name,
      patient_mrn: mrn,
      patient_age: document.getElementById('nw-age').value.trim() || null,
      patient_gender: document.getElementById('nw-gender').value || null,
      ward: document.getElementById('nw-ward').value.trim() || null,
      bed_number: document.getElementById('nw-bed').value.trim() || null,
      date_of_surgery: document.getElementById('nw-date').value || null,
      time_start: document.getElementById('nw-time-start').value || null,
      time_end: document.getElementById('nw-time-end').value || null,
    });
    currentNoteId = note.id;
    document.getElementById('dictation-note-id-badge').textContent = `Draft • ${mrn}`;
    hideLoader();
    goToStep(2);
    toast('Draft created. Start dictating!', 'success');
  } catch (err) {
    hideLoader();
    toast(err.message, 'error');
  }
});

// ═══════════════════════════════════════════════════════════════
// DICTATION — MediaRecorder + Waveform
// ═══════════════════════════════════════════════════════════════
document.getElementById('record-btn').addEventListener('click', startRecording);
document.getElementById('stop-btn').addEventListener('click', stopRecording);
document.getElementById('clear-transcript-btn').addEventListener('click', () => {
  document.getElementById('transcript-area').value = '';
});

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    setupWaveform(stream);

    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    audioChunks = [];
    mediaRecorder.ondataavailable = e => { if (e.data.size) audioChunks.push(e.data); };
    mediaRecorder.onstop = handleRecordingStop;
    mediaRecorder.start(250);

    // UI
    document.getElementById('record-btn').classList.add('hidden');
    document.getElementById('stop-btn').classList.remove('hidden');
    document.getElementById('waveform-idle').classList.add('hidden');
    document.getElementById('waveform-canvas').classList.remove('hidden');
    document.getElementById('recording-pulse').classList.remove('hidden');

    recSeconds = 0;
    updateTimer();
    recInterval = setInterval(updateTimer, 1000);
  } catch (err) {
    toast('Microphone access denied: ' + err.message, 'error');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
  }
  clearInterval(recInterval);
  if (animRAF) cancelAnimationFrame(animRAF);

  document.getElementById('stop-btn').classList.add('hidden');
  document.getElementById('record-btn').classList.remove('hidden');
  document.getElementById('waveform-canvas').classList.add('hidden');
  document.getElementById('waveform-idle').classList.remove('hidden');
  document.getElementById('recording-pulse').classList.add('hidden');
}

async function handleRecordingStop() {
  if (!audioChunks.length) return;
  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  await uploadAudio(blob);
}

async function uploadAudio(blob) {
  showLoader('Transcribing audio…');
  try {
    const form = new FormData();
    form.append('audio', blob, 'dictation.webm');
    if (currentNoteId) form.append('note_id', currentNoteId);
    const res = await api('POST', '/api/speech/transcribe', form, true);
    const area = document.getElementById('transcript-area');
    area.value = (area.value ? area.value + '\n\n' : '') + res.transcript;
    toast(`Transcribed ${res.words} words (${res.confidence}% confidence)`, 'success');
  } catch (err) {
    toast('Transcription failed: ' + err.message, 'error');
  } finally {
    hideLoader();
  }
}

function setupWaveform(stream) {
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  const source = audioCtx.createMediaStreamSource(stream);
  source.connect(analyser);
  drawWaveform();
}

function drawWaveform() {
  const canvas = document.getElementById('waveform-canvas');
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.offsetWidth;
  const H = canvas.height = canvas.offsetHeight;
  const buf = new Uint8Array(analyser.frequencyBinCount);

  function frame() {
    animRAF = requestAnimationFrame(frame);
    analyser.getByteFrequencyData(buf);
    ctx.clearRect(0, 0, W, H);

    const bars = buf.length;
    const bw = W / bars;
    for (let i = 0; i < bars; i++) {
      const h = (buf[i] / 255) * H;
      const hue = 180 + (buf[i] / 255) * 60;
      ctx.fillStyle = `hsla(${hue},80%,60%,0.8)`;
      ctx.fillRect(i * bw, H - h, bw - 1, h);
    }
  }
  frame();
}

function updateTimer() {
  recSeconds++;
  const m = String(Math.floor(recSeconds / 60)).padStart(2, '0');
  const s = String(recSeconds % 60).padStart(2, '0');
  document.getElementById('rec-timer').textContent = `${m}:${s}`;
}

// ═══════════════════════════════════════════════════════════════
// STRUCTURE WITH AI
// ═══════════════════════════════════════════════════════════════
document.getElementById('structure-btn').addEventListener('click', async () => {
  const transcript = document.getElementById('transcript-area').value.trim();
  if (!transcript) { toast('Please record or type a transcription first.', 'error'); return; }
  if (!currentNoteId) { toast('Create a draft note first (go back to Step 1).', 'error'); return; }

  showLoader('Structuring with Gemini AI…');
  try {
    // Save transcript first
    await api('PATCH', `/api/notes/${currentNoteId}`, { raw_transcription: transcript });

    const res = await api('POST', `/api/speech/structure?note_id=${currentNoteId}`);
    populateReviewFields(res.structured);

    const missing = res.missing_fields || [];
    if (missing.length) {
      document.getElementById('missing-fields-alert').classList.remove('hidden');
      document.getElementById('missing-fields-list').textContent = missing.join(', ');
    } else {
      document.getElementById('missing-fields-alert').classList.add('hidden');
    }

    updatePreview();
    goToStep(3);
    hideLoader();
    toast(missing.length
      ? `⚠ ${missing.length} mandatory fields missing — please fill them in.`
      : '✓ AI structured your note successfully!',
      missing.length ? 'error' : 'success', 5000);
  } catch (err) {
    hideLoader();
    toast('Structuring failed: ' + err.message, 'error');
  }
});

function populateReviewFields(d) {
  const set = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
  set('rv-surgeon', d.surgeon_name || currentUser?.full_name);
  set('rv-assistant', d.assistant_surgeon);
  set('rv-anesthetist', d.anesthetist);
  set('rv-scrub-nurse', d.scrub_nurse);
  set('rv-circ-nurse', d.circulating_nurse);
  set('rv-anesthesia', d.type_of_anesthesia);
  set('rv-pre-op', d.pre_op_diagnosis);
  set('rv-post-op', d.post_op_diagnosis);
  set('rv-procedure-name', d.procedure_name);
  set('rv-procedure-desc', d.procedure_description);
  set('rv-intra-op', d.intra_op_findings);
  set('rv-blood-loss', d.blood_loss_ml && d.blood_loss_ml !== 'not_mentioned' ? d.blood_loss_ml : '');
  set('rv-fluids', d.fluids_given);
  if (d.sponge_count_correct) document.getElementById('rv-sponge').value = d.sponge_count_correct;
  if (d.instrument_count_correct) document.getElementById('rv-instrument').value = d.instrument_count_correct;
  if (d.needle_count_correct) document.getElementById('rv-needle').value = d.needle_count_correct;
  if (d.drain_placed) document.getElementById('rv-drain').value = d.drain_placed;
  set('rv-wound', d.wound_closure);
  set('rv-implants', d.implants_used);
  set('rv-consumables', d.consumables);
  set('rv-specimen', d.specimen_sent);
  if (d.disposition) document.getElementById('rv-disposition').value = d.disposition;
  set('rv-complications', d.complications);
  set('rv-post-op-inst', d.post_op_instructions);
}

function clearReviewFields() {
  const ids = ['rv-surgeon', 'rv-assistant', 'rv-anesthetist', 'rv-scrub-nurse', 'rv-circ-nurse',
    'rv-anesthesia', 'rv-pre-op', 'rv-post-op', 'rv-procedure-name', 'rv-procedure-desc',
    'rv-intra-op', 'rv-blood-loss', 'rv-fluids', 'rv-wound', 'rv-implants', 'rv-consumables',
    'rv-specimen', 'rv-complications', 'rv-post-op-inst'];
  ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  ['rv-sponge', 'rv-instrument', 'rv-needle', 'rv-drain', 'rv-disposition'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
}

// ── Live preview update on typing ───────────────────────────
document.querySelectorAll('[id^="rv-"]').forEach(el => {
  el.addEventListener('input', updatePreview);
  el.addEventListener('change', updatePreview);
});

function updatePreview() {
  const g = id => document.getElementById(id)?.value || '';
  const pv = v => v ? `<span class="preview-field-val">${esc(v)}</span>` : '<span class="preview-missing">Missing</span>';

  const html = `
    <div class="preview-section">
      <div class="preview-section-title">Care Team</div>
      <div class="preview-field"><span class="preview-field-key">Surgeon</span>${pv(g('rv-surgeon'))}</div>
      <div class="preview-field"><span class="preview-field-key">Anesthesia</span>${pv(g('rv-anesthesia'))}</div>
    </div>
    <div class="preview-section">
      <div class="preview-section-title">Diagnosis</div>
      <div class="preview-field"><span class="preview-field-key">Pre-op</span>${pv(g('rv-pre-op'))}</div>
      <div class="preview-field"><span class="preview-field-key">Post-op</span>${pv(g('rv-post-op'))}</div>
      <div class="preview-field"><span class="preview-field-key">Procedure</span>${pv(g('rv-procedure-name'))}</div>
    </div>
    <div class="preview-section">
      <div class="preview-section-title">Procedure</div>
      <div style="font-size:0.78rem;color:var(--text-secondary);line-height:1.5">
        ${g('rv-procedure-desc') ? esc(g('rv-procedure-desc').substring(0, 180)) + (g('rv-procedure-desc').length > 180 ? '…' : '') : '<em style="color:var(--text-muted)">Not documented</em>'}
      </div>
    </div>
    <div class="preview-section">
      <div class="preview-section-title">Safety</div>
      <div class="preview-field"><span class="preview-field-key">Blood Loss</span>${pv(g('rv-blood-loss'))}</div>
      <div class="preview-field"><span class="preview-field-key">Sponge</span>${pv(g('rv-sponge'))}</div>
      <div class="preview-field"><span class="preview-field-key">Complications</span>${pv(g('rv-complications'))}</div>
    </div>`;
  document.getElementById('note-preview').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
// SAVE DRAFT
// ═══════════════════════════════════════════════════════════════
document.getElementById('save-draft-btn').addEventListener('click', async () => {
  if (!currentNoteId) { toast('No active note.', 'error'); return; }
  showLoader('Saving draft…');
  try {
    await api('PATCH', `/api/notes/${currentNoteId}`, collectReviewData());
    hideLoader(); toast('Draft saved.', 'success');
  } catch (err) { hideLoader(); toast(err.message, 'error'); }
});

function collectReviewData() {
  const g = id => document.getElementById(id)?.value?.trim() || null;
  return {
    surgeon_name: g('rv-surgeon'),
    assistant_surgeon: g('rv-assistant'),
    anesthetist: g('rv-anesthetist'),
    scrub_nurse: g('rv-scrub-nurse'),
    circulating_nurse: g('rv-circ-nurse'),
    type_of_anesthesia: g('rv-anesthesia'),
    pre_op_diagnosis: g('rv-pre-op'),
    post_op_diagnosis: g('rv-post-op'),
    procedure_name: g('rv-procedure-name'),
    procedure_description: g('rv-procedure-desc'),
    intra_op_findings: g('rv-intra-op'),
    blood_loss_ml: g('rv-blood-loss'),
    fluids_given: g('rv-fluids'),
    sponge_count_correct: g('rv-sponge'),
    instrument_count_correct: g('rv-instrument'),
    needle_count_correct: g('rv-needle'),
    drain_placed: g('rv-drain'),
    wound_closure: g('rv-wound'),
    implants_used: g('rv-implants'),
    consumables: g('rv-consumables'),
    specimen_sent: g('rv-specimen'),
    disposition: g('rv-disposition'),
    complications: g('rv-complications'),
    post_op_instructions: g('rv-post-op-inst'),
  };
}

// ═══════════════════════════════════════════════════════════════
// SIGN NOTE
// ═══════════════════════════════════════════════════════════════
document.getElementById('sign-note-btn').addEventListener('click', async () => {
  if (!currentNoteId) { toast('No active note.', 'error'); return; }

  const sigData = sigCanvas.toDataURL('image/png');
  const isEmpty = isCanvasBlank(sigCanvas);
  if (isEmpty) { toast('Please sign the note before finalising.', 'error'); return; }

  showLoader('Saving and signing note…');
  try {
    await api('PATCH', `/api/notes/${currentNoteId}`, collectReviewData());
    const res = await api('POST', `/api/notes/${currentNoteId}/sign`, { signature_data: sigData });
    hideLoader();
    toast('✓ OT Note signed and finalised!', 'success', 5000);
    currentNoteId = null;
    navigate('notes');
  } catch (err) { hideLoader(); toast(err.message, 'error'); }
});

// ═══════════════════════════════════════════════════════════════
// PDF EXPORT
// ═══════════════════════════════════════════════════════════════
document.getElementById('export-pdf-btn').addEventListener('click', async () => {
  if (!currentNoteId) { toast('Save the note first.', 'error'); return; }
  await exportPDF(currentNoteId);
});

async function exportPDF(noteId) {
  showLoader('Generating PDF…');
  try {
    const blob = await api('GET', `/api/notes/${noteId}/export/pdf`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `OT_Note_${noteId}.pdf`;
    a.click(); URL.revokeObjectURL(url);
    hideLoader(); toast('PDF downloaded.', 'success');
  } catch (err) { hideLoader(); toast(err.message, 'error'); }
}

async function exportConsultPDF(consultId) {
  showLoader('Generating OPD Summary PDF…');
  try {
    const blob = await api('GET', `/api/consultations/${consultId}/export/pdf`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `OPD_Summary_${consultId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    hideLoader();
    toast('OPD Summary PDF downloaded.', 'success');
  } catch (err) { hideLoader(); toast(err.message, 'error'); }
}


// ═══════════════════════════════════════════════════════════════
// DELETE NOTE
// ═══════════════════════════════════════════════════════════════
async function deleteNote(id) {
  if (!confirm('Delete this OT note? This cannot be undone.')) return;
  try {
    await api('DELETE', `/api/notes/${id}`);
    toast('Note deleted.', 'info');
    loadNotesList(currentNotesFilter);
  } catch (err) { toast(err.message, 'error'); }
}

// ═══════════════════════════════════════════════════════════════
// PATIENTS
// ═══════════════════════════════════════════════════════════════
async function loadPatients(search = '') {
  const container = document.getElementById('patients-list-container');
  container.innerHTML = '<div class="empty-state">Loading…</div>';
  try {
    const url = `/api/patients?limit=100${search ? `&search=${encodeURIComponent(search)}` : ''}`;
    const patients = await api('GET', url);
    renderPatientsTable(patients, container);
  } catch (err) { container.innerHTML = `<div class="empty-state">${err.message}</div>`; }
}

function renderPatientsTable(patients, container) {
  if (!patients.length) {
    container.innerHTML = '<div class="card"><div class="empty-state"><div class="empty-state-icon">👤</div><p>No patients found.</p></div></div>';
    return;
  }
  container.innerHTML = `
    <div class="card">
      <table class="notes-table">
        <thead>
          <tr><th>Name</th><th>MRN</th><th>DOB</th><th>Gender</th><th>Blood Group</th><th>Ward / Bed</th></tr>
        </thead>
        <tbody>
          ${patients.map(p => `
            <tr>
              <td><strong>${esc(p.full_name)}</strong></td>
              <td style="font-family:var(--font-mono);font-size:0.8rem">${esc(p.mrn)}</td>
              <td>${esc(p.dob || '—')}</td>
              <td>${esc(p.gender || '—')}</td>
              <td>${esc(p.blood_group || '—')}</td>
              <td>${esc([p.ward, p.bed_number].filter(Boolean).join(' / ') || '—')}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

// Patient search
let patientSearchDebounce;
document.getElementById('patient-search').addEventListener('input', e => {
  clearTimeout(patientSearchDebounce);
  patientSearchDebounce = setTimeout(() => loadPatients(e.target.value), 350);
});

// Add Patient Modal
document.getElementById('add-patient-btn').addEventListener('click', () => {
  document.getElementById('patient-modal').classList.remove('hidden');
});
document.getElementById('close-patient-modal').addEventListener('click', () => {
  document.getElementById('patient-modal').classList.add('hidden');
});
document.getElementById('cancel-patient-modal').addEventListener('click', () => {
  document.getElementById('patient-modal').classList.add('hidden');
});

document.getElementById('save-patient-btn').addEventListener('click', async () => {
  const errEl = document.getElementById('patient-modal-error');
  errEl.classList.add('hidden');
  const g = id => document.getElementById(id)?.value?.trim() || null;
  const body = {
    full_name: g('pm-name'),
    mrn: g('pm-mrn'),
    dob: g('pm-dob'),
    gender: g('pm-gender'),
    blood_group: g('pm-blood'),
    contact_number: g('pm-contact'),
    ward: g('pm-ward'),
    bed_number: g('pm-bed'),
    address: g('pm-address'),
  };
  if (!body.full_name || !body.mrn) {
    errEl.textContent = 'Name and MRN are required.'; errEl.classList.remove('hidden'); return;
  }
  try {
    showLoader('Saving patient…');
    await api('POST', '/api/patients/', body);
    hideLoader();
    document.getElementById('patient-modal').classList.add('hidden');
    toast('Patient added.', 'success');
    loadPatients();
  } catch (err) {
    hideLoader(); errEl.textContent = err.message; errEl.classList.remove('hidden');
  }
});

// ═══════════════════════════════════════════════════════════════
// COLLAPSIBLE SECTIONS
// ═══════════════════════════════════════════════════════════════
function toggleSection(name) {
  const body = document.getElementById(`body-${name}`);
  const header = body.previousElementSibling;
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : '';
  header.querySelector('.chevron').textContent = open ? '►' : '▼';
}

// ═══════════════════════════════════════════════════════════════
// SIGNATURE PAD
// ═══════════════════════════════════════════════════════════════
function initSignaturePad() {
  sigCanvas = document.getElementById('sig-canvas');
  sigCtx = sigCanvas.getContext('2d');
  sigCtx.strokeStyle = '#60a5fa';
  sigCtx.lineWidth = 2.5;
  sigCtx.lineCap = 'round';
  sigCtx.lineJoin = 'round';

  const getPos = (e) => {
    const rect = sigCanvas.getBoundingClientRect();
    const scaleX = sigCanvas.width / rect.width;
    const scaleY = sigCanvas.height / rect.height;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return [(clientX - rect.left) * scaleX, (clientY - rect.top) * scaleY];
  };

  sigCanvas.addEventListener('mousedown', e => {
    sigDrawing = true;
    [sigLastX, sigLastY] = getPos(e);
    sigCtx.beginPath(); sigCtx.moveTo(sigLastX, sigLastY);
  });
  sigCanvas.addEventListener('mousemove', e => {
    if (!sigDrawing) return;
    const [x, y] = getPos(e);
    sigCtx.lineTo(x, y); sigCtx.stroke();
    sigLastX = x; sigLastY = y;
  });
  sigCanvas.addEventListener('mouseup', () => sigDrawing = false);
  sigCanvas.addEventListener('mouseleave', () => sigDrawing = false);
  sigCanvas.addEventListener('touchstart', e => { e.preventDefault(); sigDrawing = true;[sigLastX, sigLastY] = getPos(e); }, { passive: false });
  sigCanvas.addEventListener('touchmove', e => {
    if (!sigDrawing) return; e.preventDefault();
    const [x, y] = getPos(e); sigCtx.lineTo(x, y); sigCtx.stroke(); sigLastX = x; sigLastY = y;
  }, { passive: false });
  sigCanvas.addEventListener('touchend', () => sigDrawing = false);

  document.getElementById('clear-sig-btn').addEventListener('click', clearCanvas);
}

function clearCanvas() {
  if (!sigCtx) return;
  sigCtx.clearRect(0, 0, sigCanvas.width, sigCanvas.height);
}

function isCanvasBlank(canvas) {
  const ctx = canvas.getContext('2d');
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  return !data.some(v => v !== 0);
}

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function statusBadge(status) {
  const map = {
    draft: 'badge-draft', review: 'badge-review', signed: 'badge-signed',
    processing: 'badge-processing', dictating: 'badge-dictating',
  };
  return `<span class="badge ${map[status] || 'badge-draft'}">${status || 'draft'}</span>`;
}

function formatDate(val) {
  if (!val) return '—';
  try {
    return new Date(val).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch { return val; }
}

function formatDateTime(val) {
  if (!val) return '—';
  try {
    return new Date(val).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return val; }
}

// ═══════════════════════════════════════════════════════════════
// CONSULTATION MODULE
// ═══════════════════════════════════════════════════════════════

// ── State ────────────────────────────────────────────────────────
let currentConsultId = null;
let cwMediaRecorder = null;
let cwAudioChunks = [];
let cwRecInterval = null;
let cwRecSeconds = 0;
let cwAudioCtx = null;
let cwAnalyser = null;
let cwAnimRAF = null;
let cwPrescription = [];
let cwLabTests = [];
let cwImaging = [];



// ── Status badge ─────────────────────────────────────────────────
function consultBadge(status) {
  const map = {
    draft: 'badge-draft', review: 'badge-review',
    finalized: 'badge-finalized', processing: 'badge-processing',
    recording: 'badge-recording',
  };
  return `<span class="badge ${map[status] || 'badge-draft'}">${status || 'draft'}</span>`;
}

// ── Load consultations list ──────────────────────────────────────
async function loadConsultations(status = '', search = '') {
  const container = document.getElementById('consultations-list-container');
  container.innerHTML = '<div class="empty-state">Loading…</div>';
  try {
    const [stats, list] = await Promise.all([
      api('GET', '/api/consultations/stats'),
      api('GET', `/api/consultations?limit=100${status ? '&status=' + status : ''}${search ? '&search=' + encodeURIComponent(search) : ''}`),
    ]);
    document.getElementById('cs-total').textContent = stats.total;
    document.getElementById('cs-finalized').textContent = stats.finalized;
    document.getElementById('cs-drafts').textContent = stats.drafts;
    document.getElementById('cs-incomplete').textContent = stats.incomplete;
    renderConsultTable(list, container);
  } catch (err) {
    container.innerHTML = `<div class="empty-state">${err.message}</div>`;
  }
}

function renderConsultTable(list, container) {
  if (!list.length) {
    container.innerHTML = '<div class="card"><div class="empty-state"><div class="empty-state-icon">💬</div><p>No consultations yet. Start a new one!</p></div></div>';
    return;
  }
  container.innerHTML = `
    <div class="card">
      <table class="notes-table">
        <thead>
          <tr>
            <th>Patient</th><th>MRN</th><th>Diagnosis</th>
            <th>Date</th><th>Doctor</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${list.map(c => `
            <tr onclick="openConsultModal('${c.id}')" style="cursor:pointer">
              <td><strong>${esc(c.patient_name || '—')}</strong></td>
              <td style="font-family:var(--font-mono);font-size:0.8rem">${esc(c.patient_mrn || '—')}</td>
              <td>${esc(c.diagnosis || '—')}</td>
              <td>${formatDate(c.consultation_date || c.created_at)}</td>
              <td>${esc(c.doctor_name || '—')}</td>
              <td>${consultBadge(c.status)}</td>
              <td>
                <div style="display:flex;gap:6px">
                  <button class="btn-ghost btn-xs" onclick="event.stopPropagation();exportConsultPDF('${c.id}')">PDF</button>
                  ${c.status !== 'finalized' ? `<button class="btn-ghost btn-xs" onclick="event.stopPropagation();deleteConsult('${c.id}')">Del</button>` : ''}
                </div>
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
}

// Filter chips for consultations (scoped to consult page only)
document.querySelectorAll('[data-cstatus]').forEach(chip => {
  chip.addEventListener('click', () => {
    chip.closest('.filter-chips').querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    loadConsultations(chip.dataset.cstatus, document.getElementById('consult-search').value);
  });
});
let consultSearchDebounce;
document.getElementById('consult-search')?.addEventListener('input', e => {
  clearTimeout(consultSearchDebounce);
  const activeChip = document.querySelector('[data-cstatus].active');
  consultSearchDebounce = setTimeout(() => loadConsultations(activeChip?.dataset.cstatus || '', e.target.value), 350);
});

// ── Consultation modal (detail view) ─────────────────────────────
async function openConsultModal(id) {
  try {
    const c = await api('GET', `/api/consultations/${id}`);
    document.getElementById('modal-note-title').textContent =
      `Consultation — ${c.patient_name || 'Unknown'} (${c.patient_mrn || '—'})`;
    document.getElementById('modal-note-body').innerHTML = renderConsultDetail(c);

    // Wire up PDF button for OPD Summary
    const pdfBtn = document.getElementById('modal-export-pdf');
    pdfBtn.style.display = '';
    pdfBtn.textContent = '';
    pdfBtn.innerHTML = `<svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:currentColor;margin-right:4px"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>OPD PDF`;
    pdfBtn.onclick = () => exportConsultPDF(id);

    document.getElementById('note-modal').classList.remove('hidden');
  } catch (err) { toast(err.message, 'error'); }
}




function renderConsultDetail(c) {
  const f = (label, val) => `<div class="note-detail-field">
    <span class="note-detail-label">${label}</span>
    <span class="note-detail-value">${val ? esc(val) : '<em style="color:var(--text-muted)">—</em>'}</span>
  </div>`;
  const tb = val => val
    ? `<div class="note-detail-text">${esc(val)}</div>`
    : `<div style="color:var(--text-muted);font-size:0.82rem;font-style:italic">Not documented</div>`;

  const rxHtml = (c.prescription || []).map(r =>
    `<div class="rx-card" style="margin-bottom:0.5rem">
      <div class="rx-drug-name">💊 ${esc(r.drug)}</div>
      <div class="rx-meta">${[r.dose, r.route, r.frequency, r.duration].filter(Boolean).join(' · ')}</div>
      ${r.notes ? `<div class="rx-note">${esc(r.notes)}</div>` : ''}
    </div>`).join('') || '<em style="color:var(--text-muted)">None prescribed</em>';

  const labHtml = (c.lab_tests || []).map(l =>
    `<div class="rx-card" style="margin-bottom:0.5rem">
      <div class="rx-drug-name">🔬 ${esc(l.test_name)}</div>
      <div class="rx-meta">${esc(l.urgency || 'routine')}${l.reason ? ' · ' + esc(l.reason) : ''}</div>
    </div>`).join('') || '<em style="color:var(--text-muted)">No tests ordered</em>';

  const imgHtml = (c.imaging_ordered || []).map(i =>
    `<div class="rx-card" style="margin-bottom:0.5rem">
      <div class="rx-drug-name">🩻 ${esc(i.modality)} — ${esc(i.region || '')}</div>
      ${i.reason ? `<div class="rx-meta">${esc(i.reason)}</div>` : ''}
    </div>`).join('') || '<em style="color:var(--text-muted)">No imaging ordered</em>';

  const audit = (c.audit_trail || []).map(a => `
    <div class="audit-item">
      <span class="audit-time">${formatDateTime(a.timestamp)}</span>
      <span class="audit-details"><span class="audit-action">${esc(a.action)}</span> by ${esc(a.user)} — ${esc(a.note)}</span>
    </div>`).join('') || '<div class="empty-state" style="padding:1rem">No events</div>';

  return `
    <div class="note-detail-grid">
      <div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Patient</div>
          ${f('Name', c.patient_name)}${f('MRN', c.patient_mrn)}
          ${f('Age / Gender', [c.patient_age, c.patient_gender].filter(Boolean).join(' / '))}
          ${f('Chief Complaint', c.chief_complaint)}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Consultation</div>
          ${f('Doctor', c.doctor_name)}${f('Date', c.consultation_date)}
          ${f('Department', c.department)}${f('Status', c.status?.toUpperCase())}
        </div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Diagnosis</div>
          ${f('Primary Dx', c.diagnosis)}${f('Differential Dx', c.differential_diagnosis)}
        </div>
      </div>
      <div>
        <div class="note-detail-section">
          <div class="note-detail-heading">Follow-up</div>
          ${f('Date / Interval', c.follow_up_date)}${f('Referral', c.referral)}
        </div>
      </div>
    </div>
    <div class="note-detail-section"><div class="note-detail-heading">History of Present Illness</div>${tb(c.history_of_present_illness)}</div>
    <div class="note-detail-section"><div class="note-detail-heading">Examination Findings</div>${tb(c.examination_findings)}</div>
    <div class="note-detail-section"><div class="note-detail-heading">💊 Prescription</div>${rxHtml}</div>
    <div class="note-detail-section"><div class="note-detail-heading">🔬 Lab Tests</div>${labHtml}</div>
    <div class="note-detail-section"><div class="note-detail-heading">🩻 Imaging</div>${imgHtml}</div>
    <div class="note-detail-section"><div class="note-detail-heading">Follow-up Instructions</div>${tb(c.follow_up_instructions)}</div>
    <div class="note-detail-section"><div class="note-detail-heading">Lifestyle Advice</div>${tb(c.lifestyle_advice)}</div>
    <div class="note-detail-section"><div class="note-detail-heading">Audit Trail</div><div class="audit-trail">${audit}</div></div>`;
}

async function deleteConsult(id) {
  if (!confirm('Delete this consultation?')) return;
  try { await api('DELETE', `/api/consultations/${id}`); toast('Deleted.', 'info'); loadConsultations(); }
  catch (err) { toast(err.message, 'error'); }
}

// ═══════════════════════════════════════════════════════════════
// CONSULTATION WIZARD
// ═══════════════════════════════════════════════════════════════
function resetConsultWizard() {
  currentConsultId = null;
  cwPrescription = []; cwLabTests = []; cwImaging = [];
  cwGoToStep(1);
  ['cw-patient-name', 'cw-mrn', 'cw-age', 'cw-department', 'cw-complaint']
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  const cwDate = document.getElementById('cw-date');
  if (cwDate) cwDate.valueAsDate = new Date();
  document.getElementById('cw-gender').value = '';
  document.getElementById('cw-transcript-area').value = '';
  document.getElementById('cw-missing-alert').classList.add('hidden');
  clearCwReviewFields();
  renderCwRxList(); renderCwLabList(); renderCwImagingList();
}

function cwGoToStep(n) {
  document.querySelectorAll('#page-new-consultation .wizard-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`cw-wizard-step-${n}`).classList.add('active');
  document.querySelectorAll('#page-new-consultation .step').forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i + 1 < n) s.classList.add('done');
    if (i + 1 === n) s.classList.add('active');
  });
}

document.getElementById('cw-step1-next-btn')?.addEventListener('click', async () => {
  const name = document.getElementById('cw-patient-name').value.trim();
  if (!name) { toast('Patient name is required.', 'error'); return; }
  try {
    showLoader('Creating consultation record…');
    const c = await api('POST', '/api/consultations/', {
      patient_name: name,
      patient_mrn: document.getElementById('cw-mrn').value.trim() || null,
      patient_age: document.getElementById('cw-age').value.trim() || null,
      patient_gender: document.getElementById('cw-gender').value || null,
      department: document.getElementById('cw-department').value.trim() || null,
      consultation_date: document.getElementById('cw-date').value || null,
    });
    currentConsultId = c.id;
    document.getElementById('cw-consult-id-badge').textContent = `Draft • ${name}`;
    hideLoader(); cwGoToStep(2);
    toast('Consultation created. Start recording!', 'success');
  } catch (err) { hideLoader(); toast(err.message, 'error'); }
});

// ── Recording ────────────────────────────────────────────────────
document.getElementById('cw-record-btn')?.addEventListener('click', cwStartRecording);
document.getElementById('cw-stop-btn')?.addEventListener('click', cwStopRecording);
document.getElementById('cw-clear-transcript-btn')?.addEventListener('click', () => {
  document.getElementById('cw-transcript-area').value = '';
});

async function cwStartRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    cwSetupWaveform(stream);
    cwMediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    cwAudioChunks = [];
    cwMediaRecorder.ondataavailable = e => { if (e.data.size) cwAudioChunks.push(e.data); };
    cwMediaRecorder.onstop = cwHandleStop;
    cwMediaRecorder.start(250);
    document.getElementById('cw-record-btn').classList.add('hidden');
    document.getElementById('cw-stop-btn').classList.remove('hidden');
    document.getElementById('cw-waveform-idle').classList.add('hidden');
    document.getElementById('cw-waveform-canvas').classList.remove('hidden');
    document.getElementById('cw-recording-pulse').classList.remove('hidden');
    cwRecSeconds = 0; cwUpdateTimer();
    cwRecInterval = setInterval(cwUpdateTimer, 1000);
  } catch (err) { toast('Microphone access denied: ' + err.message, 'error'); }
}

function cwStopRecording() {
  if (cwMediaRecorder && cwMediaRecorder.state !== 'inactive') {
    cwMediaRecorder.stop(); cwMediaRecorder.stream.getTracks().forEach(t => t.stop());
  }
  clearInterval(cwRecInterval);
  if (cwAnimRAF) cancelAnimationFrame(cwAnimRAF);
  document.getElementById('cw-stop-btn').classList.add('hidden');
  document.getElementById('cw-record-btn').classList.remove('hidden');
  document.getElementById('cw-waveform-canvas').classList.add('hidden');
  document.getElementById('cw-waveform-idle').classList.remove('hidden');
  document.getElementById('cw-recording-pulse').classList.add('hidden');
}

async function cwHandleStop() {
  if (!cwAudioChunks.length) return;
  const blob = new Blob(cwAudioChunks, { type: 'audio/webm' });
  showLoader('Transcribing consultation audio…');
  try {
    const form = new FormData();
    form.append('audio', blob, 'consultation.webm');
    const res = await api('POST', `/api/consultations/${currentConsultId}/transcribe`, form, true);
    const area = document.getElementById('cw-transcript-area');
    area.value = (area.value ? area.value + '\n\n' : '') + res.transcript;
    toast(`Transcribed (${res.duration?.toFixed(1) || '?'}s)`, 'success');
  } catch (err) { toast('Transcription failed: ' + err.message, 'error'); }
  finally { hideLoader(); }
}

function cwSetupWaveform(stream) {
  cwAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
  cwAnalyser = cwAudioCtx.createAnalyser(); cwAnalyser.fftSize = 256;
  cwAudioCtx.createMediaStreamSource(stream).connect(cwAnalyser);
  const canvas = document.getElementById('cw-waveform-canvas');
  const ctx = canvas.getContext('2d');
  const buf = new Uint8Array(cwAnalyser.frequencyBinCount);
  function frame() {
    cwAnimRAF = requestAnimationFrame(frame);
    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = canvas.offsetHeight;
    cwAnalyser.getByteFrequencyData(buf);
    ctx.clearRect(0, 0, W, H);
    const bw = W / buf.length;
    for (let i = 0; i < buf.length; i++) {
      const h = (buf[i] / 255) * H;
      ctx.fillStyle = `hsla(${180 + (buf[i] / 255) * 60},80%,60%,0.8)`;
      ctx.fillRect(i * bw, H - h, bw - 1, h);
    }
  }
  frame();
}
function cwUpdateTimer() {
  cwRecSeconds++;
  const m = String(Math.floor(cwRecSeconds / 60)).padStart(2, '0');
  const s = String(cwRecSeconds % 60).padStart(2, '0');
  document.getElementById('cw-rec-timer').textContent = `${m}:${s}`;
}

// ── Analyse with AI ──────────────────────────────────────────────
document.getElementById('cw-structure-btn')?.addEventListener('click', async () => {
  const transcript = document.getElementById('cw-transcript-area').value.trim();
  if (!transcript) { toast('Please record or type the conversation first.', 'error'); return; }
  if (!currentConsultId) { toast('Go back to Step 1 to create a record.', 'error'); return; }

  showLoader('Analysing with Gemini AI…');
  try {
    await api('PATCH', `/api/consultations/${currentConsultId}`, { raw_transcription: transcript });
    const res = await api('POST', `/api/consultations/${currentConsultId}/structure`);
    const s = res.structured;
    const set = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
    set('cw-rv-diagnosis', s.diagnosis);
    set('cw-rv-ddx', s.differential_diagnosis);
    set('cw-rv-hpi', s.history_of_present_illness);
    set('cw-rv-exam', s.examination_findings);
    set('cw-rv-followup-date', s.follow_up_date);
    set('cw-rv-followup-inst', s.follow_up_instructions);
    set('cw-rv-referral', s.referral);
    set('cw-rv-lifestyle', s.lifestyle_advice);
    cwPrescription = Array.isArray(s.prescription) ? s.prescription : [];
    cwLabTests = Array.isArray(s.lab_tests) ? s.lab_tests : [];
    cwImaging = Array.isArray(s.imaging_ordered) ? s.imaging_ordered : [];
    renderCwRxList(); renderCwLabList(); renderCwImagingList();
    const missing = res.missing_fields || [];
    if (missing.length) {
      document.getElementById('cw-missing-alert').classList.remove('hidden');
      document.getElementById('cw-missing-list').textContent = missing.join(', ');
    } else {
      document.getElementById('cw-missing-alert').classList.add('hidden');
    }
    updateCwPreview(); cwGoToStep(3); hideLoader();

    // Show a Download PDF button in the preview panel
    const previewEl = document.getElementById('cw-preview');
    if (previewEl && currentConsultId) {
      const existingBtn = previewEl.querySelector('.cw-pdf-btn');
      if (!existingBtn) {
        const pdfBtnWrap = document.createElement('div');
        pdfBtnWrap.style.cssText = 'padding:1rem 1.25rem;border-top:1px solid var(--border);margin-top:0.5rem;';
        pdfBtnWrap.innerHTML = `
          <button class="btn-primary cw-pdf-btn" style="width:100%" onclick="exportConsultPDF('${currentConsultId}')">
            <svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:currentColor;margin-right:6px"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            Download OPD Summary PDF
          </button>`;
        previewEl.appendChild(pdfBtnWrap);
      }
    }

    toast(missing.length ? `⚠ AI filled fields — ${missing.length} item(s) need review.` : '✓ AI structured the consultation! Review and finalize.',
      missing.length ? 'error' : 'success', 5000);
  } catch (err) { hideLoader(); toast('Analysis failed: ' + err.message, 'error'); }
});

// ── Rx List ──────────────────────────────────────────────────────
function renderCwRxList() {
  const container = document.getElementById('cw-rx-list');
  if (!container) return;
  if (!cwPrescription.length) { container.innerHTML = '<em style="color:var(--text-muted);font-size:0.82rem">No drugs added yet</em>'; return; }
  container.innerHTML = cwPrescription.map((rx, i) => `
    <div class="rx-card">
      <div class="rx-card-header">
        <span class="rx-drug-name">💊 ${esc(rx.drug)}</span>
        <button class="rx-remove" onclick="cwRemoveRx(${i})">✕</button>
      </div>
      <div class="rx-fields">
        <input placeholder="Dose" value="${esc(rx.dose || '')}" oninput="cwPrescription[${i}].dose=this.value;updateCwPreview()" />
        <input placeholder="Route" value="${esc(rx.route || '')}" oninput="cwPrescription[${i}].route=this.value" />
        <input placeholder="Frequency" value="${esc(rx.frequency || '')}" oninput="cwPrescription[${i}].frequency=this.value;updateCwPreview()" />
        <input placeholder="Duration" value="${esc(rx.duration || '')}" oninput="cwPrescription[${i}].duration=this.value" />
      </div>
      <input placeholder="Notes (e.g. take after food)" value="${esc(rx.notes || '')}" oninput="cwPrescription[${i}].notes=this.value" />
    </div>`).join('');
}
function cwRemoveRx(i) { cwPrescription.splice(i, 1); renderCwRxList(); updateCwPreview(); }
document.getElementById('cw-add-drug-btn')?.addEventListener('click', () => {
  const drug = prompt('Drug name?'); if (!drug) return;
  cwPrescription.push({ drug, dose: '', route: '', frequency: '', duration: '', notes: '' });
  renderCwRxList(); updateCwPreview();
});

// ── Lab List ─────────────────────────────────────────────────────
function renderCwLabList() {
  const container = document.getElementById('cw-labs-list');
  if (!container) return;
  if (!cwLabTests.length) { container.innerHTML = '<em style="color:var(--text-muted);font-size:0.82rem">No tests added yet</em>'; return; }
  container.innerHTML = cwLabTests.map((lab, i) => `
    <div class="rx-card">
      <div class="rx-card-header">
        <span class="rx-drug-name">🔬 ${esc(lab.test_name)}</span>
        <button class="rx-remove" onclick="cwRemoveLab(${i})">✕</button>
      </div>
      <div class="rx-fields">
        <input placeholder="Urgency" value="${esc(lab.urgency || 'routine')}" oninput="cwLabTests[${i}].urgency=this.value" />
        <input placeholder="Reason" value="${esc(lab.reason || '')}" oninput="cwLabTests[${i}].reason=this.value" />
      </div>
    </div>`).join('');
}
function cwRemoveLab(i) { cwLabTests.splice(i, 1); renderCwLabList(); updateCwPreview(); }
document.getElementById('cw-add-lab-btn')?.addEventListener('click', () => {
  const test = prompt('Lab test name?'); if (!test) return;
  cwLabTests.push({ test_name: test, urgency: 'routine', reason: '' });
  renderCwLabList(); updateCwPreview();
});

// ── Imaging List ─────────────────────────────────────────────────
function renderCwImagingList() {
  const container = document.getElementById('cw-imaging-list');
  if (!container) return;
  if (!cwImaging.length) { container.innerHTML = '<em style="color:var(--text-muted);font-size:0.82rem">No imaging added yet</em>'; return; }
  container.innerHTML = cwImaging.map((img, i) => `
    <div class="rx-card">
      <div class="rx-card-header">
        <span class="rx-drug-name">🩻 ${esc(img.modality)} — ${esc(img.region || '')}</span>
        <button class="rx-remove" onclick="cwRemoveImaging(${i})">✕</button>
      </div>
      <input placeholder="Reason" value="${esc(img.reason || '')}" oninput="cwImaging[${i}].reason=this.value" />
    </div>`).join('');
}
function cwRemoveImaging(i) { cwImaging.splice(i, 1); renderCwImagingList(); updateCwPreview(); }
document.getElementById('cw-add-imaging-btn')?.addEventListener('click', () => {
  const mod = prompt('Modality (X-Ray, CT, USG, MRI…)?'); if (!mod) return;
  const region = prompt('Region (Chest, Abdomen…)?') || '';
  cwImaging.push({ modality: mod, region, reason: '' });
  renderCwImagingList(); updateCwPreview();
});

// ── Live preview ─────────────────────────────────────────────────
document.querySelectorAll('[id^="cw-rv-"]').forEach(el => {
  el.addEventListener('input', updateCwPreview);
  el.addEventListener('change', updateCwPreview);
});
function updateCwPreview() {
  const g = id => document.getElementById(id)?.value || '';
  const pv = v => v ? `<span class="preview-field-val">${esc(v)}</span>` : '<span class="preview-missing">Missing</span>';
  const rxP = cwPrescription.length
    ? cwPrescription.map(r => `<div class="preview-field"><span class="preview-field-key">💊</span><span>${esc(r.drug)} · ${esc(r.dose)} · ${esc(r.frequency)}</span></div>`).join('')
    : '<span class="preview-missing">None</span>';
  const labP = cwLabTests.length
    ? cwLabTests.map(l => `<div class="preview-field"><span class="preview-field-key">🔬</span><span>${esc(l.test_name)} (${esc(l.urgency || 'routine')})</span></div>`).join('')
    : '<span class="preview-missing">None</span>';
  const imgP = cwImaging.length
    ? cwImaging.map(i => `<div class="preview-field"><span class="preview-field-key">🩻</span><span>${esc(i.modality)} — ${esc(i.region)}</span></div>`).join('')
    : '<span class="preview-missing">None</span>';
  const el = document.getElementById('cw-preview');
  if (el) el.innerHTML = `
    <div class="preview-section"><div class="preview-section-title">🩺 Diagnosis</div>
      <div class="preview-field"><span class="preview-field-key">Primary</span>${pv(g('cw-rv-diagnosis'))}</div>
      <div class="preview-field"><span class="preview-field-key">Differential</span><span style="color:var(--text-secondary)">${esc(g('cw-rv-ddx')) || '—'}</span></div>
    </div>
    <div class="preview-section"><div class="preview-section-title">💊 Prescription</div>${rxP}</div>
    <div class="preview-section"><div class="preview-section-title">🔬 Lab Tests</div>${labP}</div>
    <div class="preview-section"><div class="preview-section-title">🩻 Imaging</div>${imgP}</div>
    <div class="preview-section"><div class="preview-section-title">📅 Follow-up</div>
      <div class="preview-field"><span class="preview-field-key">Date</span>${pv(g('cw-rv-followup-date'))}</div>
      <div class="preview-field"><span class="preview-field-key">Instructions</span>${pv(g('cw-rv-followup-inst'))}</div>
    </div>`;
}

// ── Save draft ────────────────────────────────────────────────────
document.getElementById('cw-save-draft-btn')?.addEventListener('click', async () => {
  if (!currentConsultId) { toast('No active consultation.', 'error'); return; }
  showLoader('Saving draft…');
  try {
    await api('PATCH', `/api/consultations/${currentConsultId}`, collectCwData());
    hideLoader(); toast('Draft saved.', 'success');
  } catch (err) { hideLoader(); toast(err.message, 'error'); }
});

function collectCwData() {
  const g = id => document.getElementById(id)?.value?.trim() || null;
  return {
    diagnosis: g('cw-rv-diagnosis'),
    differential_diagnosis: g('cw-rv-ddx'),
    history_of_present_illness: g('cw-rv-hpi'),
    examination_findings: g('cw-rv-exam'),
    prescription: cwPrescription,
    lab_tests: cwLabTests,
    imaging_ordered: cwImaging,
    follow_up_date: g('cw-rv-followup-date'),
    follow_up_instructions: g('cw-rv-followup-inst'),
    referral: g('cw-rv-referral'),
    lifestyle_advice: g('cw-rv-lifestyle'),
  };
}
function clearCwReviewFields() {
  ['cw-rv-diagnosis', 'cw-rv-ddx', 'cw-rv-hpi', 'cw-rv-exam',
    'cw-rv-followup-date', 'cw-rv-followup-inst', 'cw-rv-referral', 'cw-rv-lifestyle']
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
}

// ── Finalize ──────────────────────────────────────────────────────
document.getElementById('cw-finalize-btn')?.addEventListener('click', async () => {
  if (!currentConsultId) { toast('No active consultation.', 'error'); return; }
  if (!document.getElementById('cw-rv-diagnosis')?.value?.trim()) {
    toast('Primary Diagnosis is required before finalizing.', 'error'); return;
  }
  showLoader('Saving and finalizing consultation…');
  try {
    const savedId = currentConsultId;
    await api('PATCH', `/api/consultations/${savedId}`, collectCwData());
    await api('POST', `/api/consultations/${savedId}/finalize`);
    hideLoader();
    toast('✓ Consultation finalized! Downloading OPD PDF…', 'success', 4000);
    // Auto-download the OPD Summary PDF
    await exportConsultPDF(savedId);
    currentConsultId = null;
    navigate('consultations');
  } catch (err) { hideLoader(); toast(err.message, 'error'); }
});

