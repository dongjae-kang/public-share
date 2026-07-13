#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build prism-us/card.html (Today's Issue cards, US real data) from the review batch.

- Design source (spec): the v16 card design already in prism-us/card.html
  (glass .gcard / .tstrip / .mod / .pers / .chat / .clist / deck 3D peek / .drail).
  CSS classes and values are reused verbatim; only the data is US.
- Data source: ~/Desktop/prism-us-review-batch1-0713.html  ->  const CARDS=[...]
- Hard rule: never invent. If a datum is absent, the element is dropped, and the
  drop is listed in the page's bottom note.
    * no spread curve  (no time series in the batch)
    * no MDS scatter   (no 2D coordinates in the batch)
    * no thumbnails in 03 (perspectives carry no video link)
"""
import json, html, re, datetime, pathlib

SRC = pathlib.Path("/Users/jackkang/Desktop/prism-us-review-batch1-0713.html")
OUT = pathlib.Path("/Users/jackkang/github/public-share/prism-us/card.html")
DESIGN = OUT  # the current card.html is the design source; we read its <style> block

# US 6-category taxonomy colors — taken from prism-us/home.html (.fcat), not invented.
ISSUE = {
    "diplomacy": ("Foreign Policy & Security", "#0c4a6e"),
    "justice":   ("Justice & Courts",          "#581c87"),
    "society":   ("Society",                   "#7c2d12"),
}
# opinion-group colors — existing card.html 04 palette
GC = ["#3730A3", "#065F46", "#92400E"]


def e(s):
    return html.escape(str(s), quote=True)


def views(n):
    if n is None:
        return None
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return f"{n:,}"


def vid(link):
    m = re.search(r"[?&]v=([\w-]{6,})", link or "")
    return m.group(1) if m else None


def load_cards():
    s = SRC.read_text(encoding="utf-8")
    i = s.index("const CARDS=") + len("const CARDS=")
    cards, _ = json.JSONDecoder().raw_decode(s[i:])
    return cards


def style_block():
    """Lift the <style>…</style> of the existing v16 card as-is (design = spec)."""
    s = DESIGN.read_text(encoding="utf-8")
    a = s.index("<style>")
    b = s.index("</style>") + len("</style>")
    return s[a:b]


def quote(q):
    q = q.strip()
    # batch stores repeated-comment quotes clipped at ~200 chars
    if len(q) >= 195 and q[-1] not in ".!?”\"'":
        q += "…"
    return q


# ── modules ────────────────────────────────────────────────────────────────────
def mh(num, title, sub):
    n = f'<span class="mnum">{num}</span>' if num else ""
    s = f'<span class="msub">{e(sub)}</span>' if sub else ""
    return f'<div class="mh">{n}<span class="mt">{e(title)}</span>{s}</div>'


def m_head(c):
    st = c["stats"]
    sec = dict(c["sections"])
    stat = (f'Collected · {st["outlets"]} outlets · {st["videos"]} videos · '
            f'{views(st["views"])} views · {st["comments"]:,} comments')
    return f'''  <div class="chead">
    <h2 class="ctitle">{e(c["title"])}</h2>
    <p class="csub">{e(c["subtitle"])}</p>
    <p class="clead">{e(sec["Overview"])}</p>
    <div class="cstat">{e(stat)}</div>
  </div>'''


def m_strip(c):
    cells = []
    for f in c["framing"]:
        v = vid(f["link"])
        if not v:
            continue
        # two shapes in the data: (a) channel + view count, title is a synthetic
        # label ("Fox News (117,828 views)") -> show channel + views, no title;
        # (b) view=None, channel==title == real video headline -> show headline only.
        if f.get("view") is not None:
            meta = (f'<div class="tmeta"><b>{e(f["channel"])}</b>'
                    f'<span>{views(f["view"])} views</span></div>')
            ttl = ""
        else:
            meta = ""
            ttl = f'<div class="ttl">{e(f["title"])}</div>'
        cells.append(f'''<a class="tcell" href="{e(f["link"])}" target="_blank" rel="noopener">
  <div class="tth"><img loading="lazy" src="https://i.ytimg.com/vi/{v}/mqdefault.jpg" alt=""></div>
  {meta}{ttl}
</a>''')
    if not cells:
        return ""
    return '  <div class="tstrip">' + "".join(cells) + "</div>\n"


def m_spread(c):
    sec = dict(c["sections"])
    o = c.get("origin_line") or ""
    m = re.match(r"(.*?):\s*(.+?)\s*\((.+)\)\s*$", o)
    if m:
        oline = (f'<div class="oline">{e(m.group(1))}&ensp;<b>{e(m.group(2))}</b>'
                 f'&ensp;<span class="otime">{e(m.group(3))}</span></div>')
    elif o:
        oline = f'<div class="oline">{e(o)}</div>'
    else:
        oline = ""

    bar = ""
    sc = c.get("spread_caveat") or ""
    mb = re.search(r"Top 2 channels \((.+?)\).*?about (\d+)%", sc)
    if mb:
        chans, pct = mb.group(1), int(mb.group(2))
        bar = (f'<div class="shbar"><div class="shfill" style="width:{pct}%"></div></div>\n'
               f'    <div class="shlab"><span>Top 2 channels · {e(chans)} <b>{pct}%</b></span>'
               f'<span>All others {100-pct}%</span></div>')
    body = f'<p class="ptext">{e(sec["Spread"])}</p>' if sec.get("Spread") else ""
    return f'''  <div class="mod">
    {mh("01","Spread & Origin","Where it started, who amplified it")}
    {oline}
    {body}
    {bar}
  </div>'''


def m_story(c):
    return f'''  <div class="mod">
    {mh("02","The Story","Enough to understand it from this card alone")}
    <p class="dtext">{e(c["detail"])}</p>
  </div>'''


def m_lenses(c):
    ax = (c.get("axis") or {}).get("axis")
    axis_html = ""
    if ax and ax.get("axis_name"):
        axis_html = (f'<div class="axis">Where the coverage split — <b>{e(ax["axis_name"])}</b>: '
                     f'{e(ax.get("pole_a_label",""))} vs {e(ax.get("pole_b_label",""))}.</div>')
    rows = []
    colors = [("#1e1b4b", "rgba(79,70,229,0.28)", "rgba(79,70,229,0.16)", "rgba(79,70,229,0.04)"),
              ("#134e4a", "rgba(13,148,136,0.28)", "rgba(13,148,136,0.16)", "rgba(13,148,136,0.04)"),
              ("#9f1239", "rgba(225,29,72,0.28)", "rgba(225,29,72,0.16)", "rgba(225,29,72,0.04)")]
    for i, p in enumerate(c["perspectives"][:3]):
        pc, pcs, pct, pct2 = colors[i]
        rows.append(f'''<div class="prow" style="--pc:{pc};--pcs:{pcs};--pct:{pct};--pct2:{pct2}">
  <div class="pbody">
    <div class="pch"><b>{e(p["channel"])}</b><span class="pv">{p["views"]:,} views</span></div>
    <div class="pq">“{e(p["title"])}”</div>
  </div>
</div>''')
    if not rows:
        return ""
    return f'''  <div class="mod">
    {mh("03","Media Lenses","The same event, different angles")}
    {axis_html}
    <div class="pers">{"".join(rows)}</div>
  </div>'''


def m_reactions(c):
    sec = dict(c["sections"])
    d = c["debate"]
    dist = d.get("distribution") or {}
    lead = f'<p class="ptext">{e(sec["Reaction"])}</p>' if sec.get("Reaction") else ""

    dist_html = ""
    if dist and dist.get("a") and dist.get("b"):
        groups = [(d.get("a_label") or "Group A", dist["a"]["n"], GC[0]),
                  (d.get("b_label") or "Group B", dist["b"]["n"], GC[1])]
        nn = (dist.get("neither") or {}).get("n")
        if nn:
            groups.append(("Neither / other", nn, GC[2]))
        tot = sum(g[1] for g in groups) or 1
        bars = "".join(f'<i style="width:{g[1]/tot*100:.1f}%;background:{g[2]}"></i>' for g in groups)
        legs = "".join(f'<span class="gleg"><i style="background:{g[2]}"></i>{e(g[0])}'
                       f'<em>{g[1]/tot*100:.0f}%</em></span>' for g in groups)
        tip = (f'How this split is produced: comments from the top-viewed videos are pooled '
               f'({dist.get("pool_considered")} comments considered), each is assigned to an '
               f'opinion group by an LLM, and the shares are counted in code '
               f'(method: {dist.get("method")}).')
        dist_html = (f'<div class="glegrow"><span class="glab">Opinion split</span>'
                     f'<div class="gbarwrap" tabindex="0"><div class="gbar">{bars}</div>'
                     f'<div class="gtip">{e(tip)}</div></div></div>'
                     f'<div class="gleglist">{legs}</div>')
    elif d.get("reason"):
        dist_html = (f'<p class="ptext">No opposing opinion groups were separated in this card’s '
                     f'comment pool (pipeline result: <b>{e(d["reason"])}</b>). The split bar is '
                     f'therefore not shown.</p>')

    # bubbles: reception carries text/likes/channel. Color only when the exact text
    # also appears in debate a_comments / b_comments — otherwise neutral.
    a_set = set(d.get("a_comments") or [])
    b_set = set(d.get("b_comments") or [])
    bubs = []
    for i, r in enumerate(c["reception"]):
        side = "bl" if i % 2 == 0 else "br"
        if r["text"] in a_set:
            col, lab = GC[0], d.get("a_label")
        elif r["text"] in b_set:
            col, lab = GC[1], d.get("b_label")
        else:
            col, lab = None, None
        if col:
            rgb = tuple(int(col[k:k+2], 16) for k in (1, 3, 5))
            bg = f'background:rgba({rgb[0]},{rgb[1]},{rgb[2]},0.09);border-color:rgba({rgb[0]},{rgb[1]},{rgb[2]},0.35)'
            pill = f'<div class="gpill" style="color:{col}"><i style="background:{col}"></i>{e(lab)}</div>'
            bub = f'<div class="bub" style="{bg}">{pill}'
        else:
            bub = '<div class="bub tn">'
        bubs.append(f'''<div class="brow {side}">
  {bub}
    <div class="qt">{e(r["text"])}</div>
    <div class="qm"><span class="ql">♥ {r["likes"]:,}</span><span>{e(r["channel"])}</span></div>
  </div>
</div>''')
    chat = f'<div class="chat">{"".join(bubs)}</div>' if bubs else ""
    cav = f'<p class="caveat">{e(c["reception_caveat"])}</p>' if c.get("reception_caveat") else ""
    return f'''  <div class="mod">
    {mh("04","Reactions","What the audience said")}
    {lead}
    {dist_html}{chat}
    {cav}
  </div>'''


def m_patterns(c):
    """05 — observation only. No judgment vocabulary (bot / brigading / coordination)."""
    if c.get("patterns_none") or not c.get("patterns"):
        st = c["stats"]
        body = (f'<p class="onone">No repeated-comment pattern above threshold (the same wording '
                f'from several accounts, or one account reposting the same text) was '
                f'<b>observed</b> in this card’s comment pool '
                f'(<b>{st["videos"]}</b> videos · <b>{st["comments"]:,}</b> comments).</p>'
                f'<p class="oinv">The absence is reported as-is. It is a fact about the collected '
                f'sample and says nothing about activity outside it.</p>')
        return f'''  <div class="mod">
    {mh("05","Repeated Comments","Observed across the whole comment pool, not the quotes above")}
    {body}
  </div>'''

    multi = [p for p in c["patterns"] if p["kind"] == "multi_account_repeat"]
    single = [p for p in c["patterns"] if p["kind"] != "multi_account_repeat"]
    secs = []
    if multi:
        rows = []
        for p in multi:
            rows.append(f'''      <div class="orow">
        <p class="osent">The same wording appeared in <b>{p["n_comments"]}</b> comments posted from '''
                        f'''<b>{p["n_accounts"]}</b> different accounts.</p>
        <p class="oq">“{e(quote(p["quote"]))}”</p>
      </div>''')
        secs.append(f'''    <div class="osec">
      <div class="ohead"><span class="ochip multi">Repeated across accounts</span>'''
                    f'''<span class="ocount">{len(multi)} observed</span><span class="orule"></span></div>
{"".join(rows)}
    </div>''')
    if single:
        rows = []
        for i, p in enumerate(single):
            who = "One account" if i == 0 else "Another account"
            rows.append(f'''      <div class="orow">
        <p class="osent">{who} posted the same text on <b>{p["n_comments"]}</b> occasions.</p>
        <p class="oq">“{e(quote(p["quote"]))}”</p>
      </div>''')
        secs.append(f'''    <div class="osec">
      <div class="ohead"><span class="ochip single">Single-account repost</span>'''
                    f'''<span class="ocount">{len(single)} observed</span><span class="orule"></span></div>
{"".join(rows)}
    </div>''')
    note = ('<p class="caveat">This module describes <b>observations only</b>. Repetition is the fact; '
            'the reason is left open. Accounts are described anonymously and quotes are kept verbatim so '
            'the observation stays checkable. The batch stores counts and quotes only — posting times '
            'and the list of videos each comment landed on are not in this data, so they are not shown.</p>')
    return f'''  <div class="mod">
    {mh("05","Repeated Comments","Observed across the whole comment pool, not the quotes above")}
{"".join(secs)}
    {note}
  </div>'''


def m_limits(c):
    st, rel = c["stats"], (c.get("relevance") or {})
    sec = dict(c["sections"])
    scope = (f'<b>Collection scope.</b> {st["videos"]} videos from {st["outlets"]} outlets, '
             f'{st["views"]:,} views, {st["comments"]:,} comments.')
    if rel.get("n_in_cluster"):
        scope += (f' The relevance gate kept {rel.get("n_kept")} of {rel.get("n_in_cluster")} videos in the '
                  f'cluster; {len(rel.get("dropped") or [])} were dropped as a different event '
                  f'(status: {rel.get("status")}).')
    lim = f'<p>{e(sec["Limits"])}</p>' if sec.get("Limits") else ""
    return f'''  <div class="mod">
    {mh("","Limits of this card","What this card does not cover")}
    <details class="pfull"><summary>Show the three limits</summary>
      <p>{scope}</p>
      <p><b>Reception sample.</b> {e(c.get("reception_caveat") or "")}</p>
      <p><b>Repeated-comment observation.</b> Counted inside the collected comment pool only; an
         absence here is an absence in the sample, not in the world. Posting times and per-video
         locations are not preserved in this batch.</p>
      {lim}
    </details>
  </div>'''


def m_press(c):
    lis = []
    for i, s in enumerate(c["canonical"], 1):
        lis.append(f'<li><span class="cn">[{i:02d}]</span>'
                   f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["title"])}</a>'
                   f'<span class="cs">{e(s["outlet"])}</span></li>')
    if not lis:
        return ""
    return f'''  <div class="mod foot">
    {mh("","Press Coverage","")}
    <ul class="clist">{"".join(lis)}</ul>
  </div>'''


def card_html(c):
    label, color = ISSUE[c["issue"]]
    return f'''<section class="deckitem" data-date="{c["date"]}">
<div class="cardwrap">
  <div class="bookmark" style="background:{color}">{e(label)}</div>
  <article class="gcard">
{m_head(c)}
{m_strip(c)}
{m_spread(c)}
{m_story(c)}
{m_lenses(c)}
{m_reactions(c)}
{m_patterns(c)}
{m_limits(c)}
{m_press(c)}
  </article>
</div>
</section>'''


NOTE = '''  <details class="note"><summary style="cursor:pointer;font-weight:700;color:var(--ink-soft);list-style:none">◆ About this draft — what is real data, and what was left out (expand)</summary><div style="margin-top:10px">
  ① <b>Real data.</b> Every headline, subtitle, overview, story text, thumbnail, channel, view count, comment quote, like count, opinion split and press link on this page comes from the US corpus (collected 9–11 July 2026) and is pipeline output. Nothing on this page was written by hand.
  ② <b>Draft, not yet human-reviewed.</b> These are the raw LLM outputs of the pipeline, shown before editorial review. Wording, labels and category calls may still change.
  ③ <b>What is missing is left empty, not invented.</b> Two figures from the KR pilot card are absent here on purpose: the <b>spread curve</b> (the batch keeps no per-hour time series) and the <b>MDS media plane</b> (no 2D coordinates were generated). Module 03 therefore shows the three outlets as rows without a scatter plot, and without thumbnails — the perspective records carry no video link. Module 05 shows counts and quotes only: posting times and per-video locations are not in this batch. Where a card has no opinion divide, the pipeline’s own absence statement is printed instead of a bar.
  ④ <b>Categories</b> (the bookmark tab) are the pipeline’s call, mapped onto the 6-category taxonomy currently reused from KR (Society / Justice &amp; Courts / Foreign Policy &amp; Security …). The US taxonomy will be re-derived from the US corpus.
  ⑤ Module 05 (Repeated Comments) states <b>observations only</b> — no bot / brigading / coordination vocabulary exists in its phrasing table. Repetition is the fact; the reason stays open.
  </div></details>'''


def build():
    cards = load_cards()
    order = {"2026-07-11": 0, "2026-07-10": 1, "2026-07-09": 2}
    # newest date first; within a date keep the batch's own order (pipeline order)
    cards = [c for _, c in sorted(enumerate(cards), key=lambda t: (order[t[1]["date"]], t[0]))]
    dates = sorted({c["date"] for c in cards}, reverse=True)
    counts = {d: sum(1 for c in cards if c["date"] == d) for d in dates}

    rail = []
    for i, d in enumerate(dates):
        dt = datetime.date.fromisoformat(d)
        lab = dt.strftime("%b %-d (%a)")
        on = " on" if i == 0 else ""
        rail.append(f'<button class="drow{on}" data-date="{d}" onclick="showDate(\'{d}\')">'
                    f'<span>{lab}</span><em>{counts[d]}</em></button>')

    deck = "\n".join(card_html(c) for c in cards)

    doc = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRISM — Today's Issue Cards (US)</title>
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
{style_block()}
<div class="ambient"></div><div class="ambient-wash"></div>
<header class="hdr"><div class="hin">
  <div class="hleft"><img class="logo" src="prism-logo.png" alt="PRISM"><div class="tag">How the story travels<br>Recorded daily</div></div>
  <nav class="hnav"><a href="home.html">Home</a><a class="on" href="card.html">Today's Issues</a><a href="roundup.html">Issue Roundup</a></nav>
</div></header>
<nav class="drail" aria-label="Pick a date">
  <span class="drm">Date</span>
  {"".join(rail)}
</nav>
<button class="navarr left" onclick="stepCard(-1)" aria-label="Previous card">&#8592;</button>
<button class="navarr right" onclick="stepCard(1)" aria-label="Next card">&#8594;</button>
<main class="main">
  <div class="stage" id="stage">{deck}</div>
{NOTE}
</main>
<script>
// Deck 3D peek — ported from the live Deck.jsx spec (peek 80% · rotY 10° · TZ -90 · opacity .42 · blur 1.4px)
var stage=document.getElementById('stage');
var ALL=[].slice.call(document.querySelectorAll('.deckitem'));
var items=[], cur=0, total=0;
function layout(dragX){{
  dragX=dragX||0;
  items.forEach(function(el,i){{
    var diff=i-cur, isActive=diff===0, isAdj=Math.abs(diff)===1, isFar=Math.abs(diff)>=2;
    var tx=diff*80, rotY=isActive?0:Math.sign(diff)*-10, tz=isActive?0:-90;
    var dx=isActive?dragX:0;
    el.style.transform='translate3d(calc('+tx+'% + '+dx+'px), 0, '+tz+'px) rotateY('+rotY+'deg)';
    el.style.opacity=isFar?0:(isAdj?0.42:1);
    el.style.filter=isActive?'none':'blur(1.4px)';
    el.style.pointerEvents=isFar?'none':'auto';
    el.style.cursor=isAdj?'pointer':'default';
    el.style.zIndex=100-Math.abs(diff);
    el.style.visibility=isFar?'hidden':'visible';
  }});
  var al=document.querySelector('.navarr.left'),ar=document.querySelector('.navarr.right');
  al.style.opacity=cur===0?0.25:1; al.style.pointerEvents=cur===0?'none':'auto';
  ar.style.opacity=cur>=total-1?0.25:1; ar.style.pointerEvents=cur>=total-1?'none':'auto';
  if(items[cur])stage.style.height=items[cur].offsetHeight+'px';
}}
function showCard(i){{cur=i;layout();}}
function stepCard(d){{var n=cur+d;if(n<0||n>=total)return;showCard(n);}}
function showDate(d){{
  ALL.forEach(function(el){{el.style.display=(el.dataset.date===d)?'':'none';}});
  items=ALL.filter(function(el){{return el.dataset.date===d;}});
  total=items.length; cur=0;
  [].slice.call(document.querySelectorAll('.drow')).forEach(function(b){{
    b.classList.toggle('on', b.dataset.date===d);
  }});
  layout();
  window.scrollTo({{top:0,behavior:'smooth'}});
}}
ALL.forEach(function(el){{el.addEventListener('click',function(ev){{
  var i=items.indexOf(el);
  if(i>-1&&i!==cur){{ev.preventDefault();ev.stopPropagation();showCard(i);}}
}},true);}});
// swipe — 50px threshold on the active card
var sx=null,sy=null,drag=0;
stage.addEventListener('touchstart',function(ev){{sx=ev.touches[0].clientX;sy=ev.touches[0].clientY;drag=0;}},{{passive:true}});
stage.addEventListener('touchmove',function(ev){{
  if(sx===null)return;
  var dx=ev.touches[0].clientX-sx, dy=ev.touches[0].clientY-sy;
  if(Math.abs(dx)>Math.abs(dy)){{drag=dx;layout(dx*0.6);}}
}},{{passive:true}});
stage.addEventListener('touchend',function(){{
  if(Math.abs(drag)>50)stepCard(drag<0?1:-1);else layout();
  sx=sy=null;drag=0;
}});
document.addEventListener('keydown',function(ev){{
  if(ev.key==='ArrowLeft')stepCard(-1);if(ev.key==='ArrowRight')stepCard(1);
}});
if(window.ResizeObserver){{
  var ro=new ResizeObserver(function(){{if(items[cur])stage.style.height=items[cur].offsetHeight+'px';}});
  ALL.forEach(function(el){{ro.observe(el);}});
}}
showDate('{dates[0]}');
window.addEventListener('load',function(){{layout();}});
</script>
</html>
'''
    OUT.write_text(doc, encoding="utf-8")
    print("wrote", OUT, len(doc), "bytes;", len(cards), "cards;", counts)


if __name__ == "__main__":
    build()
