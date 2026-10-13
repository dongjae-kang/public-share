#!/usr/bin/env python3
"""Resolve Irish outlets whose handle guess failed, via search.list(type=channel) — the route the
Data API caps at 100 calls per day. Prints candidates; writes ie_search_resolved.json."""
import json, urllib.request, urllib.parse
from pathlib import Path
ENV = Path.home()/"github"/"prism-us"/".env"
key = next(l.split("=",1)[1].strip().strip('"') for l in ENV.read_text().splitlines() if l.startswith("YOUTUBE_API_KEY="))
OUT = Path("data"); quota=0
def api(m, **p):
    global quota; p["key"]=key; quota+=1
    with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/"+m+"?"+urllib.parse.urlencode(p), timeout=30) as r: return json.load(r)
NAMES = ["Virgin Media News","TheJournal.ie","Irish Independent","Oireachtas TV","Sunday World","Irish Mirror"]
resolved=[]; log=[]
for q in NAMES:
    r = api("search", part="snippet", type="channel", q=q, regionCode="IE", maxResults=3)
    ids=[it["snippet"]["channelId"] for it in r.get("items") or []]
    if not ids: log.append({"query":q,"candidates":[]}); continue
    c = api("channels", part="snippet,statistics,contentDetails", id=",".join(ids))
    cands=[{"channel_id":it["id"],"title":it["snippet"]["title"],"subs":int(it["statistics"].get("subscriberCount",0) or 0),"country":it["snippet"].get("country"),"uploads":it["contentDetails"]["relatedPlaylists"]["uploads"]} for it in c.get("items") or []]
    cands.sort(key=lambda x:-x["subs"])
    log.append({"query":q,"candidates":cands})
    if cands: resolved.append({**cands[0],"query":q})
json.dump({"log":log,"resolved":resolved,"quota_units_used":quota,"search_calls":len(NAMES)}, open(OUT/"ie_search_resolved.json","w"), indent=2, ensure_ascii=False)
for e in log:
    print("Q:",e["query"]); [print(f"   {c['title'][:40]:40} subs {c['subs']:>9,} {c['country']}") for c in e["candidates"]]
print("quota units used:",quota,"(search calls:",len(NAMES),")")
