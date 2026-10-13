#!/usr/bin/env python3
"""Step 3 feasibility probe: Irish news channels on YouTube via the official Data API only.
Resolves handles (channels.list forHandle, 1 unit each), lists last-24h uploads
(playlistItems.list, 1 unit each), fetches metadata (videos.list, 1 unit / 50),
Quota is counted locally. The API key is read from the prism-us repo .env and never printed."""
import json, os, sys, datetime as dt
from pathlib import Path
import urllib.request, urllib.parse

ENV = Path.home()/"github"/"prism-us"/".env"
key = None
for line in ENV.read_text().splitlines():
    if line.startswith("YOUTUBE_API_KEY="):
        key = line.split("=",1)[1].strip().strip('"').strip("'"); break
assert key, "no key"
OUT = Path.home()/"Work"/"prism"/"gppn-gpc-1013"/"prototype"/"data"
OUT.mkdir(parents=True, exist_ok=True)
quota = 0
def api(method, **params):
    global quota
    params["key"] = key
    url = f"https://www.googleapis.com/youtube/v3/{method}?" + urllib.parse.urlencode(params)
    quota += 1
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)

HANDLES = ["rtenews","rte","VirginMediaNews","irishtimes","IrishIndependent","independent.ie",
           "thejournal_ie","TheJournalie","NewstalkFM","newstalk","irishexaminer","griptmedia","gript",
           "theditch","OireachtasTV","breakingnewsie","sundayworld","TodayFM","irishmirror","extraie",
           "TG4TV","TheIrishSun","businesspost","farmersjournal","dublinlive","irishlegalnews"]
now = dt.datetime.now(dt.timezone.utc)
w24 = now - dt.timedelta(hours=24); w7 = now - dt.timedelta(days=7)
channels = []; not_found = []
for h in HANDLES:
    try:
        r = api("channels", part="snippet,contentDetails,statistics", forHandle=h)
    except Exception as e:
        not_found.append((h, f"err {e}")); continue
    items = r.get("items") or []
    if not items: not_found.append((h,"no channel")); continue
    it = items[0]
    channels.append({"handle": h, "channel_id": it["id"], "title": it["snippet"]["title"],
        "country": it["snippet"].get("country"), "subscribers": int(it["statistics"].get("subscriberCount",0) or 0),
        "video_count": int(it["statistics"].get("videoCount",0) or 0),
        "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"]})
# channels resolved through search.list (resolve_ie_search.py) — real outlets whose handle guess failed
_res = json.load(open(OUT/"ie_search_resolved.json"))["resolved"] if (OUT/"ie_search_resolved.json").exists() else []
_keep = {"Virgin Media News","The Journal","Irish Independent","VideoParliament Ireland","Irish Mirror"}
for rr in _res:
    if rr["title"] in _keep and rr["channel_id"] not in {c["channel_id"] for c in channels}:
        channels.append({"handle": "(search) "+rr["query"], "channel_id": rr["channel_id"], "title": rr["title"], "country": rr.get("country"),
                         "subscribers": rr["subs"], "video_count": None, "uploads": rr["uploads"]})
# drop handle hits that are not the outlet (impostor or empty channels, under 1,000 subscribers)
impostors = [c for c in channels if (c["subscribers"] or 0) < 1000]
channels = [c for c in channels if (c["subscribers"] or 0) >= 1000]
# dedupe by channel_id (two handles may hit one channel)
seen=set(); uniq=[]
for c in channels:
    if c["channel_id"] in seen: continue
    seen.add(c["channel_id"]); uniq.append(c)
channels = uniq
vids24 = []; vids7 = 0
for c in channels:
    page=None; c24=[]; c7=0; stop=False; pages=0
    while not stop and pages < 3:
        params=dict(part="contentDetails,snippet", playlistId=c["uploads"], maxResults=50)
        if page: params["pageToken"]=page
        try: r = api("playlistItems", **params)
        except Exception as e: c["error"]=str(e)[:80]; break
        pages+=1
        for it in r.get("items") or []:
            pub = it["contentDetails"].get("videoPublishedAt") or it["snippet"]["publishedAt"]
            t = dt.datetime.fromisoformat(pub.replace("Z","+00:00"))
            if t >= w24: c24.append({"video_id": it["contentDetails"]["videoId"], "published_at": pub, "channel": c["title"], "title": it["snippet"]["title"]})
            if t >= w7: c7 += 1
            else: stop=True
        page = r.get("nextPageToken")
        if not page: break
    c["videos_24h"]=len(c24); c["videos_7d"]=c7; vids24 += c24; vids7 += c7
# metadata for 24h videos
ids=[v["video_id"] for v in vids24]
meta={}
for i in range(0,len(ids),50):
    r = api("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i+50]), maxResults=50)
    for it in r.get("items") or []:
        s=it.get("statistics",{}); meta[it["id"]]={"view_count": int(s.get("viewCount",0) or 0), "comment_count": int(s.get("commentCount",0) or 0) if "commentCount" in s else None,
            "duration": it["contentDetails"].get("duration"), "caption_flag": it["contentDetails"].get("caption"), "default_audio_language": it["snippet"].get("defaultAudioLanguage")}
for v in vids24: v.update(meta.get(v["video_id"],{}))
res={"impostor_or_empty_handles":[{"handle":c["handle"],"title":c["title"],"subscribers":c["subscribers"]} for c in impostors],"probed_at_utc": now.isoformat(), "window_24h_start": w24.isoformat(), "handles_tried": HANDLES, "not_found": not_found,
     "channels": channels, "videos_24h": vids24, "videos_7d_total": vids7, "quota_units_used": quota}
(OUT/"ie_probe.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
print(f"handles tried {len(HANDLES)} · resolved {len(channels)} channels · not found {len(not_found)}: {[h for h,_ in not_found]}")
for c in channels: print(f"  {c['title'][:34]:34} subs {c['subscribers']:>9,} 24h {c['videos_24h']:>3} 7d {c['videos_7d']:>3} country {c['country']}")
print(f"videos in last 24h: {len(vids24)} · last 7d: {vids7} · quota used: {quota}")
