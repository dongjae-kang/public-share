/* YouTube Access Ledger: scenes, figures, planner, routing. Every number comes from data/facts.js (calc.py). */
(function () {
  "use strict";
  var F = window.FACTS;
  var root = document.documentElement;
  root.classList.add("js");
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function fmt(n) { return (n === null || n === undefined || n === "") ? "" : Number(n).toLocaleString("en-US"); }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function dstr(iso) { var d = new Date(iso); return d.toISOString().slice(0, 16).replace("T", " ") + " UTC"; }
  function dayOnly(iso) { return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }); }
  function dur(s) { return s.replace("PT", "").replace("H", "h ").replace("M", "m ").replace("S", "s"); }
  function $(id) { return document.getElementById(id); }

  /* ---------- count-up (masthead strip, module B) ---------- */
  function countUp(el) {
    var target = parseFloat(el.getAttribute("data-count")), pre = el.getAttribute("data-prefix") || "", suf = el.getAttribute("data-suffix") || "", dec = +(el.getAttribute("data-dec") || 0);
    var show = function (v) { el.textContent = pre + (dec ? v.toFixed(dec) : Math.round(v).toLocaleString("en-US")) + suf; };
    if (reduced) { show(target); return; }
    var t0 = null, T = target > 10000 ? 1100 : 850;
    function step(ts) { if (!t0) t0 = ts; var p = Math.min(1, (ts - t0) / T); p = 1 - Math.pow(1 - p, 3); show(target * p); if (p < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }
  (function () {
    var els = document.querySelectorAll("#strip [data-count]");
    if ("IntersectionObserver" in window && !reduced) {
      var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); countUp(e.target); } }); }, { threshold: 0.4 });
      els.forEach(function (el) { io.observe(el); });
    } else { els.forEach(countUp); }
  })();

  /* ---------- scenes: the step card nearest the middle of the screen sets the stage ---------- */
  var sceneHandlers = {};
  function setupScene(scene) {
    var steps = [].slice.call(scene.querySelectorAll(".step"));
    var name = scene.getAttribute("data-scene");
    function activate(k) {
      scene.setAttribute("data-step", k);
      steps.forEach(function (s) { s.classList.toggle("on", +s.getAttribute("data-step") === k); });
      if (sceneHandlers[name]) sceneHandlers[name](k);
    }
    if (!("IntersectionObserver" in window)) { activate(0); return; }
    // The stage is on the right on wide screens (band = middle of the viewport); on narrow screens it is
    //   sticky at the top, so the band sits in the part of the screen the cards scroll through, below it.
    var narrow = window.matchMedia && window.matchMedia("(max-width: 999px)").matches;
    var band = narrow ? [0.64, 0.84] : [0.42, 0.58]; // the slice of the viewport a card must cross to become the step
    var inBand = {};
    // Several cards can enter or leave the band in one callback (layout settles after fonts load, or a long
    //   scroll). Keep the set of cards in the band and pick the one nearest its middle, so the last entry
    //   in the batch does not win by accident and a card that left the band does not stay active.
    function choose() {
      var mid = window.innerHeight * (band[0] + band[1]) / 2, best = -1, bd = Infinity;
      Object.keys(inBand).forEach(function (k) {
        if (!inBand[k]) return;
        var r = steps[k].querySelector(".card").getBoundingClientRect(), c = (r.top + r.bottom) / 2, d = Math.abs(c - mid);
        if (d < bd) { bd = d; best = +k; }
      });
      if (best >= 0) activate(+steps[best].getAttribute("data-step"));
    }
    var obs = new IntersectionObserver(function (es) {
      es.forEach(function (e) { inBand[steps.indexOf(e.target)] = e.isIntersecting; });
      choose();
    }, { rootMargin: (-band[0] * 100) + "% 0px " + (-(1 - band[1]) * 100) + "% 0px", threshold: 0 });
    steps.forEach(function (s) { obs.observe(s); });
    activate(0);
  }

  /* ---------- chapter 01: matrix + receipt ---------- */
  var VIDS = F.videos, DL = F.captions_download, cur = 0, routeStep = 0;
  var STEPNAME = ["A · Video metadata", "B · Caption text", "C · View counts over time", "D · Public comments", "E · Beyond the specification"];
  function av(src) { return src ? '<img class="av" src="' + src + '" alt="" width="18" height="18" loading="lazy">' : ''; }
  function shortStory(v) { if (!v.story) return "Irish probe"; var m = F.spread.stories.filter(function (st) { return st.title === v.story; })[0]; return m ? m.short : v.story; }
  function pickBtns() {
    var html = "";
    // Eight videos = the top video of each October 12 story plus two Irish ones, so each button is named by
    //   its story (two stories share MeidasTouch as their top channel) and carries the channel as its avatar.
    VIDS.forEach(function (v, i) { html += '<button type="button" data-i="' + i + '" title="' + esc(v.ch + ' · ' + v.title) + '"' + (i === cur ? ' class="on"' : '') + '>' + av(v.avatar) + (v.set === "IE" ? esc(v.ch) + ' <small>IE</small>' : esc(shortStory(v))) + '</button>'; });
    $("vidpick").innerHTML = html;
  }
  function receipt() {
    var v = VIDS[cur], h = "", last = v.reads[v.reads.length - 1][1];
    $("vidhead").innerHTML = av(v.avatar) + '<b>' + esc(v.ch) + '</b> · ' + esc(shortStory(v)) + ' · ' + esc(v.title) + ' · published ' + dstr(v.pub) + ' · <a href="https://www.youtube.com/watch?v=' + v.id + '" target="_blank" rel="noopener">watch?v=' + v.id + '</a>';
    $("rc-cost").textContent = STEPNAME[routeStep];
    if (routeStep === 0) {
      h += '<div class="req">GET youtube/v3/<b>videos</b>?part=snippet,statistics,contentDetails&id=' + v.id + '&key=REDACTED</div>';
      h += '<div class="resp"><span class="k">status</span> <span class="okk">200</span> · <span class="k">cost</span> <span class="v">1 unit</span><br>'
        + '<span class="k">snippet.title</span> <span class="v">"' + esc(v.title) + '"</span><br>'
        + '<span class="k">snippet.channelTitle</span> <span class="v">"' + esc(v.ch) + '"</span><br>'
        + '<span class="k">snippet.publishedAt</span> <span class="v">"' + v.pub + '"</span><br>'
        + '<span class="k">snippet.description</span> <span class="v">"' + esc(v.desc) + '"</span><br>'
        + '<span class="k">snippet.tags</span> <span class="v">' + esc(JSON.stringify(v.tags)) + '</span><br>'
        + '<span class="k">contentDetails.duration</span> <span class="v">"' + v.dur + '"</span> <span class="k">= ' + dur(v.dur) + '</span><br>'
        + '<span class="k">statistics.viewCount</span> <span class="v">"' + last + '"</span><br>'
        + '<span class="k">statistics.likeCount</span> <span class="v">"' + v.likes + '"</span><br>'
        + '<span class="k">statistics.commentCount</span> ' + (v.comments === null ? '<span class="err">absent (comments disabled)</span>' : '<span class="v">"' + v.comments + '"</span>') + '</div>';
      h += '<div class="verdict">Every field the watch page shows, in one call. Finding the channel in the first place is the cost the API does not cover: <code>search.list</code> is capped at 100 calls a day.</div>';
    } else if (routeStep === 1) {
      var tr = v.tracks.map(function (t) { return '<span class="v">{ language: "' + t[0] + '", trackKind: "' + t[1] + '" }</span>'; }).join("<br>");
      h += '<div class="req">GET youtube/v3/<b>captions</b>?part=snippet&videoId=' + v.id + '&key=REDACTED</div>';
      h += '<div class="resp"><span class="k">status</span> <span class="okk">200</span> · <span class="k">items</span> <span class="v">' + v.tracks.length + '</span> · <span class="k">cost</span> <span class="v">50 units</span><br>' + tr + '<br><span class="k">contentDetails.caption</span> <span class="v">"' + v.caption_flag + '"</span> <span class="k">= has a non-asr track</span></div>';
      h += '<div class="req">GET youtube/v3/<b>captions</b>/' + (v.id === DL.video ? 'AUieDaa…zi0g' : '{caption id}') + '?key=REDACTED <span class="k">(download)</span></div>';
      h += '<div class="resp">' + (v.id === DL.video ? '' : '<span class="k">as recorded for the MeidasTouch track; the documentation states the same requirement for every video</span><br>')
        + '<span class="k">status</span> <span class="err">401</span><br><span class="k">error.message</span> <span class="err">"' + esc(DL.message) + '"</span><br><span class="k">errors[0].message</span> <span class="err">"' + esc(DL.detail) + '"</span> · <span class="k">reason</span> <span class="err">"' + DL.reason + '"</span> · <span class="k">status</span> <span class="err">"' + DL.status2 + '"</span></div>';
      h += '<div class="verdict">The API lists <b>' + v.tracks.length + ' track' + (v.tracks.length > 1 ? 's' : '') + '</b> for this video' + (v.tracks.some(function (t) { return t[1] === "asr"; }) ? ', including the platform\'s auto track,' : '') + ' and refuses the text. The player plays the same track to anyone.</div>';
    } else if (routeStep === 2) {
      h += '<div class="req">GET youtube/v3/<b>videos</b>?part=statistics&id=' + v.id + '&key=REDACTED <span class="k">× ' + v.reads.length + ', one per reading</span></div>';
      var rh = ""; v.reads.forEach(function (r, k) { if (k > 0) rh += '<div class="gap"></div>'; rh += '<div class="r"><div class="v">' + fmt(r[1]) + '</div><div class="t">' + dstr(r[0]).replace(" UTC", "").slice(5) + ' UTC</div></div>'; });
      h += '<div class="readings">' + rh + '</div>';
      var first = new Date(v.reads[0][0]), exp = new Date(first.getTime() + 30 * 86400000), left = Math.ceil((exp - new Date()) / 86400000);
      h += '<div class="clock' + (left <= 0 ? ' expired' : '') + '">' + (left > 0
        ? 'first reading ' + dayOnly(v.reads[0][0]) + ' · delete or refresh by <b>' + dayOnly(exp.toISOString()) + '</b> · <b>' + left + ' day' + (left === 1 ? '' : 's') + ' left</b>'
        : 'first reading ' + dayOnly(v.reads[0][0]) + ' · <b>30 days have passed</b>: under III.E.4.b these readings should by now have been deleted or refreshed') + '</div>';
      h += '<div class="verdict">Each reading is <code>statistics.viewCount</code> at the moment of the call. Nothing between two readings can be recovered, and the clock counts from the first reading of this video.</div>';
    } else if (routeStep === 3) {
      h += '<div class="req">GET youtube/v3/<b>commentThreads</b>?part=snippet&videoId=' + v.id + '&maxResults=5&order=time&key=REDACTED</div>';
      if (v.ct.status === 200) {
        h += '<div class="resp"><span class="k">status</span> <span class="okk">200</span> · <span class="k">cost</span> <span class="v">1 unit per page of up to 100</span><br><span class="k">items</span> <span class="v">' + v.ct.n + '</span> <span class="k">(text and authors not stored here)</span><br><span class="k">nextPageToken</span> <span class="v">present</span><br><span class="k">pageInfo.totalResults</span> <span class="v">' + v.ct.total + '</span> <span class="k">= the page size, not the total</span><br><span class="k">items[0]…publishedAt</span> <span class="v">"' + v.ct.newest + '"</span><br><span class="k">order accepted</span> <span class="v">' + v.ct.orders.join(", ") + '</span> <span class="k">(no oldest-first)</span></div>';
        h += '<div class="verdict">Returned, one page at a time. No count of pages and no way to start from the first comment. The page shows ' + fmt(v.comments) + ' comments; the API counted the same.</div>';
      } else {
        h += '<div class="resp"><span class="k">status</span> <span class="err">' + v.ct.status + '</span><br><span class="k">errors[0].reason</span> <span class="err">"' + v.ct.reason + '"</span><br><span class="k">message</span> <span class="err">"' + esc(v.ct.message) + '"</span></div>';
        h += '<div class="verdict">This channel turned comments off for the video, which the page shows as "comments are turned off". On October 12, ' + F.const.night.disabled_in_collection + ' of the ' + fmt(F.const.night.videos_collected) + ' videos whose comments the pipeline collected (' + F.const.night.disabled_in_collection_pct + '%) answered this way; in the Irish probe, ' + F.irish.disabled_24h + ' of ' + F.irish.videos_24h + '.</div>';
      }
    } else {
      h += '<div class="resp"><span class="k">community posts</span> <span class="err">no endpoint in the Data API</span><br><span class="k">impressions, watch time, why it was shown</span> <span class="err">not in the public API; Art. 40(4) vetted access only</span></div>';
      h += '<div class="verdict">There is no request to send. For this video, as for every other, the public route ends at what the watch page already shows.</div>';
    }
    $("rc-body").innerHTML = h;
  }
  function showVid(i) { cur = i; pickBtns(); receipt(); }
  function setMatrix(k) {
    var rows = document.querySelectorAll("#matrix tr.row");
    [].forEach.call(rows, function (r) { r.classList.toggle("on", +r.getAttribute("data-step") === k); });
    $("matrix").classList.add("dim");
    routeStep = k; receipt();
  }
  sceneHandlers.route = setMatrix;
  $("vidpick").addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) showVid(+b.getAttribute("data-i")); });
  [].forEach.call(document.querySelectorAll("#matrix tr.row"), function (r) {
    r.addEventListener("click", function () { var k = +r.getAttribute("data-step"); var el = document.querySelector('#route-steps .step[data-step="' + k + '"]'); if (el) el.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" }); });
  });
  showVid(0);

  /* ---------- chapter 02: switching panels, dumbbell chart, repeated comment ---------- */
  var S = F.const.story;
  $("outs").innerHTML = S.framing.map(function (f) { return '<li><b>' + esc(f[0]) + '</b><span class="fr">' + esc(f[1]) + '</span></li>'; }).join("");
  (function () {
    var R = F.repeat, h = "";
    if (R) {
      R.instances.forEach(function (x) {
        h += '<a class="rv" href="https://www.youtube.com/watch?v=' + x.video_id + '" target="_blank" rel="noopener" title="' + esc(x.title) + '">'
          + '<span class="th"><img src="' + x.thumb + '" alt="" loading="lazy" width="320" height="180"></span>'
          + '<span class="rc">' + av(x.avatar) + '<span class="rn">' + esc(x.channel) + '</span></span>'
          + '<span class="rt">' + x.comment_at.slice(11, 19) + '</span></a>';
      });
      var m = Math.floor(R.span_seconds / 60), sec = Math.round(R.span_seconds % 60);
      $("repbrace").textContent = "the same comment, posted " + R.first_seen.slice(11, 19) + " to " + R.last_seen.slice(11, 19) + " UTC, " + m + " min " + sec + " s apart · at most " + R.max_like + " likes on any copy";
    } else {
      for (var i = 0; i < S.repeat_videos; i++) h += '<i data-ch="video ' + (i + 1) + '"></i>';
    }
    $("repvids").innerHTML = h;
    $("liked").innerHTML = S.most_liked.map(function (m) { return '<li><span>' + esc(m[0]) + '</span><b>' + fmt(m[1]) + ' likes</b></li>'; }).join("");
  })();
  // Chapter 02 figures unfold once, when they come into view (Jack 10/26: bars fill, dots and lines appear
  //   one by one, the six videos arrive in order). Everything is drawn at rest; the CSS under `.mf.in` adds
  //   the motion, and reduced-motion settings skip it.
  (function () {
    var figs = document.querySelectorAll(".mod .mf");
    function reveal(f) {
      if (f.classList.contains("in")) return;
      f.classList.add("in");
      [].forEach.call(f.querySelectorAll("[data-count]"), function (c) { setTimeout(function () { countUp(c); }, reduced ? 0 : 120); });
    }
    if (!("IntersectionObserver" in window) || reduced) { [].forEach.call(figs, reveal); return; }
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); reveal(e.target); } }); }, { threshold: 0.3 });
    [].forEach.call(figs, function (f) { io.observe(f); });
  })();

  // dumbbell: six stories, two readings, log axis
  (function () {
    var sp = F.spread, W = 640, L = 172, R = 78, rowH = 40, T = 30, H = T + rowH * sp.stories.length + 32;
    var lo = Math.log10(4e5), hi = Math.log10(3e7);
    function x(v) { return L + (W - L - R) * (Math.log10(v) - lo) / (hi - lo); }
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Views of six stories at two readings 16.6 hours apart, on a logarithmic axis">';
    [5e5, 1e6, 3e6, 1e7, 3e7].forEach(function (t) { s += '<line class="ax" x1="' + x(t) + '" x2="' + x(t) + '" y1="' + (T - 6) + '" y2="' + (H - 24) + '"/><text class="axl" x="' + x(t) + '" y="' + (H - 10) + '" text-anchor="middle">' + (t >= 1e6 ? (t / 1e6) + 'M' : (t / 1e3) + 'K') + '</text>'; });
    s += '<text class="shl" x="' + x(5e5) + '" y="' + (T - 12) + '">VIEWS, READING 1 (04:43 UTC) → READING 2 (21:21 UTC)</text>';
    sp.stories.forEach(function st(d, i) {
      var y = T + rowH * i + rowH / 2, x0 = x(d.v0), x1 = x(d.v1), curc = d.external_id === S.external_id;
      s += '<g class="row' + (curc ? ' cur' : '') + '" data-i="' + i + '" style="--d:' + (i * 0.22).toFixed(2) + 's" tabindex="0" data-tip="' + esc(d.title) + '&#10;' + fmt(d.v0) + ' → ' + fmt(d.v1) + ' views · ' + sp.hours + ' h · ' + d.n + ' videos">';
      s += '<rect class="hit" x="0" y="' + (y - rowH / 2) + '" width="' + W + '" height="' + rowH + '"/>';
      s += '<text class="lbl" x="0" y="' + (y + 1) + '">' + esc(d.short) + '</text><text class="sub" x="0" y="' + (y + 15) + '">' + d.n + ' videos</text>';
      s += '<line class="ln" x1="' + x0 + '" y1="' + y + '" x2="' + x1 + '" y2="' + y + '"/>';
      s += '<circle class="d0" cx="' + x0 + '" cy="' + y + '" r="4.5"/><circle class="d1" cx="' + x1 + '" cy="' + y + '" r="5"/>';
      s += '<text class="pct" x="' + (x1 + 10) + '" y="' + (y + 4) + '">+' + d.pct + '%</text></g>';
    });
    s += '</svg>';
    var cap = '<figcaption>Each story\'s YouTube videos, summed. Hollow dot = reading 1, filled dot = reading 2, ' + sp.hours + ' hours later; the line between them is the interval no call returns. All ' + sp.n_videos + ' videos: ' + (sp.total_v0 / 1e6).toFixed(1) + 'M → ' + (sp.total_v1 / 1e6).toFixed(1) + 'M views (+' + sp.total_pct + '%); per video the median change was +' + sp.median_pct + '% and ' + sp.doubled + ' videos at least doubled. The highlighted row is the story of this filing.</figcaption>';
    $("dumb").innerHTML = s + cap;
    [].forEach.call(document.querySelectorAll("#dumb .ln"), function (el) { try { var l = el.getTotalLength(); el.style.setProperty("--len", l + 2); } catch (e) { } });
  })();

  // tooltip that follows the pointer
  (function () {
    var tip = $("tip");
    function show(el, e) { tip.textContent = el.getAttribute("data-tip"); tip.classList.add("show"); move(e, el); }
    function move(e, el) {
      var x = e && e.clientX !== undefined ? e.clientX + 14 : el.getBoundingClientRect().left, y = e && e.clientY !== undefined ? e.clientY + 14 : el.getBoundingClientRect().top;
      var r = tip.getBoundingClientRect();
      if (x + r.width > window.innerWidth - 8) x = (e ? e.clientX : x) - r.width - 14;
      if (y + r.height > window.innerHeight - 8) y = (e ? e.clientY : y) - r.height - 14;
      tip.style.left = x + "px"; tip.style.top = y + "px";
    }
    function hide() { tip.classList.remove("show"); }
    [].forEach.call(document.querySelectorAll("[data-tip]"), function (el) {
      el.addEventListener("pointerenter", function (e) { show(el, e); });
      el.addEventListener("pointermove", function (e) { move(e, el); });
      el.addEventListener("pointerleave", hide);
      el.addEventListener("focus", function () { show(el, null); });
      el.addEventListener("blur", hide);
    });
  })();

  /* ---------- chapter 03: planner + eligibility ---------- */
  var IE = F.irish.outlets, sel = IE.map(function () { return true; }), maxV = Math.max.apply(null, IE.map(function (o) { return o.v24; }));
  function drawPlan() {
    var tb = document.querySelector("#plantable tbody"), html = "";
    IE.forEach(function (o, i) {
      html += '<tr' + (sel[i] ? '' : ' class="off"') + '><td><label><input type="checkbox" data-i="' + i + '"' + (sel[i] ? ' checked' : '') + '>' + av(o.avatar) + '<span>' + esc(o.label) + (o.found === "search" ? '<span class="tag">search</span>' : '') + '</span></label></td><td class="r">' + fmt(o.subs) + '</td><td class="r"><i class="ib" style="width:' + Math.round(40 * o.v24 / maxV) + 'px"></i>' + o.v24 + '</td><td class="r">' + fmt(o.c24) + '</td><td class="r">' + o.pg + '</td></tr>';
    });
    tb.innerHTML = html;
    var n = 0, v = 0, c = 0, pg = 0; IE.forEach(function (o, i) { if (sel[i]) { n++; v += o.v24; c += o.c24; pg += o.pg; } });
    var lookups = Math.ceil(n / 50), playlist = n, vids = Math.ceil(v / 50), units = lookups + playlist + vids + pg;
    $("p-units").textContent = fmt(units);
    $("p-pct").textContent = (units / 100).toFixed(1) + "%";
    $("p-6m").textContent = fmt(units * 183);
    $("p-vid").textContent = fmt(v);
    $("p-com").textContent = fmt(c);
    var m = $("p-meter"); m.classList.toggle("over", units > 10000); m.firstElementChild.style.width = Math.min(100, units / 100) + "%";
    $("p-formula").innerHTML = "channel lookups " + lookups + " + playlist pages " + playlist + " + video batches " + vids + " (" + v + " / 50) + comment pages " + pg + " = <b>" + fmt(units) + " units a day</b>; 183 days = " + fmt(units * 183) + ". Comment pages are counted per video at 1 page per 100 comments, at least one page for every video whose comments are on, from the counts the API returned.";
  }
  document.querySelector("#plantable").addEventListener("change", function (e) { var cb = e.target.closest("input[type=checkbox]"); if (cb) { sel[+cb.getAttribute("data-i")] = cb.checked; drawPlan(); } });
  drawPlan();

  var TEAMS = {
    "us-uni": { label: "a university team in New York", e1: [true, "Named: researchers who meet paragraph 8 points (b) to (e). The text has no affiliation test and no residence test."], e2: [false, "\"This programme is currently only available for researchers affiliated with an EU-based institution.\" A New York institution is not EU-based."], e3: [true, "\"affiliated with an accredited, higher-education institution that can grant degrees\"; the United States is on the list of 60 countries."] },
    "ie-uni": { label: "a university team in Dublin", e1: [true, "Named: researchers who meet paragraph 8 points (b) to (e)."], e2: [true, "An EU-based institution; the page lists the Art. 40(8) conditions, and \"Individual platform teams may have additional eligibility requirements\"."], e3: [true, "A degree-granting institution; Ireland is on the list of 60 countries."] },
    "ie-npo": { label: "a not-for-profit newsroom in Dublin", e1: [true, "Named expressly: \"including those affiliated to not for profit bodies, organisations and associations\"."], e2: [true, "The page lists \"affiliated with not for profit bodies, organizations and associations\" and requires an EU-based institution; a Dublin not-for-profit is EU-based. Whether a newsroom counts as an institution is for the platform to decide."], e3: [false, "Not \"an accredited, higher-education institution that can grant degrees\"."] },
    "us-npo": { label: "a not-for-profit in the United States", e1: [true, "Named expressly: \"including those affiliated to not for profit bodies, organisations and associations\"."], e2: [false, "Not affiliated with an EU-based institution."], e3: [false, "Not an accredited degree-granting institution."] }
  };
  function setTeam(key) {
    var t = TEAMS[key];
    [].forEach.call(document.querySelectorAll("#teamseg button"), function (b) { b.classList.toggle("on", b.getAttribute("data-team") === key); });
    ["e1", "e2", "e3"].forEach(function (k) { $(k + "-r").innerHTML = t[k][0] ? '<span class="pass">OPEN</span>' : '<span class="fail">CLOSED</span>'; $(k + "-w").textContent = t[k][1]; });
    var opens = ["e2", "e3"].filter(function (k) { return t[k][0]; }).length;
    $("eligsum").innerHTML = "For " + t.label + ": the legal entitlement is there in every case; of the two routes Google operates today, " + opens + " of 2 " + (opens === 1 ? "is" : "are") + " open. Neither route returns caption text or a view history; the Researcher Program returns metadata, and the DSA page does not list fields.";
  }
  $("teamseg").addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) setTeam(b.getAttribute("data-team")); });
  setTeam("us-uni");

  /* ---------- position: rail (wide), bar (narrow), chapter progress ---------- */
  var chapters = [].slice.call(document.querySelectorAll("section.chapter[data-ch]"));
  var railLis = [].slice.call(document.querySelectorAll("#rail li")), barLinks = [].slice.call(document.querySelectorAll(".bar nav a"));
  var fills = railLis.map(function (li) { return li.querySelector(".rb i b"); });
  function goChapter(i) { var el = chapters[i]; if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 8, behavior: reduced ? "auto" : "smooth" }); }
  railLis.forEach(function (li, i) {
    li.querySelector(".rn").addEventListener("click", function () { goChapter(i); });
    li.querySelector(".rb").addEventListener("click", function (e) {
      var r = e.currentTarget.getBoundingClientRect(), f = e.clientY ? (e.clientY - r.top) / r.height : 0, el = chapters[i];
      var top = el.getBoundingClientRect().top + window.scrollY, h = el.offsetHeight;
      window.scrollTo({ top: top + Math.max(0, Math.min(1, f)) * Math.max(0, h - window.innerHeight * 0.6), behavior: reduced ? "auto" : "smooth" });
    });
  });
  var raf = 0;
  function paint() {
    raf = 0;
    var y = window.scrollY, H = window.innerHeight, curCh = -1, inAny = false;
    chapters.forEach(function (el, i) {
      var top = el.getBoundingClientRect().top + y, h = el.offsetHeight, p = (y + H * 0.4 - top) / Math.max(1, h);
      if (fills[i]) fills[i].style.transform = "scaleY(" + Math.max(0, Math.min(1, p)).toFixed(3) + ")";
      if (p >= 0 && p < 1) { curCh = i; inAny = true; }
    });
    var tail = document.getElementById("terms"), tailTop = tail ? tail.getBoundingClientRect().top + y : Infinity;
    $("rail").classList.toggle("on", inAny && y + H * 0.4 < tailTop);
    railLis.forEach(function (li, i) { li.classList.toggle("on", i === curCh); });
    barLinks.forEach(function (a, i) { a.classList.toggle("on", i === curCh); });
    if (curCh >= 0) { $("bar-n").textContent = "0" + (curCh + 1); $("bar-t").textContent = chapters[curCh].getAttribute("data-title"); }
    else if (y + H * 0.4 >= tailTop) { $("bar-n").textContent = y + H * 0.4 >= (document.getElementById("method").getBoundingClientRect().top + y) ? "05" : "04"; $("bar-t").textContent = $("bar-n").textContent === "05" ? "Method and sources" : "The terms"; }
    else { $("bar-n").textContent = "00"; $("bar-t").textContent = "Start"; }
  }
  function kick() { if (!raf) raf = requestAnimationFrame(paint); }
  window.addEventListener("scroll", kick, { passive: true });
  window.addEventListener("resize", kick);

  /* ---------- routing: the hashes the proposal links to, plus old deep links ---------- */
  var ALIAS = { ledger: "ledger", exhibit2: "ledger", overview: "ledger", matrix: "ledger", step1: "ledger", demo1: "ledger", start: "top",
    brief: "brief", demo2: "brief", step2: "brief",
    ireland: "ireland", demo3: "ireland", step3: "ireland", calculator: "ireland", quota: "ireland", eligibility: "who",
    metadata: "route-a", transcripts: "route-b", captions: "route-b", views: "route-c", comments: "route-d", "demo1-q1": "route-a", "demo1-q2": "route-b", "demo1-q3": "route-c", "demo1-q4": "route-d", "demo3-cannot": "cannot",
    night: "method", sources: "method", terms: "terms", method: "method" };
  function openFor(hash) {
    var h = (hash || "").replace(/^#/, ""); if (!h) return;
    var id = ALIAS[h] || h, el = document.getElementById(id); if (!el) return;
    var isStep = el.classList.contains("step");
    var top = el.getBoundingClientRect().top + window.scrollY - (isStep ? window.innerHeight * 0.25 : 8);
    window.scrollTo({ top: Math.max(0, top), behavior: "instant" });
  }
  document.querySelectorAll(".scene").forEach(setupScene);
  addEventListener("hashchange", function () { openFor(location.hash); kick(); });
  // after fonts and layout settle, land where the link points
  function land() { openFor(location.hash); kick(); }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { setTimeout(land, 30); }); else setTimeout(land, 120);
  window.addEventListener("load", function () { setTimeout(land, 50); });
  kick();
})();
