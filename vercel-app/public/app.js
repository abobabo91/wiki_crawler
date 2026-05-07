const WIKI_BASE = "https://en.wikipedia.org";
const MAX_S = 20;
const STEP_DELAY = 1200;

const MODELS = [
  {id:"openai/gpt-5.4",name:"GPT-5.4",provider:"openai",color:"#10c87f"},
  {id:"openai/gpt-5.4-mini",name:"GPT-5.4 Mini",provider:"openai",color:"#34d99a"},
  {id:"openai/gpt-5.4-nano",name:"GPT-5.4 Nano",provider:"openai",color:"#2ea88c"},
  {id:"openai/gpt-5",name:"GPT-5",provider:"openai",color:"#1a9e6c"},
  {id:"openai/gpt-5-mini",name:"GPT-5 Mini",provider:"openai",color:"#148a5a"},
  {id:"openai/gpt-4.1",name:"GPT-4.1",provider:"openai",color:"#0e7a4a"},
  {id:"openai/gpt-4.1-mini",name:"GPT-4.1 Mini",provider:"openai",color:"#0e6651"},
  {id:"openai/gpt-4.1-nano",name:"GPT-4.1 Nano",provider:"openai",color:"#0a5040"},
  {id:"openai/gpt-4o",name:"GPT-4o",provider:"openai",color:"#1a8c6c"},
  {id:"openai/gpt-4o-mini",name:"GPT-4o Mini",provider:"openai",color:"#148a6b"},
  {id:"gemini/gemini-3.1-pro-preview",name:"Gemini 3.1 Pro",provider:"gemini",color:"#0d652b"},
  {id:"gemini/gemini-3.1-flash-lite-preview",name:"Gemini 3.1 Flash Lite",provider:"gemini",color:"#0f9d58"},
  {id:"gemini/gemini-3-pro-preview",name:"Gemini 3 Pro",provider:"gemini",color:"#1b7a35"},
  {id:"gemini/gemini-3-flash-preview",name:"Gemini 3 Flash",provider:"gemini",color:"#34a853"},
  {id:"gemini/gemini-2.5-flash",name:"Gemini 2.5 Flash",provider:"gemini",color:"#4285f4"},
  {id:"gemini/gemini-2.5-flash-lite",name:"Gemini 2.5 Flash Lite",provider:"gemini",color:"#1565c0"},
  {id:"anthropic/claude-opus-4-7",name:"Claude Opus 4.7",provider:"anthropic",color:"#b05e38"},
  {id:"anthropic/claude-sonnet-4-6",name:"Claude Sonnet 4.6",provider:"anthropic",color:"#e8937a"},
  {id:"anthropic/claude-haiku-4-5-20251001",name:"Claude Haiku 4.5",provider:"anthropic",color:"#f0b8a0"},
  {id:"xai/grok-3",name:"Grok 3",provider:"xai",color:"#8b5cf6"},
  {id:"xai/grok-3-mini",name:"Grok 3 Mini",provider:"xai",color:"#a78bfa"},
];

const PROV = {openai:"OpenAI",gemini:"Google",anthropic:"Anthropic",xai:"xAI"};
const KEY_MAP = {openai:"openai_key",gemini:"gemini_key",anthropic:"anthropic_key",xai:"xai_key"};
const KEYS = [
  {k:"openai_key",lbl:"OpenAI",ph:"sk-..."},
  {k:"gemini_key",lbl:"Gemini",ph:"AIza..."},
  {k:"anthropic_key",lbl:"Anthropic",ph:"sk-ant-..."},
  {k:"xai_key",lbl:"xAI / Grok",ph:"xai-..."},
];
const GROUPS = [
  {lbl:"All Available",cls:"on",fn:m=>hasKey(m.provider)},
  {lbl:"OpenAI",cls:"on-openai",fn:m=>m.provider==="openai"&&hasKey("openai")},
  {lbl:"Gemini",cls:"on-gemini",fn:m=>m.provider==="gemini"&&hasKey("gemini")},
  {lbl:"Anthropic",cls:"on-anthropic",fn:m=>m.provider==="anthropic"&&hasKey("anthropic")},
  {lbl:"xAI",cls:"on-xai",fn:m=>m.provider==="xai"&&hasKey("xai")},
  {lbl:"Clear All",fn:()=>false},
];

let cancelled = false;
let racing = false;

// ── Storage helpers (localStorage) ──
function loadKeys() {
  try { return JSON.parse(localStorage.getItem("wikirace_keys") || "{}"); } catch { return {}; }
}
function saveKeysToStorage(keys) { localStorage.setItem("wikirace_keys", JSON.stringify(keys)); }
function hasKey(provider) { return !!loadKeys()[KEY_MAP[provider]]; }
function getKey(provider) { return loadKeys()[KEY_MAP[provider]] || ""; }
function loadResults() {
  try { return JSON.parse(localStorage.getItem("wikirace_results") || "[]"); } catch { return []; }
}
function saveResults(r) { localStorage.setItem("wikirace_results", JSON.stringify(r)); }

function articleName(url) { return decodeURIComponent((url.split("/wiki/")[1] || url)).replace(/_/g, " "); }
function articleUrl(name) { return `${WIKI_BASE}/wiki/${name.replace(/ /g, "_")}`; }

// ── Init ──
async function init() {
  buildSelBar(); buildModelGrid(); buildKeyGrid(); loadPresets(); renderLB();
}

function buildSelBar() {
  const bar = document.getElementById("sel-bar"); bar.innerHTML = "";
  GROUPS.forEach((g, i) => {
    const b = document.createElement("button");
    b.className = "sel-btn"; b.textContent = g.lbl;
    b.onclick = () => applyGroup(i);
    bar.appendChild(b);
  });
}

function applyGroup(gi) {
  const g = GROUPS[gi];
  document.querySelectorAll(".mc").forEach(el => {
    const m = MODELS.find(x => x.id === el.dataset.id);
    const cb = el.querySelector("input");
    if (!cb || cb.disabled) return;
    const on = g.fn(m);
    cb.checked = on; el.classList.toggle("on", on);
  });
  document.querySelectorAll(".sel-btn").forEach((b, i) => {
    b.className = "sel-btn" + (i === gi && gi !== GROUPS.length - 1 ? (" on " + (g.cls || "on")).trim() : "");
  });
}

function buildModelGrid() {
  const g = document.getElementById("model-grid"); g.innerHTML = "";
  MODELS.forEach(m => {
    const avail = hasKey(m.provider);
    const el = document.createElement("label");
    el.className = "mc" + (avail ? "" : " off");
    el.style.setProperty("--c", m.color);
    el.dataset.id = m.id; el.dataset.provider = m.provider;
    el.innerHTML =
      `<input type="checkbox" value="${m.id}" ${avail ? "" : "disabled"} onchange="syncMC(this)">` +
      `<span class="dot"></span><span class="lbl">${m.name}</span>` +
      `<span class="prov">${PROV[m.provider] || m.provider}</span>`;
    g.appendChild(el);
  });
}

function syncMC(cb) {
  cb.closest("label").classList.toggle("on", cb.checked);
  document.querySelectorAll(".sel-btn").forEach(b => b.className = "sel-btn");
}

async function loadPresets() {
  try {
    const tests = await fetch("/test_sets.json").then(r => r.json());
    const sel = document.getElementById("sel-preset");
    tests.forEach(t => {
      const o = document.createElement("option");
      o.value = JSON.stringify(t);
      const diff = {easy: "🟢", medium: "🟡", hard: "🔴"}[t.difficulty] || "";
      o.textContent = `${diff} #${t.id}  ${t.start} → ${t.target}`;
      sel.appendChild(o);
    });
  } catch {}
}

function applyPreset() {
  const v = document.getElementById("sel-preset").value;
  if (!v) return;
  const t = JSON.parse(v);
  document.getElementById("inp-start").value = t.start;
  document.getElementById("inp-target").value = t.target;
}

// ── Build prompt (same logic as Python) ──
function buildPrompt(currentUrl, pageText, links, history, target) {
  const path = history.slice(-6).map(articleName).join(" -> ");
  const visited = new Set(history);
  const fresh = links.filter(l => !visited.has(l)).slice(0, 50);
  const seen = links.filter(l => visited.has(l)).slice(0, 10);

  let linksSection = "Unvisited links:\n" + fresh.join("\n");
  if (seen.length) linksSection += "\n\nPreviously visited links (backtrack here only if truly stuck):\n" + seen.join("\n");

  return `You are playing Wikipedia Race. Reach "${target}" in as few clicks as possible.

Current page: ${articleName(currentUrl)}
Path so far: ${path}
Target: ${target}

Page excerpt:
${pageText.slice(0, 1500)}

${linksSection}

Rules:
- You MUST pick a link from the "Unvisited links" list above. Do not invent URLs.
- If "${target}" appears in any list, pick it immediately.
- Navigate through real content articles - avoid meta/hub pages.
- You may pick a previously visited link to backtrack only if truly stuck.

Reply in EXACTLY this format:
LINK: <exact URL from the list above>
REASON: <one sentence why this page leads toward ${target}>`;
}

function parseResponse(text, links) {
  const m = text.match(/LINK:\s*(https?:\/\/[^\s\n]+)/);
  if (m) {
    const c = m[1].replace(/[.,)]+$/, "");
    if (links.includes(c)) return c;
    for (const l of links) { if (c.includes(l) || l.includes(c)) return l; }
  }
  for (const l of links) {
    const slug = l.split("/wiki/")[1] || "";
    if (slug.length > 3 && text.toLowerCase().includes(slug.toLowerCase())) return l;
  }
  return null;
}

function extractReason(text) {
  const m = text.match(/REASON:\s*(.+)/s);
  return m ? m[1].trim().slice(0, 200) : "";
}

// ── Race execution (client-side, per model) ──
async function runRaceForModel(modelId, startUrl, target) {
  const targetSlug = target.replace(/ /g, "_").toLowerCase();
  const targetUrl = articleUrl(target);
  let currentUrl = startUrl;
  const history = [currentUrl];
  const reasons = [""];
  let steps = 0;
  const started = Date.now();
  const provider = modelId.split("/")[0];
  const apiKey = getKey(provider);

  const emit = (data) => updateLane(modelId, data);

  emit({ status: "running", current_page: articleName(currentUrl), steps: 0, path: [...history], score: 0, last_reason: "Starting...", time: 0, error: "" });

  for (let i = 0; i < MAX_S; i++) {
    if (cancelled) {
      const r = { status: "cancelled", success: false, steps, time: elapsed(), score: 0, error: "Cancelled", path: [...history], last_reason: reasons[reasons.length - 1], current_page: articleName(currentUrl) };
      emit(r); return r;
    }

    if (targetSlug === currentUrl.toLowerCase().split("/wiki/")[1]?.toLowerCase()) {
      const score = Math.max(0, 1000 - steps * 50 - Math.round(elapsed() * 2));
      const r = { status: "success", success: true, steps, time: elapsed(), score, error: "", path: [...history], last_reason: reasons[reasons.length - 1], current_page: articleName(currentUrl) };
      emit(r); return r;
    }

    // Fetch Wikipedia page via proxy
    let pageText, links;
    try {
      const wd = await fetch(`/api/wiki?url=${encodeURIComponent(currentUrl)}`).then(r => r.json());
      pageText = wd.text || "";
      links = wd.links || [];
    } catch {
      const r = { status: "failed", success: false, steps, time: elapsed(), score: 0, error: "Wiki fetch failed", path: [...history], last_reason: "", current_page: articleName(currentUrl) };
      emit(r); return r;
    }

    if (!links.length) {
      const r = { status: "failed", success: false, steps, time: elapsed(), score: 0, error: "No links found", path: [...history], last_reason: "", current_page: articleName(currentUrl) };
      emit(r); return r;
    }

    // Direct link to target?
    if (links.includes(targetUrl)) {
      history.push(targetUrl); reasons.push("Direct link to target found."); steps++;
      const score = Math.max(0, 1000 - steps * 50 - Math.round(elapsed() * 2));
      const r = { status: "success", success: true, steps, time: elapsed(), score, error: "", path: [...history], last_reason: "Direct link to target found.", current_page: target };
      emit(r); return r;
    }

    // Ask AI
    const prompt = buildPrompt(currentUrl, pageText, links, history, target);
    let aiText;
    try {
      const aiResp = await fetch("/api/ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId, prompt, api_key: apiKey }),
      }).then(r => r.json());
      if (aiResp.error) throw new Error(aiResp.error);
      aiText = aiResp.text || "";
    } catch (err) {
      const r = { status: "failed", success: false, steps, time: elapsed(), score: 0, error: `AI error: ${err.message}`.slice(0, 120), path: [...history], last_reason: "", current_page: articleName(currentUrl) };
      emit(r); return r;
    }

    let chosen = parseResponse(aiText, links);
    if (!chosen) {
      const fresh = links.filter(l => !history.includes(l));
      chosen = fresh[0] || links[0] || null;
    }
    if (!chosen) {
      const r = { status: "failed", success: false, steps, time: elapsed(), score: 0, error: "No valid link", path: [...history], last_reason: "", current_page: articleName(currentUrl) };
      emit(r); return r;
    }
    if (history.filter(h => h === chosen).length >= 2) {
      const r = { status: "failed", success: false, steps, time: elapsed(), score: 0, error: "Loop detected", path: [...history], last_reason: "", current_page: articleName(currentUrl) };
      emit(r); return r;
    }

    const reason = extractReason(aiText);
    currentUrl = chosen;
    history.push(currentUrl);
    reasons.push(reason);
    steps++;

    emit({ status: "running", current_page: articleName(currentUrl), steps, path: [...history], score: 0, last_reason: reason, time: elapsed(), error: "" });

    await new Promise(r => setTimeout(r, STEP_DELAY));
  }

  const r = { status: "failed", success: false, steps, time: elapsed(), score: 0, error: `Max ${MAX_S} steps reached`, path: [...history], last_reason: reasons[reasons.length - 1], current_page: articleName(currentUrl) };
  emit(r); return r;

  function elapsed() { return Math.round((Date.now() - started) / 100) / 10; }
}

// ── Start race ──
async function startRace() {
  const start = document.getElementById("inp-start").value.trim();
  const target = document.getElementById("inp-target").value.trim();
  const mids = [...document.querySelectorAll(".mc input:checked")].map(c => c.value);
  if (!start || !target) { alert("Enter start and target articles."); return; }
  if (!mids.length) { alert("Select at least one model."); return; }

  cancelled = false; racing = true;
  document.getElementById("btn-start").disabled = true;
  document.getElementById("btn-cancel").style.display = "";
  document.getElementById("race-info").textContent = "Starting…";
  document.getElementById("ra-start").textContent = start;
  document.getElementById("ra-target").textContent = target;
  document.getElementById("race-area").style.display = "";
  buildLanes(mids, start);

  const startUrl = articleUrl(start);
  const promises = mids.map(mid => runRaceForModel(mid, startUrl, target));
  const results = await Promise.all(promises);

  // Save results to leaderboard
  const stored = loadResults();
  results.forEach((res, i) => {
    if (res.status === "cancelled") return;
    const m = MODELS.find(x => x.id === mids[i]);
    stored.push({
      model_id: mids[i], model_name: m ? m.name : mids[i],
      start: startUrl, target, steps: res.steps, time: res.time,
      score: res.score, success: res.success,
      timestamp: new Date().toISOString(),
    });
  });
  saveResults(stored);

  // Announce winner
  const winners = results.filter(r => r.success).sort((a, b) => b.score - a.score);
  if (winners.length) {
    const wi = results.indexOf(winners[0]);
    const wm = MODELS.find(x => x.id === mids[wi]);
    document.getElementById("race-info").textContent = `🏆 Winner: ${wm ? wm.name : mids[wi]} · Score ${winners[0].score}`;
  } else {
    document.getElementById("race-info").textContent = "No AI reached the target.";
  }

  racing = false;
  resetUI();
  renderLB();
}

function cancelRace() { cancelled = true; resetUI(); }
function resetUI() { document.getElementById("btn-start").disabled = false; document.getElementById("btn-cancel").style.display = "none"; }

// ── Lanes ──
function lid(mid) { return "L" + mid.replace(/[\/.\-]/g, "_"); }

function buildLanes(mids, start) {
  const c = document.getElementById("lanes"); c.innerHTML = "";
  mids.forEach(mid => {
    const m = MODELS.find(x => x.id === mid) || { name: mid, color: "#8b949e" };
    const id = lid(mid);
    const d = document.createElement("div");
    d.className = "lane"; d.id = id; d.style.setProperty("--c", m.color);
    d.innerHTML = `<div class="lane-hd"><span class="ldot"></span><span class="lname">${m.name}</span><span class="lstatus" id="st_${id}">Pending</span><span class="lscore" id="sc_${id}">—</span></div><div class="lbar-wrap"><div class="lbar" id="bar_${id}" style="width:0%"></div></div><div class="lpage" id="pg_${id}">📍 ${start}</div><div class="lreason" id="rs_${id}"></div><div class="lsteps" id="sp_${id}">Step 0 / ${MAX_S}</div><div class="path-scroll" id="pt_${id}"></div>`;
    c.appendChild(d);
  });
}

const ST_LABEL = { pending: "Pending", running: "Running…", success: "✓ Found!", failed: "✗ Failed", cancelled: "Cancelled" };

function updateLane(mid, mr) {
  const id = lid(mid);
  const lane = document.getElementById(id); if (!lane) return;
  lane.className = "lane " + (mr.status || "");
  const st = document.getElementById("st_" + id);
  if (st) { st.textContent = ST_LABEL[mr.status] || mr.status; st.className = "lstatus " + (mr.status || ""); }
  const sc = document.getElementById("sc_" + id);
  if (sc) sc.textContent = mr.status === "success" ? mr.score : (mr.status === "failed" ? "0" : "—");
  const bar = document.getElementById("bar_" + id);
  if (bar) bar.style.width = Math.min(100, (mr.steps / MAX_S) * 100) + "%";
  const pg = document.getElementById("pg_" + id);
  if (pg) pg.textContent = "📍 " + (mr.current_page || "");
  const rs = document.getElementById("rs_" + id);
  if (rs && mr.last_reason) rs.textContent = "💬 " + mr.last_reason;
  const sp = document.getElementById("sp_" + id);
  if (sp) { let t = `Step ${mr.steps} / ${MAX_S}`; if (mr.time) t += ` · ${mr.time}s`; if (mr.error) t += ` · ⚠ ${mr.error}`; sp.textContent = t; }
  const pt = document.getElementById("pt_" + id);
  if (pt && mr.path && mr.path.length) {
    pt.innerHTML = mr.path.map((u, i) => {
      const name = articleName(u);
      const icon = i === 0 ? "🚀" : mr.status === "success" && i === mr.path.length - 1 ? "🎯" : "↳";
      return `<span class="pi">${icon} ${name}</span><br>`;
    }).join("");
    pt.scrollTop = pt.scrollHeight;
  }
}

// ── Leaderboard ──
function renderLB() {
  const results = loadResults();
  const stats = {};
  for (const r of results) {
    if (!stats[r.model_id]) stats[r.model_id] = { model_id: r.model_id, model_name: r.model_name, runs: 0, wins: 0, total_score: 0, total_steps: 0, total_time: 0 };
    const s = stats[r.model_id];
    s.runs++; s.wins += r.success ? 1 : 0; s.total_score += r.score || 0; s.total_steps += r.steps || 0; s.total_time += r.time || 0;
  }
  const lb = Object.values(stats).map(s => ({
    ...s, avg_score: (s.total_score / (s.runs || 1)).toFixed(1), avg_steps: (s.total_steps / (s.runs || 1)).toFixed(1),
    avg_time: (s.total_time / (s.runs || 1)).toFixed(1), win_rate: ((s.wins / (s.runs || 1)) * 100).toFixed(1),
  })).sort((a, b) => b.avg_score - a.avg_score || b.win_rate - a.win_rate);

  const el = document.getElementById("lb-body");
  if (!lb.length) { el.innerHTML = '<div class="empty">No results yet — run a race first!</div>'; return; }
  const tr = ["🥇", "🥈", "🥉"];
  el.innerHTML = `<table><thead><tr><th>Rank</th><th>Model</th><th>Avg Score</th><th>Avg Steps</th><th>Avg Time</th><th>Win Rate</th><th>Races</th></tr></thead><tbody>${lb.map((d, i) => `<tr><td class="rk ${i < 3 ? 'rk' + (i + 1) : ''}">${tr[i] || i + 1}</td><td><strong>${d.model_name}</strong></td><td class="sc" style="color:#58a6ff">${d.avg_score}</td><td>${d.avg_steps}</td><td>${d.avg_time}s</td><td>${d.win_rate}%<span class="wbar" style="width:${d.win_rate}px"></span></td><td style="color:#8b949e">${d.runs}</td></tr>`).join("")}</tbody></table>`;
}

function clearResults() {
  if (!confirm("Clear all race results?")) return;
  saveResults([]); renderLB();
}

// ── Settings ──
function buildKeyGrid() {
  const keys = loadKeys();
  const g = document.getElementById("key-grid"); g.innerHTML = "";
  KEYS.forEach(f => {
    const has = !!keys[f.k];
    g.innerHTML += `<div class="krow"><label>${f.lbl}</label><input type="password" id="ki_${f.k}" placeholder="${has ? "(already set — paste to update)" : f.ph}"><span class="kstat ${has ? "ok" : "no"}">${has ? "✓ Set" : "✗ Missing"}</span></div>`;
  });
}

function saveKeys() {
  const keys = loadKeys();
  KEYS.forEach(f => {
    const v = document.getElementById("ki_" + f.k).value.trim();
    if (v) keys[f.k] = v;
  });
  saveKeysToStorage(keys);
  buildModelGrid(); buildKeyGrid();
  alert("Saved! Models with valid keys are now available.");
}

// ── Tabs ──
function showTab(name) {
  document.querySelectorAll(".tab").forEach((t, i) => {
    t.classList.toggle("active", ["race", "leaderboard", "settings"][i] === name);
  });
  document.querySelectorAll(".pane").forEach(p => p.classList.toggle("active", p.id === "pane-" + name));
  if (name === "leaderboard") renderLB();
}

init();
