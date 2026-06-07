"""
Debug: show what img tags exist in an article and whether they resolve in the ZIM.
Run: python debug_zim.py --zim /path/to/wikipedia.zim --title Acrocanthosaurus
"""
import argparse, re, sys
from pathlib import Path
from libzim.reader import Archive
from bs4 import BeautifulSoup

ap = argparse.ArgumentParser()
ap.add_argument("--zim",   required=True)
ap.add_argument("--title", default="Aardonyx")
args = ap.parse_args()

zim = Archive(args.zim)

# ── Find the article ─────────────────────────────────────────────────────────
html = None
tried = []
for path in [args.title, args.title.replace(" ","_"),
             f"A/{args.title}", f"A/{args.title.replace(' ','_')}",
             f"wiki/{args.title.replace(' ','_')}"]:
    try:
        e = zim.get_entry_by_path(path)
        while e.is_redirect:
            e = e.get_redirect_entry()
        html = bytes(e.get_item().content).decode("utf-8", errors="replace")
        print(f"✓ Found at path: {path!r}\n")
        break
    except KeyError:
        tried.append(path)

if not html:
    print(f"✗ Article not found. Tried: {tried}")
    sys.exit(1)

# ── Print ALL img tags ────────────────────────────────────────────────────────
soup = BeautifulSoup(html, "lxml")
imgs = soup.find_all("img")
print(f"Total <img> tags: {len(imgs)}\n")

for i, img in enumerate(imgs):
    src = img.get("src","")
    w   = img.get("width","?")
    h   = img.get("height","?")
    alt = img.get("alt","")[:40]
    print(f"[{i:02d}] {w}x{h}  src={src[:90]}")
    print(f"      alt={alt!r}")

    # Try to resolve in ZIM
    if src and not src.startswith("//") and not src.startswith("http"):
        zim_path = re.sub(r'^[./]+', '', src)
        try:
            e = zim.get_entry_by_path(zim_path)
            data = bytes(e.get_item().content)
            print(f"      ✓ ZIM resolved → {zim_path!r}  ({len(data)//1024} KB)")
        except KeyError:
            print(f"      ✗ ZIM MISS  → {zim_path!r}")
            # Try stripping one more path component
            parts = zim_path.split("/")
            for start in range(1, min(4, len(parts))):
                alt_path = "/".join(parts[start:])
                try:
                    e = zim.get_entry_by_path(alt_path)
                    data = bytes(e.get_item().content)
                    print(f"      ✓ ZIM resolved (trimmed) → {alt_path!r}  ({len(data)//1024} KB)")
                    break
                except KeyError:
                    pass
    print()

# ── Also show what structure the HTML uses ────────────────────────────────────
print("\n── Parent div/table classes for each img ──")
for i, img in enumerate(imgs[:10]):
    classes = []
    p = img.parent
    for _ in range(4):
        if p and hasattr(p, 'get'):
            c = p.get("class", [])
            if c:
                classes.append(f"{p.name}.{' '.join(c)}")
        p = p.parent if p else None
    print(f"[{i:02d}] {' > '.join(reversed(classes))}")
