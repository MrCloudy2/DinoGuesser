"""
Step 6c — Compare regex validity (validity.json) vs PBDB validity (validity_pbdb.json).
          Then outputs the FINAL merged validity.json used by the game.

Merge logic (PBDB-primary):
  - If PBDB has a definite answer (valid / synonym / nomen_dubium) → use it
  - If PBDB says 'unknown_pbdb' → fall back to regex result
  - If PBDB says 'uncertain' (unrecognised diff field) → fall back to regex

Output:
  ../data/validity_final.json   — merged result used in 5_build_db.py
  prints a diff table for review

Run AFTER 6_flag_validity.py and 6b_flag_validity_pbdb.py.
"""
import json
from collections import defaultdict

with open("../data/validity.json",      encoding="utf-8") as f: regex = json.load(f)
with open("../data/validity_pbdb.json", encoding="utf-8") as f: pbdb  = json.load(f)

# Final-stage overrides — applied AFTER PBDB merge.
# Use sparingly: only when both PBDB and regex are wrong and we have a clear reason.
POST_OVERRIDES: dict[str, str] = {
    "Troodon":       "nomen_dubium",  # formally restricted to teeth only (2017); PBDB lags
    "Nanotyrannus":  "disputed",      # T.rex juvenile vs. separate genus — scientifically live
    "Stygimoloch":   "disputed",      # likely juvenile Pachycephalosaurus — still debated
    "Dracorex":      "disputed",      # likely juvenile Pachycephalosaurus — still debated
}

names = list(regex.keys())   # canonical order from our list

# ── Merge ─────────────────────────────────────────────────────────────────────
PBDB_DEFINITE = {"valid", "synonym", "nomen_dubium"}

final: dict[str, str] = {}
source_used: dict[str, str] = {}   # for reporting

for name in names:
    r = regex.get(name, "unknown")
    p = pbdb.get(name, "unknown_pbdb")

    if p in PBDB_DEFINITE:
        final[name] = p
        source_used[name] = "pbdb"
    else:
        # unknown_pbdb or uncertain → trust regex
        final[name] = r
        source_used[name] = "regex_fallback"

# ── Save final ────────────────────────────────────────────────────────────────
# Apply post-merge overrides
for name, status in POST_OVERRIDES.items():
    if name in final:
        final[name] = status
        source_used[name] = "post_override"

with open("../data/validity_final.json", "w", encoding="utf-8") as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

# ── Print summary counts ──────────────────────────────────────────────────────
from collections import Counter
counts = Counter(final.values())
pbdb_sourced  = sum(1 for s in source_used.values() if s == "pbdb")
regex_sourced = sum(1 for s in source_used.values() if s == "regex_fallback")

print(f"{'='*60}")
print(f"  FINAL MERGED validity — {len(names)} genera")
print(f"{'─'*60}")
print(f"  ✅ valid:        {counts['valid']:>4}")
print(f"  🔬 disputed:     {counts['disputed']:>4}")
print(f"  ❓ uncertain:    {counts['uncertain']:>4}")
print(f"  ❌ nomen_dubium: {counts['nomen_dubium']:>4}")
print(f"  ❌ synonym:      {counts['synonym']:>4}")
print(f"  ❌ unknown:      {counts['unknown']:>4}")
print(f"{'─'*60}")
print(f"  Source: PBDB={pbdb_sourced}  Regex fallback={regex_sourced}")
print(f"{'='*60}")
print("\nSaved → ../data/validity_final.json\n")

# ── Print disagreements grouped by pattern ───────────────────────────────────
disagree: dict[str, list[str]] = defaultdict(list)
for name in names:
    r = regex.get(name, "unknown")
    p = pbdb.get(name, "unknown_pbdb")
    f_status = final[name]
    if r != f_status:
        key = f"regex={r:12}  pbdb={p:12}  →final={f_status}"
        disagree[key].append(name)

if disagree:
    print("DISAGREEMENTS (regex vs final, sorted by pattern):")
    print(f"{'─'*60}")
    for pattern in sorted(disagree):
        names_list = sorted(disagree[pattern])
        print(f"\n  {pattern}  ({len(names_list)} genera)")
        for n in names_list:
            print(f"    {n}")
else:
    print("No disagreements — regex and PBDB fully agree.")

# ── Also flag genera not in PBDB (regex-fallback) ───────────────────────────
not_in_pbdb = [n for n in names if pbdb.get(n) == "unknown_pbdb"]
print(f"\n\nNOT IN PBDB ({len(not_in_pbdb)} genera — using regex result):")
for n in sorted(not_in_pbdb):
    print(f"  {n:30}  regex={regex.get(n,'?')}")
