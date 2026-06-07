# 🦕 DinoGuess

A Wordle-style dinosaur guessing game. Up to 5 guesses to identify a dinosaur genus, with hints revealed after each wrong guess.

**Live at:** [cloudy.freemyip.com/dinoguess](http://cloudy.freemyip.com/dinoguess)

---

## Game Modes

| Mode | Description |
|---|---|
| 📅 Daily | Same dinosaur for everyone, resets at UTC midnight |
| 🎲 Random | New random dinosaur each game |
| 🌿 Casual | Multiple-choice buttons, well-known genera only |
| 💀 Hard | Image hidden until game ends, start with 1 hint |
| 🔬 Rare | Include disputed / uncertain genera |

Up to 5 guesses. Each wrong guess reveals the next hint (hardest → easiest).
Art / Fossil image toggle when both exist. Common-name aliases work in the text input (e.g. typing "T. rex" resolves to *Tyrannosaurus*).

---

## Hints

Hints are ordered **hardest → easiest**:

| # | Type | Source |
|---|------|--------|
| 1 | Geological formation + age in Ma | PBDB (verified) |
| 2 | Distinctive anatomical feature | Qwen 35B from Wikipedia |
| 3 | Size, weight, and diet | Qwen 35B from Wikipedia |
| 4 | Continent and geological period | PBDB (verified) |
| 5 | Most famous / iconic fact | Qwen 35B from Wikipedia |

---

## Repository Structure

```
DinoGuesser/
├── www/                        ← the website (deploy this)
│   ├── index.html
│   ├── style.css
│   ├── game.js
│   └── dinosaurs.json          ← full game database (~200 KB)
└── data/                       ← source data files
    ├── dinosaurs_list.txt       ← ~1,400 genus names from Wikipedia
    ├── pbdb_dinosauria.csv      ← PBDB taxa snapshot (validity, n_occs)
    ├── pbdb_occurrences.csv     ← PBDB fossil occurrences (formation, Ma, location)
    ├── pbdb_data.json           ← aggregated per-genus PBDB facts
    ├── validity.json            ← regex-based validity (Wikipedia text)
    ├── validity_pbdb.json       ← PBDB-based validity
    └── validity_final.json      ← merged final validity (PBDB-primary)
```

Images are served from the production server and are not tracked in this repo.
Pipeline scripts are local-only and not published.

---

## Validity System

Each genus is classified using the [Paleobiology Database](https://paleobiodb.org) as the primary source, with Wikipedia text as fallback:

| Status | Meaning | In game |
|--------|---------|---------|
| `valid` | Accepted genus | ✅ Always |
| `disputed` | Validity actively debated | 🔬 Rare toggle only |
| `uncertain` | Fragmentary / possibly invalid | 🔬 Rare toggle only |
| `nomen_dubium` | Named from indistinguishable material | ❌ Never |
| `synonym` | Junior synonym of another genus | ❌ Never |

---

## Deploy

```bash
rsync -av --progress www/ user@server:/var/www/dinoguess/
```

nginx tip — enable gzip for the JSON database:
```nginx
gzip on;
gzip_types application/json;
```

Images should be served from `/var/www/dinoguess/images/` on the same server.
