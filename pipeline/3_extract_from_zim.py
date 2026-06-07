"""
Step 3 — Extract dinosaur images from local Wikipedia ZIM file.
Tested against the 2026-02 Kiwix Wikipedia maxi ZIM.

Path format (2026+):  ./_assets_/{page_hash}/{filename}
Resolution:  strip leading "./" → "_assets_/{hash}/{filename}"

Filtering logic (in order):
  1. Strip cladogram cells (td.clade-leaf) and navboxes from soup
  2. Keep images whose filename contains the genus name  (primary)
  3. Fallback: keep any image with display-width >= 200px   (catches
     images with generic names, e.g. Comahuesaurus fossil photo)
  4. Skip tiny icons / SVG-converted-PNGs

Run:
    python 3_extract_from_zim.py --zim /path/to/wikipedia_en_all_maxi_*.zim
"""
import argparse, os, json, re, sys
from pathlib import Path

try:
    from libzim.reader import Archive
except ImportError:
    print("Missing: pip install libzim --break-system-packages"); sys.exit(1)
try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Missing: pip install beautifulsoup4 lxml --break-system-packages"); sys.exit(1)

os.makedirs("../data/images",      exist_ok=True)
os.makedirs("../data/image_lists", exist_ok=True)

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

SKIP_FILENAME = re.compile(
    r'OOjs|Commons-logo|Symbol_|WikiProject|Flag_of|'
    r'Edit-ltr|Red_Pencil|Padlock|Lock|Star|Arrow|'
    r'\.svg\.png$',          # converted SVG icons
    re.I
)

def safe_name(s):
    return re.sub(r'[^\w\-]', '_', s)


# ── ZIM access ───────────────────────────────────────────────────────────────

def get_html(zim, title):
    for path in [title, title.replace(" ", "_"),
                 f"A/{title}", f"A/{title.replace(' ','_')}",
                 f"wiki/{title.replace(' ','_')}"]:
        try:
            e = zim.get_entry_by_path(path)
            while e.is_redirect:
                e = e.get_redirect_entry()
            return bytes(e.get_item().content).decode("utf-8", errors="replace")
        except KeyError:
            continue
    return None


def get_image_bytes(zim, src: str):
    """
    Resolve img src to ZIM bytes.
    2026 format:  ./_assets_/HASH/filename.ext
    """
    if not src or src.startswith("//") or src.startswith("http"):
        return None, None

    # Strip leading "./" → "_assets_/HASH/filename.ext"
    zim_path = src.lstrip("./")
    filename  = Path(zim_path).name

    try:
        data = bytes(zim.get_entry_by_path(zim_path).get_item().content)
        return data, filename
    except KeyError:
        pass

    # Legacy fallback: old I/m/ format
    m = re.match(r'(?:I|-)/.+?/(\d+px-(.+))$', zim_path)
    if m:
        tail = m.group(2)
        base = zim_path.rsplit("/", 2)[0]
        for px in [1200, 800, 640, 480]:
            try:
                data = bytes(zim.get_entry_by_path(f"{base}/{px}px-{tail}").get_item().content)
                return data, tail
            except KeyError:
                pass

    return None, None


# ── HTML parsing ─────────────────────────────────────────────────────────────

def collect_srcs(html: str, genus: str) -> list[str]:
    """
    Return img src list for the dinosaur, in priority order.
    Cladogram (td.clade-leaf) and navbox elements are removed first.
    """
    soup = BeautifulSoup(html, "lxml")

    # ── strip noise ──────────────────────────────────────────────────────────
    def has_cls(el, *kws):
        if not isinstance(el, Tag): return False
        c = " ".join(el.get("class") or [])
        return any(k in c for k in kws)

    # Cladogram cells
    for el in soup.find_all("td", class_="clade-leaf"):
        el.decompose()
    for el in soup.find_all(lambda t: has_cls(t, "clade")):
        el.decompose()
    # Navigation / footer boxes
    for el in soup.find_all(lambda t: has_cls(t, "navbox", "navbar",
                                               "noprint", "mw-empty-elt")):
        el.decompose()
    # Hatnotes / sister-site boxes
    for el in soup.find_all(lambda t: has_cls(t, "hatnote", "sistersitebox")):
        el.decompose()

    # ── collect candidates ───────────────────────────────────────────────────
    g_lower   = genus.lower()
    primary   = []   # genus name in filename
    fallback  = []   # width >= 200, no genus name

    seen = set()
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or src in seen:
            continue
        seen.add(src)

        fname = Path(src).name
        if SKIP_FILENAME.search(fname):
            continue
        if Path(fname).suffix.lower() not in IMG_EXTS:
            continue

        try:
            w = int(img.get("width",  0) or 0)
            h = int(img.get("height", 0) or 0)
        except (ValueError, TypeError):
            w = h = 0

        # Skip unmistakable icons (very small in both dimensions)
        if 0 < w < 80 and 0 < h < 80:
            continue

        has_genus = g_lower in fname.lower()

        if has_genus:
            primary.append(src)
        elif w >= 200:
            # Fallback: large image without genus name
            # (e.g. fossil photo with specimen-number filename)
            fallback.append((w * h, src))

    fallback.sort(reverse=True)   # largest first
    fallback_srcs = [s for _, s in fallback[:3]]  # max 3 fallbacks

    # Primary images first; if none exist, use fallback
    return primary if primary else fallback_srcs


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zim",   required=True)
    ap.add_argument("--limit", type=int, default=5,
                    help="Max images saved per dinosaur (default 5)")
    args = ap.parse_args()

    if not os.path.exists(args.zim):
        print(f"ZIM not found: {args.zim}"); sys.exit(1)

    print(f"Opening {Path(args.zim).name} …")
    zim = Archive(args.zim)
    print(f"ZIM ready — {zim.all_entry_count:,} entries\n")

    with open("../data/dinosaurs_list.txt", encoding="utf-8") as f:
        names = [l.strip() for l in f if l.strip()]

    total = len(names)

    for idx, name in enumerate(names, 1):
        safe  = safe_name(name)
        genus = name.split()[0]
        lout  = f"../data/image_lists/{safe}.json"

        if os.path.exists(lout):
            continue   # resume

        print(f"[{idx}/{total}] {name}", end=" ... ", flush=True)

        html = get_html(zim, name)
        if not html:
            print("not in ZIM")
            with open(lout, "w") as f: json.dump([], f)
            continue

        srcs  = collect_srcs(html, genus)
        saved = []
        img_n = 1

        for src in srcs:
            if img_n > args.limit:
                break

            data, filename = get_image_bytes(zim, src)
            if not data or len(data) < 1500:
                continue

            ext = Path(filename or "").suffix.lower()
            if ext not in IMG_EXTS:
                ext = ".jpg"

            dest = f"../data/images/{safe}_{img_n}{ext}"
            with open(dest, "wb") as f:
                f.write(data)

            rel = f"data/images/{safe}_{img_n}{ext}"
            saved.append({"filename": filename or f"{name}_{img_n}{ext}",
                          "thumb": rel, "full": rel, "w": 0, "h": 0})
            img_n += 1

        with open(lout, "w", encoding="utf-8") as f:
            json.dump(saved, f)

        print(f"{len(saved)} saved  ({', '.join(e['filename'] for e in saved)})")

    print("\nDone!")


if __name__ == "__main__":
    main()
