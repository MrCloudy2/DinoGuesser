"""
Step 1 — Fetch dinosaur genera list from Wikipedia.
Output: ../data/dinosaurs_list.txt  (one genus per line, ~1100 entries)
"""
import requests
import time
import os

os.makedirs("../data", exist_ok=True)

BASE = "https://en.wikipedia.org/w/api.php"

HEADERS = {"User-Agent": "DinoGuess/1.0 (educational project; https://github.com/dinoguess)"}

params = {
    "action": "query",
    "list": "categorymembers",
    "cmtitle": "Category:Dinosaur genera",
    "cmlimit": "500",
    "cmtype": "page",
    "format": "json",
}

names = []
print("Fetching dinosaur genera from Wikipedia category...")

while True:
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()

    for member in data["query"]["categorymembers"]:
        names.append(member["title"])

    print(f"  fetched {len(names)} so far...")

    if "continue" not in data:
        break
    params["cmcontinue"] = data["continue"]["cmcontinue"]
    time.sleep(0.5)

# Clean up
names = [n for n in names if "(disambiguation)" not in n]
names = sorted(set(names))

out = "../data/dinosaurs_list.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(names))

print(f"\nDone. Saved {len(names)} genera to {out}")
