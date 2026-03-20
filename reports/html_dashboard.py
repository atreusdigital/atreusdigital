"""
Genera dashboard HTML dinámico de Meta Ads para todas las cuentas.
Uso: python -m reports.html_dashboard --days 7
"""
import argparse
import json
import os
from datetime import date
from pathlib import Path

from integrations.meta_ads.metrics import get_campaign_metrics, get_account_summary, extract_all_metrics, _extract_action, _extract_action_value
from integrations.meta_ads.ads import get_top_ads
from reports.meta_performance import _period_label, _extract_roas, _extract_purchases, _video_3sec, _analyze_campaigns

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def fetch_account_data(account_id: str, account_name: str, account_type: str, days_back: int) -> dict:
    summary_raw = get_account_summary(days_back, account_id=account_id)
    campaigns_raw = get_campaign_metrics(days_back, account_id=account_id)
    top_ads = get_top_ads(days_back, top_n=5, account_id=account_id)
    metrics = extract_all_metrics(summary_raw)

    campaign_rows = []
    for c in campaigns_raw:
        impr = int(c.get("impressions", 0))
        v3sec = _video_3sec(c)
        hook_rate = round((v3sec / impr) * 100, 2) if impr > 0 else 0.0
        spend = round(float(c.get("spend", 0)), 2)
        purchases = _extract_purchases(c.get("actions", []))
        purchase_value = _extract_action_value(c.get("action_values", []), "purchase")
        ticket = round(purchase_value / purchases, 2) if purchases > 0 else 0.0
        convs = int(_extract_action(c.get("actions", []), "onsite_conversion.messaging_conversation_started_7d"))
        cost_conv = round(spend / convs, 2) if convs > 0 else 0.0

        campaign_rows.append({
            "name": c.get("campaign_name", ""),
            "spend": spend,
            "impressions": impr,
            "clicks": int(c.get("clicks", 0)),
            "ctr": round(float(c.get("ctr", 0)), 2),
            "cpc": round(float(c.get("cpc", 0)), 2),
            "hook_rate": hook_rate,
            "purchases": purchases,
            "ticket_promedio": ticket,
            "roas": _extract_roas(c.get("purchase_roas", [])),
            "conversations": convs,
            "cost_per_conversation": cost_conv,
            "frequency": round(float(c.get("frequency", 0)), 2),
        })

    analysis = _analyze_campaigns(campaign_rows, account_type)

    return {
        "name": account_name,
        "type": account_type,
        "period": _period_label(days_back),
        "summary": {
            "spend": round(float(summary_raw.get("spend", 0)), 2),
            "impressions": int(summary_raw.get("impressions", 0)),
            "reach": metrics["reach"],
            "clicks": int(summary_raw.get("clicks", 0)),
            "ctr": round(float(summary_raw.get("ctr", 0)), 2),
            "cpm": round(float(summary_raw.get("cpm", 0)), 2),
            "frequency": metrics["frequency"],
            "roas": metrics["roas"],
            "hook_rate": metrics["hook_rate"],
            "hold_rate": metrics["hold_rate"],
        },
        "ecommerce": {
            "purchases": metrics["purchases"],
            "purchase_value": metrics["purchase_value"],
            "ticket_promedio": metrics["ticket_promedio"],
        },
        "conversation": {
            "conversations": metrics["conversations"],
            "cost_per_conversation": metrics["cost_per_conversation"],
        },
        "instagram": {
            "profile_visits": metrics["instagram_profile_visits"],
            "follows": metrics["instagram_follows"],
            "cost_per_follow": metrics["cost_per_follow"],
            "follow_rate_pct": metrics["follow_rate_pct"],
        },
        "campaigns": campaign_rows,
        "top_ads": top_ads,
        "actions": analysis.get("actions", []),
        "creative_recs": analysis.get("creative_recs", []),
    }


HTML = r"""<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Atreus Digital — Meta Ads Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root[data-theme="dark"] {
  --bg: #0a0a14;
  --bg-gradient: radial-gradient(ellipse at 20% 50%, #1a0a3e 0%, #0a0a14 60%), radial-gradient(ellipse at 80% 20%, #0a1a3e 0%, transparent 50%);
  --glass: rgba(255,255,255,0.04);
  --glass-border: rgba(255,255,255,0.10);
  --glass-hover: rgba(255,255,255,0.07);
  --glass-strong: rgba(255,255,255,0.08);
  --text: #f0f0ff; --muted: #8888bb; --muted2: #55557a;
  --accent: #a78bfa; --green: #34d399; --red: #f87171; --yellow: #fbbf24;
  --blue: #60a5fa; --orange: #fb923c; --pink: #f472b6;
  --shadow: 0 8px 32px rgba(0,0,0,.4), 0 2px 8px rgba(0,0,0,.3);
  --glow-accent: 0 0 20px rgba(167,139,250,.2);
}
:root[data-theme="light"] {
  --bg: #f0f0ff;
  --bg-gradient: radial-gradient(ellipse at 20% 50%, #e8e0ff 0%, #f0f0ff 60%), radial-gradient(ellipse at 80% 20%, #e0e8ff 0%, transparent 50%);
  --glass: rgba(255,255,255,0.55);
  --glass-border: rgba(255,255,255,0.8);
  --glass-hover: rgba(255,255,255,0.75);
  --glass-strong: rgba(255,255,255,0.70);
  --text: #1a1a3e; --muted: #6060a0; --muted2: #9090c0;
  --accent: #7c3aed; --green: #059669; --red: #dc2626; --yellow: #d97706;
  --blue: #2563eb; --orange: #ea580c; --pink: #db2777;
  --shadow: 0 8px 32px rgba(100,80,200,.12), 0 2px 8px rgba(100,80,200,.08);
  --glow-accent: 0 0 20px rgba(124,58,237,.1);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  background-image: var(--bg-gradient);
  background-attachment: fixed;
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
  min-height: 100vh;
  transition: background .4s, color .3s;
}

/* LIQUID GLASS BASE */
.glass {
  background: var(--glass);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow);
}

/* HEADER */
header {
  padding: 16px 28px;
  background: var(--glass-strong);
  backdrop-filter: blur(24px) saturate(200%);
  -webkit-backdrop-filter: blur(24px) saturate(200%);
  border-bottom: 1px solid var(--glass-border);
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 100;
}
.header-left { display: flex; align-items: center; gap: 14px; }
header h1 { font-size: 17px; font-weight: 800; letter-spacing: -.3px; }
.period-pill {
  background: rgba(167,139,250,.18);
  color: var(--accent);
  border: 1px solid rgba(167,139,250,.3);
  padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
  backdrop-filter: blur(8px);
}

/* THEME TOGGLE */
.theme-toggle {
  background: var(--glass);
  backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: 20px; padding: 7px 16px;
  cursor: pointer; font-size: 12px; font-weight: 600; color: var(--muted);
  display: flex; align-items: center; gap: 6px; transition: all .2s;
}
.theme-toggle:hover { color: var(--text); border-color: var(--accent); box-shadow: var(--glow-accent); }

/* TABS */
.tabs-wrapper {
  background: var(--glass);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--glass-border);
  padding: 0 28px; overflow-x: auto; display: flex; gap: 4px;
}
.tab {
  padding: 12px 16px; cursor: pointer; font-size: 12px; font-weight: 600;
  color: var(--muted); background: transparent; border: none;
  border-bottom: 2px solid transparent; white-space: nowrap;
  transition: all .15s; display: flex; align-items: center; gap: 6px;
}
.tab:hover { color: var(--text); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot.ecommerce { background: var(--green); }
.dot.conversation { background: var(--blue); }
.dot.both { background: var(--yellow); }

/* PANELS */
.panel { display: none; padding: 24px 28px; max-width: 1400px; margin: 0 auto; }
.panel.active { display: block; }

/* TYPE BANNER */
.type-banner { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; margin-bottom: 20px; }
.type-banner.ecommerce { background: rgba(0,212,170,.1); color: var(--green); border: 1px solid rgba(0,212,170,.2); }
.type-banner.conversation { background: rgba(78,168,222,.1); color: var(--blue); border: 1px solid rgba(78,168,222,.2); }
.type-banner.both { background: rgba(255,209,102,.1); color: var(--yellow); border: 1px solid rgba(255,209,102,.2); }

/* SECTION */
.section { margin-bottom: 28px; }
.section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: 14px; }

/* METRIC CARDS */
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.mcard {
  background: var(--glass);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid var(--glass-border);
  border-radius: 18px; padding: 16px;
  box-shadow: var(--shadow);
  transition: transform .2s, box-shadow .2s;
}
.mcard:hover { transform: translateY(-3px); box-shadow: var(--shadow), var(--glow-accent); }
.mcard.featured {
  background: linear-gradient(135deg, rgba(167,139,250,.15), rgba(167,139,250,.05));
  border-color: rgba(167,139,250,.35);
  box-shadow: var(--shadow), var(--glow-accent);
}
.mcard .mlabel { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 8px; }
.mcard .mval { font-size: 22px; font-weight: 800; line-height: 1; }
.mcard .msub { font-size: 10px; color: var(--muted2); margin-top: 4px; }
.c-green { color: var(--green); }
.c-red { color: var(--red); }
.c-yellow { color: var(--yellow); }
.c-blue { color: var(--blue); }
.c-purple { color: var(--accent); }
.c-orange { color: var(--orange); }
.c-pink { color: var(--pink); }

/* PROGRESS BAR */
.progress-bar { height: 6px; background: var(--border); border-radius: 10px; overflow: hidden; margin-top: 8px; }
.progress-fill { height: 100%; border-radius: 10px; transition: width .6s ease; }

/* CHARTS GRID */
.charts-3 { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 16px; }
.charts-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-card {
  background: var(--glass);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid var(--glass-border);
  border-radius: 18px; padding: 20px;
  box-shadow: var(--shadow);
}
.chart-card h3 { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 16px; }

/* TABLE */
.table-card {
  background: var(--glass);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid var(--glass-border);
  border-radius: 18px; overflow: hidden;
  box-shadow: var(--shadow);
}
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { padding: 10px 14px; color: var(--muted); font-size: 10px; text-transform: uppercase; letter-spacing: .06em; text-align: left; border-bottom: 1px solid var(--glass-border); font-weight: 600; background: rgba(255,255,255,0.03); }
td { padding: 11px 14px; border-bottom: 1px solid var(--glass-border); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(167,139,250,.06); }
.badge { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 10px; font-weight: 800; }
.badge.g { background: rgba(0,212,170,.15); color: var(--green); }
.badge.y { background: rgba(255,209,102,.15); color: var(--yellow); }
.badge.r { background: rgba(255,77,109,.15); color: var(--red); }
.badge.b { background: rgba(78,168,222,.15); color: var(--blue); }

/* RECS */
.recs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.rec-card {
  background: var(--glass);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid var(--glass-border);
  border-radius: 18px; padding: 18px;
  box-shadow: var(--shadow);
}
.rec-card h3 { font-size: 12px; font-weight: 700; margin-bottom: 14px; }
.rec-item { font-size: 12px; line-height: 1.65; padding: 9px 0; border-bottom: 1px solid var(--border); color: var(--text); }
.rec-item:last-child { border-bottom: none; padding-bottom: 0; }

/* INSTAGRAM NOTE */
.ig-note {
  background: rgba(96,165,250,.06);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(96,165,250,.2);
  border-radius: 12px; padding: 10px 14px; font-size: 11px; color: var(--muted); margin-top: 12px;
}

hr.divider { border: none; border-top: 1px solid var(--glass-border); margin: 24px 0; }
.generated { text-align: center; padding: 20px; font-size: 11px; color: var(--muted2); border-top: 1px solid var(--glass-border); }

@media (max-width: 900px) {
  .charts-3, .charts-2, .recs-grid { grid-template-columns: 1fr; }
  .panel { padding: 16px; }
}
</style>
</head>
<body>

<header>
  <div class="header-left">
    <h1>⚡ Atreus Digital — Meta Ads</h1>
    <span class="period-pill" id="hperiod"></span>
  </div>
  <button class="theme-toggle" onclick="toggleTheme()">
    <span id="theme-icon">☀️</span> <span id="theme-label">Light mode</span>
  </button>
</header>

<div class="tabs-wrapper" id="tabs"></div>
<div id="panels"></div>
<div class="generated">Generado el __DATE__ · Atreus Digital</div>

<script>
const DATA = __DATA__;
let chartInstances = {};

// Theme
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  document.getElementById('theme-icon').textContent = isDark ? '🌙' : '☀️';
  document.getElementById('theme-label').textContent = isDark ? 'Dark mode' : 'Light mode';
  rebuildCharts();
}

function getCSS(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
function gridColor() { return getCSS('--border'); }
function textColor() { return getCSS('--muted'); }

// Format
function fmt(n) { return '$' + n.toLocaleString('es-AR', {minimumFractionDigits:2, maximumFractionDigits:2}); }
function num(n) { return n.toLocaleString('es-AR'); }
function pct(n) { return n > 0 ? n + '%' : '—'; }
function dash(n) { return n > 0 ? n : '—'; }

function roas_badge(r) {
  if (!r || r === 0) return '<span style="color:var(--muted)">—</span>';
  const cls = r >= 4 ? 'g' : r >= 2 ? 'y' : 'r';
  return `<span class="badge ${cls}">${r}x</span>`;
}
function ctr_badge(c) {
  const cls = c >= 2.5 ? 'g' : c >= 1.5 ? 'y' : 'r';
  return `<span class="badge ${cls}">${c}%</span>`;
}
function hook_badge(h) {
  if (!h) return '<span style="color:var(--muted)">—</span>';
  const cls = h >= 40 ? 'g' : h >= 25 ? 'y' : 'r';
  return `<span class="badge ${cls}">${h}%</span>`;
}
function roas_color(r) { return r >= 4 ? 'c-green' : r >= 2 ? 'c-yellow' : 'c-red'; }
function type_label(t) {
  if (t === 'ecommerce') return '🛍️ eCommerce';
  if (t === 'conversation') return '💬 Conversaciones';
  return '🛍️ eCommerce · 💬 Conversaciones';
}

function render_panel(acc, idx) {
  const s = acc.summary;
  const ec = acc.ecommerce;
  const cv = acc.conversation;
  const ig = acc.instagram;
  const type = acc.type;
  const camps = acc.campaigns;

  const banner = `<div class="type-banner ${type}">${type_label(type)}</div>`;

  // ── MÉTRICAS GENERALES ──
  let gen_cards = `
    <div class="mcard"><div class="mlabel">Inversión</div><div class="mval">${fmt(s.spend)}</div></div>
    <div class="mcard"><div class="mlabel">Alcance</div><div class="mval c-purple">${num(s.reach || 0)}</div></div>
    <div class="mcard"><div class="mlabel">Impresiones</div><div class="mval">${num(s.impressions)}</div></div>
    <div class="mcard"><div class="mlabel">CTR</div><div class="mval ${s.ctr >= 2.5 ? 'c-green' : s.ctr >= 1.5 ? 'c-yellow' : 'c-red'}">${s.ctr}%</div>
      <div class="progress-bar"><div class="progress-fill" style="width:${Math.min(s.ctr/5*100,100)}%;background:var(--${s.ctr >= 2.5 ? 'green' : s.ctr >= 1.5 ? 'yellow' : 'red'})"></div></div>
    </div>
    <div class="mcard"><div class="mlabel">CPM</div><div class="mval">${fmt(s.cpm)}</div></div>
    <div class="mcard"><div class="mlabel">Frecuencia</div><div class="mval ${s.frequency > 3.5 ? 'c-red' : s.frequency > 2 ? 'c-yellow' : 'c-green'}">${s.frequency || '—'}</div><div class="msub">veces por persona</div></div>`;

  if (s.hook_rate > 0) {
    gen_cards += `<div class="mcard featured"><div class="mlabel">🎣 Hook Rate</div><div class="mval ${s.hook_rate >= 40 ? 'c-green' : s.hook_rate >= 25 ? 'c-yellow' : 'c-red'}">${s.hook_rate}%</div>
      <div class="progress-bar"><div class="progress-fill" style="width:${Math.min(s.hook_rate*2,100)}%;background:var(--${s.hook_rate >= 40 ? 'green' : s.hook_rate >= 25 ? 'yellow' : 'red'})"></div></div>
    </div>`;
    if (s.hold_rate > 0) {
      gen_cards += `<div class="mcard"><div class="mlabel">⏱️ Hold Rate</div><div class="mval ${s.hold_rate >= 50 ? 'c-green' : s.hold_rate >= 30 ? 'c-yellow' : 'c-red'}">${s.hold_rate}%</div></div>`;
    }
  }

  let primary_cards = '';

  // eCommerce metrics
  if (type === 'ecommerce' || type === 'both') {
    primary_cards += `
      <div class="mcard featured"><div class="mlabel">ROAS</div><div class="mval ${roas_color(s.roas)}">${s.roas > 0 ? s.roas+'x' : '—'}</div></div>
      <div class="mcard"><div class="mlabel">Compras</div><div class="mval c-green">${ec.purchases > 0 ? num(ec.purchases) : '—'}</div></div>
      <div class="mcard"><div class="mlabel">Ticket promedio</div><div class="mval c-orange">${ec.ticket_promedio > 0 ? fmt(ec.ticket_promedio) : '—'}</div><div class="msub">valor de compra</div></div>
      <div class="mcard"><div class="mlabel">Revenue</div><div class="mval c-yellow">${ec.purchase_value > 0 ? fmt(ec.purchase_value) : '—'}</div></div>`;
  }

  // Conversation metrics
  if (type === 'conversation' || type === 'both') {
    primary_cards += `
      <div class="mcard featured"><div class="mlabel">Conversaciones</div><div class="mval c-blue">${cv.conversations > 0 ? num(cv.conversations) : '—'}</div></div>
      <div class="mcard"><div class="mlabel">Costo / conversación</div><div class="mval c-blue">${cv.cost_per_conversation > 0 ? fmt(cv.cost_per_conversation) : '—'}</div></div>`;
  }

  // Instagram metrics
  const ig_cards = `
    <div class="mcard"><div class="mlabel">👁️ Visitas al perfil</div><div class="mval c-pink">${dash(ig.profile_visits)}</div></div>
    <div class="mcard"><div class="mlabel">➕ Seguimientos</div><div class="mval c-pink">${dash(ig.follows)}</div></div>
    <div class="mcard"><div class="mlabel">💰 Costo/seguidor</div><div class="mval c-pink">${ig.cost_per_follow > 0 ? fmt(ig.cost_per_follow) : '—'}</div></div>
    <div class="mcard"><div class="mlabel">📊 % seguidor</div><div class="mval c-pink">${ig.follow_rate_pct > 0 ? ig.follow_rate_pct+'%' : '—'}</div></div>`;

  const ig_note = `<div class="ig-note">ℹ️ Las métricas de Instagram muestran interacciones generadas directamente por los anuncios. Para métricas orgánicas (seguidores totales, alcance orgánico) se requiere conectar la Instagram Graph API.</div>`;

  const metrics_section = `
    <div class="section">
      <div class="section-title">Métricas generales</div>
      <div class="metrics-grid">${gen_cards}</div>
    </div>`;

  const primary_section = primary_cards ? `
    <div class="section">
      <div class="section-title">${type === 'conversation' ? 'Conversaciones' : type === 'both' ? 'eCommerce + Conversaciones' : 'eCommerce'}</div>
      <div class="metrics-grid">${primary_cards}</div>
    </div>` : '';

  const ig_section = `
    <div class="section">
      <div class="section-title">Instagram (desde anuncios)</div>
      <div class="metrics-grid">${ig_cards}</div>
      ${ig_note}
    </div>`;

  // ── CHARTS ──
  const names = camps.map(c => c.name.length > 20 ? c.name.substring(0,20)+'…' : c.name);
  const spends = camps.map(c => c.spend);
  const roas_vals = camps.map(c => c.roas);
  const ctrs = camps.map(c => c.ctr);
  const hooks = camps.map(c => c.hook_rate || 0);
  const total_spend = spends.reduce((a,b) => a+b, 0);

  const charts_section = `
    <div class="section">
      <div class="section-title">Distribución de presupuesto & performance</div>
      <div class="charts-3">
        <div class="chart-card"><h3>Inversión por campaña</h3><canvas id="cs-${idx}" height="220"></canvas></div>
        <div class="chart-card"><h3>Distribución del spend</h3><canvas id="cd-${idx}" height="220"></canvas></div>
        <div class="chart-card"><h3>CTR por campaña</h3><canvas id="cc-${idx}" height="220"></canvas></div>
      </div>
      <div class="charts-2" style="margin-top:16px">
        <div class="chart-card"><h3>ROAS por campaña</h3><canvas id="cr-${idx}" height="180"></canvas></div>
        <div class="chart-card"><h3>🎣 Hook Rate por campaña</h3><canvas id="ch-${idx}" height="180"></canvas></div>
      </div>
    </div>`;

  // ── TABLA CAMPAÑAS ──
  const camp_rows = camps.map(c => `<tr>
    <td style="font-weight:600;max-width:180px">${c.name}</td>
    <td>${fmt(c.spend)}</td>
    <td>${ctr_badge(c.ctr)}</td>
    <td>${hook_badge(c.hook_rate)}</td>
    <td>${c.frequency > 0 ? c.frequency : '—'}</td>
    <td>${c.purchases > 0 ? c.purchases : '—'}</td>
    <td>${c.ticket_promedio > 0 ? fmt(c.ticket_promedio) : '—'}</td>
    <td>${c.conversations > 0 ? c.conversations : '—'}</td>
    <td>${roas_badge(c.roas)}</td>
  </tr>`).join('');

  const camp_section = `
    <div class="section">
      <div class="section-title">Detalle por campaña</div>
      <div class="table-card">
        <table>
          <thead><tr><th>Campaña</th><th>Inversión</th><th>CTR</th><th>Hook Rate</th><th>Freq.</th><th>Compras</th><th>Ticket prom.</th><th>Convers.</th><th>ROAS</th></tr></thead>
          <tbody>${camp_rows}</tbody>
        </table>
      </div>
    </div>`;

  // ── TOP 5 ADS ──
  const ads_rows = (acc.top_ads || []).map((a, i) => `<tr>
    <td><strong>#${i+1}</strong></td>
    <td style="max-width:200px">${a.ad_name}</td>
    <td style="color:var(--muted);font-size:11px">${a.campaign_name.substring(0,25)}</td>
    <td>${fmt(a.spend)}</td>
    <td>${ctr_badge(a.ctr)}</td>
    <td>${a.purchases > 0 ? a.purchases : '—'}</td>
    <td>${roas_badge(a.roas)}</td>
  </tr>`).join('');

  const ads_section = acc.top_ads && acc.top_ads.length > 0 ? `
    <div class="section">
      <div class="section-title">🏆 Top 5 anuncios de la semana</div>
      <div class="table-card">
        <table>
          <thead><tr><th>#</th><th>Anuncio</th><th>Campaña</th><th>Inversión</th><th>CTR</th><th>Compras</th><th>ROAS</th></tr></thead>
          <tbody>${ads_rows}</tbody>
        </table>
      </div>
    </div>` : '';

  // ── RECS ──
  const acts = (acc.actions || []).map(a => `<div class="rec-item">${a}</div>`).join('');
  const crecs = (acc.creative_recs || []).map(r => `<div class="rec-item">${r}</div>`).join('');

  const recs_section = `
    <div class="section">
      <div class="section-title">Análisis & recomendaciones</div>
      <div class="recs-grid">
        <div class="rec-card"><h3 style="color:var(--green)">📊 Acciones recomendadas</h3>${acts || '<div class="rec-item" style="color:var(--muted)">Sin datos suficientes.</div>'}</div>
        <div class="rec-card"><h3 style="color:var(--accent)">🎬 Creativos</h3>${crecs || '<div class="rec-item" style="color:var(--muted)">Sin recomendaciones.</div>'}</div>
      </div>
    </div>`;

  return {
    html: banner + metrics_section + primary_section + ig_section + charts_section + camp_section + ads_section + recs_section,
    chart_data: { names, spends, roas_vals, ctrs, hooks, total_spend }
  };
}

// ── BUILD UI ──
const tabsEl = document.getElementById('tabs');
const panelsEl = document.getElementById('panels');
document.getElementById('hperiod').textContent = DATA.length > 0 ? DATA[0].period : '';

const all_chart_data = [];

DATA.forEach((acc, idx) => {
  const tab = document.createElement('button');
  tab.className = 'tab' + (idx === 0 ? ' active' : '');
  tab.innerHTML = `<span class="dot ${acc.type}"></span>${acc.name}`;
  tab.onclick = () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + idx).classList.add('active');
  };
  tabsEl.appendChild(tab);

  const { html, chart_data } = render_panel(acc, idx);
  const panel = document.createElement('div');
  panel.className = 'panel' + (idx === 0 ? ' active' : '');
  panel.id = 'panel-' + idx;
  panel.innerHTML = html;
  panelsEl.appendChild(panel);
  all_chart_data.push({ idx, ...chart_data });
});

function buildCharts() {
  Object.values(chartInstances).forEach(c => c.destroy());
  chartInstances = {};

  const grid = gridColor();
  const txt = textColor();
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const COLORS = ['#7c5cfc','#00d4aa','#ffd166','#4ea8de','#ff9f43','#fd79a8','#a29bfe'];

  all_chart_data.forEach(({ idx, names, spends, roas_vals, ctrs, hooks, total_spend }) => {
    const opts_base = {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: txt, font: { size: 10 } }, grid: { color: grid } },
        y: { ticks: { color: txt, font: { size: 10 } }, grid: { color: grid } }
      }
    };

    // Horizontal bar — inversión
    const csEl = document.getElementById('cs-' + idx);
    if (csEl) {
      chartInstances['cs'+idx] = new Chart(csEl, {
        type: 'bar',
        data: { labels: names, datasets: [{ data: spends, backgroundColor: COLORS.map((c,i) => COLORS[i % COLORS.length] + 'bb'), borderRadius: 6 }] },
        options: { ...opts_base, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { ticks: { color: txt, font: { size: 10 } }, grid: { color: grid } }, y: { ticks: { color: txt, font: { size: 10 } }, grid: { color: 'transparent' } } } }
      });
    }

    // Donut — distribución spend
    const cdEl = document.getElementById('cd-' + idx);
    if (cdEl) {
      chartInstances['cd'+idx] = new Chart(cdEl, {
        type: 'doughnut',
        data: { labels: names, datasets: [{ data: spends, backgroundColor: COLORS.map(c => c + 'cc'), borderColor: isDark ? '#1a1a26' : '#ffffff', borderWidth: 3 }] },
        options: { plugins: { legend: { display: true, position: 'bottom', labels: { color: txt, font: { size: 10 }, boxWidth: 10, padding: 8 } } }, cutout: '65%' }
      });
    }

    // Bar — CTR
    const ccEl = document.getElementById('cc-' + idx);
    if (ccEl) {
      chartInstances['cc'+idx] = new Chart(ccEl, {
        type: 'bar',
        data: { labels: names, datasets: [{ data: ctrs, backgroundColor: ctrs.map(c => c >= 2.5 ? '#00d4aa99' : c >= 1.5 ? '#ffd16699' : '#ff4d6d99'), borderRadius: 6 }] },
        options: opts_base
      });
    }

    // Bar — ROAS
    const crEl = document.getElementById('cr-' + idx);
    if (crEl) {
      chartInstances['cr'+idx] = new Chart(crEl, {
        type: 'bar',
        data: { labels: names, datasets: [{ data: roas_vals, backgroundColor: roas_vals.map(r => r >= 4 ? '#00d4aa99' : r >= 2 ? '#ffd16699' : '#ff4d6d99'), borderRadius: 6 }] },
        options: { ...opts_base, plugins: { ...opts_base.plugins, annotation: {} } }
      });
    }

    // Bar — Hook Rate
    const chEl = document.getElementById('ch-' + idx);
    if (chEl) {
      chartInstances['ch'+idx] = new Chart(chEl, {
        type: 'bar',
        data: { labels: names, datasets: [{ data: hooks, backgroundColor: hooks.map(h => h >= 40 ? '#00d4aa99' : h >= 25 ? '#ffd16699' : h > 0 ? '#ff4d6d99' : '#44444499'), borderRadius: 6 }] },
        options: opts_base
      });
    }
  });
}

function rebuildCharts() {
  setTimeout(buildCharts, 50);
}

requestAnimationFrame(buildCharts);
</script>
</body>
</html>"""


def build_dashboard(days_back: int = 7, output_path: str = None) -> str:
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)

    all_data = []
    for acc in accounts:
        print(f"→ Cargando {acc['name']} ({acc.get('type','ecommerce')})...")
        try:
            data = fetch_account_data(acc["account_id"], acc["name"], acc.get("type", "ecommerce"), days_back)
            all_data.append(data)
        except Exception as e:
            print(f"  ❌ {acc['name']}: {e}")

    html = HTML.replace("__DATA__", json.dumps(all_data, ensure_ascii=False))
    html = html.replace("__DATE__", str(date.today()))

    OUTPUT_DIR.mkdir(exist_ok=True)
    out = output_path or str(OUTPUT_DIR / f"dashboard_{date.today()}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    path = build_dashboard(days_back=args.days, output_path=args.output)
    print(f"\n✅ Dashboard: {path}")
    os.system(f"open '{path}'")


if __name__ == "__main__":
    main()
