'use strict';

// ── Config ───────────────────────────────────────────────────────────────────
const MAX_TRIES  = 5;
const DB_URL     = 'dinosaurs.json';
const LS_PREFIX  = 'dinoguess_daily_';

// ── State ────────────────────────────────────────────────────────────────────
let db    = [];   // all dinosaur entries from JSON
let names = [];   // lowercase names for autocomplete (normal modes)

// common-name → genus name map  (e.g. "t. rex" → "Tyrannosaurus")
let commonAliases = {};   // lower(alias) → canonical name

let g = {
  dino:    null,   // { name, validity, image, image_art, image_fossil, hints[], casual, clade, common_name? }
  mode:    'daily',
  hard:    false,
  guesses: [],
  wrong:   0,
  done:    false,
  won:     false,
  choices: [],    // casual mode: [{name, correct}]
};

let ddItems = [];
let ddIdx   = -1;
let imgView  = 'art';
let rareMode = false;

// ── Filtered database ─────────────────────────────────────────────────────────
function filteredDb() {
  let pool = db;
  if (!rareMode) pool = pool.filter(d => !d.validity || d.validity === 'valid');
  return pool;
}

function casualDb() {
  return filteredDb().filter(d => d.casual);
}

function activePool() {
  return g.mode === 'casual' ? casualDb() : filteredDb();
}

// ── Boot ──────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    const r = await fetch(DB_URL);
    if (!r.ok) throw new Error(`HTTP ${r.status} — make sure you ran 5_build_db.py first`);
    db = await r.json();

    if (!db.length) throw new Error('dinosaurs.json is empty — run the pipeline scripts first');

    // Build common-name alias map
    db.forEach(d => {
      if (d.common_name) {
        commonAliases[d.common_name.toLowerCase()] = d.name;
      }
    });

    rebuildNames();
    applyStoredMode();
    startGame();

  } catch (err) {
    document.getElementById('app').innerHTML = `
      <div class="loading-screen">
        <h2>⚠ Could not load dinosaurs.json</h2>
        <p style="margin:10px 0 6px">Run the pipeline scripts first, then serve the site:</p>
        <code>cd www &amp;&amp; python -m http.server 8000</code>
        <p style="margin-top:12px;font-size:12px;color:#5a5248">${err.message}</p>
      </div>`;
  }
}

function rebuildNames() {
  names = filteredDb().map(d => d.name);
}

// ── Mode persistence ──────────────────────────────────────────────────────────
function applyStoredMode() {
  try {
    const saved = JSON.parse(localStorage.getItem('dinoguess_prefs') || '{}');
    g.mode   = saved.mode  || 'daily';
    g.hard   = saved.hard  || false;
    rareMode = saved.rare  || false;
  } catch { /* ignore */ }
  syncModeBtns();
}

function savePrefs() {
  try {
    localStorage.setItem('dinoguess_prefs',
      JSON.stringify({ mode: g.mode, hard: g.hard, rare: rareMode }));
  } catch { /* ignore */ }
}

// ── Game start ────────────────────────────────────────────────────────────────
function startGame() {
  const dino = pickDino(g.mode);

  g = {
    dino,
    mode:    g.mode,
    hard:    g.hard,
    guesses: [],
    wrong:   0,
    done:    false,
    won:     false,
    choices: [],
  };

  if (g.mode === 'daily') {
    const saved = loadDailyProgress(dino.name);
    if (saved) {
      g.guesses = saved.guesses;
      g.wrong   = saved.wrong;
      g.done    = saved.done;
      g.won     = saved.won;
    }
  }

  if (g.mode === 'casual') {
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
    // Fallback: casual pool empty → use full filtered db
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

// ── Casual mode: build 4 multiple-choice options ──────────────────────────────
function buildChoices(correct) {
  const pool = casualDb().length ? casualDb() : filteredDb();

  // Pick 3 decoys from same clade; fall back to random pool
  const sameClade = pool.filter(d => d.name !== correct.name && d.clade === correct.clade);
  const other     = pool.filter(d => d.name !== correct.name && d.clade !== correct.clade);

  const decoyPool = sameClade.length >= 3 ? sameClade : [...sameClade, ...other];
  const decoys    = shuffle(decoyPool).slice(0, 3);

  const all = shuffle([{ name: correct.name, correct: true }, ...decoys.map(d => ({ name: d.name, correct: false }))]);
  return all;
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
  if (g.mode !== 'daily') return;
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

// ── Mode controls ─────────────────────────────────────────────────────────────
function setMode(mode) {
  g.mode = mode;
  closeOverlay();
  syncModeBtns();
  savePrefs();
  rebuildNames();
  startGame();
}

function toggleHard() {
  g.hard = !g.hard;
  syncModeBtns();
  savePrefs();
  startGame();
}

function toggleRare() {
  rareMode = !rareMode;
  syncModeBtns();
  savePrefs();
  rebuildNames();
  startGame();
}

function syncModeBtns() {
  el('btn-daily') .classList.toggle('active', g.mode === 'daily');
  el('btn-random').classList.toggle('active', g.mode === 'random');
  el('btn-casual').classList.toggle('active', g.mode === 'casual');
  el('btn-hard')  .classList.toggle('active', g.hard);
  const rareBtn = el('btn-rare');
  if (rareBtn) rareBtn.classList.toggle('active', rareMode);
}

function newGame() {
  if (g.mode === 'random' || g.mode === 'casual') {
    startGame();
  } else {
    closeOverlay();
  }
}

// ── Render ─────────────────────────────────────────────────────────────────────
function render() {
  renderSubtitle();
  renderImage();
  renderHints();
  renderDots();
  renderGuesses();

  const isCasual = g.mode === 'casual';
  el('input-area')     .style.display = isCasual ? 'none'  : 'block';
  el('casual-choices') .style.display = isCasual ? 'block' : 'none';

  if (!isCasual) {
    el('submit-btn') .disabled = g.done;
    el('guess-input').disabled = g.done;
  } else {
    renderCasualChoices();
  }
}

function renderSubtitle() {
  const label = g.mode === 'casual' ? 'Casual 🌿'
              : g.mode === 'daily'  ? `Day #${(dailyIndex() + 1)}`
              : 'Random';
  el('day-label').textContent = label + (g.hard ? ' · Hard Mode 💀' : '');
}

function renderImage() {
  const showImg   = !g.hard || g.done;
  const dino      = g.dino;
  const imgArt    = dino?.image_art    || dino?.image || null;
  const imgFossil = dino?.image_fossil || null;
  const hasBoth   = !!(imgArt && imgFossil);

  const src = imgView === 'fossil' ? (imgFossil || imgArt) : (imgArt || imgFossil);

  el('dino-img')    .style.display = (showImg && !!src)  ? 'block' : 'none';
  el('ph-no-image') .style.display = (showImg && !src)   ? 'flex'  : 'none';
  el('ph-hidden')   .style.display = (!showImg)          ? 'flex'  : 'none';

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
  // Normal: 0 hints at start; Hard: 1 hint at start; Casual: always show 2 hints
  let count;
  if (g.mode === 'casual') {
    count = Math.min(2 + g.wrong, g.dino.hints.length);
  } else {
    count = Math.min(g.hard ? g.wrong + 1 : g.wrong, g.dino.hints.length);
  }

  const section = el('hints-section');
  const list    = el('hints-list');

  section.style.display = count > 0 ? 'block' : 'none';

  const existing = list.querySelectorAll('.hint-card').length;
  if (existing === count) return;

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
  for (let i = 0; i < MAX_TRIES; i++) {
    const d = document.createElement('span');
    d.className = 'dot';
    if (i < g.wrong)                   d.classList.add('used');
    else if (i === g.wrong && !g.done) d.classList.add('current');
    container.appendChild(d);
  }
}

function renderGuesses() {
  const list = el('guesses-list');
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

  // 1. Exact match against genus names
  const exact = names.find(n => n.toLowerCase() === q);
  if (exact) return exact;

  // 2. Common-name alias  (e.g. "t. rex" → "Tyrannosaurus")
  if (commonAliases[q]) return commonAliases[q];

  return null;
}

function submitGuess(name) {
  if (g.done || !name.trim()) return;

  // In casual mode bypass validation — buttons only contain valid names
  const match = g.mode === 'casual'
    ? name.trim()
    : resolveGuess(name);

  if (!match) { shakeInput(); return; }

  // Prevent duplicate guesses
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
    if (g.wrong >= MAX_TRIES) {
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

  // Check if it matches a common alias — prepend the resolved genus
  const aliasMatch = commonAliases[q];

  const starts   = names.filter(n => n.toLowerCase().startsWith(q));
  const contains = names.filter(n => !n.toLowerCase().startsWith(q) && n.toLowerCase().includes(q));
  let results    = [...starts, ...contains];

  // If alias resolves to a genus not already in results, prepend it
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
    // Show common name hint in dropdown if applicable
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
  if (e.key === 'Enter') { e.preventDefault(); submitFromInput(); return; }
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

  el('overlay-result').textContent = g.won
    ? (g.wrong === 0 ? '🏆 Perfect score!' : `🎉 Got it in ${g.wrong + 1}/${MAX_TRIES}${g.hard ? ' · Hard' : ''}`)
    : '😔 Game over — it was…';

  el('overlay-name').textContent = dino.name;

  // Common name below genus
  const commonEl = el('overlay-common');
  if (commonEl) {
    if (dino.common_name) {
      commonEl.textContent = `"${dino.common_name}"`;
      commonEl.style.display = 'block';
    } else {
      commonEl.style.display = 'none';
    }
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

// ── Share ─────────────────────────────────────────────────────────────────────
function shareResult() {
  const grid  = g.guesses.map(gu => gu.correct ? '🟩' : '🟥').join('');
  const score = g.won ? `${g.wrong + 1}/${MAX_TRIES}` : `X/${MAX_TRIES}`;
  const mode  = [
    g.mode === 'daily'  ? '📅' : g.mode === 'casual' ? '🌿' : '🎲',
    g.hard ? '💀' : '',
  ].filter(Boolean).join('');

  const text = [
    `🦕 DinoGuess ${mode}`,
    g.mode === 'daily' ? `Day #${dailyIndex() + 1}` : g.mode === 'casual' ? 'Casual' : 'Random',
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

// ── Start ─────────────────────────────────────────────────────────────────────
boot();
