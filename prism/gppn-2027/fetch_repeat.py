#!/usr/bin/env python3
"""The repeated comment of chapter 02, module F: find the six videos it landed on, and store their thumbnails.

1. Re-read the public card (/api/v1/public/topics/by-external-id) and take the first single_account_repost
   observation; match each instance (channel + title) to a video id in the card's own video list.
2. videos.list (part=snippet) for those ids: channelId and the 320 px thumbnail URL. channels.list for any
   channel not yet in data/channels.json. Thumbnails go to img/vid/, avatars to img/ch/.
Writes data/repeat.json. The API key is read from the prism-us repo .env and never printed."""
import json, urllib.request, urllib.parse, datetime as dt
from pathlib import Path

HERE = Path(__file__).parent
EXT = "trend_2026-10-12_backlash-grows-over-trump-s-russian-diesel-d"
ENV = Path.home() / "github" / "prism-us" / ".env"
key = next(l.split("=", 1)[1].strip().strip('"').strip("'") for l in ENV.read_text().splitlines() if l.startswith("YOUTUBE_API_KEY="))
units = 0

def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()
def api(ep, params):
    global units; units += 1
    p = dict(params); p["key"] = key
    return json.loads(get("https://www.googleapis.com/youtube/v3/" + ep + "?" + urllib.parse.urlencode(p)))

card = json.loads(get("https://prism-news.org/api/v1/public/topics/by-external-id/" + EXT + "?locale=en"))["data"]
obs = card["comment_patterns"]["observations"][0]
assert obs["kind"] == "single_account_repost" and obs["n_videos"] == 6
vlist = card["payload"]["vector_pipeline"]["trend"]["videos"]
def norm(s): return " ".join(s.split()).lower()
inst = []
for i in obs["instances"]:
    # the card lists each video as {video_id, title, channel: {id, title, ...}}
    m = [v for v in vlist if norm(v["title"]) == norm(i["video_title"]) and norm(v["channel"]["title"]) == norm(i["channel"])]
    assert len(m) >= 1, i
    inst.append({"video_id": m[0]["video_id"], "channel": i["channel"], "channel_id_card": m[0]["channel"]["id"], "title": i["video_title"], "comment_at": i["published_at"]})
ids = [x["video_id"] for x in inst]
vres = api("videos", {"part": "snippet", "id": ",".join(ids), "maxResults": 50})
meta = {it["id"]: it for it in vres["items"]}
(HERE / "img/vid").mkdir(parents=True, exist_ok=True)
chf = HERE / "data/channels.json"; ch = json.loads(chf.read_text())
need = []
for x in inst:
    it = meta[x["video_id"]]; sn = it["snippet"]
    x["channel_id"] = sn["channelId"]; x["video_published_at"] = sn["publishedAt"]
    th = sn["thumbnails"]; url = (th.get("medium") or th.get("default"))["url"]
    f = HERE / "img/vid" / (x["video_id"] + ".jpg"); f.write_bytes(get(url)); x["thumb"] = "img/vid/" + f.name; x["thumb_bytes"] = f.stat().st_size
    if sn["channelId"] not in ch["channels"]: need.append(sn["channelId"])
need = sorted(set(need))
if need:
    cres = api("channels", {"part": "snippet", "id": ",".join(need), "maxResults": 50})
    for it in cres["items"]:
        th = it["snippet"]["thumbnails"]; url = (th.get("default") or th.get("medium"))["url"]
        f = HERE / "img/ch" / (it["id"] + ".jpg"); f.write_bytes(get(url))
        ch["channels"][it["id"]] = {"title": it["snippet"]["title"], "file": "img/ch/" + f.name, "thumb_url": url, "bytes": f.stat().st_size}
    ch["units"] = ch.get("units", 0) + 1; ch["avatars_added_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    chf.write_text(json.dumps(ch, indent=1, ensure_ascii=False))
for x in inst: x["avatar"] = ch["channels"][x["channel_id"]]["file"]
times = sorted(x["comment_at"] for x in inst)
span = (dt.datetime.fromisoformat(times[-1].replace("Z", "+00:00")) - dt.datetime.fromisoformat(times[0].replace("Z", "+00:00"))).total_seconds()
rec = {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "units": units, "card": EXT, "quote": obs["quote"], "max_like": obs["max_like"],
       "n_videos": obs["n_videos"], "n_channels": obs["n_channels"], "first_seen": times[0], "last_seen": times[-1], "span_seconds": span, "instances": inst}
(HERE / "data/repeat.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
print("units", units, "| span", span, "s | new channels", need)
for x in inst: print(f"  {x['comment_at'][11:19]}  {x['channel']:18s} {x['video_id']}  {x['thumb_bytes']:>6} B  {x['title'][:50]}")
