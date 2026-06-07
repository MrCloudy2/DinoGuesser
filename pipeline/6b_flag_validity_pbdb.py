"""
Step 6b — Build validity data from Paleobiology Database (primary source).

Reads:  ../data/pbdb_dinosauria.csv   (download once from PBDB)
        ../data/dinosaurs_list.txt

Output: ../data/validity_pbdb.json

PBDB 'difference' field → our status:
  ''                    → valid
  'subjective synonym of' / 'objective synonym of' / 'replaced by' → synonym
  'nomen dubium'        → nomen_dubium
  'nomen nudum'         → nomen_dubium
  'nomen vanum'         → nomen_dubium

PBDB 'flags' field:
  'I' = invalid (form taxa, ichnotaxa, etc.) → excluded as nomen_dubium

Genera on our list but not in PBDB → status = 'unknown_pbdb' (handled by 6c).
"""
import csv, json, re

PBDB_CSV  = "../data/pbdb_dinosauria.csv"
NAMES_TXT = "../data/dinosaurs_list.txt"

DIFF_MAP = {
    "":                     "valid",
    "subjective synonym of":"synonym",
    "objective synonym of": "synonym",
    "replaced by":          "synonym",
    "nomen dubium":         "nomen_dubium",
    "nomen nudum":          "nomen_dubium",
    "nomen vanum":          "nomen_dubium",
}

def norm(name: str) -> str:
    return name.strip().lower()

# ── Load PBDB taxa ────────────────────────────────────────────────────────────
pbdb: dict[str, str] = {}          # genus_name (lower) → status

with open(PBDB_CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        name = row["taxon_name"].strip()
        if not name:
            continue

        # Form taxa / ichnotaxa (flag contains 'I') are not body-fossil genera
        if "I" in row.get("flags", ""):
            pbdb[norm(name)] = "nomen_dubium"
            continue

        diff  = row["difference"].strip()
        status = DIFF_MAP.get(diff, "uncertain")   # unknown difference values → uncertain
        pbdb[norm(name)] = status

# ── Map our name list → PBDB status ──────────────────────────────────────────
with open(NAMES_TXT, encoding="utf-8") as f:
    names = [l.strip() for l in f if l.strip()]

results: dict[str, str] = {}
counts = {"valid": 0, "synonym": 0, "nomen_dubium": 0,
          "uncertain": 0, "unknown_pbdb": 0}

for name in names:
    key = norm(name)
    if key in pbdb:
        status = pbdb[key]
    else:
        status = "unknown_pbdb"   # not in PBDB at all
    results[name] = status
    counts[status] = counts.get(status, 0) + 1

with open("../data/validity_pbdb.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

total = len(names)
print(f"{'='*50}")
print(f"  PBDB source — {total} genera")
print(f"{'─'*50}")
print(f"  ✅ valid:        {counts['valid']:>4}")
print(f"  ❌ synonym:      {counts['synonym']:>4}")
print(f"  ❌ nomen_dubium: {counts['nomen_dubium']:>4}")
print(f"  ❓ uncertain:    {counts.get('uncertain',0):>4}  (unrecognised PBDB status)")
print(f"  ─  unknown_pbdb: {counts['unknown_pbdb']:>4}  (not in PBDB — see 6c)")
print(f"{'='*50}")
print("\nSaved → ../data/validity_pbdb.json")
