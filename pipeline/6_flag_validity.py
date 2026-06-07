"""
Step 6 — Scan raw Wikipedia text and flag validity status for each genus.

Output: ../data/validity.json

Statuses (in priority order):
  nomen_dubium  — explicitly dubious / indistinguishable  → ALWAYS EXCLUDED
  synonym       — junior synonym of another genus         → ALWAYS EXCLUDED
  disputed      — validity actively debated               → included with "rare" toggle
  uncertain     — fragmentary / possibly invalid          → included with "rare" toggle
  valid         — no dubious markers found                → always included
  unknown       — no Wikipedia text found                 → ALWAYS EXCLUDED
"""
import re, json, os

RAW_DIR = "../data/raw_pages"

# ── Detection patterns ───────────────────────────────────────────────────────
# Ordered by priority. First tier that matches wins.
TIERS = [
    ("nomen_dubium", [
        r'\bnomen\s+dubi[ua]\b',
        r'\bnomina\s+dubi[ua]\b',
        r'\bconsidered\s+(?:to\s+be\s+)?dubious\b',
        r'\bregarded\s+as\s+(?:a\s+)?dubious\b',
        r'\bremains?\s+(?:a\s+)?dubious\b',
        r'\bspecies\s+(?:(?:is|are|was|were)\s+)?(?:both\s+)?(?:considered\s+)?dubious\b',
        r'\bhas\s+been\s+considered\s+(?:a\s+)?nomen',
    ]),
    ("synonym", [
        # Present-tense only — "was considered a synonym" is historical context (e.g. Brontosaurus)
        r'\bis\s+(?:now\s+|currently\s+)?(?:a\s+)?(?:junior\s+)?synonym\s+of\b',
        r'\bis\s+(?:now\s+)?(?:considered|regarded)\s+(?:a\s+)?(?:junior\s+)?synonym\b',
        r'\bhas\s+been\s+synonymized\s+with\b',
    ]),
    ("disputed", [
        r'\bvalidity\s+(?:is|has\s+been|remains?)\s+(?:highly\s+)?disputed\b',
        r'\bvalidity\s+(?:is|has\s+been)\s+questioned\b',
        r'\bcontroversial\s+(?:genus|taxon|species)\b',
        r'\bwhether\s+.{0,80}(?:valid|separate)\s+(?:genus|species|taxon)\b',
        r'\blong-?standing\s+(?:scientific\s+)?controversy\b',
    ]),
    ("uncertain", [
        r'\bvalidity\s+(?:is|remains?)\s+uncertain\b',
        r'\bof\s+(?:uncertain|questionable|doubtful)\s+validity\b',
        r'\bknown\s+only\s+from\s+(?:a\s+)?(?:single\s+)?'
        r'(?:fragmentary|incomplete|isolated|partial|poorly\s+preserved)\b',
        r'\bknown\s+only\s+from\s+(?:a?\s+single\s+)?(?:tooth|teeth|bone|fragment|vertebra|claw|jaw)\b',
        r'\bbased\s+(?:solely\s+)?on\s+(?:a\s+)?(?:single\s+)?'
        r'(?:fragmentary|incomplete|isolated|partial)\b',
        r'\bindeterminate\s+(?:sauropod|theropod|ornithopod|ceratopsian|ankylosaur|'
        r'stegosaur|hadrosaur|dinosaur|saurischian|ornithischian|dromaeosaurid|'
        r'troodontid|oviraptorosaur)\b',
        r'\bpossibly\s+(?:a\s+)?(?:junior\s+)?synonym\b',
        r'\bmay\s+be\s+(?:a\s+)?(?:junior\s+)?synonym\b',
        r'\bperhaps\s+(?:a\s+)?synonym\b',
        r'\bcannot\s+be\s+distinguished\b',
        r'\bindistinguishable\s+from\b',
        r'\bno\s+(?:known\s+)?(?:diagnostic|distinguishing)\s+(?:features?|characteristics?)\b',
    ]),
]

FLAGS = re.compile(
    '|'.join(
        f'(?P<{name}_{i}>{pat})'
        for name, patterns in TIERS
        for i, pat in enumerate(patterns)
    ),
    re.I | re.S
)

# ── Manual overrides ─────────────────────────────────────────────────────────
# Add any misclassified genera here. These take priority over text detection.
# Status options: valid | uncertain | disputed | synonym | nomen_dubium | unknown
MANUAL_OVERRIDES = {
    # Resurrected genera (were once sunk, now valid again)
    "Brontosaurus":      "valid",      # formally resurrected 2015 from Apatosaurus synonymy

    # Actively disputed genera
    "Nanotyrannus":      "disputed",   # T. rex juvenile vs. separate genus
    "Stygimoloch":       "disputed",   # likely juvenile Pachycephalosaurus
    "Dracorex":          "disputed",   # likely juvenile Pachycephalosaurus
    "Dromiceiomimus":    "uncertain",  # possibly lumped with Ornithomimus

    # False positives — valid genera whose articles mention synonyms OF them
    "Spinosaurus":       "valid",      # article mentions Oxalaia/Sigilmassasaurus as synonyms
    "Irritator":         "valid",
    "Suchomimus":        "valid",
    "Majungasaurus":     "valid",      # Majungatholus is a synonym OF it
    "Pelorosaurus":      "valid",      # valid brachiosaur; referred species synonymies
    "Stokesosaurus":     "valid",      # valid tyrannosauroid
    "Serikornis":        "valid",      # described 2017, valid troodontid
    "Nomingia":          "valid",      # known oviraptorosaur

    # False positive nomen_dubia — article mentions dubious specimens referred TO them
    "Saurornitholestes": "valid",      # well-known dromaeosaurid
    "Sinocephale":       "valid",      # known pachycephalosaurid from China

    # Nomina dubia missed or wrongly assigned by text scan
    "Chiayusaurus":      "nomen_dubium",  # known only from teeth
    "Troodon":           "nomen_dubium",  # formally restricted to teeth only
}


STATUS_PRIORITY = ["nomen_dubium", "synonym", "disputed", "uncertain"]

# Only scan the lead paragraph — body text discusses *other* taxa
# (e.g. Tyrannosaurus article says "Dynamosaurus is a junior synonym of T. rex"
#  which would falsely flag Tyrannosaurus as a synonym).
# Wikipedia always states genus-level validity in the first 1-2 sentences.
LEAD_CHARS = 1500

def detect(text: str) -> str:
    """Return the highest-priority status found in the lead paragraph."""
    lead = text[:LEAD_CHARS]
    found = set()
    for m in FLAGS.finditer(lead):
        for key in m.groupdict():
            if m.group(key) is not None:
                status = key.rsplit("_", 1)[0]
                found.add(status)

    for status in STATUS_PRIORITY:
        if status in found:
            return status
    return "valid"


# ── Run ───────────────────────────────────────────────────────────────────────
def safe_name(s):
    import re as _re
    return _re.sub(r'[^\w\-]', '_', s)

with open("../data/dinosaurs_list.txt", encoding="utf-8") as f:
    names = [l.strip() for l in f if l.strip()]

results  = {}
counts   = {"valid": 0, "uncertain": 0, "disputed": 0,
            "synonym": 0, "nomen_dubium": 0, "unknown": 0}

for name in names:
    path = f"{RAW_DIR}/{safe_name(name)}.txt"
    if not os.path.exists(path):
        status = MANUAL_OVERRIDES.get(name, "unknown")
        results[name] = status
        counts[status] += 1
        continue

    with open(path, encoding="utf-8") as f:
        text = f.read()

    status = MANUAL_OVERRIDES.get(name) or detect(text)
    results[name] = status
    counts[status] += 1

with open("../data/validity.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

total = len(names)
print(f"{'='*46}")
print(f"  Total genera:   {total}")
print(f"{'─'*46}")
print(f"  ✅ valid:        {counts['valid']:>4}  (always in game)")
print(f"  🔬 disputed:     {counts['disputed']:>4}  (rare toggle)")
print(f"  ❓ uncertain:    {counts['uncertain']:>4}  (rare toggle)")
print(f"  ❌ nomen_dubium: {counts['nomen_dubium']:>4}  (excluded)")
print(f"  ❌ synonym:      {counts['synonym']:>4}  (excluded)")
print(f"  ❌ unknown:      {counts['unknown']:>4}  (excluded)")
print(f"{'='*46}")
print(f"\nSaved to ../data/validity.json")

# Print ALL non-valid entries for spot-checking
print("\nAll nomen_dubia:")
for n in sorted(n for n, s in results.items() if s == "nomen_dubium"): print(f"  {n}")

print("\nAll disputed:")
for n in sorted(n for n, s in results.items() if s == "disputed"): print(f"  {n}")

print("\nAll synonyms:")
for n in sorted(n for n, s in results.items() if s == "synonym"): print(f"  {n}")

print("\nManual overrides applied:", list(MANUAL_OVERRIDES.keys()))
