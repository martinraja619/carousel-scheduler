"""Build the carousel queue that the GitHub scheduler posts from.

For each carousel folder in F:\\AED\\carousels ("<n>. <Word>"), crops slides 01-08 to 4:5 the way the Instagram app
does (centred), saves them as JPEGs (the API takes JPEG only), and gives it the next posting slot (3 a day, IST) and
its caption in schedule.csv. The workflow doesn't check out carousels/, so everything post.py reads is in the CSVs.

  python build.py --first 37 --last 127 --start "2026-11-02 09:17"

Re-running rebuilds everything from the source folders. Carousels already in posted.csv get no new slot.
"""
import argparse
import csv
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

SRC = Path(r"F:\AED\carousels")
HERE = Path(__file__).resolve().parent
OUT = HERE / "carousels"
SLOTS = ["09:17", "14:34", "19:36"]  # IST
SLIDES = 8
# v3 slides are 1080x1440 (3:4) with content between y=72 and y=1224. Choosing 4:5 in the Instagram app keeps the
# centre 1080x1350, i.e. 45 px off the top and the bottom; no slide has text there.
CROP_BOX = (0, 45, 1080, 1395)
# Words about a person get "யாரு", everything else "என்ன" (user, 23 Oct 2026)
PEOPLE = {"Noob", "Novice", "Pantheist", "Dictator", "Benefactor", "Mortician"}


def carousel_folders(first, last):
    found = {}
    for d in SRC.iterdir():
        m = re.match(r"^(\d+)\. (.+)$", d.name)
        if d.is_dir() and m and first <= int(m[1]) <= last:
            found[int(m[1])] = d
    missing = [n for n in range(first, last + 1) if n not in found]
    if missing:
        raise SystemExit(f"No folder for carousel(s) {missing} in {SRC}")
    return [found[n] for n in sorted(found)]


def slug_of(folder):
    n, word = re.match(r"^(\d+)\. (.+)$", folder.name).groups()
    return f"{int(n):03d}-" + re.sub(r"[^a-z0-9]+", "-", word.lower()).strip("-"), word


def slides_of(folder):
    slides = [folder / f"{folder.name} - {i:02d}.png" for i in range(1, SLIDES + 1)]
    missing = [p.name for p in slides if not p.exists()]
    if missing:
        raise SystemExit(f"{folder.name}: missing {missing}")
    return slides


def to_jpeg(png, jpg):
    im = Image.open(png).convert("RGB")
    if im.size != (1080, 1440):
        raise SystemExit(f"{png}: {im.size[0]}x{im.size[1]}, expected 1080x1440")
    top, bottom = im.crop((0, 0, 1080, CROP_BOX[1])), im.crop((0, CROP_BOX[3], 1080, 1440))
    if min(top.convert("L").getextrema()[0], bottom.convert("L").getextrema()[0]) < 110:
        print(f"  WARN {png.name}: something dark in the part being cropped off, check {jpg}")
    im.crop(CROP_BOX).save(jpg, "JPEG", quality=92, optimize=True)


def caption_of(word):
    return f"{word} னா {'யாரு' if word in PEOPLE else 'என்ன'}? | Root words in Tamil | Word Power Made Easy in Tamil"


def slots_from(start):
    t = datetime.strptime(start, "%Y-%m-%d %H:%M")
    if t.strftime("%H:%M") not in SLOTS:
        raise SystemExit(f"--start must be at one of the slots {SLOTS}")
    i = SLOTS.index(t.strftime("%H:%M"))
    day = t.date()
    while True:
        yield f"{day} {SLOTS[i]}"
        i += 1
        if i == len(SLOTS):
            i, day = 0, day + timedelta(days=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--start", required=True, help='first slot, e.g. "2026-11-02 09:17" (IST)')
    args = ap.parse_args()

    posted = set()
    if (HERE / "posted.csv").exists():
        with open(HERE / "posted.csv", encoding="utf-8", newline="") as f:
            posted = {r["slug"] for r in csv.DictReader(f)}

    rows, slots = [], slots_from(args.start)
    for folder in carousel_folders(args.first, args.last):
        slug, word = slug_of(folder)
        dest = OUT / slug
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for i, png in enumerate(slides_of(folder), 1):
            to_jpeg(png, dest / f"{i:02d}.jpg")
        slot = "" if slug in posted else next(slots)
        rows.append({"slot": slot, "slug": slug, "slides": SLIDES, "word": word, "caption": caption_of(word)})
        print(f"{slot or 'posted':16}  {slug}  {caption_of(word)}")

    with open(HERE / "schedule.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["slot", "slug", "slides", "word", "caption"], lineterminator="\n")
        w.writeheader()
        w.writerows(r for r in rows if r["slot"])
    size = sum(p.stat().st_size for p in OUT.rglob("*.jpg")) / 2**20
    print(f"\n{sum(1 for r in rows if r['slot'])} carousels queued, {size:.0f} MB of JPEGs in {OUT}")


if __name__ == "__main__":
    main()
