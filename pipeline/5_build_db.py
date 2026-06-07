"""
Step 5 — Assemble www/dinosaurs.json.

Reads:
  ../data/validity_final.json   (from 6c — PBDB-primary merged)
  ../data/hints_cache/{name}.json
  ../data/pbdb_data.json         (from 7 — fame_rank, casual, clade)
  ../data/images/
  ../data/raw_pages/             (for clade detection from Wikipedia text)
"""
import os, json, re, shutil

os.makedirs("../www/images", exist_ok=True)
EXTS = ("jpg", "jpeg", "png", "webp")

def safe(name):
    return re.sub(r'[^\w\-]', '_', name)

def find_image(safe_name, suffix=""):
    for ext in EXTS:
        src  = f"../data/images/{safe_name}{suffix}.{ext}"
        if os.path.exists(src):
            dest = f"../www/images/{safe_name}{suffix}.{ext}"
            if not os.path.exists(dest):
                shutil.copy2(src, dest)
            return f"images/{safe_name}{suffix}.{ext}"
    return None

# ── Validity — PBDB-primary merged ───────────────────────────────────────────
validity = {}
for fname in ("../data/validity_final.json", "../data/validity.json"):
    if os.path.exists(fname):
        with open(fname, encoding="utf-8") as f:
            validity = json.load(f)
        print(f"Using validity source: {fname}")
        break
else:
    print("WARNING: no validity file found — all entries marked valid.")

# ── PBDB data ─────────────────────────────────────────────────────────────────
pbdb_data: dict = {}
if os.path.exists("../data/pbdb_data.json"):
    with open("../data/pbdb_data.json", encoding="utf-8") as f:
        pbdb_data = json.load(f)

# ── Clade detection from Wikipedia text ──────────────────────────────────────
CLADE_PATTERNS = [
    ("Ceratopsia",       ["ceratopsian","ceratopsia","ceratopsidae","ceratopsid","neoceratopsia"]),
    ("Sauropoda",        ["sauropod","titanosaur","diplodocid","brachiosaurid","macronaria"]),
    ("Ankylosauria",     ["ankylosaur","nodosaur","ankylosauria"]),
    ("Stegosauria",      ["stegosaur"]),
    ("Ornithopoda",      ["hadrosaur","hadrosaurid","ornithopod","iguanodont","hypsilophodont"]),
    ("Pachycephalosauria",["pachycephalosaur"]),
    ("Tyrannosauridae",  ["tyrannosaurid","tyrannosauroid"]),
    ("Dromaeosauridae",  ["dromaeosaurid","velociraptorine","eudromaeosauria"]),
    ("Troodontidae",     ["troodontid"]),
    ("Oviraptorosauria", ["oviraptorosaur","oviraptorid","caenagnathid"]),
    ("Spinosauridae",    ["spinosaurid"]),
    ("Abelisauridae",    ["abelisaurid"]),
    ("Allosauridae",     ["allosaurid","allosauroid","carnosaurid"]),
    ("Coelurosauria",    ["coelurosaur","maniraptora","compsognathid"]),
    ("Theropoda",        ["theropod"]),
    ("Ornithischia",     ["ornithischian","ornithischia"]),
]

_clade_cache: dict[str, str] = {}

def detect_clade(name: str) -> str:
    if name in _clade_cache:
        return _clade_cache[name]
    path = f"../data/raw_pages/{safe(name)}.txt"
    if not os.path.exists(path):
        _clade_cache[name] = "Unknown"
        return "Unknown"
    with open(path, encoding="utf-8") as f:
        lead = f.read(2000).lower()
    for clade, keywords in CLADE_PATTERNS:
        if any(k in lead for k in keywords):
            _clade_cache[name] = clade
            return clade
    _clade_cache[name] = "Unknown"
    return "Unknown"

# ── Common names — small hand-curated dict ────────────────────────────────────
# Add more as needed. These are shown in the answer reveal overlay and
# accepted as autocomplete aliases when typing.
COMMON_NAMES: dict[str, str] = {
    "Tyrannosaurus":       "T. rex",
    "Triceratops":         "Triceratops",
    "Brachiosaurus":       "Brachiosaurus",
    "Stegosaurus":         "Stegosaurus",
    "Velociraptor":        "Velociraptor",
    "Ankylosaurus":        "Ankylosaurus",
    "Pteranodon":          "Pteranodon",
    "Diplodocus":          "Diplodocus",
    "Allosaurus":          "Allosaurus",
    "Spinosaurus":         "Spinosaurus",
    "Pachycephalosaurus":  "Bonehead",
    "Parasaurolophus":     "Duckbill",
    "Iguanodon":           "Iguanodon",
    "Apatosaurus":         "Apatosaurus",
    "Brontosaurus":        "Thunder lizard",
    "Carnotaurus":         "Carnotaurus",
    "Dilophosaurus":       "Dilophosaurus",
    "Oviraptor":           "Egg thief",
    "Maiasaura":           "Good mother lizard",
    "Hadrosaurus":         "Duck-billed dinosaur",
}

# ── Main build loop ───────────────────────────────────────────────────────────
with open("../data/dinosaurs_list.txt", encoding="utf-8") as f:
    names = [l.strip() for l in f if l.strip()]

database  = []
no_hints  = 0
excluded  = 0

for name in names:
    s = safe(name)

    hints_path = f"../data/hints_cache/{s}.json"
    if not os.path.exists(hints_path):
        no_hints += 1
        continue

    with open(hints_path, encoding="utf-8") as f:
        raw = json.load(f)

    # Support both old (list) and new (dict with 'hints' key) formats
    if isinstance(raw, list):
        hints = raw
    elif isinstance(raw, dict) and "hints" in raw:
        hints = raw["hints"]
    else:
        no_hints += 1
        continue

    v = validity.get(name, "valid")

    if v in ("nomen_dubium", "synonym", "unknown", "unknown_pbdb"):
        excluded += 1
        continue

    img_art    = find_image(s, "_art")
    img_fossil = find_image(s, "_fossil")
    if not img_art and not img_fossil:
        img_art = find_image(s)

    pd = pbdb_data.get(name, {})

    entry = {
        "name":         name,
        "validity":     v,
        "image":        img_art or img_fossil,
        "image_art":    img_art,
        "image_fossil": img_fossil,
        "hints":        hints,
        "fame_rank":    pd.get("fame_rank", 0),
        "casual":       pd.get("casual", False),
        "clade":        detect_clade(name),
        "continents":   pd.get("continents", []),
        "interval":     pd.get("interval", ""),
    }

    common = COMMON_NAMES.get(name)
    if common:
        entry["common_name"] = common

    database.append(entry)

out = "../www/dinosaurs.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(database, f, ensure_ascii=False, separators=(",", ":"))

size_kb    = os.path.getsize(out) // 1024
n_valid    = sum(1 for d in database if d["validity"] == "valid")
n_disputed = sum(1 for d in database if d["validity"] == "disputed")
n_uncertain= sum(1 for d in database if d["validity"] == "uncertain")
with_img   = sum(1 for d in database if d["image"])
n_casual   = sum(1 for d in database if d["casual"])

print("=" * 50)
print(f"  Output:        {out}  ({size_kb} KB)")
print(f"  ✅ valid:       {n_valid}")
print(f"  🔬 disputed:    {n_disputed}")
print(f"  ❓ uncertain:   {n_uncertain}")
print(f"  ❌ excluded:    {excluded}")
print(f"  ─ no hints:    {no_hints}")
print(f"  With image:    {with_img}")
print(f"  🌿 casual pool: {n_casual}")
print("=" * 50)
