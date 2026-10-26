#!/usr/bin/env python3
"""Fetch channel avatars for the eight videos (chapter 01) and the twelve Irish outlets (chapter 03).

Two Data API calls, 1 unit each: videos.list (part=snippet) to learn each video's channelId, and
channels.list (part=snippet) for the avatar URLs. The 88 px avatars are saved under img/ch/ so the page
never hotlinks Google's CDN. The key is read from the prism-us repo .env and never printed."""
import json, urllib.request, urllib.parse, datetime as dt
from pathlib import Path

HERE = Path(__file__).parent
ENV = Path.home() / "github" / "prism-us" / ".env"
key = next(l.split("=", 1)[1].strip().strip('"').strip("'") for l in ENV.read_text().splitlines() if l.startswith("YOUTUBE_API_KEY="))
units = 0

def call(ep, params):
    global units
    params = dict(params); params["key"] = key
    url = "https://www.googleapis.com/youtube/v3/" + ep + "?" + urllib.parse.urlencode(params)
    units += 1
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)

api = json.loads((HERE / "data/api_record.json").read_text())
probe = json.loads((HERE / "data/ie_probe.json").read_text())
vids = [v["video_id"] for v in api["videos"]]
vres = call("videos", {"part": "snippet", "id": ",".join(vids), "maxResults": 50})
video_channel = {it["id"]: it["snippet"]["channelId"] for it in vres["items"]}
ids = sorted(set(video_channel.values()) | {c["channel_id"] for c in probe["channels"]})
cres = call("channels", {"part": "snippet", "id": ",".join(ids), "maxResults": 50})
out = HERE / "img" / "ch"; out.mkdir(parents=True, exist_ok=True)
channels = {}
for it in cres["items"]:
    th = it["snippet"]["thumbnails"]
    url = (th.get("default") or th.get("medium"))["url"]
    f = out / (it["id"] + ".jpg")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(f, "wb") as w:
        w.write(r.read())
    channels[it["id"]] = {"title": it["snippet"]["title"], "file": "img/ch/" + f.name, "thumb_url": url, "bytes": f.stat().st_size}
rec = {"fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "units": units, "videos": video_channel, "channels": channels}
(HERE / "data/channels.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
print("units", units, "| videos", len(video_channel), "| channels", len(channels), "| missing", [i for i in ids if i not in channels])
for cid, c in channels.items(): print(f"  {c['title'][:34]:34s} {c['bytes']:>6} B")
