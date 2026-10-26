#!/usr/bin/env python3
"""Derive every number the ledger page shows from data/*.json, and write data/facts.js.

Two layers, kept apart on purpose:
  DERIVED  = recomputed here from the four recorded files (api_record, view_snapshots_aggregate,
             ie_probe, ie_search_resolved). Re-run this script and the page's figures follow.
  CONST    = measured once on Oct 12-13, 2026 by the nightly pipeline (counts that live in the
             team's run logs, not in data/). Each carries a `src` label. They are not re-derivable
             from data/, so they are copied, never edited by hand elsewhere.

Usage: python3 calc.py            -> writes data/facts.js, prints a summary
       python3 calc.py --check    -> also greps index.html for each headline number
"""
import json, math, sys, re
from pathlib import Path

HERE = Path(__file__).parent
D = HERE / "data"

api = json.loads((D / "api_record.json").read_text())
snap = json.loads((D / "view_snapshots_aggregate.json").read_text())
probe = json.loads((D / "ie_probe.json").read_text())
search = json.loads((D / "ie_search_resolved.json").read_text())

# ---------------------------------------------------------------- CONST (pipeline logs, Oct 12 news day)
CONST = {
    "night": {
        "news_day": "2026-10-12",
        "window": "04:00 UTC Oct 12 to 04:00 UTC Oct 13",
        "universe_channels": 485, "channels_published": 398, "universe_locked": "June 28",
        "videos_24h": 5889, "units_metadata": 1028, "units_metadata_pct": 10.3,
        "units_arith_floor": 613,
        "comments_counted": 553191, "videos_with_comments": 3965, "videos_with_comments_pct": 66,
        "comments_collected": 205613, "videos_collected": 1049, "units_comments": 2338, "units_comments_pct": 23,
        "stories_selected": 6, "disabled_in_collection": 35, "disabled_in_collection_pct": 3.3,
        "discover_items": 5983, "discover_sources": 426,
        "src": "pipeline run log, Oct 12 news day (07_phase2a_24h_fetch.py, collect_comments.py); discover count from PROGRESS.md 00:43",
    },
    # One story, as cooked on Oct 13 from the same run (card data). Live card stats re-read Oct 26, 2026:
    # videos 208, outlets 83, total_views 9,774,739 (matches).
    "story": {
        "external_id": "trend_2026-10-12_backlash-grows-over-trump-s-russian-diesel-d",
        "url": "https://prism-news.org/en/today/trend_2026-10-12_backlash-grows-over-trump-s-russian-diesel-d",
        "title": "Bipartisan backlash grows over Trump's Russian diesel deal as Zelenskyy says Russia violated the energy ceasefire",
        "items": 208, "outlets": 83, "youtube": 198, "podcast": 10,
        "origin": "Bloomberg Television", "origin_date": "October 12",
        "top_two": "MeidasTouch and CNN", "top_two_share_pct": 31, "dominant_channel_share_pct": 23.4,
        "peak_channel": "MeidasTouch", "peak_views": 1008850,
        "comment_sample": 34685, "repeat_videos": 6, "repeat_channels": 5, "repeat_minutes": 6, "repeat_max_likes": 11,
        "repeat_text": "Why isn't Putin speaking for himself instead of letting Trump speak on his behalf?",
        "most_liked": [["CNN", 1086], ["MeidasTouch", 876], ["MeidasTouch", 791]],
        "framing": [
            ["BBC News", "led with Zelenskyy's statement that Russia hit a power plant after the ceasefire was declared"],
            ["The Damage Report", "folded the deal into a multi-topic episode in which Trump “angers republicans” with a “fake ceasefire”"],
            ["Forbes Breaking News", "put Trump's response to Republican criticism first"],
        ],
        "src": "card data cooked Oct 13, 2026 from the Oct 12 run; live card re-read Oct 26 (208 / 83 / 9,774,739 match)",
    },
}

# The six stories of Oct 12, in the order of view_snapshots_aggregate.json. Card ids re-read from the
# public API on Oct 26, 2026 (/api/v1/public/topics?locale=en). Short names are for chart labels only.
CONST["stories"] = [
    {"short": "Russian diesel deal", "external_id": "trend_2026-10-12_backlash-grows-over-trump-s-russian-diesel-d"},
    {"short": "Ilhan Omar raid", "external_id": "trend_2026-10-12_federal-agents-raid-rep-ilhan-omar-s-home-in"},
    {"short": "Taxpayer-funded ads halted", "external_id": "trend_2026-10-12_federal-judge-halts-trump-administration-s-t"},
    {"short": "Talarico, Texas Senate", "external_id": "trend_2026-10-12_james-talarico-returns-to-the-texas-senate-c"},
    {"short": "Goliath roller coaster", "external_id": "trend_2026-10-12_man-dies-after-falling-from-goliath-roller-c"},
    {"short": "South Carolina debate", "external_id": "trend_2026-10-12_south-carolina-u-s-senate-debate-between-gra"},
]
KEYS = ["diesel", "Omar", "taxpayer", "Talarico", "Goliath", "South Carolina"]

# ---------------------------------------------------------------- DERIVED
def fmt(n): return f"{n:,}"

# 1) the eight videos (chapter 01)
vids = []
for v in api["videos"]:
    f = v["videos_list"]["fields"]
    reads = [[v["t0_utc"], v["t0_views"]]]
    if v["t1_utc"]: reads.append([v["t1_utc"], v["t1_views"]])
    reads.append([v["recorded_at_utc"], int(f["statistics.viewCount"])])
    ct = v["comment_threads"]
    vids.append({
        "id": v["video_id"], "set": v["set"], "ch": v["channel"], "story": v["story"],
        "title": f["snippet.title"], "pub": f["snippet.publishedAt"], "dur": f["contentDetails.duration"],
        "desc": f["snippet.description"], "tags": f["snippet.tags"], "lang": f["snippet.defaultAudioLanguage"],
        "caption_flag": f["contentDetails.caption"],
        "likes": int(f["statistics.likeCount"]),
        "comments": (int(f["statistics.commentCount"]) if f["statistics.commentCount"] is not None else None),
        "tracks": [[t["language"], t["trackKind"]] for t in v["captions_list"]["tracks"]],
        "reads": reads,
        "ct": ({"status": 200, "n": ct["items_on_page"], "next": ct["has_next_page"], "total": ct["pageInfo"]["totalResults"],
                "newest": ct["newest_published_at"], "orders": ct["orders_available"]} if ct["status"] == 200
               else {"status": ct["status"], "reason": ct["error"]["errors"][0]["reason"],
                     "message": re.sub(r"<[^>]+>", "", ct["error"]["message"])}),
    })
dl = api["captions_download_attempt"]
captions_download = {"video": dl["video_id"], "caption_id": dl["caption_id"], "status": dl["status"],
                     "message": dl["response"]["error"]["message"], "detail": dl["response"]["error"]["errors"][0]["message"],
                     "reason": dl["response"]["error"]["errors"][0]["reason"], "status2": dl["response"]["error"]["status"]}
eight = {"recorded_at": api["recorded_at_utc"], "units": api["quota_units_used"], "n": len(vids),
         "us": sum(1 for v in vids if v["set"] == "US"), "ie": sum(1 for v in vids if v["set"] == "IE")}

# 2) two readings of 586 videos (chapter 02 spread)
stories = snap["stories"]
tot0 = sum(s["views_t0"] for s in stories); tot1 = sum(s["views_t1"] for s in stories)
spread = {
    "t0": snap["t0_utc"], "t1": snap["t1_utc"], "hours": snap["hours_between"], "n_videos": snap["n_videos"],
    "stories": [{"title": s["title"], "n": s["n_youtube"], "v0": s["views_t0"], "v1": s["views_t1"],
                 "pct": round((s["views_t1"] / s["views_t0"] - 1) * 100, 1)} for s in stories],
    "total_v0": tot0, "total_v1": tot1, "total_pct": round((tot1 / tot0 - 1) * 100, 1),
    "median_pct": snap["per_video_growth"]["median_pct"], "p90_pct": snap["per_video_growth"]["p90_pct"],
    "doubled": snap["per_video_growth"]["at_least_doubled"],
}
assert sum(s["n_youtube"] for s in stories) == snap["n_videos"], "story video counts must sum to n_videos"
for k, d, c in zip(KEYS, spread["stories"], CONST["stories"]):
    assert k in d["title"], (k, d["title"])
    d["short"] = c["short"]; d["external_id"] = c["external_id"]
    d["url"] = "https://prism-news.org/en/today/" + c["external_id"]
for s, d in zip(stories, spread["stories"]):
    assert abs(s["change_pct"] - d["pct"]) < 0.11, (s["title"], s["change_pct"], d["pct"])

# 3) the Irish probe (chapter 03 planner)
by_handle = {c["title"] for c in probe["channels"] if c["handle"] not in {"search"}}
resolved_titles = {r["title"] for r in search["resolved"]}
ie = []
for c in probe["channels"]:
    vs = [v for v in probe["videos_24h"] if v["channel"] == c["title"]]
    assert len(vs) == c["videos_24h"], (c["title"], len(vs), c["videos_24h"])
    c24 = sum((v["comment_count"] or 0) for v in vs)
    # pages = one call per 100 threads, at least one call for every video whose comments are on
    pg = sum(max(1, math.ceil((v["comment_count"] or 0) / 100)) for v in vs if v["comment_count"] is not None)
    disabled = sum(1 for v in vs if v["comment_count"] is None)
    ie.append({"name": c["title"], "handle": c["handle"], "subs": c["subscribers"], "v24": c["videos_24h"], "v7": c["videos_7d"],
               "c24": c24, "pg": pg, "disabled": disabled, "found": "search" if c["title"] in resolved_titles else "handle"})
# display names as on the page (two long titles shortened, same channel)
NAMES = {"RTÉ - IRELAND’S NATIONAL PUBLIC SERVICE MEDIA": "RTÉ (main channel)", "VideoParliament Ireland": "VideoParliament Ireland (Oireachtas)"}
for r in ie: r["label"] = NAMES.get(r["name"], r["name"])
def plan(rows):
    n = len(rows); v = sum(r["v24"] for r in rows); c = sum(r["c24"] for r in rows); pg = sum(r["pg"] for r in rows)
    lookups = math.ceil(n / 50); playlist = n; vb = math.ceil(v / 50)
    units = lookups + playlist + vb + pg
    return {"n": n, "videos": v, "comments": c, "pages": pg, "lookups": lookups, "playlist": playlist, "batches": vb,
            "units": units, "pct": round(units / 100, 1), "six_months": units * 183}
irish = {
    "probed_at": probe["probed_at_utc"], "window_start": probe["window_24h_start"], "units": probe["quota_units_used"],
    "search_units": search["quota_units_used"], "search_calls": search["search_calls"],
    "videos_24h": len(probe["videos_24h"]), "videos_7d": probe["videos_7d_total"],
    "disabled_24h": sum(1 for v in probe["videos_24h"] if v["comment_count"] is None),
    "found_by_handle": sum(1 for r in ie if r["found"] == "handle"), "found_by_search": sum(1 for r in ie if r["found"] == "search"),
    "by_search": [r["label"] for r in ie if r["found"] == "search"],
    "lookalikes": [[i["handle"], i["subscribers"]] for i in probe["impostor_or_empty_handles"]],
    "handles_tried": len(probe["handles_tried"]), "not_found": len(probe["not_found"]),
    "outlets": ie, "all": plan(ie),
}
assert len(probe["videos_24h"]) == sum(r["v24"] for r in ie)

# channel avatars (fetch_logos.py, optional): file per channel id, joined by video id and by Irish channel id
try:
    ch = json.loads((D / "channels.json").read_text())
    for v in vids:
        cid = ch["videos"].get(v["id"]); v["channel_id"] = cid
        v["avatar"] = ch["channels"].get(cid, {}).get("file")
    for r in ie:
        cid = next(c["channel_id"] for c in probe["channels"] if c["title"] == r["name"]); r["channel_id"] = cid
        r["avatar"] = ch["channels"].get(cid, {}).get("file")
    logos = {"fetched_at": ch["fetched_at_utc"], "units": ch["units"], "n": len(ch["channels"])}
except FileNotFoundError:
    logos = None

# the repeated comment's six videos (fetch_repeat.py, optional)
try:
    rep = json.loads((D / "repeat.json").read_text())
    assert rep["n_videos"] == CONST["story"]["repeat_videos"] and rep["n_channels"] == CONST["story"]["repeat_channels"] and rep["max_like"] == CONST["story"]["repeat_max_likes"]
    assert rep["span_seconds"] <= CONST["story"]["repeat_minutes"] * 60, rep["span_seconds"]
except FileNotFoundError:
    rep = None

facts = {"logos": logos, "repeat": rep, "generated_from": ["data/api_record.json", "data/view_snapshots_aggregate.json", "data/ie_probe.json", "data/ie_search_resolved.json"],
         "const": CONST, "eight": eight, "videos": vids, "captions_download": captions_download, "spread": spread, "irish": irish}
out = "// Generated by calc.py from data/*.json. Do not edit by hand.\nwindow.FACTS = " + json.dumps(facts, ensure_ascii=False, indent=1) + ";\n"
(D / "facts.js").write_text(out)

print("eight videos:", eight)
print("captions.download:", captions_download["status"], captions_download["reason"])
print("spread totals:", fmt(tot0), "->", fmt(tot1), f"+{spread['total_pct']}%  median {spread['median_pct']}%  doubled {spread['doubled']} of {spread['n_videos']}")
for s in spread["stories"]: print(f"  {s['n']:>4} vids  {fmt(s['v0']):>11} -> {fmt(s['v1']):>11}  +{s['pct']}%  {s['title'][:60]}")
print("irish:", {k: irish[k] for k in ("units", "search_units", "videos_24h", "videos_7d", "disabled_24h", "found_by_handle", "found_by_search")})
for r in ie: print(f"  {r['label']:38s} subs={r['subs']:>7} v24={r['v24']:>3} c24={r['c24']:>4} pg={r['pg']:>3} {r['found']}")
print("planner all 12:", irish["all"])
print("wrote", D / "facts.js", (D / "facts.js").stat().st_size, "bytes")

if "--check" in sys.argv:
    html = (HERE / "index.html").read_text()
    keys = {"5,889": CONST["night"]["videos_24h"], "1,028": CONST["night"]["units_metadata"], "553,191": CONST["night"]["comments_counted"],
            "205,613": CONST["night"]["comments_collected"], "466": eight["units"], "16.6": spread["hours"],
            f"{spread['total_pct']}": 1, "9,774,739": CONST["story"]["items"], "12.68M": 1, "29.7": 1, "141": spread["doubled"],
            "85": irish["videos_24h"], "43": irish["units"], "1,008,850": CONST["story"]["peak_views"], "34,685": CONST["story"]["comment_sample"]}
    miss = [k for k in keys if k not in html]
    print("check index.html:", "all present" if not miss else f"MISSING {miss}")
