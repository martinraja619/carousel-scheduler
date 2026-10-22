"""Publish the next due carousel to Instagram. GitHub Actions runs this (.github/workflows/post.yml).

  python post.py post     publish the oldest carousel whose slot has passed; if none has, wait for one due
                          within WAIT_MAX minutes (the workflow starts ~15 min early to absorb GitHub's delays)
  python post.py check    test the token and the next carousel's images without publishing anything
  python post.py status   show what's next and what's been posted

Needs IG_TOKEN (an Instagram User access token with instagram_business_content_publish). Standard library only.
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
IST = timezone(timedelta(hours=5, minutes=30))
API = "https://graph.instagram.com/" + os.environ.get("IG_API_VERSION", "v26.0")
REPO = os.environ.get("GITHUB_REPOSITORY", "martinraja619/carousel-scheduler")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
IMAGE_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/carousels"
WAIT_MAX = int(os.environ.get("WAIT_MAX", "40"))
LOG_FIELDS = ["slot", "slug", "media_id", "posted_at", "permalink"]


def now():
    return datetime.now(IST)


def slot_time(row):
    return datetime.strptime(row["slot"], "%Y-%m-%d %H:%M").replace(tzinfo=IST)


def load(name):
    path = HERE / name
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def log_posted(row, media_id, permalink):
    path = HERE / "posted.csv"
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"slot": row["slot"], "slug": row["slug"], "media_id": media_id,
                    "posted_at": now().strftime("%Y-%m-%d %H:%M"), "permalink": permalink})


def pending():
    done = {r["slug"] for r in load("posted.csv")}
    return sorted((r for r in load("schedule.csv") if r["slug"] not in done), key=slot_time)


def call(method, path, **params):
    params["access_token"] = os.environ["IG_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        url, data = f"{url}?{data.decode()}", None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                err = json.loads(body)["error"]
                msg = f"{err.get('message')} (code {err.get('code')}, subcode {err.get('error_subcode')})"
                transient = err.get("is_transient") or e.code >= 500
            except (ValueError, KeyError):
                msg, transient = body[:300], e.code >= 500
            if not transient or attempt == 2:
                raise SystemExit(f"Instagram API {method} {path}: {msg}")
        except urllib.error.URLError as e:
            if attempt == 2:
                raise SystemExit(f"Network error on {method} {path}: {e.reason}")
        time.sleep(10 * (attempt + 1))


def account():
    me = call("GET", "me", fields="user_id,username")
    return me.get("user_id") or me["id"], me.get("username", "?")


def image_urls(row):
    return [f"{IMAGE_BASE}/{row['slug']}/{i:02d}.jpg" for i in range(1, int(row["slides"]) + 1)]


def caption(row):
    return row["caption"].strip()


def build_container(ig_id, row):
    children = [call("POST", f"{ig_id}/media", image_url=u, is_carousel_item="true")["id"] for u in image_urls(row)]
    container = call("POST", f"{ig_id}/media", media_type="CAROUSEL", children=",".join(children),
                     caption=caption(row))["id"]
    for _ in range(30):  # images are usually ready at once; give up after ~5 minutes
        status = call("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            return container
        if status in ("ERROR", "EXPIRED"):
            raise SystemExit(f"{row['slug']}: Instagram rejected the carousel container ({status})")
        time.sleep(10)
    raise SystemExit(f"{row['slug']}: container still not ready after 5 minutes")


def already_on_instagram(ig_id, row):
    """Guards against a double post when a run published but couldn't save posted.csv."""
    first_line = caption(row).splitlines()[0].strip()
    recent = call("GET", f"{ig_id}/media", fields="id,caption,permalink", limit="10").get("data", [])
    return next((m for m in recent if (m.get("caption") or "").strip().startswith(first_line)), None)


def post():
    queue = pending()
    if not queue:
        print("Queue is empty: everything in schedule.csv has been posted.")
        return
    row = queue[0]
    wait = (slot_time(row) - now()).total_seconds()
    if wait > WAIT_MAX * 60:
        print(f"Nothing due. Next: {row['slug']} at {row['slot']} IST.")
        return
    if wait > 0:
        print(f"Waiting {wait / 60:.0f} min for the {row['slot']} slot ({row['slug']}).")
        time.sleep(wait)

    ig_id, username = account()
    dup = already_on_instagram(ig_id, row)
    if dup:
        print(f"{row['slug']} is already on @{username} ({dup.get('permalink')}); recording it, not reposting.")
        log_posted(row, dup["id"], dup.get("permalink", ""))
        return
    container = build_container(ig_id, row)
    media_id = call("POST", f"{ig_id}/media_publish", creation_id=container)["id"]
    permalink = call("GET", media_id, fields="permalink").get("permalink", "")
    log_posted(row, media_id, permalink)
    late = (now() - slot_time(row)).total_seconds() / 60
    print(f"Posted {row['slug']} to @{username} ({late:.0f} min after its slot): {permalink}")


def check():
    ig_id, username = account()
    print(f"Token works: @{username} (id {ig_id})")
    queue = pending()
    if not queue:
        print("Queue is empty.")
        return
    row = queue[0]
    for u in image_urls(row):
        with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30) as r:
            if r.status != 200 or r.headers.get("Content-Type") != "image/jpeg":
                raise SystemExit(f"{u}: HTTP {r.status}, {r.headers.get('Content-Type')}")
    print(f"All {row['slides']} images of {row['slug']} are reachable.")
    build_container(ig_id, row)  # never published; Instagram discards it after 24 hours
    print(f"Instagram accepted {row['slug']} as a carousel (not published). Next slot: {row['slot']} IST.")
    limit = call("GET", f"{ig_id}/content_publishing_limit", fields="quota_usage,config").get("data", [{}])[0]
    print(f"API posts in the last 24 h: {limit.get('quota_usage')} of {limit.get('config', {}).get('quota_total')}")


def status():
    queue, log = pending(), load("posted.csv")
    print(f"{len(log)} posted, {len(queue)} to go" + (f", last slot {queue[-1]['slot']} IST" if queue else ""))
    late = [r for r in queue if slot_time(r) < now() - timedelta(hours=2)]
    if late:
        print(f"OVERDUE: {', '.join(r['slug'] for r in late)}")
    for r in log[-5:]:
        print(f"  posted  {r['posted_at']}  {r['slug']}  {r['permalink']}")
    for r in queue[:5]:
        print(f"  next    {r['slot']}  {r['slug']}")


if __name__ == "__main__":
    try:
        {"post": post, "check": check, "status": status}[sys.argv[1] if len(sys.argv) > 1 else "status"]()
    except (SystemExit, Exception) as e:
        msg = e.code if isinstance(e, SystemExit) else f"{type(e).__name__}: {e}"
        if msg and os.environ.get("GITHUB_ACTIONS"):
            # an annotation shows on the run's summary page (and in the public API), unlike the step log
            print(f"::error title=post.py {sys.argv[1:]}::{msg}")
        raise
