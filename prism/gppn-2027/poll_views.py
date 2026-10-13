#!/usr/bin/env python3
"""Second snapshot of view counts for every video in the six Oct 12 cards.
The pipeline reads statistics once at fetch time (first snapshot, stored in the card payload).
This re-reads them now through videos.list (1 unit per 50 ids) to show what 'view counts over
time' costs and what it cannot give (no history endpoint; only what you poll yourself)."""
import json, glob, urllib.request, urllib.parse, datetime as dt
from pathlib import Path
ENV = Path.home()/"github"/"prism-us"/".env"
key = next(l.split("=",1)[1].strip().strip('"') for l in ENV.read_text().splitlines() if l.startswith("YOUTUBE_API_KEY="))
quota=0
def api(m, **p):
    global quota; p["key"]=key; quota+=1
    with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/"+m+"?"+urllib.parse.urlencode(p), timeout=30) as r: return json.load(r)
cards = sorted(glob.glob(str(Path.home()/"github/prism-us/etl/cooked/2026-10-12/topic_*.json")))
first={}; by_card={}
for f in cards:
    o=json.load(open(f)); eid=o["external_id"]
    vids=o["payload"]["vector_pipeline"]["trend"]["videos"]
    by_card[eid]={"title":o["title"],"n":len(vids),"ids":[]}
    for v in vids:
        vid=v["video_id"]
        url=v.get("url") or ""
        if "youtube.com" not in url and not (len(vid)==11 and v.get("view_count")):
            by_card[eid].setdefault("podcast_items",0); by_card[eid]["podcast_items"]+=1; continue
        first[vid]={"card":eid,"view_count_t0":v.get("view_count"),"published_at":v.get("published_at"),"channel":(v.get("channel") or {}).get("title") if isinstance(v.get("channel"),dict) else v.get("channel"),"title":v.get("title")}
        by_card[eid]["ids"].append(vid)
ids=list(first); now=dt.datetime.now(dt.timezone.utc)
second={}
for i in range(0,len(ids),50):
    r=api("videos", part="statistics", id=",".join(ids[i:i+50]), maxResults=50)
    for it in r.get("items") or []:
        s=it["statistics"]; second[it["id"]]={"view_count_t1":int(s.get("viewCount",0) or 0),"comment_count_t1":int(s["commentCount"]) if "commentCount" in s else None}
rows=[]
for vid,f in first.items():
    s=second.get(vid); rows.append({"video_id":vid, **f, **(s or {}), "missing_at_t1": s is None})
missing=[r for r in rows if r["missing_at_t1"]]
# t0 time: the card fetch (discover) ran 2026-10-13 00:43 ET = 04:43 UTC (PROGRESS.md)
t0=dt.datetime(2026,10,13,4,43,tzinfo=dt.timezone.utc)
out={"t0_utc":t0.isoformat(),"t0_note":"first snapshot = pipeline fetch at discover time (PROGRESS.md 00:43 ET)","t1_utc":now.isoformat(),"hours_between":round((now-t0).total_seconds()/3600,1),
     "n_videos":len(rows),"n_missing_at_t1":len(missing),"quota_units_used":quota,"cards":{k:{"title":v["title"],"n_items":v["n"],"n_youtube":len(v["ids"]),"podcast_items":v.get("podcast_items",0)} for k,v in by_card.items()},"rows":rows}
Path("data").mkdir(exist_ok=True); json.dump(out, open("data/view_snapshots.json","w"), indent=2, ensure_ascii=False)
tot0=sum(r["view_count_t0"] or 0 for r in rows); tot1=sum(r.get("view_count_t1") or 0 for r in rows if not r["missing_at_t1"])
print(f"videos {len(rows)} · missing at t1 {len(missing)} · quota {quota} units · hours between {out['hours_between']}")
print(f"views t0 {tot0:,} → t1 {tot1:,} (+{(tot1-tot0)/max(tot0,1):.1%})")
for eid,c in by_card.items():
    sub=[r for r in rows if r["card"]==eid]; a=sum(r["view_count_t0"] or 0 for r in sub); b=sum(r.get("view_count_t1") or 0 for r in sub if not r["missing_at_t1"]); m=sum(1 for r in sub if r["missing_at_t1"])
    print(f"  {eid[-45:]:45} n {len(sub):3} t0 {a:>10,} t1 {b:>10,} +{(b-a)/max(a,1):5.1%} missing {m}")
for r in missing[:10]: print("   missing:",r["channel"],"|",(r["title"] or "")[:60])
