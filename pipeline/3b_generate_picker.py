"""
Step 3b — Generate the image picker UI (picker.html).

Requires ../data/validity.json (run 6_flag_validity.py first).
Excludes nomen_dubium / synonym / unknown from the picker — no point
tagging images for dinosaurs that will never appear in the game.
Uncertain / disputed entries show a badge so you know they are rare-mode only.
"""
import json, os, re

ALWAYS_EXCLUDED = {"nomen_dubium", "synonym", "unknown"}

validity = {}
if os.path.exists("../data/validity.json"):
    with open("../data/validity.json", encoding="utf-8") as f:
        validity = json.load(f)
    print("Loaded validity.json — filtering out nomen_dubia, synonyms, unknowns.")
else:
    print("WARNING: ../data/validity.json not found — run 6_flag_validity.py first.")
    print("         Proceeding without filter (all genera included).\n")

with open("../data/dinosaurs_list.txt", encoding="utf-8") as f:
    names = [l.strip() for l in f if l.strip()]

dino_data = []
excluded = no_img = 0

for name in names:
    v = validity.get(name, "valid")
    if v in ALWAYS_EXCLUDED:
        excluded += 1
        continue
    safe = re.sub(r'[^\w\-]', '_', name)
    path = f"../data/image_lists/{safe}.json"
    imgs = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            imgs = json.load(f)
    dino_data.append({"name": name, "validity": v, "images": imgs})
    if not imgs:
        no_img += 1

print(f"Picker: {len(dino_data)} dinosaurs")
print(f"  valid={sum(1 for d in dino_data if d['validity']=='valid')}  "
      f"disputed={sum(1 for d in dino_data if d['validity']=='disputed')}  "
      f"uncertain={sum(1 for d in dino_data if d['validity']=='uncertain')}  "
      f"excluded(skipped)={excluded}  no_image={no_img}\n")

data_js = json.dumps(dino_data, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DinoGuess — Image Picker</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0e0d0c;--bg2:#181714;--bg3:#222020;
  --border:#2b2820;--border2:#3d3a32;
  --accent:#c9943a;--accent2:rgba(201,148,58,.18);
  --blue:#3b7fc4;--blue2:rgba(59,127,196,.2);
  --text:#e2dbd0;--muted:#736b5e;--hint:#9e9080;
  --green:#4a7c59;--green2:rgba(74,124,89,.2);
}
body{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif;font-size:14px;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{display:flex;align-items:center;gap:16px;padding:10px 16px;border-bottom:1px solid var(--border);flex-shrink:0}
.logo{font-family:Georgia,serif;font-size:20px;color:var(--accent);font-weight:700}
.progress{color:var(--muted);font-size:13px}
#prog-bar{flex:1;height:6px;background:var(--border2);border-radius:3px;overflow:hidden}
#prog-fill{height:100%;background:var(--accent);border-radius:3px;transition:width .3s}
.hdr-btn{padding:8px 16px;border-radius:7px;border:1px solid var(--border2);background:transparent;color:var(--text);cursor:pointer;font-size:13px;transition:.2s}
.hdr-btn:hover{border-color:var(--accent);color:var(--accent)}
.hdr-btn.primary{background:var(--accent);border-color:var(--accent);color:#111;font-weight:700}
.hdr-btn.primary:hover{opacity:.85}
.layout{display:flex;flex:1;overflow:hidden}

/* Sidebar */
.sidebar{width:230px;flex-shrink:0;border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
#search{padding:8px 12px;background:var(--bg3);border:none;border-bottom:1px solid var(--border);color:var(--text);font-size:13px;width:100%;outline:none}
#search::placeholder{color:var(--muted)}
.dino-list{flex:1;overflow-y:auto}
.dino-item{padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:7px;transition:background .15s}
.dino-item:hover{background:var(--bg3)}
.dino-item.active{background:var(--accent2);color:var(--accent)}
.dino-item .badge{font-size:11px;flex-shrink:0}
.dino-item .dname{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.validity-badge{font-size:9px;padding:1px 5px;border-radius:3px;flex-shrink:0;font-weight:700}
.vb-disputed{background:rgba(59,127,196,.25);color:#7ab4e8}
.vb-uncertain{background:rgba(201,148,58,.2);color:#d4a843}

/* Main panel */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.main-header{padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px;flex-shrink:0}
.main-header h2{font-size:18px;font-family:Georgia,serif;color:var(--accent)}
.nav-btns{display:flex;gap:6px;margin-left:auto}
.sel-status{display:flex;gap:10px;padding:8px 16px;border-bottom:1px solid var(--border);flex-shrink:0}
.sel-tag{padding:4px 12px;border-radius:5px;font-size:12px;font-weight:600;border:1px solid var(--border2);color:var(--muted)}
.sel-tag.art-set{background:var(--blue2);border-color:var(--blue);color:#7ab4e8}
.sel-tag.fossil-set{background:var(--accent2);border-color:var(--accent);color:var(--accent)}
.image-grid{flex:1;overflow-y:auto;padding:12px;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;align-content:start}
.img-card{background:var(--bg2);border:2px solid var(--border);border-radius:8px;overflow:hidden;transition:border-color .2s}
.img-card img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;cursor:pointer;transition:opacity .2s}
.img-card img:hover{opacity:.85}
.img-card .card-btns{display:flex;gap:6px;padding:7px}
.card-btn{flex:1;padding:5px;border:1px solid var(--border2);border-radius:5px;background:transparent;color:var(--muted);font-size:11px;font-weight:600;cursor:pointer;transition:.15s}
.card-btn:hover{border-color:var(--accent);color:var(--accent)}
.card-btn.art-sel{background:var(--blue2);border-color:var(--blue);color:#7ab4e8}
.card-btn.fossil-sel{background:var(--accent2);border-color:var(--accent);color:var(--accent)}
.img-card.is-art{border-color:var(--blue)}
.img-card.is-fossil{border-color:var(--accent)}
.img-name{font-size:10px;color:var(--hint);padding:0 7px 6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.empty-state{color:var(--muted);text-align:center;padding:40px;grid-column:1/-1}
.filter-bar{display:flex;gap:6px;padding:8px 16px;border-bottom:1px solid var(--border);flex-shrink:0}
.filt-btn{padding:4px 10px;border-radius:12px;border:1px solid var(--border2);background:transparent;color:var(--muted);font-size:11px;cursor:pointer;transition:.15s}
.filt-btn.active,.filt-btn:hover{border-color:var(--accent);color:var(--accent)}
</style>
</head>
<body>

<header>
  <div class="logo">🦕 DinoGuess — Image Picker</div>
  <div id="prog-bar"><div id="prog-fill" style="width:0%"></div></div>
  <div class="progress" id="prog-label">0 / 0 curated</div>
  <button class="hdr-btn" onclick="loadFile()">📂 Load selections.json</button>
  <button class="hdr-btn primary" onclick="saveSelections()">💾 Save selections.json</button>
</header>

<div class="layout">
  <div class="sidebar">
    <input id="search" type="text" placeholder="Search dinosaurs…" oninput="filterList(this.value)">
    <div class="dino-list" id="dino-list"></div>
  </div>

  <div class="main">
    <div class="main-header">
      <h2 id="dino-name">← Select a dinosaur</h2>
      <div class="nav-btns">
        <button class="hdr-btn" onclick="navigate(-1)">← Prev</button>
        <button class="hdr-btn" onclick="navigate(1)">Next →</button>
        <button class="hdr-btn" onclick="skipCurrent()" id="skip-btn">⏭ Skip</button>
      </div>
    </div>
    <div class="sel-status">
      <span class="sel-tag" id="art-tag">🎨 Art: —</span>
      <span class="sel-tag" id="fossil-tag">🦴 Fossil: —</span>
      <span style="color:var(--muted);font-size:12px;margin-left:8px">Click an image to cycle: untagged → Art → Fossil → untagged</span>
    </div>
    <div class="filter-bar">
      <span style="color:var(--muted);font-size:12px;margin-right:4px">Show:</span>
      <button class="filt-btn active" onclick="setFilter('all',this)">All</button>
      <button class="filt-btn" onclick="setFilter('todo',this)">Not done</button>
      <button class="filt-btn" onclick="setFilter('partial',this)">Partial</button>
      <button class="filt-btn" onclick="setFilter('done',this)">✅ Done</button>
      <button class="filt-btn" onclick="setFilter('skipped',this)">⏭ Skipped</button>
      <button class="filt-btn" onclick="setFilter('rare',this)">🔬❓ Rare only</button>
    </div>
    <div class="image-grid" id="image-grid">
      <div class="empty-state">Select a dinosaur from the sidebar.</div>
    </div>
  </div>
</div>

<input type="file" id="file-input" accept=".json" style="display:none" onchange="handleFileLoad(this)">

<script>
const DINOS = PLACEHOLDER_DATA;

let selections = {};   // {name: {art:{filename,url}, fossil:{filename,url}, skipped:bool}}
let currentIdx  = null;
let visibleIdxs = DINOS.map((_,i)=>i);
let filterMode  = 'all';
let searchQuery = '';

// ── Status helpers ─────────────────────────────────────────────────────────
function status(name) {
  const s = selections[name];
  if (!s) return 'todo';
  if (s.skipped) return 'skipped';
  const hasArt = !!s.art, hasFossil = !!s.fossil;
  if (hasArt && hasFossil) return 'done';
  if (hasArt || hasFossil) return 'partial';
  return 'todo';
}

function badge(st) {
  return {todo:'⭕', partial:'🟡', done:'✅', skipped:'⏭'}[st] || '⭕';
}

// ── Sidebar ────────────────────────────────────────────────────────────────
function buildVisible() {
  const q = searchQuery.toLowerCase();
  visibleIdxs = [];
  for (let i = 0; i < DINOS.length; i++) {
    const d = DINOS[i];
    if (q && !d.name.toLowerCase().includes(q)) continue;
    const st = status(d.name);
    const isRare = d.validity === 'disputed' || d.validity === 'uncertain';
    if (filterMode === 'rare' && !isRare) continue;
    else if (filterMode !== 'all' && filterMode !== 'rare' && st !== filterMode) continue;
    visibleIdxs.push(i);
  }
}

function renderList() {
  buildVisible();
  const el = document.getElementById('dino-list');
  const frag = document.createDocumentFragment();
  for (const idx of visibleIdxs) {
    const d  = DINOS[idx];
    const st = status(d.name);
    const div = document.createElement('div');
    div.className = 'dino-item' + (idx === currentIdx ? ' active' : '');
    div.setAttribute('data-idx', idx);
    const vbadge = d.validity === 'disputed'  ? '<span class="validity-badge vb-disputed">🔬</span>' :
                   d.validity === 'uncertain' ? '<span class="validity-badge vb-uncertain">❓</span>' : '';
    div.innerHTML = `<span class="badge">${badge(st)}</span><span class="dname">${d.name}</span>${vbadge}`;
    div.onclick = () => selectDino(idx);
    frag.appendChild(div);
  }
  el.innerHTML = '';
  el.appendChild(frag);
  updateProgress();
}

function filterList(q) {
  searchQuery = q;
  renderList();
}

function setFilter(mode, btn) {
  filterMode = mode;
  document.querySelectorAll('.filt-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderList();
}

// ── Select / navigate ──────────────────────────────────────────────────────
function selectDino(idx) {
  currentIdx = idx;
  renderList();
  renderImages();
}

function navigate(dir) {
  if (currentIdx === null) {
    if (visibleIdxs.length) selectDino(visibleIdxs[0]);
    return;
  }
  const pos = visibleIdxs.indexOf(currentIdx);
  const next = visibleIdxs[pos + dir];
  if (next !== undefined) selectDino(next);
}

function skipCurrent() {
  if (currentIdx === null) return;
  const name = DINOS[currentIdx].name;
  if (!selections[name]) selections[name] = {};
  selections[name].skipped = !selections[name].skipped;
  renderList();
  renderImages();
}

// ── Image grid ─────────────────────────────────────────────────────────────
function renderImages() {
  const grid = document.getElementById('image-grid');
  if (currentIdx === null) { grid.innerHTML = '<div class="empty-state">Select a dinosaur.</div>'; return; }

  const dino = DINOS[currentIdx];
  document.getElementById('dino-name').textContent = dino.name;

  const sel = selections[dino.name] || {};
  document.getElementById('skip-btn').textContent = sel.skipped ? '↩ Unskip' : '⏭ Skip';
  updateSelStatus(dino.name);

  if (!dino.images.length) {
    grid.innerHTML = '<div class="empty-state">No images found on Wikipedia for this dinosaur.</div>';
    return;
  }

  const frag = document.createDocumentFragment();
  for (const img of dino.images) {
    const artSel    = sel.art    && sel.art.filename    === img.filename;
    const fossilSel = sel.fossil && sel.fossil.filename === img.filename;

    const card = document.createElement('div');
    card.className = 'img-card' + (artSel ? ' is-art' : fossilSel ? ' is-fossil' : '');
    card.id = 'card-' + CSS.escape(img.filename);

    const imgEl = document.createElement('img');
    imgEl.src   = img.thumb || img.full;
    imgEl.alt   = img.filename;
    imgEl.loading = 'lazy';
    imgEl.onclick = () => cycleImage(dino.name, img);

    const btns = document.createElement('div');
    btns.className = 'card-btns';
    btns.innerHTML = `
      <button class="card-btn ${artSel?'art-sel':''}"    onclick="tagImage('${dino.name}','art','${esc(img.filename)}','${esc(img.full)}')">🎨 Art</button>
      <button class="card-btn ${fossilSel?'fossil-sel':''}" onclick="tagImage('${dino.name}','fossil','${esc(img.filename)}','${esc(img.full)}')">🦴 Fossil</button>`;

    const name = document.createElement('div');
    name.className = 'img-name';
    name.textContent = img.filename;

    card.append(imgEl, btns, name);
    frag.appendChild(card);
  }
  grid.innerHTML = '';
  grid.appendChild(frag);
}

function esc(s) { return s.replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }

function cycleImage(dinoName, img) {
  if (!selections[dinoName]) selections[dinoName] = {};
  const sel = selections[dinoName];
  const isArt    = sel.art    && sel.art.filename    === img.filename;
  const isFossil = sel.fossil && sel.fossil.filename === img.filename;
  if (!isArt && !isFossil) {
    // was untagged → set as art
    sel.art = {filename: img.filename, url: img.full};
  } else if (isArt) {
    // was art → set as fossil
    sel.art = null;
    sel.fossil = {filename: img.filename, url: img.full};
  } else {
    // was fossil → clear
    sel.fossil = null;
  }
  updateSelStatus(dinoName);
  renderImages();
}

function tagImage(dinoName, type, filename, url) {
  if (!selections[dinoName]) selections[dinoName] = {};
  const sel = selections[dinoName];
  // Toggle: if already this type, unset; otherwise set
  if (sel[type] && sel[type].filename === filename) {
    sel[type] = null;
  } else {
    sel[type] = {filename, url};
  }
  updateSelStatus(dinoName);
  renderImages();
}

function updateSelStatus(name) {
  const sel = selections[name] || {};
  const artTag    = document.getElementById('art-tag');
  const fossilTag = document.getElementById('fossil-tag');
  if (sel.art) {
    artTag.textContent = '🎨 Art: ' + sel.art.filename.split('/').pop().slice(0,30);
    artTag.className   = 'sel-tag art-set';
  } else {
    artTag.textContent = '🎨 Art: —';
    artTag.className   = 'sel-tag';
  }
  if (sel.fossil) {
    fossilTag.textContent = '🦴 Fossil: ' + sel.fossil.filename.split('/').pop().slice(0,30);
    fossilTag.className   = 'sel-tag fossil-set';
  } else {
    fossilTag.textContent = '🦴 Fossil: —';
    fossilTag.className   = 'sel-tag';
  }
}

// ── Progress ───────────────────────────────────────────────────────────────
function updateProgress() {
  let done = 0;
  for (const d of DINOS) {
    const st = status(d.name);
    if (st === 'done' || st === 'skipped' || st === 'partial') done++;
  }
  const total = DINOS.length;
  document.getElementById('prog-label').textContent = `${done} / ${total} curated`;
  document.getElementById('prog-fill').style.width  = (done/total*100).toFixed(1)+'%';
}

// ── Save / load ────────────────────────────────────────────────────────────
function saveSelections() {
  const blob = new Blob([JSON.stringify(selections, null, 2)], {type:'application/json'});
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = 'selections.json';
  a.click();
  URL.revokeObjectURL(a.href);
}

function loadFile() {
  document.getElementById('file-input').click();
}

function handleFileLoad(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      selections = JSON.parse(e.target.result);
      renderList();
      if (currentIdx !== null) renderImages();
      alert(`Loaded ${Object.keys(selections).length} selections.`);
    } catch { alert('Invalid JSON file.'); }
  };
  reader.readAsText(file);
}

// Keyboard shortcuts
document.addEventListener('keydown', e => {
  if (['INPUT'].includes(e.target.tagName)) return;
  if (e.key === 'ArrowRight' || e.key === 'd') navigate(1);
  if (e.key === 'ArrowLeft'  || e.key === 'a') navigate(-1);
  if (e.key === 's') skipCurrent();
});

// Init
renderList();
</script>
</body>
</html>
"""

# Embed data — use a placeholder swap so the JSON doesn't need escaping inside a string
html_out = HTML.replace('PLACEHOLDER_DATA', data_js)

outpath = "../picker.html"
with open(outpath, "w", encoding="utf-8") as f:
    f.write(html_out)

size_kb = os.path.getsize(outpath) // 1024
print(f"\nGenerated: {outpath}  ({size_kb} KB)")
print("Open it in a browser — no server needed.")
print("After tagging, click 'Save selections.json' → place that file in data/")
print("Then run:  python 3c_download_selected.py")
