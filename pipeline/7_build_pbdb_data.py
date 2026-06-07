"""
Step 7 — Aggregate PBDB data into per-genus structured facts.

Reads:
  ../data/pbdb_dinosauria.csv    — n_occs (fame proxy), diet via taxon_name lookup
  ../data/pbdb_occurrences.csv   — formation, Ma range, countries, geological interval
  ../data/dinosaurs_list.txt

Output: ../data/pbdb_data.json
  {
    "Tyrannosaurus": {
      "n_occs":      86,
      "formations":  ["Hell Creek", "Scollard", ...],   # most-common first
      "max_ma":      72.2,
      "min_ma":      66.0,
      "interval":    "Late Cretaceous",                 # broad plain-language period
      "countries":   ["US", "CA"],                      # most-common first
      "continents":  ["North America"],
      "fame_rank":   86,
      "casual":      true                               # n_occs >= 50
    },
    ...
  }
"""
import csv, json
from collections import Counter, defaultdict

PBDB_TAXA_CSV = "../data/pbdb_dinosauria.csv"
PBDB_OCCS_CSV = "../data/pbdb_occurrences.csv"
NAMES_TXT     = "../data/dinosaurs_list.txt"
CASUAL_THRESH = 20   # minimum occurrence count to qualify for casual pool

CC_TO_CONTINENT = {
    "US":"North America","CA":"North America","MX":"North America",
    "AR":"South America","BR":"South America","CL":"South America",
    "CO":"South America","PE":"South America","UY":"South America",
    "UK":"Europe","FR":"Europe","ES":"Europe","PT":"Europe","DE":"Europe",
    "IT":"Europe","RO":"Europe","AT":"Europe","BE":"Europe","PL":"Europe",
    "HU":"Europe","CZ":"Europe","SK":"Europe","NO":"Europe","SE":"Europe",
    "DK":"Europe","CH":"Europe","NL":"Europe","RS":"Europe",
    "CN":"Asia","MN":"Asia","JP":"Asia","IN":"Asia","KZ":"Asia",
    "UZ":"Asia","KG":"Asia","TJ":"Asia","TM":"Asia","IR":"Asia",
    "TH":"Asia","KR":"Asia","TW":"Asia",
    "AU":"Australia","NZ":"Australia/New Zealand",
    "MG":"Africa","ZA":"Africa","NI":"Africa","TN":"Africa","MA":"Africa",
    "EG":"Africa","NE":"Africa","NG":"Africa","TD":"Africa","ML":"Africa",
    "ET":"Africa","TZ":"Africa","ZW":"Africa",
    "RU":"Asia/Europe",
}

# Interval → plain-language broad period
def broad_period(interval: str) -> str:
    i = interval.lower()
    if any(x in i for x in ["maastrichtian","campanian","santonian","coniacian",
                              "turonian","cenomanian","late cretaceous"]):
        return "Late Cretaceous"
    if any(x in i for x in ["albian","aptian","barremian","hauterivian",
                              "valanginian","berriasian","early cretaceous"]):
        return "Early Cretaceous"
    if any(x in i for x in ["tithonian","kimmeridgian","oxfordian","callovian",
                              "bathonian","bajocian","aalenian","late jurassic"]):
        return "Late Jurassic"
    if any(x in i for x in ["toarcian","pliensbachian","sinemurian","hettangian",
                              "early jurassic","middle jurassic"]):
        return "Early/Middle Jurassic"
    if any(x in i for x in ["rhaetian","norian","carnian","ladinian","anisian",
                              "triassic"]):
        return "Triassic"
    return ""

def norm(name: str) -> str:
    return name.strip()

# ── Load taxa CSV for n_occs ──────────────────────────────────────────────────
n_occs_map: dict[str, int] = {}
with open(PBDB_TAXA_CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        name = row["taxon_name"].strip()
        try:
            n_occs_map[name] = int(row["n_occs"])
        except (ValueError, KeyError):
            n_occs_map[name] = 0

# ── Load occurrences CSV ──────────────────────────────────────────────────────
# Aggregate per genus: formations, Ma range, countries, interval
genus_data: dict[str, dict] = defaultdict(lambda: {
    "formations": Counter(),
    "countries":  Counter(),
    "intervals":  Counter(),
    "max_ma":     [],
    "min_ma":     [],
})

with open(PBDB_OCCS_CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        accepted = row["accepted_name"].strip()
        rank     = row["accepted_rank"].strip()

        # Extract genus from species name
        genus = accepted.split()[0] if accepted else ""
        if not genus:
            continue

        d = genus_data[genus]

        fm = row.get("formation", "").strip()
        if fm:
            d["formations"][fm] += 1

        cc = row.get("cc", "").strip().upper()
        if cc:
            d["countries"][cc] += 1

        interval = row.get("early_interval", "").strip()
        period   = broad_period(interval)
        if period:
            d["intervals"][period] += 1

        try:
            d["max_ma"].append(float(row["max_ma"]))
        except (ValueError, KeyError):
            pass
        try:
            d["min_ma"].append(float(row["min_ma"]))
        except (ValueError, KeyError):
            pass

# ── Load our dinosaur list ────────────────────────────────────────────────────
with open(NAMES_TXT, encoding="utf-8") as f:
    names = [l.strip() for l in f if l.strip()]

# ── Assemble output ───────────────────────────────────────────────────────────
output: dict[str, dict] = {}
matched = 0
unmatched = []

for name in names:
    n_occ = n_occs_map.get(name, 0)
    d = genus_data.get(name)

    entry: dict = {
        "n_occs":    n_occ,
        "fame_rank": n_occ,
        "casual":    n_occ >= CASUAL_THRESH,
    }

    if d:
        matched += 1
        # Top 3 formations
        top_formations = [f for f, _ in d["formations"].most_common(3)]
        entry["formations"] = top_formations

        # Ma range
        if d["max_ma"]:
            entry["max_ma"] = round(max(d["max_ma"]), 1)
        if d["min_ma"]:
            entry["min_ma"] = round(min(d["min_ma"]), 1)

        # Most common geological interval (plain language)
        if d["intervals"]:
            entry["interval"] = d["intervals"].most_common(1)[0][0]

        # Top countries + continents
        top_cc = [cc for cc, _ in d["countries"].most_common(5)]
        entry["countries"] = top_cc
        continents = list(dict.fromkeys(
            CC_TO_CONTINENT[cc] for cc in top_cc if cc in CC_TO_CONTINENT
        ))
        entry["continents"] = continents
    else:
        unmatched.append(name)
        entry["formations"] = []
        entry["countries"]  = []
        entry["continents"] = []

    output[name] = entry

with open("../data/pbdb_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

casual_count = sum(1 for e in output.values() if e["casual"])
print(f"{'='*50}")
print(f"  Processed {len(names)} genera")
print(f"  Matched in PBDB occurrences: {matched}")
print(f"  Not in PBDB occurrences:     {len(unmatched)}")
print(f"  Casual pool (n_occs≥{CASUAL_THRESH}): {casual_count}")
print(f"{'='*50}")
print("\nSaved → ../data/pbdb_data.json")

if unmatched:
    print(f"\nFirst 20 unmatched (no occurrence data):")
    for n in unmatched[:20]:
        print(f"  {n}")
