#!/usr/bin/env python3
"""Demo 1 material: for eight real videos, record what the Data API returns through the sanctioned
route only. videos.list (fields), captions.list (expected to be refused with an API key), and the
first page of commentThreads.list (counts only; no comment text, no author names are stored).
Request URLs are stored with the key redacted."""
import json, urllib.request, urllib.parse, urllib.error, datetime as dt
from pathlib import Path
ENV = Path.home()/"github"/"prism-us"/".env"
key = next(l.split("=",1)[1].strip().strip('"') for l in ENV.read_text().splitlines() if l.startswith("YOUTUBE_API_KEY="))
quota = 0
def call(method, cost=1, **p):
    global quota; quota += cost
    p["key"] = key
    url = "https://www.googleapis.com/youtube/v3/"+method+"?"+urllib.parse.urlencode(p)
    shown = url.replace(key, "REDACTED")
    try:
        with urllib.request.urlopen(url, timeout=30) as r: return {"url": shown, "status": r.status, "body": json.load(r)}
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read().decode())
        except Exception: body = None
        return {"url": shown, "status": e.code, "body": body}
# pick videos: top video (by first reading) of each Oct 12 story + top two Irish by views
vs = json.load(open("data/view_snapshots.json")); ie = json.load(open("data/ie_probe.json"))
picks = []
for card, info in vs["cards"].items():
    rows = [r for r in vs["rows"] if r["card"]==card]
    top = max(rows, key=lambda r: r["view_count_t0"] or 0)
    picks.append({"video_id": top["video_id"], "set": "US", "story": info["title"], "channel": top["channel"], "t0_views": top["view_count_t0"], "t0_utc": vs["t0_utc"], "t1_views": top["view_count_t1"], "t1_utc": vs["t1_utc"]})
for v in sorted(ie["videos_24h"], key=lambda x: -(x.get("view_count") or 0))[:2]:
    picks.append({"video_id": v["video_id"], "set": "IE", "story": None, "channel": v["channel"], "t0_views": v.get("view_count"), "t0_utc": ie["probed_at_utc"], "t1_views": None, "t1_utc": None})
now = dt.datetime.now(dt.timezone.utc).isoformat()
out = []
for p in picks:
    vid = p["video_id"]; rec = dict(p); rec["recorded_at_utc"] = now
    r = call("videos", part="snippet,statistics,contentDetails,topicDetails", id=vid)
    it = (r["body"].get("items") or [None])[0] if r["status"]==200 else None
    if it:
        sn, st, cd = it["snippet"], it["statistics"], it["contentDetails"]
        rec["videos_list"] = {"url": r["url"], "status": r["status"], "fields": {
            "snippet.title": sn.get("title"), "snippet.channelTitle": sn.get("channelTitle"), "snippet.publishedAt": sn.get("publishedAt"),
            "snippet.description": (sn.get("description") or "")[:160] + ("…" if len(sn.get("description") or "")>160 else ""),
            "snippet.tags": (sn.get("tags") or [])[:6], "snippet.defaultAudioLanguage": sn.get("defaultAudioLanguage"),
            "contentDetails.duration": cd.get("duration"), "contentDetails.caption": cd.get("caption"),
            "statistics.viewCount": st.get("viewCount"), "statistics.likeCount": st.get("likeCount"), "statistics.commentCount": st.get("commentCount"),
            "topicDetails.topicCategories": (it.get("topicDetails") or {}).get("topicCategories")}}
    else:
        rec["videos_list"] = {"url": r["url"], "status": r["status"], "error": r["body"]}
    r = call("captions", cost=50, part="snippet", videoId=vid)
    rec["captions_list"] = {"url": r["url"], "status": r["status"], "error": (r["body"] or {}).get("error") if r["status"]!=200 else None,
                            "tracks": [{"language": i["snippet"].get("language"), "trackKind": i["snippet"].get("trackKind"), "name": i["snippet"].get("name")} for i in (r["body"].get("items") or [])] if r["status"]==200 else None}
    r = call("commentThreads", part="snippet", videoId=vid, maxResults=5, order="time", textFormat="plainText")
    if r["status"]==200:
        b = r["body"]
        rec["comment_threads"] = {"url": r["url"], "status": 200, "items_on_page": len(b.get("items") or []), "has_next_page": bool(b.get("nextPageToken")),
                                  "pageInfo": b.get("pageInfo"), "newest_published_at": (b["items"][0]["snippet"]["topLevelComment"]["snippet"]["publishedAt"] if b.get("items") else None),
                                  "orders_available": ["time", "relevance"], "note": "comment text and author names not stored"}
    else:
        rec["comment_threads"] = {"url": r["url"], "status": r["status"], "error": (r["body"] or {}).get("error")}
    out.append(rec)
res = {"recorded_at_utc": now, "quota_units_used": quota, "videos": out}
json.dump(res, open("data/api_record.json","w"), indent=2, ensure_ascii=False)
print("recorded", len(out), "videos · quota", quota)
for r in out:
    vl = r["videos_list"]; cl = r["captions_list"]; ct = r["comment_threads"]
    print(f"  {r['set']} {r['video_id']} {r['channel'][:18]:18} | views t0 {r['t0_views']} now {vl.get('fields',{}).get('statistics.viewCount')} | caption flag {vl.get('fields',{}).get('contentDetails.caption')} | captions.list {cl['status']} {((cl.get('error') or {}).get('errors') or [{}])[0].get('reason') if cl.get('error') else len(cl.get('tracks') or [])} | comments {ct['status']} n={ct.get('items_on_page')} next={ct.get('has_next_page')} total={ (ct.get('pageInfo') or {}).get('totalResults') }")
