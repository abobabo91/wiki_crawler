#!/usr/bin/env python3
"""
WikiRace AI Benchmark – HTML Leaderboard Generator
Run: python generate_leaderboard.py  →  outputs leaderboard.html
"""
import json
from datetime import datetime

from .paths import LEADERBOARD_FILE, RESULTS_FILE, TESTS_FILE

RELEASE_DATES = {
    "openai/gpt-4o":                        "2024-05-13",
    "openai/gpt-4o-mini":                   "2024-07-18",
    "openai/gpt-4.1":                       "2025-04-14",
    "openai/gpt-4.1-mini":                  "2025-04-14",
    "openai/gpt-4.1-nano":                  "2025-04-14",
    "openai/gpt-5":                         "2026-02-20",
    "openai/gpt-5-mini":                    "2026-02-20",
    "openai/gpt-5.4":                       "2026-04-01",
    "openai/gpt-5.4-mini":                  "2026-04-01",
    "openai/gpt-5.4-nano":                  "2026-04-01",
    "gemini/gemini-2.0-flash":              "2025-02-05",
    "gemini/gemini-2.0-flash-lite":         "2025-02-05",
    "gemini/gemini-2.5-flash":              "2025-03-25",
    "gemini/gemini-2.5-flash-lite":         "2025-04-17",
    "gemini/gemini-3-flash-preview":        "2025-12-11",
    "gemini/gemini-3-pro-preview":          "2026-01-15",
    "gemini/gemini-3.1-flash-lite": "2026-03-10",
    "gemini/gemini-3.1-pro-preview":        "2026-03-10",
    "anthropic/claude-haiku-4-5-20251001":  "2025-10-01",
    "anthropic/claude-sonnet-4-6":          "2025-12-01",
    "anthropic/claude-opus-4-7":            "2026-02-15",
    "xai/grok-2-1212":                      "2024-12-12",
    "xai/grok-3":                           "2025-02-17",
    "xai/grok-3-mini":                      "2025-02-17",
}

TIERS = {
    "openai/gpt-4o": "Flagship",       "openai/gpt-4o-mini": "Mini",
    "openai/gpt-4.1": "Flagship",      "openai/gpt-4.1-mini": "Mini",
    "openai/gpt-4.1-nano": "Nano",     "openai/gpt-5": "Flagship",
    "openai/gpt-5-mini": "Mini",       "openai/gpt-5.4": "Flagship",
    "openai/gpt-5.4-mini": "Mini",     "openai/gpt-5.4-nano": "Nano",
    "gemini/gemini-2.0-flash": "Flash","gemini/gemini-2.0-flash-lite": "Lite",
    "gemini/gemini-2.5-flash": "Flash","gemini/gemini-2.5-flash-lite": "Lite",
    "gemini/gemini-3-flash-preview": "Flash", "gemini/gemini-3-pro-preview": "Pro",
    "gemini/gemini-3.1-flash-lite": "Lite", "gemini/gemini-3.1-pro-preview": "Pro",
    "anthropic/claude-haiku-4-5-20251001": "Haiku", "anthropic/claude-sonnet-4-6": "Sonnet",
    "anthropic/claude-opus-4-7": "Opus", "xai/grok-2-1212": "Mini", "xai/grok-3": "Flagship",
    "xai/grok-3-mini": "Mini",
}


def load_data():
    with RESULTS_FILE.open(encoding="utf-8") as f:
        results = json.load(f)
    with TESTS_FILE.open(encoding="utf-8") as f:
        tests = json.load(f)
    return results, tests


def compute_stats(results, tests):
    test_map = {t["id"]: t for t in tests}
    stats = {}
    for r in results:
        mid = r["model_id"]
        if mid not in stats:
            stats[mid] = {
                "model_id": mid, "name": r["model_name"],
                "provider": mid.split("/")[0],
                "wins": 0, "n": 0,
                "score_t": 0, "steps_t": 0, "time_t": 0,
                "diff": {"easy": [0, 0], "medium": [0, 0], "hard": [0, 0]},
                "tests": {}
            }
        s = stats[mid]
        s["n"] += 1
        s["score_t"] += r.get("score", 0)
        s["steps_t"] += r.get("steps", 0) if r.get("success") else 20
        s["time_t"]  += r.get("time", 0)
        d = r.get("difficulty", "medium")
        s["diff"][d][1] += 1
        if r.get("success"):
            s["wins"] += 1
            s["diff"][d][0] += 1
        s["tests"][str(r["test_id"])] = {
            "success": r.get("success", False),
            "steps":   r.get("steps", 0),
            "score":   r.get("score", 0),
            "time":    round(r.get("time", 0), 1),
            "start":   test_map.get(r["test_id"], {}).get("start", ""),
            "target":  r.get("target", ""),
            "diff":    d,
            "path":    r.get("path", []),
            "reasons": r.get("reasons", []),
        }

    models = []
    for mid, s in stats.items():
        n = s["n"]
        models.append({
            "model_id":     mid,
            "name":         s["name"],
            "provider":     s["provider"],
            "tier":         TIERS.get(mid, ""),
            "release_date": RELEASE_DATES.get(mid, "2025-01-01"),
            "wins":         s["wins"],
            "n":            n,
            "win_rate":     round(s["wins"] / n * 100, 1) if n else 0,
            "avg_score":    round(s["score_t"] / n, 1) if n else 0,
            "avg_steps":    round(s["steps_t"] / n, 1) if n else 0,
            "avg_time":     round(s["time_t"]  / n, 1) if n else 0,
            "by_diff": {
                k: {"w": v[0], "n": v[1],
                    "rate": round(v[0] / v[1] * 100) if v[1] else 0}
                for k, v in s["diff"].items()
            },
            "tests": s["tests"],
        })

    models.sort(key=lambda x: (-x["win_rate"], -x["avg_score"]))
    for i, m in enumerate(models):
        m["rank"] = i + 1
    return models


def build_html(models, tests, data_json, generated_at):
    total_runs = sum(m["n"] for m in models)
    best = models[0]

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>WikiRace AI Benchmark</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
:root {
  --bg:       #07070f;
  --bg2:      #0d0d1e;
  --card:     #111127;
  --border:   rgba(120,130,255,0.13);
  --text:     #e2e8f0;
  --muted:    #64748b;
  --openai:   #10b981;
  --gemini:   #60a5fa;
  --anthropic:#fb923c;
  --xai:      #a78bfa;
  --gold:     #fbbf24;
  --easy:     #22c55e;
  --medium:   #f59e0b;
  --hard:     #ef4444;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.5;min-height:100vh}

/* HEADER */
.hero{background:linear-gradient(135deg,#0d0d2e 0%,#090920 50%,#0a0a1e 100%);border-bottom:1px solid var(--border);padding:40px 24px 32px;text-align:center;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 60% 40% at 50% 0%,rgba(96,165,250,0.07) 0%,transparent 70%);pointer-events:none}
.hero-title{font-size:clamp(22px,4vw,38px);font-weight:800;letter-spacing:-0.5px;background:linear-gradient(135deg,#fff 0%,#94a3b8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:14px;color:var(--muted);margin:8px 0 20px}
.stats-row{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:8px}
.stat-chip{background:rgba(255,255,255,0.06);border:1px solid var(--border);border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600;display:flex;align-items:center;gap:6px}
.stat-chip span{color:var(--muted);font-weight:400}
.generated{font-size:11px;color:var(--muted);margin-top:8px}

/* TABS */
.tab-nav{display:flex;background:var(--bg2);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
.tab-btn{flex:1;max-width:220px;padding:14px 20px;background:none;border:none;color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;transition:all .2s}
.tab-btn:hover{color:var(--text);background:rgba(255,255,255,0.03)}
.tab-btn.active{color:var(--text);border-bottom-color:#60a5fa;background:rgba(96,165,250,0.06)}
.tab-content{display:none;padding:24px}
.tab-content.active{display:block}

/* CONTROLS */
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:20px}
.chip-group{display:flex;gap:6px;flex-wrap:wrap}
.filter-chip{padding:5px 14px;border-radius:20px;border:1px solid var(--border);background:rgba(255,255,255,0.04);color:var(--muted);font-size:12px;font-weight:600;cursor:pointer;transition:all .2s}
.filter-chip:hover{border-color:rgba(255,255,255,0.25);color:var(--text)}
.filter-chip.active{color:#fff;border-color:transparent}
.filter-chip[data-f="all"].active{background:rgba(255,255,255,0.15)}
.filter-chip[data-f="openai"].active{background:var(--openai);color:#000}
.filter-chip[data-f="gemini"].active{background:var(--gemini);color:#000}
.filter-chip[data-f="anthropic"].active{background:var(--anthropic);color:#000}
.filter-chip[data-f="xai"].active{background:var(--xai);color:#000}
.th-sort{cursor:pointer;user-select:none}
.th-sort:hover{color:#93c5fd}
.th-sort-active{color:#60a5fa}
.sort-arrow{font-size:10px;margin-left:2px;opacity:0.8}

/* INFO ICONS */
.info-icon{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px;border-radius:50%;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.15);font-size:9px;font-weight:800;cursor:help;color:var(--muted);margin-left:4px;vertical-align:middle;transition:all .15s;font-style:normal;line-height:1;flex-shrink:0}
.info-icon:hover{background:rgba(96,165,250,.2);border-color:#60a5fa;color:#60a5fa}

/* TABLE */
.table-wrap{overflow-x:auto;border-radius:12px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;background:var(--card)}
thead tr{background:rgba(255,255,255,0.04);border-bottom:1px solid var(--border)}
thead th{padding:12px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);white-space:nowrap}
thead th.r{text-align:right}
tbody tr.model-row{cursor:pointer;transition:background .15s;border-bottom:1px solid var(--border)}
tbody tr.model-row:hover{background:rgba(255,255,255,0.03)}
tbody tr.model-row.expanded{background:rgba(96,165,250,0.04)}
tbody tr.detail-row{display:none;border-bottom:1px solid var(--border)}
tbody tr.detail-row.open{display:table-row}
td{padding:12px 16px;vertical-align:middle}
td.r{text-align:right}

.rank-cell{font-weight:800;font-size:15px;width:52px}
.medal{font-size:20px}
.rank-num{color:var(--muted)}
.model-name{font-weight:700;font-size:14px}
.model-meta{display:flex;gap:6px;margin-top:3px;flex-wrap:wrap}
.tier-badge{font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;border:1px solid rgba(255,255,255,0.12);color:var(--muted)}
.provider-badge{font-size:11px;font-weight:700;padding:3px 9px;border-radius:10px}
.pv-openai{background:rgba(16,185,129,.15);color:#10b981;border:1px solid rgba(16,185,129,.3)}
.pv-gemini{background:rgba(96,165,250,.15);color:#60a5fa;border:1px solid rgba(96,165,250,.3)}
.pv-anthropic{background:rgba(251,146,60,.15);color:#fb923c;border:1px solid rgba(251,146,60,.3)}
.pv-xai{background:rgba(167,139,250,.15);color:#a78bfa;border:1px solid rgba(167,139,250,.3)}

.win-bar-wrap{display:flex;align-items:center;gap:10px;min-width:160px}
.win-bar-bg{flex:1;height:8px;background:rgba(255,255,255,0.07);border-radius:4px;overflow:hidden}
.win-bar-fill{height:100%;border-radius:4px;transition:width 1s ease}
.win-pct{font-weight:800;font-size:14px;min-width:42px;text-align:right}
.win-frac{font-size:11px;color:var(--muted);white-space:nowrap}
.score-val{font-weight:700;font-size:14px}
.steps-val{font-weight:600;font-size:14px}

.diff-mini{display:flex;gap:4px;align-items:center;flex-direction:column}
.diff-row{display:flex;gap:3px;align-items:center;font-size:10px;white-space:nowrap}
.diff-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.diff-easy{background:var(--easy)}
.diff-med{background:var(--medium)}
.diff-hard{background:var(--hard)}

.expand-btn{background:none;border:1px solid var(--border);color:var(--muted);width:26px;height:26px;border-radius:50%;cursor:pointer;font-size:12px;transition:all .2s;display:flex;align-items:center;justify-content:center}
.expand-btn:hover{border-color:#60a5fa;color:#60a5fa}

/* EXPANDED DETAIL */
.detail-inner{padding:16px 20px 20px;background:rgba(0,0,10,0.3)}
.detail-header{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px}
.test-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px}
.test-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px 12px;transition:border-color .15s}
.test-card:hover{border-color:rgba(255,255,255,0.2)}
.test-card.pass{border-left:3px solid #22c55e}
.test-card.fail{border-left:3px solid #ef4444}
.tc-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.tc-icon{font-size:14px}
.tc-diff{font-size:9px;font-weight:700;padding:1px 6px;border-radius:8px;text-transform:uppercase}
.tc-diff.easy{background:rgba(34,197,94,.15);color:#22c55e}
.tc-diff.medium{background:rgba(245,158,11,.15);color:#f59e0b}
.tc-diff.hard{background:rgba(239,68,68,.15);color:#ef4444}
.tc-route{font-size:12px;margin-bottom:4px}
.tc-route strong{color:#fff}
.tc-route span{color:var(--muted)}
.tc-stats{display:flex;gap:10px;font-size:11px;color:var(--muted)}
.tc-stats b{color:var(--text)}

/* HIGHLIGHTS */
.highlights{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin-bottom:24px}
.hl-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;position:relative;overflow:hidden}
.hl-card.gold{border-color:rgba(251,191,36,.35);box-shadow:0 0 30px rgba(251,191,36,.07)}
.hl-card.surprise{border-color:rgba(96,165,250,.3);box-shadow:0 0 20px rgba(96,165,250,.06)}
.hl-card.efficient{border-color:rgba(167,139,250,.3);box-shadow:0 0 20px rgba(167,139,250,.06)}
.hl-card.warn{border-color:rgba(239,68,68,.25);box-shadow:0 0 20px rgba(239,68,68,.05)}
.hl-icon{font-size:24px;margin-bottom:8px}
.hl-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:4px}
.hl-name{font-size:16px;font-weight:800;margin-bottom:2px}
.hl-sub{font-size:11px;color:var(--muted)}

/* CHARTS */
.charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){.charts-grid{grid-template-columns:1fr}}
.chart-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px}
.chart-title{font-size:14px;font-weight:700;margin-bottom:4px;display:flex;align-items:center;gap:6px}
.chart-sub{font-size:11px;color:var(--muted);margin-bottom:12px}
.chart-wrap{position:relative;height:340px}

/* CHART CONTROLS */
.chart-controls{display:flex;gap:16px;flex-wrap:wrap;align-items:center;padding:12px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);margin-bottom:16px}
.ctrl-group{display:flex;align-items:center;gap:8px}
.ctrl-group label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);white-space:nowrap;display:flex;align-items:center;gap:4px}
.ctrl-select{background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:5px 10px;font-size:12px;cursor:pointer;transition:border-color .15s;outline:none;-webkit-appearance:none;padding-right:24px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2364748b'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}
.ctrl-select:hover,.ctrl-select:focus{border-color:#60a5fa}
.ctrl-select option{background:#1a1a2e}
.chart-controls-hint{font-size:11px;color:var(--muted);margin-left:auto}

/* MATRIX */
.matrix-wrap{overflow-x:auto}
.matrix-table{border-collapse:separate;border-spacing:3px;min-width:max-content}
.mx-header{font-size:10px;color:var(--muted);text-align:center;padding:4px 2px;white-space:nowrap;max-width:80px;overflow:hidden;text-overflow:ellipsis;cursor:default}
.mx-model{font-size:11px;font-weight:600;padding:4px 10px 4px 4px;white-space:nowrap;text-align:right}
.mx-cell{width:36px;height:36px;border-radius:5px;cursor:pointer;transition:transform .1s,box-shadow .1s;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:rgba(255,255,255,0.7);position:relative}
.mx-cell:hover{transform:scale(1.2);box-shadow:0 4px 12px rgba(0,0,0,.4);z-index:10}
.mx-cell.pass0{background:#064e3b}
.mx-cell.pass1{background:#065f46}
.mx-cell.pass2{background:#047857}
.mx-cell.pass3{background:#059669}
.mx-cell.pass4{background:#10b981}
.mx-cell.fail{background:rgba(127,29,29,0.7)}
.mx-cell.fail0{background:#1a0505}
.diff-easy-hdr{color:#22c55e}
.diff-med-hdr{color:#f59e0b}
.diff-hard-hdr{color:#ef4444}
.mx-legend{display:flex;gap:16px;align-items:center;margin-bottom:16px;flex-wrap:wrap;font-size:11px;color:var(--muted)}
.mx-legend-swatch{display:flex;gap:6px;align-items:center}
.swatch{width:16px;height:16px;border-radius:3px}

/* RICH TOOLTIP */
#tooltip{
  position:fixed;z-index:9999;pointer-events:none;
  background:rgba(10,10,28,.97);border:1px solid rgba(96,165,250,0.2);
  border-radius:10px;padding:10px 14px;font-size:12px;line-height:1.6;
  max-width:300px;box-shadow:0 8px 40px rgba(0,0,0,.6);
  opacity:0;transition:opacity .15s;color:var(--text);
}
#tooltip b{color:#60a5fa}

/* RUN SIDEBAR */
#sidebar-overlay{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.45);opacity:0;pointer-events:none;transition:opacity .25s}
#sidebar-overlay.open{opacity:1;pointer-events:auto}
#run-sidebar{position:fixed;top:0;right:-420px;width:390px;height:100vh;background:var(--card);border-left:1px solid rgba(96,165,250,0.18);z-index:10000;overflow-y:auto;padding:28px 24px;transition:right .25s cubic-bezier(.4,0,.2,1);box-shadow:-12px 0 50px rgba(0,0,0,0.6)}
#run-sidebar.open{right:0}
.sb-close{position:absolute;top:16px;right:16px;background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;padding:4px 8px;border-radius:4px;line-height:1}
.sb-close:hover{color:var(--text);background:rgba(255,255,255,0.06)}
.sb-model{font-size:16px;font-weight:700;margin-bottom:2px;padding-right:32px}
.sb-route{font-size:12px;color:var(--muted);margin-bottom:18px;line-height:1.5}
.sb-route b{color:var(--text)}
.sb-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:20px}
.sb-stat{background:var(--bg2);border-radius:8px;padding:10px 8px;text-align:center;border:1px solid var(--border)}
.sb-stat-val{font-size:20px;font-weight:700;color:#60a5fa;line-height:1.2}
.sb-stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.sb-section{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}
.sb-step{display:flex;align-items:flex-start;gap:10px;padding:6px 0;border-bottom:1px solid rgba(120,130,255,0.07)}
.sb-step:last-child{border-bottom:none}
.sb-step-num{color:var(--muted);font-size:10px;min-width:20px;padding-top:2px;text-align:right;flex-shrink:0}
.sb-step-arrow{color:var(--muted);font-size:10px;padding-top:2px;flex-shrink:0}
.sb-step-right{display:flex;flex-direction:column;gap:2px;min-width:0}
.sb-step-page{font-size:12px;color:var(--text);word-break:break-word;line-height:1.4}
.sb-step-page.sb-start{color:#60a5fa;font-weight:600}
.sb-step-page.sb-end{color:#10b981;font-weight:600}
.sb-reason{font-size:11px;color:var(--muted);font-style:italic;line-height:1.4}
.sb-nopath{font-size:12px;color:var(--muted);font-style:italic;padding:8px 0}
</style>
</head>
<body>
<div id="tooltip"></div>
<div id="sidebar-overlay" onclick="closeRunSidebar()"></div>
<div id="run-sidebar">
  <button class="sb-close" onclick="closeRunSidebar()">&#10005;</button>
  <div id="sb-content"></div>
</div>

<header class="hero">
  <div class="hero-title">WikiRace AI Benchmark</div>
  <div class="hero-sub">Which AI can navigate Wikipedia to any target in the fewest clicks?</div>
  <div class="stats-row">
    <div class="stat-chip">""" + str(len(models)) + """ <span>models tested</span></div>
    <div class="stat-chip">""" + str(total_runs) + """ <span>total runs</span></div>
    <div class="stat-chip">20 <span>test scenarios</span></div>
    <div class="stat-chip" style="color:var(--gold)">""" + best["name"] + """ <span>""" + str(best["wins"]) + """/""" + str(best["n"]) + """ wins</span></div>
  </div>
  <div class="generated">Generated """ + generated_at + """</div>
</header>

<nav class="tab-nav">
  <button class="tab-btn active" onclick="switchTab('leaderboard',this)">&#127942; Leaderboard</button>
  <button class="tab-btn" onclick="switchTab('charts',this)">&#128200; Timeline &amp; Charts</button>
  <button class="tab-btn" onclick="switchTab('matrix',this)">&#129514; Test Matrix</button>
</nav>

<!-- LEADERBOARD TAB -->
<div id="tab-leaderboard" class="tab-content active">
  <div id="highlights" class="highlights"></div>
  <div class="controls">
    <div class="chip-group">
      <button class="filter-chip active" data-f="all"       onclick="setFilter('all',this)">All</button>
      <button class="filter-chip"        data-f="openai"    onclick="setFilter('openai',this)">OpenAI</button>
      <button class="filter-chip"        data-f="gemini"    onclick="setFilter('gemini',this)">Gemini</button>
      <button class="filter-chip"        data-f="anthropic" onclick="setFilter('anthropic',this)">Anthropic</button>
      <button class="filter-chip"        data-f="xai"       onclick="setFilter('xai',this)">xAI</button>
    </div>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th style="width:52px">#</th>
          <th>Model</th>
          <th>Provider</th>
          <th class="th-sort th-sort-active" data-sort="win_rate" onclick="setSort('win_rate')">Win Rate <span class="sort-arrow">↓</span><i class="info-icon" data-metric="win_rate">?</i></th>
          <th class="th-sort r" data-sort="avg_score" onclick="setSort('avg_score')">Avg Score <span class="sort-arrow"></span><i class="info-icon" data-metric="avg_score">?</i></th>
          <th class="th-sort r" data-sort="avg_steps" onclick="setSort('avg_steps')">Avg Steps <span class="sort-arrow"></span><i class="info-icon" data-metric="avg_steps">?</i></th>
          <th class="th-sort r" data-sort="avg_time" onclick="setSort('avg_time')">Avg Time <span class="sort-arrow"></span><i class="info-icon" data-metric="avg_time">?</i></th>
          <th>By Difficulty <i class="info-icon" data-metric="difficulty">?</i></th>
          <th style="width:40px"></th>
        </tr>
      </thead>
      <tbody id="lb-body"></tbody>
    </table>
  </div>
</div>

<!-- CHARTS TAB -->
<div id="tab-charts" class="tab-content">
  <div class="charts-grid">

    <!-- Main explorer chart (full width) -->
    <div class="chart-card" style="grid-column:1/-1">
      <div class="chart-title">
        Model Performance Explorer
        <i class="info-icon" data-metric="explorer">?</i>
      </div>
      <div class="chart-sub">Each bubble is one model. Change axes and encoding below to explore different relationships.</div>
      <div class="chart-controls">
        <div class="ctrl-group">
          <label>X Axis <i class="info-icon" data-metric="xaxis">?</i></label>
          <select id="tl-x" class="ctrl-select" onchange="rebuildTimeline()">
            <option value="release_date" selected>Release Date</option>
            <option value="win_rate">Win Rate</option>
            <option value="avg_score">Avg Score</option>
            <option value="avg_steps">Avg Steps</option>
            <option value="avg_time">Avg Time</option>
          </select>
        </div>
        <div class="ctrl-group">
          <label>Y Axis <i class="info-icon" data-metric="yaxis">?</i></label>
          <select id="tl-y" class="ctrl-select" onchange="rebuildTimeline()">
            <option value="win_rate" selected>Win Rate</option>
            <option value="avg_score">Avg Score</option>
            <option value="avg_steps">Avg Steps</option>
            <option value="avg_time">Avg Time</option>
            <option value="release_date">Release Date</option>
          </select>
        </div>
        <div class="ctrl-group">
          <label>Bubble Size <i class="info-icon" data-metric="bubble_size">?</i></label>
          <select id="tl-r" class="ctrl-select" onchange="rebuildTimeline()">
            <option value="avg_score" selected>Avg Score</option>
            <option value="win_rate">Win Rate</option>
            <option value="avg_steps">Avg Steps (inverted)</option>
            <option value="fixed">Fixed (equal)</option>
          </select>
        </div>
        <div class="ctrl-group">
          <label>Color By <i class="info-icon" data-metric="color_by">?</i></label>
          <select id="tl-c" class="ctrl-select" onchange="rebuildTimeline()">
            <option value="provider" selected>Provider</option>
            <option value="win_rate">Win Rate</option>
            <option value="tier">Model Tier</option>
          </select>
        </div>
        <span class="chart-controls-hint">Hover bubbles for details</span>
      </div>
      <div class="chart-wrap" style="height:420px"><canvas id="timeline-chart"></canvas></div>
    </div>

    <!-- Win rate bar -->
    <div class="chart-card">
      <div class="chart-title">
        Win Rate by Model
        <i class="info-icon" data-metric="win_rate">?</i>
      </div>
      <div class="chart-sub">All models sorted by performance, colored by provider</div>
      <div class="chart-wrap"><canvas id="winrate-chart"></canvas></div>
    </div>

    <!-- Difficulty breakdown -->
    <div class="chart-card">
      <div class="chart-title">
        Win Rate by Difficulty
        <i class="info-icon" data-metric="difficulty">?</i>
      </div>
      <div class="chart-sub">Easy / Medium / Hard split for top 12 models</div>
      <div class="chart-wrap"><canvas id="diff-chart"></canvas></div>
    </div>

  </div>
</div>

<!-- MATRIX TAB -->
<div id="tab-matrix" class="tab-content">
  <p style="color:var(--muted);font-size:12px;margin-bottom:12px">
    Each cell = one model &times; one test. Shade of green = success (brighter = fewer steps). Red = failed. Hover any cell for details.
  </p>
  <div class="mx-legend">
    <span>Steps to win:</span>
    <div class="mx-legend-swatch"><div class="swatch" style="background:#10b981"></div>1&ndash;2</div>
    <div class="mx-legend-swatch"><div class="swatch" style="background:#059669"></div>3&ndash;4</div>
    <div class="mx-legend-swatch"><div class="swatch" style="background:#047857"></div>5&ndash;7</div>
    <div class="mx-legend-swatch"><div class="swatch" style="background:#065f46"></div>8&ndash;11</div>
    <div class="mx-legend-swatch"><div class="swatch" style="background:#064e3b"></div>12+</div>
    <div class="mx-legend-swatch"><div class="swatch" style="background:rgba(127,29,29,0.7)"></div>Failed</div>
    <span style="margin-left:8px">Difficulty:</span>
    <span class="diff-easy-hdr">&#9632; Easy</span>
    <span class="diff-med-hdr">&#9632; Medium</span>
    <span class="diff-hard-hdr">&#9632; Hard</span>
  </div>
  <div class="matrix-wrap"><div id="matrix-inner"></div></div>
</div>

<script>
const DATA = """ + data_json + """;

// ── Metric definitions shown in info tooltips ──────────────
const METRIC_DEFS = {
  win_rate: {
    label: 'Win Rate',
    desc: `Percentage of the 20 WikiRace tests where the model successfully reached the target Wikipedia article within the 20-step limit.<br><br><b>100%</b> = 20/20 tests won. Higher is always better.`
  },
  avg_score: {
    label: 'Average Score',
    desc: `Points earned per test run. Formula:<br><b>max(0, 1000 &minus; steps&times;50 &minus; seconds&times;2)</b><br><br>Only successful runs earn points. Rewards both efficiency (fewer clicks) and speed (less time). <b>Max = 1000</b> for an instant 0-step win.`
  },
  avg_steps: {
    label: 'Average Steps',
    desc: `Average Wikipedia page clicks per test. Failed tests count as <b>20 steps</b> (the max), so this penalises failures &mdash; not just slow wins.<br><br>Lower is always better: reflects both efficiency <em>and</em> reliability.`
  },
  avg_time: {
    label: 'Average Time',
    desc: `Average total seconds per test run. Includes a 1.2s delay between each step (Wikipedia rate limiting) plus model API latency.<br><br>Directly affects the score: fewer seconds = higher score for the same number of steps.`
  },
  difficulty: {
    label: 'Difficulty Breakdown',
    desc: `Win rate split by test difficulty tier:<br><br><b style="color:#22c55e">Easy (4 tests)</b> &mdash; Target reachable in 1&ndash;3 obvious clicks<br><b style="color:#f59e0b">Medium (9 tests)</b> &mdash; Needs multi-hop topic reasoning<br><b style="color:#ef4444">Hard (7 tests)</b> &mdash; Requires creative lateral thinking`
  },
  release_date: {
    label: 'Release Date',
    desc: `Approximate public release date of the model. Use the Timeline chart to see if newer models outperform older ones on this benchmark.`
  },
  explorer: {
    label: 'Model Performance Explorer',
    desc: `Interactive bubble chart. Use the controls below to change what each axis and bubble size represents.<br><br>Try: <b>X = Release Date, Y = Win Rate</b> to see the trend over time, or <b>X = Avg Steps, Y = Avg Score</b> to compare efficiency.`
  },
  xaxis: {
    label: 'X Axis',
    desc: `Metric shown on the horizontal axis. Choose <b>Release Date</b> to see how performance trends over time, or pick any other metric to compare models across two dimensions.`
  },
  yaxis: {
    label: 'Y Axis',
    desc: `Metric shown on the vertical axis. <b>Win Rate</b> is the primary performance indicator. <b>Avg Score</b> shows efficiency among winners.`
  },
  bubble_size: {
    label: 'Bubble Size',
    desc: `What controls the size of each bubble. Larger = higher value.<br><br><b>Avg Score</b> (default) &mdash; shows score magnitude<br><b>Win Rate</b> &mdash; emphasises top performers<br><b>Avg Steps</b> &mdash; inverted: fewer steps = bigger bubble<br><b>Fixed</b> &mdash; all equal size for a clean scatter plot`
  },
  color_by: {
    label: 'Color By',
    desc: `What each bubble's color represents:<br><br><b>Provider</b> &mdash; OpenAI, Gemini, Anthropic, xAI<br><b>Win Rate</b> &mdash; green = high, red = low<br><b>Model Tier</b> &mdash; Flagship, Pro, Flash, Mini, etc.`
  },
};

const PROV_COLOR = {
  openai:    '#10b981',
  gemini:    '#60a5fa',
  anthropic: '#fb923c',
  xai:       '#a78bfa',
};

const TIER_COLORS = {
  Flagship:'#fbbf24', Pro:'#fbbf24', Opus:'#fbbf24', Sonnet:'#e879f9',
  Flash:'#60a5fa', Mini:'#94a3b8', Lite:'#64748b', Nano:'#475569',
  Haiku:'#fb923c', 'Grok 3':'#a78bfa', 'Grok 2':'#7c3aed',
};

// ── Tooltip system ─────────────────────────────────────────
const TT = document.getElementById('tooltip');
let _ttTimeout = null;

function showTooltip(e, html) {
  clearTimeout(_ttTimeout);
  TT.innerHTML = html;
  TT.style.opacity = '1';
  placeTooltip(e);
}
function placeTooltip(e) {
  const x = Math.min(e.clientX + 16, window.innerWidth - 320);
  const y = Math.min(e.clientY + 10, window.innerHeight - 220);
  TT.style.left = x + 'px';
  TT.style.top  = y + 'px';
}
function hideTooltip() {
  _ttTimeout = setTimeout(() => { TT.style.opacity = '0'; }, 80);
}

function initInfoIcons() {
  document.querySelectorAll('.info-icon[data-metric]').forEach(el => {
    el.addEventListener('mouseenter', e => {
      const def = METRIC_DEFS[el.dataset.metric];
      if (!def) return;
      showTooltip(e, `<b>${def.label}</b><br><br>${def.desc}`);
    });
    el.addEventListener('mousemove', placeTooltip);
    el.addEventListener('mouseleave', hideTooltip);
    el.addEventListener('click', e => e.stopPropagation());
  });
}

// ── Tabs ───────────────────────────────────────────────────
let currentFilter = 'all';
let currentSort   = 'win_rate';

function switchTab(id, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
  if (id === 'charts' && !window._chartsReady) initCharts();
  if (id === 'matrix' && !window._matrixReady) renderMatrix();
  // Re-init info icons after chart tab renders
  if (id === 'charts') setTimeout(initInfoIcons, 50);
}

// ── Leaderboard ────────────────────────────────────────────
function filteredSorted() {
  let ms = [...DATA.models];
  if (currentFilter !== 'all') ms = ms.filter(m => m.provider === currentFilter);
  if (currentSort === 'win_rate')  ms.sort((a,b) => b.win_rate - a.win_rate || b.avg_score - a.avg_score);
  if (currentSort === 'avg_score') ms.sort((a,b) => b.avg_score - a.avg_score);
  if (currentSort === 'avg_steps') ms.sort((a,b) => a.avg_steps - b.avg_steps);
  if (currentSort === 'avg_time')  ms.sort((a,b) => a.avg_time - b.avg_time);
  return ms;
}

function setFilter(f, btn) {
  currentFilter = f;
  document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  renderLeaderboard();
}

const SORT_DIR = {win_rate:'↓', avg_score:'↓', avg_steps:'↑', avg_time:'↑'};

function setSort(s) {
  currentSort = s;
  document.querySelectorAll('th[data-sort]').forEach(th => {
    const active = th.dataset.sort === s;
    th.classList.toggle('th-sort-active', active);
    const arrow = th.querySelector('.sort-arrow');
    if (arrow) arrow.textContent = active ? SORT_DIR[s] : '';
  });
  renderLeaderboard();
}

function winColor(rate) {
  if (rate >= 95) return '#10b981';
  if (rate >= 85) return '#34d399';
  if (rate >= 70) return '#60a5fa';
  if (rate >= 50) return '#f59e0b';
  if (rate >= 25) return '#f97316';
  return '#ef4444';
}

function getScoreTip(steps, time, score) {
  const sd = steps * 50, td = Math.round(time * 2);
  return `<b>Score breakdown</b><br>1000 &minus; (${steps} steps &times; 50) &minus; (${time}s &times; 2)<br>= 1000 &minus; ${sd} &minus; ${td} = <b>${score}</b>`;
}

function renderLeaderboard() {
  const ms   = filteredSorted();
  const body = document.getElementById('lb-body');
  body.innerHTML = '';

  ms.forEach((m, i) => {
    const rank      = i + 1;
    const medal     = rank === 1 ? '&#127942;' : rank === 2 ? '&#129352;' : rank === 3 ? '&#129353;' : '';
    const wColor    = winColor(m.win_rate);
    const goldStyle = rank === 1 ? 'background:linear-gradient(90deg,rgba(251,191,36,.06),transparent)' : '';
    const bd        = m.by_diff;
    const rowId     = 'row-' + m.model_id.replace(/[^a-z0-9]/gi, '-');

    const diffHtml = `
      <div class="diff-row"><div class="diff-dot diff-easy"></div><span style="color:#22c55e;font-weight:600">${bd.easy.rate}%</span></div>
      <div class="diff-row"><div class="diff-dot diff-med"></div><span style="color:#f59e0b;font-weight:600">${bd.medium.rate}%</span></div>
      <div class="diff-row"><div class="diff-dot diff-hard"></div><span style="color:#ef4444;font-weight:600">${bd.hard.rate}%</span></div>
    `;

    body.insertAdjacentHTML('beforeend', `
      <tr class="model-row" id="${rowId}" style="${goldStyle}" onclick="toggleExpand('${m.model_id}')">
        <td class="rank-cell">${medal ? `<span class="medal">${medal}</span>` : `<span class="rank-num">${rank}</span>`}</td>
        <td>
          <div class="model-name">${m.name}</div>
          <div class="model-meta">
            <span class="tier-badge">${m.tier}</span>
            <span style="font-size:10px;color:var(--muted)">${m.release_date}</span>
          </div>
        </td>
        <td><span class="provider-badge pv-${m.provider}">${m.provider}</span></td>
        <td>
          <div class="win-bar-wrap">
            <div class="win-bar-bg"><div class="win-bar-fill" style="width:${m.win_rate}%;background:${wColor}"></div></div>
            <div class="win-pct" style="color:${wColor}">${m.win_rate}%</div>
          </div>
          <div class="win-frac">${m.wins}/${m.n} tests</div>
        </td>
        <td class="r"><span class="score-val" style="cursor:help" onmouseenter="showTooltip(event,METRIC_DEFS.avg_score.desc)" onmousemove="placeTooltip(event)" onmouseleave="hideTooltip()">${m.avg_score}</span></td>
        <td class="r"><span class="steps-val" style="cursor:help" onmouseenter="showTooltip(event,METRIC_DEFS.avg_steps.desc)" onmousemove="placeTooltip(event)" onmouseleave="hideTooltip()">${m.avg_steps}</span></td>
        <td class="r" style="color:var(--muted);cursor:help" onmouseenter="showTooltip(event,METRIC_DEFS.avg_time.desc)" onmousemove="placeTooltip(event)" onmouseleave="hideTooltip()">${m.avg_time}s</td>
        <td><div class="diff-mini">${diffHtml}</div></td>
        <td><button class="expand-btn" id="btn-${rowId}" onclick="event.stopPropagation();toggleExpand('${m.model_id}')">&#9660;</button></td>
      </tr>
      <tr class="detail-row" id="det-${rowId}">
        <td colspan="9" style="padding:0">
          <div class="detail-inner">
            <div class="detail-header">${m.name} &mdash; all 20 test results</div>
            <div class="test-grid">${buildTestCards(m)}</div>
          </div>
        </td>
      </tr>
    `);
  });
}

function buildTestCards(m) {
  return DATA.tests.map(t => {
    const r = m.tests[String(t.id)];
    if (!r) return '';
    const ok       = r.success;
    const icon     = ok ? '&#9989;' : '&#10060;';
    const stepsStr = ok ? `${r.steps} step${r.steps !== 1 ? 's' : ''}` : 'failed';
    const scoreStr = ok ? `score&nbsp;<b style="cursor:help" onmouseenter="showTooltip(event,getScoreTip(${r.steps},${r.time},${r.score}))" onmousemove="placeTooltip(event)" onmouseleave="hideTooltip()">${r.score}</b>` : '';
    const timeStr  = r.time ? `${r.time}s` : '';
    return `
      <div class="test-card ${ok ? 'pass' : 'fail'}">
        <div class="tc-head">
          <span class="tc-icon">${icon}</span>
          <span class="tc-diff ${r.diff}">${r.diff}</span>
        </div>
        <div class="tc-route">
          <strong>${t.start}</strong>
          <span> &#8594; </span>
          <strong>${t.target}</strong>
        </div>
        <div class="tc-stats">
          <span><b>${stepsStr}</b></span>
          ${scoreStr ? `<span>${scoreStr}</span>` : ''}
          ${timeStr  ? `<span>${timeStr}</span>` : ''}
        </div>
      </div>`;
  }).join('');
}

function toggleExpand(modelId) {
  const safe   = 'row-' + modelId.replace(/[^a-z0-9]/gi, '-');
  const detRow = document.getElementById('det-' + safe);
  const modRow = document.getElementById(safe);
  const btn    = document.getElementById('btn-' + safe);
  if (!detRow) return;
  const open = detRow.classList.toggle('open');
  modRow.classList.toggle('expanded', open);
  if (btn) btn.innerHTML = open ? '&#9650;' : '&#9660;';
}

// ── Highlights ─────────────────────────────────────────────
function renderHighlights() {
  const ms      = DATA.models;
  const best    = ms[0];
  const bestLite = ms.filter(m => /lite|mini|nano|haiku/i.test(m.tier)).sort((a,b) => b.win_rate - a.win_rate)[0];
  const topRate = ms[0].win_rate;
  const mostEff = ms.filter(m => m.win_rate >= topRate - 5).sort((a,b) => b.avg_score - a.avg_score)[0];
  const worst   = [...ms].sort((a,b) => a.win_rate - b.win_rate)[0];

  const cards = [
    { cls:'gold',      icon:'&#127942;', label:'Overall Winner',    name:best.name,        sub:`${best.wins}/${best.n} wins &bull; ${best.win_rate}% win rate` },
    { cls:'surprise',  icon:'&#9889;',   label:'Best Compact Model', name:bestLite?.name||'—', sub:bestLite?`${bestLite.win_rate}% win rate &bull; ${bestLite.tier} tier`:'' },
    { cls:'efficient', icon:'&#128293;', label:'Highest Avg Score',  name:mostEff.name,     sub:`${mostEff.avg_score} avg score &bull; ${mostEff.avg_steps} avg steps` },
    { cls:'warn',      icon:'&#128560;', label:'Underperformer',     name:worst.name,       sub:`${worst.wins}/${worst.n} wins &bull; ${worst.win_rate}% win rate` },
  ];

  document.getElementById('highlights').innerHTML = cards.map(c => `
    <div class="hl-card ${c.cls}">
      <div class="hl-icon">${c.icon}</div>
      <div class="hl-label">${c.label}</div>
      <div class="hl-name">${c.name}</div>
      <div class="hl-sub">${c.sub}</div>
    </div>`).join('');
}

// ── Timeline Chart (interactive) ───────────────────────────
let _tlChart = null;

function getVal(m, key) {
  if (key === 'release_date') return new Date(m.release_date).getTime();
  return m[key] ?? 0;
}
function axisLabel(key) {
  return { release_date:'Release Date', win_rate:'Win Rate (%)', avg_score:'Avg Score',
           avg_steps:'Avg Steps', avg_time:'Avg Time (s)' }[key] || key;
}
function rateColor(r) {
  return r>=95?'#10b981':r>=85?'#34d399':r>=70?'#60a5fa':r>=50?'#f59e0b':r>=25?'#f97316':'#ef4444';
}

function rebuildTimeline() {
  const xKey  = document.getElementById('tl-x').value;
  const yKey  = document.getElementById('tl-y').value;
  const rKey  = document.getElementById('tl-r').value;
  const cMode = document.getElementById('tl-c').value;

  if (_tlChart) { _tlChart.destroy(); _tlChart = null; }

  // Group models by color dimension
  const groups = {};
  DATA.models.forEach(m => {
    let gKey, color;
    if (cMode === 'provider') {
      gKey  = m.provider.charAt(0).toUpperCase() + m.provider.slice(1);
      color = PROV_COLOR[m.provider] || '#fff';
    } else if (cMode === 'win_rate') {
      gKey  = m.win_rate >= 85 ? 'Top tier (85%+)' : m.win_rate >= 50 ? 'Mid tier (50-84%)' : 'Low tier (<50%)';
      color = rateColor(m.win_rate);
    } else {
      gKey  = m.tier || 'Other';
      color = TIER_COLORS[m.tier] || '#64748b';
    }
    if (!groups[gKey]) groups[gKey] = { color, pts: [] };

    let r;
    if (rKey === 'fixed') r = 10;
    else if (rKey === 'avg_steps') r = Math.max(5, (21 - m.avg_steps) * 1.2); // invert: fewer steps = bigger
    else r = Math.max(5, Math.sqrt(getVal(m, rKey)) * (rKey === 'win_rate' ? 0.65 : 0.8));

    groups[gKey].pts.push({
      x: getVal(m, xKey),
      y: getVal(m, yKey),
      r,
      _m: m,
    });
  });

  const datasets = Object.entries(groups).map(([label, g]) => ({
    label,
    data: g.pts,
    backgroundColor: g.color + 'bb',
    borderColor: g.color,
    borderWidth: 1.5,
  }));

  const isTimeX = xKey === 'release_date';
  const isTimeY = yKey === 'release_date';
  const yIsPct  = yKey === 'win_rate';

  _tlChart = new Chart(document.getElementById('timeline-chart'), {
    type: 'bubble',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { size: 12 }, padding: 16 } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const m = ctx.raw._m;
              const lines = [`${m.name}  (${m.tier})`];
              lines.push(`Released: ${m.release_date}`);
              lines.push(`Win Rate: ${m.win_rate}%  (${m.wins}/${m.n})`);
              lines.push(`Avg Score: ${m.avg_score}`);
              lines.push(`Avg Steps: ${m.avg_steps}`);
              if (xKey !== 'release_date' && xKey !== 'win_rate') lines.push(`${axisLabel(xKey)}: ${ctx.raw.x}`);
              if (yKey !== 'release_date' && yKey !== 'win_rate') lines.push(`${axisLabel(yKey)}: ${ctx.raw.y}`);
              return lines;
            }
          }
        }
      },
      scales: {
        x: isTimeX ? {
          type: 'time',
          time: { unit: 'month', displayFormats: { month: 'MMM yy' } },
          ticks: { color: '#64748b', maxTicksLimit: 10 },
          grid: { color: 'rgba(255,255,255,0.05)' },
          title: { display: true, text: 'Release Date', color: '#64748b' },
        } : {
          type: 'linear',
          ticks: { color: '#64748b', callback: v => xKey === 'win_rate' ? v + '%' : v },
          grid: { color: 'rgba(255,255,255,0.05)' },
          title: { display: true, text: axisLabel(xKey), color: '#64748b' },
        },
        y: {
          type: isTimeY ? 'time' : 'linear',
          ticks: { color: '#64748b', callback: v => yIsPct ? v + '%' : v },
          grid: { color: 'rgba(255,255,255,0.05)' },
          title: { display: true, text: axisLabel(yKey), color: '#64748b' },
        }
      }
    }
  });
}

// ── Static charts ──────────────────────────────────────────
function initCharts() {
  window._chartsReady = true;

  rebuildTimeline();

  // Win rate bar
  const sorted = [...DATA.models].sort((a,b) => b.win_rate - a.win_rate);
  new Chart(document.getElementById('winrate-chart'), {
    type: 'bar',
    data: {
      labels: sorted.map(m => m.name),
      datasets: [{
        data: sorted.map(m => m.win_rate),
        backgroundColor: sorted.map(m => PROV_COLOR[m.provider] + '99'),
        borderColor:     sorted.map(m => PROV_COLOR[m.provider]),
        borderWidth: 1, borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const m = sorted[ctx.dataIndex];
              return [`${ctx.raw}% win rate`, `${m.wins}/${m.n} tests`, `Avg score: ${m.avg_score}`];
            }
          }
        }
      },
      scales: {
        x: { max: 108, ticks: { color: '#64748b', callback: v => v + '%' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { display: false } }
      }
    }
  });

  // Difficulty breakdown
  const top12 = [...DATA.models].sort((a,b) => b.win_rate - a.win_rate).slice(0, 12);
  new Chart(document.getElementById('diff-chart'), {
    type: 'bar',
    data: {
      labels: top12.map(m => m.name),
      datasets: [
        { label:'Easy',   data:top12.map(m=>m.by_diff.easy.rate),   backgroundColor:'#22c55e99',borderColor:'#22c55e',borderWidth:1,borderRadius:3 },
        { label:'Medium', data:top12.map(m=>m.by_diff.medium.rate), backgroundColor:'#f59e0b99',borderColor:'#f59e0b',borderWidth:1,borderRadius:3 },
        { label:'Hard',   data:top12.map(m=>m.by_diff.hard.rate),   backgroundColor:'#ef444499',borderColor:'#ef4444',borderWidth:1,borderRadius:3 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color:'#94a3b8', font:{ size:12 }, padding:12 } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const m = top12[ctx.dataIndex];
              const d = ctx.dataset.label.toLowerCase();
              const bd = m.by_diff[d];
              return `${ctx.dataset.label}: ${ctx.raw}%  (${bd.w}/${bd.n})`;
            }
          }
        }
      },
      scales: {
        x: { ticks:{ color:'#64748b',font:{size:10},maxRotation:35 }, grid:{ color:'rgba(255,255,255,0.04)' } },
        y: { max:110, ticks:{ color:'#64748b', callback:v=>v+'%' }, grid:{ color:'rgba(255,255,255,0.05)' } }
      }
    }
  });
}

// ── Test Matrix ────────────────────────────────────────────
function stepClass(steps, success) {
  if (!success) return steps === 0 ? 'fail fail0' : 'fail';
  if (steps <= 2)  return 'pass pass4';
  if (steps <= 4)  return 'pass pass3';
  if (steps <= 7)  return 'pass pass2';
  if (steps <= 11) return 'pass pass1';
  return 'pass pass0';
}

function renderMatrix() {
  window._matrixReady = true;
  const models = [...DATA.models].sort((a,b) => a.rank - b.rank);

  let html = '<table class="matrix-table"><thead><tr><th></th>';
  DATA.tests.forEach(t => {
    const dc = `diff-${t.difficulty}-hdr`;
    html += `<th class="mx-header ${dc}" title="${t.start} -> ${t.target} [${t.difficulty}]"><div>#${t.id}</div><div>${t.start.slice(0,7)}</div></th>`;
  });
  html += '</tr></thead><tbody>';

  models.forEach(m => {
    const rm = m.rank <= 3 ? ['&#127942;','&#129352;','&#129353;'][m.rank-1] : '';
    html += `<tr><td class="mx-model">
      <span style="color:${PROV_COLOR[m.provider]};margin-right:4px">&#9679;</span>
      ${rm ? rm + ' ' : ''}<b>${m.name}</b>
      <span style="color:var(--muted);font-size:10px;margin-left:6px">${m.win_rate}%</span>
    </td>`;
    DATA.tests.forEach(t => {
      const r   = m.tests[String(t.id)];
      const cls = r ? stepClass(r.steps, r.success) : 'fail fail0';
      const lbl = r ? r.steps : '';
      const tip = r && r.success
        ? `<b>${m.name}</b><br>${t.start} &rarr; ${t.target}<br><span style="color:#64748b">[${t.difficulty}]</span> &bull; <b>${r.steps}</b> steps &bull; score <b>${r.score}</b> &bull; ${r.time}s`
        : `<b>${m.name}</b><br>${t.start} &rarr; ${t.target}<br><span style="color:#64748b">[${t.difficulty}]</span> &bull; <span style="color:#ef4444">FAILED</span> at step ${r ? r.steps : 0}`;
      html += `<td><div class="mx-cell ${cls}" data-tip="${tip.replace(/"/g,'&quot;')}" data-model="${m.model_id}" data-test="${t.id}">${lbl}</div></td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  document.getElementById('matrix-inner').innerHTML = html;

  document.querySelectorAll('.mx-cell').forEach(cell => {
    cell.addEventListener('mouseenter', e => { hideTooltip(); showTooltip(e, cell.dataset.tip); });
    cell.addEventListener('mousemove',  placeTooltip);
    cell.addEventListener('mouseleave', hideTooltip);
    cell.addEventListener('click', () => { hideTooltip(); openRunSidebar(cell.dataset.model, cell.dataset.test); });
  });
}

// ── Init ───────────────────────────────────────────────────
renderHighlights();
renderLeaderboard();
initInfoIcons();

requestAnimationFrame(() => {
  document.querySelectorAll('.win-bar-fill').forEach(el => {
    const w = el.style.width; el.style.width = '0';
    requestAnimationFrame(() => { el.style.width = w; });
  });
});

// ── Run Sidebar ─────────────────────────────────────────────
function openRunSidebar(modelId, testId) {
  const m = DATA.models.find(x => x.model_id === modelId);
  const t = DATA.tests.find(x => String(x.id) === String(testId));
  const r = m && m.tests[String(testId)];
  if (!m || !t || !r) return;

  const ok = r.success;
  const diffColor = {easy:'#22c55e', medium:'#f59e0b', hard:'#ef4444'}[r.diff] || '#64748b';

  const statsHtml = [
    `<div class="sb-stat"><div class="sb-stat-val" style="color:${ok?'#10b981':'#ef4444'}">${ok?'WIN':'FAIL'}</div><div class="sb-stat-lbl">Result</div></div>`,
    `<div class="sb-stat"><div class="sb-stat-val">${r.steps}</div><div class="sb-stat-lbl">Steps</div></div>`,
    ok ? `<div class="sb-stat"><div class="sb-stat-val" style="color:#f59e0b">${r.score}</div><div class="sb-stat-lbl">Score</div></div>` : '',
    r.time ? `<div class="sb-stat"><div class="sb-stat-val">${r.time}s</div><div class="sb-stat-lbl">Time</div></div>` : '',
    `<div class="sb-stat"><div class="sb-stat-val" style="color:${diffColor};font-size:13px">${r.diff}</div><div class="sb-stat-lbl">Difficulty</div></div>`,
  ].join('');

  let pathHtml = '';
  if (r.path && r.path.length > 0) {
    const steps = r.path.map((p, i) => {
      const isStart  = i === 0;
      const isEnd    = i === r.path.length - 1 && ok;
      const cls      = isStart ? 'sb-start' : isEnd ? 'sb-end' : '';
      const reason   = r.reasons && r.reasons[i] ? `<div class="sb-reason">${r.reasons[i]}</div>` : '';
      return `<div class="sb-step"><span class="sb-step-num">${i}</span><span class="sb-step-arrow">›</span><div class="sb-step-right"><span class="sb-step-page ${cls}">${p}</span>${reason}</div></div>`;
    }).join('');
    pathHtml = `<div class="sb-section">Navigation path &mdash; ${r.path.length} pages</div>${steps}`;
  } else {
    pathHtml = `<div class="sb-nopath">Path data not recorded for this run. Re-run the benchmark to capture navigation paths.</div>`;
  }

  document.getElementById('sb-content').innerHTML = `
    <div class="sb-model">${m.name}</div>
    <div class="sb-route"><b>${t.start}</b> &rarr; <b>${t.target}</b></div>
    <div class="sb-stats">${statsHtml}</div>
    <div class="sb-section" style="margin-top:4px">Run details</div>
    ${pathHtml}
  `;
  document.getElementById('run-sidebar').classList.add('open');
  document.getElementById('sidebar-overlay').classList.add('open');
}

function closeRunSidebar() {
  document.getElementById('run-sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('open');
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeRunSidebar(); });
</script>
</body>
</html>"""

def main():
    results, tests = load_data()
    models = compute_stats(results, tests)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_json = json.dumps({"models": models, "tests": tests, "generated": generated_at})
    html = build_html(models, tests, data_json, generated_at)
    with LEADERBOARD_FILE.open("w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated: {LEADERBOARD_FILE}  ({len(html)//1024} KB)")
    print(f"Open: file:///{str(LEADERBOARD_FILE).replace(chr(92), '/')}")

if __name__ == "__main__":
    main()
