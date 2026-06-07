# 🦕 DinoGuess

A Wordle-style dinosaur guessing game. Identify a dinosaur genus from hints — harder clues first, easier ones revealed after each wrong guess.

**Live at:** [cloudy.freemyip.com/dinoguess](https://cloudy.freemyip.com/dinoguess/)

---

## Game Modes

| Mode | Description |
|---|---|
| 📅 Daily | Same dinosaur for everyone, resets at UTC midnight |
| 🎲 Expert | Type the name · hints revealed one by one after each wrong guess |
| 🌿 Choice | All 5 hints shown upfront · pick from 4 options · one chance |

### Settings

| Setting | Options | Notes |
|---|---|---|
| 🦕 Difficulty | Slider (9 levels) | Top 15 → 30 → 50 → 100 → 300 → 500 → 700 → 1000 → All |
| 🖼️ Images Only | On / Off | Exclude dinosaurs without a picture (default: on) |
| 🎯 Max Guesses | 3 / 5 / 7 | Expert & Daily modes |
| 💡 Starting Hints | 0 / 1 / 2 | Hints shown before your first guess |

Dinosaurs are ranked by Wikipedia pageviews — the easiest difficulty levels contain the most famous genera (T. rex, Velociraptor, Triceratops…). The hardest level includes all valid genera including disputed and uncertain ones.

---

## Hints

Ordered **hardest → easiest**:

| # | Type | Source |
|---|------|--------|
| 1 | Geological formation + age (Ma) | PBDB |
| 2 | Distinctive anatomical feature | Qwen 35B from Wikipedia |
| 3 | Size, weight, and diet | Qwen 35B from Wikipedia |
| 4 | Continent and geological period | PBDB |
| 5 | Most famous / iconic fact | Qwen 35B from Wikipedia |

---

## Repository Structure

```
DinoGuesser/
├── www/                        ← website (deployed to server)
│   ├── index.html
│   ├── style.css
│   ├── game.js
│   └── dinosaurs.json          ← full game database (~1 MB)
└── data/                       ← source data files
    ├── dinosaurs_list.txt       ← ~1,400 genus names
    ├── pbdb_dinosauria.csv      ← PBDB taxa snapshot
    ├── pbdb_occurrences.csv     ← PBDB fossil occurrences
    ├── pbdb_data.json           ← aggregated per-genus PBDB facts
    ├── fame_scores.json         ← Wikipedia 60-day pageviews per genus
    ├── validity.json            ← regex-based validity (Wikipedia text)
    ├── validity_pbdb.json       ← PBDB-based validity
    ├── validity_final.json      ← merged final validity (PBDB-primary)
    ├── selections.json          ← image picker selections
    └── selections_urls.json     ← original Wikipedia filenames for images
```

Images are served from the production server and are not tracked in this repo.  
Pipeline scripts are local-only and not published.

---

## Validity System

Each genus is classified using the [Paleobiology Database](https://paleobiodb.org) as the primary source, with Wikipedia text as fallback:

| Status | Meaning | In game |
|--------|---------|---------|
| `valid` | Accepted genus | ✅ Always |
| `disputed` | Validity actively debated | 🦕 High difficulty only |
| `uncertain` | Fragmentary / possibly invalid | 🦕 High difficulty only |
| `nomen_dubium` | Named from indistinguishable material | ❌ Never |
| `synonym` | Junior synonym of another genus | ❌ Never |

---

## Deploy

```bash
# Code — pull on server
ssh cloudy@192.168.1.107 "cd /home/cloudy/site/dinoguess && git pull"

# Images — rsync (not in git)
rsync -av --ignore-existing www/images/ cloudy@192.168.1.107:/home/cloudy/site/dinoguess/www/images/
```

Served by nginx inside the `nextcloud_nginx` Docker container at `cloudy.freemyip.com`.  
nginx config: `/home/cloudy/nextcloud/nginx.conf` on the host.
