"""
Step 4 — Extract 5 hints per dinosaur.

Hints are ordered HARDEST → EASIEST:
  [0] Geological/stratigraphic detail — built from PBDB data (formation + Ma)
  [1] Specific anatomical feature     — Qwen from Wikipedia
  [2] Size, weight, and diet          — Qwen from Wikipedia
  [3] Geography and time period       — built from PBDB data (continent + interval)
  [4] Most famous / visually iconic   — Qwen from Wikipedia

PBDB data for hints 0 and 3 comes from ../data/pbdb_data.json (run 7_build_pbdb_data.py first).
For genera without PBDB data, Qwen generates all 5 hints from Wikipedia text.

Output: ../data/hints_cache/{name}.json
Resumes from checkpoint — safe to interrupt and re-run.
Failed entries logged to ../data/failed_hints.txt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BEFORE RUNNING: check your model name!
  Run:  ollama list
  Then set MODEL_NAME below to match exactly.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import requests
import json
import time
import os
import re

# ── Configuration ────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11435/v1/chat/completions"
MODEL_NAME = "qwen3.6-35b"

MAX_WIKI_CHARS  = 7000
RETRY_ATTEMPTS  = 3
RETRY_DELAY     = 3
REQUEST_TIMEOUT = 120

os.makedirs("../data/hints_cache", exist_ok=True)

# ── Load PBDB data ────────────────────────────────────────────────────────────
PBDB_DATA: dict = {}
pbdb_path = "../data/pbdb_data.json"
if os.path.exists(pbdb_path):
    with open(pbdb_path, encoding="utf-8") as f:
        PBDB_DATA = json.load(f)
    print(f"Loaded PBDB data for {len(PBDB_DATA)} genera.")
else:
    print("WARNING: ../data/pbdb_data.json not found — run 7_build_pbdb_data.py first.")
    print("         Qwen will generate all 5 hints from Wikipedia text.\n")

# ── Build PBDB-sourced hint strings ──────────────────────────────────────────
def build_hint0_pbdb(name: str) -> str | None:
    """Hint 0 — geological/stratigraphic. Returns None if insufficient data."""
    d = PBDB_DATA.get(name, {})
    formations = d.get("formations", [])
    max_ma     = d.get("max_ma")
    min_ma     = d.get("min_ma")

    parts = []
    if formations:
        # Use top 1-2 formations
        fm_str = " / ".join(formations[:2]) + " Formation"
        parts.append(fm_str)
    if max_ma is not None and min_ma is not None:
        parts.append(f"approximately {min_ma}–{max_ma} million years ago")
    elif max_ma is not None:
        parts.append(f"approximately {max_ma} million years ago")

    if not parts:
        return None
    return "Fossils recovered from the " + ", ".join(parts) + "."


def build_hint3_pbdb(name: str) -> str | None:
    """Hint 3 — geography and time period. Returns None if insufficient data."""
    d = PBDB_DATA.get(name, {})
    continents = d.get("continents", [])
    interval   = d.get("interval", "")

    if not continents and not interval:
        return None

    parts = []
    if continents:
        parts.append(", ".join(continents))
    if interval:
        parts.append(f"during the {interval}")

    return "This dinosaur lived in " + " ".join(parts) + "."


# ── Qwen prompts ──────────────────────────────────────────────────────────────
SYSTEM_3HINTS = (
    "You are a paleontology expert helping create a dinosaur guessing game.\n"
    "Given a Wikipedia article about a specific dinosaur, extract exactly 3 hints for players.\n\n"
    "RULES (strictly enforced):\n"
    "- NEVER mention the dinosaur's name, genus, or any word that gives it away by name.\n"
    "- Return hints in this exact order:\n"
    "    [0] A specific anatomical or morphological feature: a distinctive bone, "
    "        crest shape, horn count, armour type, tooth serration, etc.\n"
    "    [1] Body size and diet: approximate length, weight, and what it ate.\n"
    "    [2] The single most famous or visually iconic thing about this dinosaur "
    "        that a non-expert or child might recognise.\n"
    "- Return ONLY a valid JSON array of exactly 3 strings.\n"
    "- No markdown, no backticks, no explanation, no preamble."
)

SYSTEM_5HINTS = (
    "You are a paleontology expert helping create a dinosaur guessing game.\n"
    "Given a Wikipedia article about a specific dinosaur, extract exactly 5 hints for players.\n\n"
    "RULES (strictly enforced):\n"
    "- NEVER mention the dinosaur's name, genus, or any word that gives it away by name.\n"
    "- Order hints HARDEST → EASIEST as follows:\n"
    "    [0] A specific geological fact: formation name, exact age in million years, "
    "        and/or precise fossil locality.\n"
    "    [1] A specific anatomical or morphological feature: a distinctive bone, "
    "        crest shape, horn count, armour type, tooth serration, etc.\n"
    "    [2] Body size and diet: approximate length, weight, and what it ate.\n"
    "    [3] Geography and time period in plain language (continent, broad era).\n"
    "    [4] The single most famous or visually iconic thing about this dinosaur "
    "        that a non-expert or child might recognise.\n"
    "- Return ONLY a valid JSON array of exactly 5 strings.\n"
    "- No markdown, no backticks, no explanation, no preamble."
)

def build_user_msg(dino_name: str, wiki_text: str, n_hints: int) -> str:
    text = wiki_text[:MAX_WIKI_CHARS]
    noun = f"{n_hints}-hint" if n_hints != 5 else "5-hint"
    return (
        f"Wikipedia article: {dino_name}\n\n"
        f"{text}\n\n"
        f"Return the {noun} JSON array now."
    )

def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def parse_hints(raw: str, expected: int) -> list[str]:
    text = strip_thinking(raw).strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    hints = json.loads(text)
    if not isinstance(hints, list) or len(hints) != expected:
        raise ValueError(
            f"Expected list[{expected}], got: {type(hints).__name__} "
            f"len={len(hints) if isinstance(hints, list) else '?'}"
        )
    return [str(h).strip() for h in hints]

def call_ollama(dino_name: str, wiki_text: str, n_hints: int) -> list[str]:
    system = SYSTEM_3HINTS if n_hints == 3 else SYSTEM_5HINTS
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": build_user_msg(dino_name, wiki_text, n_hints)},
        ],
        "stream": False,
        "temperature": 0.25,
        "max_tokens": 512 if n_hints == 3 else 1024,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    return parse_hints(raw, n_hints)

# ── Main loop ─────────────────────────────────────────────────────────────────
with open("../data/dinosaurs_list.txt", encoding="utf-8") as f:
    names = [l.strip() for l in f if l.strip()]

total  = len(names)
failed = []

# Counters for summary
n_pbdb_hints  = 0   # genera where both hints 0+3 came from PBDB
n_full_qwen   = 0   # genera where Qwen did all 5
n_partial_qwen = 0  # genera where Qwen did only hints 1,2,4

print(f"Model: {MODEL_NAME}  |  {total} dinosaurs to process\n")

for i, name in enumerate(names, 1):
    safe = re.sub(r'[^\w\-]', '_', name)
    cache = f"../data/hints_cache/{safe}.json"

    # Check if cache already has PBDB-quality hints
    # We mark PBDB-sourced entries with a '__pbdb': true key.
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            cached = json.load(f)
        # If it's a list (old format), check if we should upgrade hints 0 & 3
        if isinstance(cached, list) and len(cached) == 5:
            h0_pbdb = build_hint0_pbdb(name)
            h3_pbdb = build_hint3_pbdb(name)
            if h0_pbdb or h3_pbdb:
                # Patch in PBDB data
                new_hints = list(cached)
                if h0_pbdb:
                    new_hints[0] = h0_pbdb
                if h3_pbdb:
                    new_hints[3] = h3_pbdb
                with open(cache, "w", encoding="utf-8") as f:
                    json.dump({"hints": new_hints, "__pbdb": True}, f,
                              ensure_ascii=False, indent=2)
                n_pbdb_hints += 1
                print(f"[{i}/{total}] {name}  ↻ patched hints 0/3 from PBDB")
            continue
        # Already upgraded dict format → skip
        if isinstance(cached, dict):
            continue

    raw_path = f"../data/raw_pages/{safe}.txt"
    if not os.path.exists(raw_path):
        print(f"[{i}/{total}] {name} — skipped (no Wikipedia text)")
        continue

    with open(raw_path, encoding="utf-8") as f:
        wiki_text = f.read()

    if len(wiki_text) < 150:
        print(f"[{i}/{total}] {name} — skipped (article too short)")
        continue

    # Build PBDB hints first
    h0_pbdb = build_hint0_pbdb(name)
    h3_pbdb = build_hint3_pbdb(name)
    use_pbdb = bool(h0_pbdb or h3_pbdb)

    print(f"[{i}/{total}] {name}", end="  ", flush=True)

    for attempt in range(RETRY_ATTEMPTS):
        try:
            if use_pbdb:
                # Ask Qwen for only 3 hints (anatomy, size/diet, famous fact)
                qwen3 = call_ollama(name, wiki_text, 3)
                hints = [
                    h0_pbdb or qwen3[0],   # 0: geological — prefer PBDB
                    qwen3[0],               # 1: anatomy
                    qwen3[1],               # 2: size/diet
                    h3_pbdb or qwen3[2],   # 3: geography — prefer PBDB
                    qwen3[2],               # 4: famous fact
                ]
                n_partial_qwen += 1
            else:
                hints = call_ollama(name, wiki_text, 5)
                n_full_qwen += 1

            entry = {"hints": hints, "__pbdb": use_pbdb}
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            print("✓")
            break

        except json.JSONDecodeError as e:
            msg = f"JSON error: {e}"
        except requests.exceptions.HTTPError as e:
            msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            msg = str(e)

        if attempt < RETRY_ATTEMPTS - 1:
            print(f"  retry {attempt + 1} ({msg})", end="  ", flush=True)
            time.sleep(RETRY_DELAY)
        else:
            print(f"  ✗ FAILED: {msg}")
            failed.append(name)

if failed:
    with open("../data/failed_hints.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(failed))
    print(f"\n{len(failed)} failures — see ../data/failed_hints.txt")
    print("Re-run this script to retry them (checkpoint is per-entry).")

print(f"\nPBDB patches applied: {n_pbdb_hints}")
print(f"New with PBDB hints:  {n_partial_qwen}")
print(f"New full-Qwen:        {n_full_qwen}")
print("\nDone!")
