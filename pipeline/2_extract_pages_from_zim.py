"""
Step 2 (ZIM version) — Extract Wikipedia article text from local ZIM file.
Much faster than API calls, no rate limiting, no internet needed.

Same output as 2_fetch_pages.py:
    ../data/raw_pages/{safe_name}.txt

Install deps (once):
    pip install libzim beautifulsoup4 lxml --break-system-packages

Run:
    python 2_extract_pages_from_zim.py --zim /run/media/rok/.../wikipedia_en_all_maxi_*.zim
"""
import argparse, os, re, sys
from pathlib import Path

try:
    from libzim.reader import Archive
except ImportError:
    print("Missing: pip install libzim --break-system-packages")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Missing: pip install beautifulsoup4 lxml --break-system-packages")
    sys.exit(1)

os.makedirs("../data/raw_pages", exist_ok=True)


def safe_name(s):
    return re.sub(r'[^\w\-]', '_', s)


def get_html(zim, title):
    for path in [
        title,
        title.replace(" ", "_"),
        f"A/{title}",
        f"A/{title.replace(' ', '_')}",
        f"wiki/{title.replace(' ', '_')}",
    ]:
        try:
            entry = zim.get_entry_by_path(path)
            while entry.is_redirect:
                entry = entry.get_redirect_entry()
            return bytes(entry.get_item().content).decode("utf-8", errors="replace")
        except KeyError:
            continue
    return None


# Sections that are useless for hint generation — strip them
STRIP_SECTIONS = re.compile(
    r'^(references?|notes?|further reading|external links?|'
    r'see also|bibliography|footnotes?|sources?)$',
    re.I
)


def html_to_text(html: str) -> str:
    """
    Convert Wikipedia article HTML to clean plaintext.
    Removes: tables (cladograms, taxobox), navboxes, references,
             image captions (short), and wiki-markup noise.
    Keeps:   paragraphs, section headings, list items.
    """
    soup = BeautifulSoup(html, "lxml")

    # ── Remove boilerplate elements ──────────────────────────────────────────
    def has_class(el, *kw):
        if not isinstance(el, Tag):
            return False
        classes = " ".join(el.get("class") or [])
        return any(k in classes for k in kw)

    for el in soup.find_all(lambda t: has_class(
            t, "navbox", "navbar", "noprint", "mw-editsection",
            "reference", "reflist", "hatnote", "dablink",
            "sistersitebox", "infobox", "biota",  # taxobox — structured, not prose
            "thumb",        # image captions
            "gallery",
            "clade",        # cladogram tables
            "wikitable",    # data tables
    )):
        el.decompose()

    # Remove all remaining tables (they're mostly cladograms / data grids)
    for tbl in soup.find_all("table"):
        tbl.decompose()

    # Remove references spans [1], [2] etc.
    for sup in soup.find_all("sup"):
        sup.decompose()

    # ── Walk headings and paragraphs ─────────────────────────────────────────
    lines = []
    skip_section = False

    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "dt", "dd"]):
        if el.name in ("h1", "h2", "h3", "h4"):
            heading = el.get_text(" ", strip=True)
            skip_section = bool(STRIP_SECTIONS.match(heading))
            if not skip_section and heading:
                lines.append(f"\n== {heading} ==")
        elif not skip_section:
            text = el.get_text(" ", strip=True)
            # Skip very short lines (captions, stubs)
            if len(text) > 40:
                lines.append(text)

    return "\n".join(lines).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zim", required=True, help="Path to wikipedia_en_all_maxi_*.zim")
    args = ap.parse_args()

    if not os.path.exists(args.zim):
        print(f"ZIM not found: {args.zim}")
        sys.exit(1)

    print(f"Opening {Path(args.zim).name} …")
    zim = Archive(args.zim)
    print(f"ZIM ready — {zim.all_entry_count:,} entries\n")

    with open("../data/dinosaurs_list.txt", encoding="utf-8") as f:
        names = [l.strip() for l in f if l.strip()]

    total   = len(names)
    skipped = 0

    for i, name in enumerate(names, 1):
        safe = safe_name(name)
        out  = f"../data/raw_pages/{safe}.txt"

        if os.path.exists(out):
            continue  # resume

        print(f"[{i}/{total}] {name}", end=" ... ", flush=True)

        html = get_html(zim, name)
        if not html:
            print("not found in ZIM")
            skipped += 1
            continue

        text = html_to_text(html)

        if len(text) < 150:
            print(f"too short ({len(text)} chars), skipped")
            skipped += 1
            continue

        with open(out, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"ok ({len(text):,} chars)")

    print(f"\nDone. {skipped} not found / too short.")


if __name__ == "__main__":
    main()
