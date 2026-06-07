'use strict';

// ── Config ────────────────────────────────────────────────────────────────────
const DB_URL    = 'dinosaurs.json';
const LS_PREFIX = 'dinoguess_daily_';

// ── State ─────────────────────────────────────────────────────────────────────
let db    = [];
let names = [];
let commonAliases = {};

// Pool sizes per difficulty level (index 0 = easiest)
const DIFF_POOLS = [15, 30, 50, 100, 300, 500, 700, 1000, Infinity];
const DIFF_LABELS = [
  'Top 15 most famous dinosaurs',
  'Top 30 most famous dinosaurs',
  'Top 50 most famous dinosaurs',
  'Top 100 most famous dinosaurs',
  'Top 300 dinosaurs',
  'Top 500 dinosaurs',
  'Top 700 dinosaurs',
  'Top 1000 dinosaurs',
  'All dinosaurs',
];

let settings = {
  mode:       'daily',
  difficulty: 0,      // index into DIFF_POOLS
  imagesOnly: true,
  maxGuesses: 5,
  startHints: 0,
};

// modes: 'daily' | 'expert' | 'choice'

let lobbyMode = 'daily';

let g = {
  dino:    null,
  guesses: [],
  wrong:   0,
  done:    false,
  won:     false,
  choices: [],
};

let ddItems = [];
let ddIdx   = -1;
let imgView  = 'art';

// ── Database filters ──────────────────────────────────────────────────────────
// Sort db once by fame: fame_score desc, n_occs as tiebreaker
let dbByFame = [];

function buildFameOrder() {
  dbByFame = [...db].sort((a, b) => {
    const fa = a.fame_score || 0, fb = b.fame_score || 0;
    if (fb !== fa) return fb - fa;
    return (b.n_occs || 0) - (a.n_occs || 0);
  });
}

function filteredDb() {
  const limit = DIFF_POOLS[settings.difficulty] ?? Infinity;
  // Take top-N by fame across ALL valid genera (including disputed at high diff)
  const includeAll = limit >= 700;
  let pool = includeAll
    ? dbByFame
    : dbByFame.filter(d => !d.validity || d.validity === 'valid');

  if (settings.imagesOnly) pool = pool.filter(d => d.image_art || d.image_fossil || d.image);

  // Apply pool size cap — but always include at least 'limit' entries
  if (isFinite(limit)) pool = pool.slice(0, limit);
  return pool;
}

function choiceDb() {
  return filteredDb().filter(d => d.casual);
}

function activePool() {
  return settings.mode === 'choice' ? choiceDb() : filteredDb();
}

// ── Boot ──────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    const r = await fetch(DB_URL);
    if (!r.ok) throw new Error(`HTTP ${r.status} — make sure you ran 5_build_db.py first`);
    db = await r.json();
    if (!db.length) throw new Error('dinosaurs.json is empty — run the pipeline scripts first');

    db.forEach(d => {
      if (d.common_name) commonAliases[d.common_name.toLowerCase()] = d.name;
    });

    buildFameOrder();
    loadSettings();
    syncLobby();
    showLobby();

  } catch (err) {
    document.body.innerHTML = `
      <div style="text-align:center;padding:60px 20px;color:#736b5e">
        <h2 style="color:#c9943a;margin-bottom:12px">⚠ Could not load dinosaurs.json</h2>
        <p style="margin-bottom:8px">Run the pipeline scripts first, then serve the site:</p>
        <code style="background:#181714;border:1px solid #2b2820;border-radius:6px;padding:2px 8px;color:#e8b96a">
          cd www &amp;&amp; python -m http.server 8000
        </code>
        <p style="margin-top:16px;font-size:12px">${err.message}</p>
      </div>`;
  }
}

function rebuildNames() {
  names = filteredDb().map(d => d.name);
}

// ── Settings persistence ──────────────────────────────────────────────────────
function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem('dinoguess_prefs') || '{}');
    settings = { ...settings, ...saved };
  } catch { /* ignore */ }
  lobbyMode = settings.mode;
}

function saveSettings() {
  try {
    localStorage.setItem('dinoguess_prefs', JSON.stringify(settings));
  } catch { /* ignore */ }
}

// ── Lobby ─────────────────────────────────────────────────────────────────────
function showLobby() {
  closeOverlay();
  el('lobby').style.display = 'flex';
  el('app').style.display   = 'none';
  lobbyMode = settings.mode;
  syncLobby();
}

function hideLobby() {
  el('lobby').style.display = 'none';
  el('app').style.display   = 'block';
}

function lobbySelectMode(mode) {
  lobbyMode = mode;
  ['daily', 'expert', 'choice'].forEach(m => {
    el(`lm-${m}`).classList.toggle('active', m === mode);
  });
}

function lobbyToggle(key) {
  settings[key] = !settings[key];
  const ids = { imagesOnly: 'tog-images' };
  const btn = el(ids[key]);
  if (btn) {
    btn.classList.toggle('on', settings[key]);
    btn.setAttribute('aria-checked', String(settings[key]));
  }
}

function lobbySetDifficulty(val) {
  settings.difficulty = val;
  const desc = el('diff-desc');
  if (desc) desc.textContent = DIFF_LABELS[val] ?? DIFF_LABELS[DIFF_LABELS.length - 1];
}

function lobbyChoose(key, value) {
  settings[key] = value;
  const ids = { maxGuesses: 'cho-guesses', startHints: 'cho-hints' };
  el(ids[key]).querySelectorAll('.ls-choice').forEach(btn => {
    btn.classList.toggle('active', Number(btn.textContent) === value);
  });
}

function lobbyPlay() {
  settings.mode = lobbyMode;
  saveSettings();
  rebuildNames();
  hideLobby();
  startGame();
}

function syncLobby() {
  lobbySelectMode(lobbyMode);

  const imgBtn = el('tog-images');
  if (imgBtn) {
    imgBtn.classList.toggle('on', settings.imagesOnly);
    imgBtn.setAttribute('aria-checked', String(settings.imagesOnly));
  }

  const slider = el('diff-slider');
  if (slider) slider.value = settings.difficulty;
  const desc = el('diff-desc');
  if (desc) desc.textContent = DIFF_LABELS[settings.difficulty] ?? DIFF_LABELS[DIFF_LABELS.length - 1];

  el('cho-guesses').querySelectorAll('.ls-choice').forEach(btn => {
    btn.classList.toggle('active', Number(btn.textContent) === settings.maxGuesses);
  });
  el('cho-hints').querySelectorAll('.ls-choice').forEach(btn => {
    btn.classList.toggle('active', Number(btn.textContent) === settings.startHints);
  });
}

// ── Game start ────────────────────────────────────────────────────────────────
function startGame() {
  const dino = pickDino(settings.mode);

  g = {
    dino,
    guesses: [],
    wrong:   0,
    done:    false,
    won:     false,
    choices: [],
  };

  if (settings.mode === 'daily') {
    const saved = loadDailyProgress(dino.name);
    if (saved) {
      g.guesses = saved.guesses;
      g.wrong   = saved.wrong;
      g.done    = saved.done;
      g.won     = saved.won;
    }
  }

  if (settings.mode === 'choice') {
    g.choices = buildChoices(dino);
  }

  imgView = 'art';
  closeOverlay();
  resetInput();
  render();

  if (g.done) setTimeout(showOverlay, 300);
}

// ── Dino selection ────────────────────────────────────────────────────────────
function pickDino(mode) {
  const pool = activePool();
  if (!pool.length) {
    const fallback = filteredDb();
    return fallback[Math.floor(Math.random() * fallback.length)];
  }
  if (mode === 'daily') return pool[dailyIndex(pool.length)];
  return pool[Math.floor(Math.random() * pool.length)];
}

function dailyIndex(total) {
  const now = new Date();
  const dayNum = Math.floor(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()) / 86400000
  );
  return dayNum % (total || activePool().length);
}

function dailyKey() {
  const now = new Date();
  return `${LS_PREFIX}${now.getUTCFullYear()}-${String(now.getUTCMonth()+1).padStart(2,'0')}-${String(now.getUTCDate()).padStart(2,'0')}`;
}

// ── Choice mode: build 4 options ─────────────────────────────────────────────
function buildChoices(correct) {
  const pool      = choiceDb().length ? choiceDb() : filteredDb();
  const sameClade = pool.filter(d => d.name !== correct.name && d.clade === correct.clade);
  const other     = pool.filter(d => d.name !== correct.name && d.clade !== correct.clade);
  const decoyPool = sameClade.length >= 3 ? sameClade : [...sameClade, ...other];
  const decoys    = shuffle(decoyPool).slice(0, 3);
  return shuffle([{ name: correct.name, correct: true }, ...decoys.map(d => ({ name: d.name, correct: false }))]);
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ── Daily progress ────────────────────────────────────────────────────────────
function saveDailyProgress() {
  if (settings.mode !== 'daily') return;
  try {
    localStorage.setItem(dailyKey(), JSON.stringify({
      dinoName: g.dino.name,
      guesses:  g.guesses,
      wrong:    g.wrong,
      done:     g.done,
      won:      g.won,
    }));
  } catch { /* ignore */ }
}

function loadDailyProgress(dinoName) {
  try {
    const raw = localStorage.getItem(dailyKey());
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (data.dinoName !== dinoName) return null;
    return data;
  } catch { return null; }
}

// ── Render ────────────────────────────────────────────────────────────────────
function render() {
  renderSubtitle();
  renderImage();
  renderHints();
  renderDots();
  renderGuesses();

  const isChoice = settings.mode === 'choice';
  el('input-area')    .style.display = isChoice ? 'none'  : 'block';
  el('casual-choices').style.display = isChoice ? 'block' : 'none';

  if (!isChoice) {
    el('submit-btn') .disabled = g.done;
    el('guess-input').disabled = g.done;
  } else {
    renderCasualChoices();
  }
}

function renderSubtitle() {
  const modeLabel = { daily: '📅 Daily', expert: '🎲 Expert', choice: '🌿 Choice' }[settings.mode] || '';
  const poolSize  = DIFF_POOLS[settings.difficulty];
  const diffLabel = isFinite(poolSize) ? `Top ${poolSize}` : 'All';
  const parts = [
    settings.mode === 'daily' ? `Day #${dailyIndex() + 1}` : modeLabel,
    diffLabel,
  ].filter(Boolean);
  el('day-label').textContent = parts.join(' · ');
}

function renderImage() {
  const showImg   = true;
  const dino      = g.dino;
  const imgArt    = dino?.image_art    || dino?.image || null;
  const imgFossil = dino?.image_fossil || null;
  const hasBoth   = !!(imgArt && imgFossil);

  const src = imgView === 'fossil' ? (imgFossil || imgArt) : (imgArt || imgFossil);

  el('dino-img')   .style.display = (showImg && !!src) ? 'block' : 'none';
  el('ph-no-image').style.display = (showImg && !src)  ? 'flex'  : 'none';
  el('ph-hidden')  .style.display = (!showImg)         ? 'flex'  : 'none';

  const toggle = el('img-toggle');
  toggle.style.display = (showImg && hasBoth) ? 'flex' : 'none';
  if (hasBoth) {
    el('btn-view-art')   .classList.toggle('active', imgView === 'art');
    el('btn-view-fossil').classList.toggle('active', imgView === 'fossil');
  }

  if (showImg && src) {
    const img = el('dino-img');
    if (img.getAttribute('data-src') !== src) {
      img.src = src;
      img.setAttribute('data-src', src);
    }
  }
}

function setImgView(view) {
  imgView = view;
  renderImage();
}

function renderHints() {
  let count;
  if (settings.mode === 'choice') {
    // Show all hints upfront in choice mode
    count = g.dino.hints.length;
  } else {
    count = Math.min(settings.startHints + g.wrong, g.dino.hints.length);
  }

  const section = el('hints-section');
  const list    = el('hints-list');
  section.style.display = count > 0 ? 'block' : 'none';

  // Clear if dino changed or count shrank (new game)
  const existing = list.querySelectorAll('.hint-card').length;
  if (list.dataset.dino !== g.dino.name) { list.innerHTML = ''; list.dataset.dino = g.dino.name; }
  if (list.querySelectorAll('.hint-card').length === count) return;

  list.innerHTML = '';
  for (let i = 0; i < count; i++) {
    const card = document.createElement('div');
    card.className = 'hint-card';
    card.innerHTML = `<span class="hint-n">${i+1}/5</span><span class="hint-text">${esc(g.dino.hints[i])}</span>`;
    list.appendChild(card);
  }
}

function renderDots() {
  const container = el('tries-dots');
  container.innerHTML = '';
  const limit = settings.mode === 'choice' ? 1 : settings.maxGuesses;
  for (let i = 0; i < limit; i++) {
    const d = document.createElement('span');
    d.className = 'dot';
    if (i < g.wrong)                   d.classList.add('used');
    else if (i === g.wrong && !g.done) d.classList.add('current');
    container.appendChild(d);
  }
}

function renderGuesses() {
  const list = el('guesses-list');
  if (list.dataset.dino !== g.dino.name) { list.innerHTML = ''; list.dataset.dino = g.dino.name; }
  const existing = list.querySelectorAll('.guess-item').length;
  for (let i = existing; i < g.guesses.length; i++) {
    const gu = g.guesses[i];
    const item = document.createElement('div');
    item.className = 'guess-item ' + (gu.correct ? 'correct' : 'wrong');
    item.innerHTML = `<span class="guess-icon">${gu.correct ? '✓' : '✗'}</span>${esc(gu.name)}`;
    list.appendChild(item);
  }
}

function renderCasualChoices() {
  const container = el('choice-btns');
  container.innerHTML = '';
  if (g.done) return;
  g.choices.forEach(({ name }) => {
    const btn = document.createElement('button');
    btn.className = 'choice-btn';
    btn.textContent = name;
    btn.onclick = () => submitGuess(name);
    container.appendChild(btn);
  });
}

// ── Guess logic ───────────────────────────────────────────────────────────────
function resolveGuess(raw) {
  const q = raw.trim().toLowerCase();
  if (!q) return null;
  const exact = names.find(n => n.toLowerCase() === q);
  if (exact) return exact;
  if (commonAliases[q]) return commonAliases[q];
  return null;
}

function submitGuess(name) {
  if (g.done || !name.trim()) return;

  const match = settings.mode === 'choice'
    ? name.trim()
    : resolveGuess(name);

  if (!match) { shakeInput(); return; }

  if (g.guesses.some(gu => gu.name.toLowerCase() === match.toLowerCase())) {
    shakeInput();
    return;
  }

  const correct = match.toLowerCase() === g.dino.name.toLowerCase();
  g.guesses.push({ name: match, correct });

  if (correct) {
    g.done = true;
    g.won  = true;
  } else {
    g.wrong++;
    const limit = settings.mode === 'choice' ? 1 : settings.maxGuesses;
    if (g.wrong >= limit) {
      g.done = true;
      g.won  = false;
    }
  }

  saveDailyProgress();
  render();
  if (g.done) setTimeout(showOverlay, 700);
}

function submitFromInput() {
  const raw = el('guess-input').value.trim();
  if (ddIdx >= 0 && ddItems[ddIdx]) {
    submitGuess(ddItems[ddIdx]);
  } else {
    submitGuess(raw);
  }
  resetInput();
}

// ── Autocomplete ──────────────────────────────────────────────────────────────
function onInput(value) {
  ddIdx = -1;
  if (!value.trim()) { closeDropdown(); return; }
  ddItems = filterNames(value);
  renderDropdown();
}

function filterNames(query) {
  const q = query.toLowerCase().trim();
  const aliasMatch = commonAliases[q];
  const starts   = names.filter(n => n.toLowerCase().startsWith(q));
  const contains = names.filter(n => !n.toLowerCase().startsWith(q) && n.toLowerCase().includes(q));
  let results    = [...starts, ...contains];
  if (aliasMatch && !results.find(n => n.toLowerCase() === aliasMatch.toLowerCase())) {
    results = [aliasMatch, ...results];
  }
  return results.slice(0, 8);
}

function renderDropdown() {
  const dd = el('dropdown');
  dd.innerHTML = '';
  if (!ddItems.length) { dd.classList.remove('open'); return; }

  ddItems.forEach((name, i) => {
    const item = document.createElement('div');
    item.className = 'dd-item';
    item.role = 'option';
    item.setAttribute('data-i', i);
    const dino = db.find(d => d.name === name);
    const label = dino?.common_name ? `${name} <span class="dd-alias">(${dino.common_name})</span>` : name;
    item.innerHTML = label;
    item.onmousedown = e => {
      e.preventDefault();
      el('guess-input').value = name;
      closeDropdown();
      submitGuess(name);
      resetInput();
    };
    dd.appendChild(item);
  });

  dd.classList.add('open');
}

function closeDropdown() {
  ddItems = [];
  ddIdx   = -1;
  const dd = el('dropdown');
  dd.innerHTML = '';
  dd.classList.remove('open');
}

function highlightDd() {
  el('dropdown').querySelectorAll('.dd-item').forEach((item, i) => {
    item.classList.toggle('hi', i === ddIdx);
  });
}

function onKeyDown(e) {
  const dd   = el('dropdown');
  const open = dd.classList.contains('open');
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (!open) return;
    ddIdx = Math.min(ddIdx + 1, ddItems.length - 1);
    highlightDd();
    el('guess-input').value = ddItems[ddIdx] ?? el('guess-input').value;
    return;
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (!open) return;
    ddIdx = Math.max(ddIdx - 1, -1);
    highlightDd();
    if (ddIdx >= 0) el('guess-input').value = ddItems[ddIdx];
    return;
  }
  if (e.key === 'Enter')  { e.preventDefault(); submitFromInput(); return; }
  if (e.key === 'Escape') { closeDropdown(); return; }
}

document.addEventListener('click', e => {
  if (!e.target.closest('.input-area')) closeDropdown();
});

// ── Game-over overlay ─────────────────────────────────────────────────────────
function showOverlay() {
  const dino = g.dino;

  const validityBadge = { disputed: '🔬 Disputed genus', uncertain: '❓ Uncertain validity' };
  const badge   = validityBadge[dino.validity] || '';
  const badgeEl = el('overlay-validity');
  if (badgeEl) { badgeEl.textContent = badge; badgeEl.style.display = badge ? 'block' : 'none'; }

  const limit = settings.mode === 'choice' ? 1 : settings.maxGuesses;
  el('overlay-result').textContent = g.won
    ? (g.wrong === 0 ? '🏆 Perfect score!' : `🎉 Got it in ${g.wrong + 1}/${limit}`)
    : '😔 Game over — it was…';

  el('overlay-name').textContent = dino.name;

  const commonEl = el('overlay-common');
  if (commonEl) {
    if (dino.common_name) { commonEl.textContent = `"${dino.common_name}"`; commonEl.style.display = 'block'; }
    else commonEl.style.display = 'none';
  }

  const img     = el('overlay-img');
  const bestImg = dino.image_art || dino.image_fossil || dino.image || null;
  if (bestImg) { img.src = bestImg; img.style.display = 'block'; }
  else         { img.style.display = 'none'; }

  const overlayFossil = el('overlay-fossil-img');
  if (overlayFossil) {
    if (dino.image_fossil && dino.image_art) {
      overlayFossil.src = dino.image_fossil;
      overlayFossil.style.display = 'block';
    } else {
      overlayFossil.style.display = 'none';
    }
  }

  el('overlay-hints').innerHTML = dino.hints
    .map((h, i) => `<div class="overlay-hint"><strong>${i+1}/5</strong>&nbsp; ${esc(h)}</div>`)
    .join('');

  el('share-msg').style.display = 'none';
  el('overlay').classList.add('open');
  renderImage();
}

function closeOverlay() {
  el('overlay').classList.remove('open');
}

function newGame() {
  closeOverlay();
  if (settings.mode === 'expert' || settings.mode === 'choice') {
    startGame();
  }
}

// ── Share ─────────────────────────────────────────────────────────────────────
function shareResult() {
  const grid      = g.guesses.map(gu => gu.correct ? '🟩' : '🟥').join('');
  const score     = g.won ? `${g.wrong + 1}/${settings.maxGuesses}` : `X/${settings.maxGuesses}`;
  const modeEmoji = { daily: '📅', expert: '🎲', choice: '🌿' }[settings.mode] || '🎲';
  const text = [
    `🦕 DinoGuess ${modeEmoji}${settings.hard ? '💀' : ''}`,
    settings.mode === 'daily' ? `Day #${dailyIndex() + 1}` : settings.mode === 'choice' ? 'Choice' : 'Expert',
    `${grid} ${score}`,
    window.location.href,
  ].join('\n');

  navigator.clipboard.writeText(text).then(() => {
    const msg = el('share-msg');
    msg.style.display = 'block';
    setTimeout(() => { msg.style.display = 'none'; }, 2500);
  }).catch(() => {
    prompt('Copy your result:', text);
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function el(id)   { return document.getElementById(id); }
function esc(str) { return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function shakeInput() {
  const inp = el('guess-input');
  inp.classList.remove('shake');
  void inp.offsetWidth;
  inp.classList.add('shake');
  setTimeout(() => inp.classList.remove('shake'), 450);
}

function resetInput() {
  el('guess-input').value = '';
  closeDropdown();
}

boot();
