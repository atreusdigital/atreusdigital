"""
Genera un dashboard HTML dinámico con los datos de todas las cuentas de Meta Ads.
Uso: python -m reports.html_dashboard --days 7
"""
import argparse
import json
import os
from datetime import date
from pathlib import Path

from integrations.meta_ads.metrics import get_campaign_metrics, get_account_summary, extract_instagram_metrics
from integrations.meta_ads.ads import get_top_ads
from reports.meta_performance import _extract_purchases, _extract_roas, _period_label, _analyze_campaigns

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def fetch_account_data(account_id: str, account_name: str, account_type: str, days_back: int) -> dict:
    summary = get_account_summary(days_back, account_id=account_id)
    campaigns = get_campaign_metrics(days_back, account_id=account_id)
    top_ads = get_top_ads(days_back, top_n=5, account_id=account_id)
    instagram = extract_instagram_metrics(summary)

    campaign_rows = []
    for c in campaigns:
        campaign_rows.append({
            "name": c.get("campaign_name", ""),
            "spend": round(float(c.get("spend", 0)), 2),
            "impressions": int(c.get("impressions", 0)),
            "clicks": int(c.get("clicks", 0)),
            "ctr": round(float(c.get("ctr", 0)), 2),
            "cpc": round(float(c.get("cpc", 0)), 2),
            "purchases": _extract_purchases(c.get("actions", [])),
            "roas": _extract_roas(c.get("purchase_roas", [])),
        })

    analysis = _analyze_campaigns(campaign_rows)

    return {
        "name": account_name,
        "type": account_type,
        "account_id": account_id,
        "period": _period_label(days_back),
        "summary": {
            "spend": round(float(summary.get("spend", 0)), 2),
            "impressions": int(summary.get("impressions", 0)),
            "clicks": int(summary.get("clicks", 0)),
            "ctr": round(float(summary.get("ctr", 0)), 2),
            "cpm": round(float(summary.get("cpm", 0)), 2),
            "roas": _extract_roas(summary.get("purchase_roas", [])),
        },
        "instagram": instagram,
        "campaigns": campaign_rows,
        "top_ads": top_ads,
        "actions": analysis.get("actions", []),
        "creative_recs": analysis.get("creative_recs", []),
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Atreus Digital — Dashboard Meta Ads</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f0f13; --card: #1a1a24; --border: #2a2a3a;
    --accent: #7c5cfc; --accent2: #00d4aa; --red: #ff4d6d;
    --yellow: #ffd166; --blue: #4ea8de; --text: #e8e8f0; --muted: #888899;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

  header { padding: 24px 32px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 20px; font-weight: 700; }

  .tabs { display: flex; gap: 8px; padding: 20px 32px 0; overflow-x: auto; border-bottom: 1px solid var(--border); }
  .tab { padding: 10px 18px; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 13px; font-weight: 600; color: var(--muted); background: transparent; border: none; white-space: nowrap; transition: all .2s; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom: 2px solid var(--accent); }
  .tab .type-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-left: 6px; vertical-align: middle; }
  .tab .type-dot.ecommerce { background: var(--accent2); }
  .tab .type-dot.conversation { background: var(--blue); }
  .tab .type-dot.both { background: var(--yellow); }

  .panel { display: none; padding: 28px 32px; }
  .panel.active { display: block; }

  .type-banner { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; margin-bottom: 20px; }
  .type-banner.ecommerce { background: rgba(0,212,170,.1); color: var(--accent2); border: 1px solid rgba(0,212,170,.2); }
  .type-banner.conversation { background: rgba(78,168,222,.1); color: var(--blue); border: 1px solid rgba(78,168,222,.2); }
  .type-banner.both { background: rgba(255,209,102,.1); color: var(--yellow); border: 1px solid rgba(255,209,102,.2); }

  .metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(155px, 1fr)); gap: 14px; margin-bottom: 24px; }
  .metric-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
  .metric-card.highlight { border-color: var(--accent); }
  .metric-card .label { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-bottom: 8px; }
  .metric-card .value { font-size: 22px; font-weight: 700; }
  .metric-card .value.green { color: var(--accent2); }
  .metric-card .value.red { color: var(--red); }
  .metric-card .value.yellow { color: var(--yellow); }
  .metric-card .value.blue { color: var(--blue); }
  .metric-card .value.purple { color: var(--accent); }

  .section-title { font-size: 14px; font-weight: 700; margin-bottom: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
  .section-divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }

  .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
  .chart-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .chart-card h3 { font-size: 11px; color: var(--muted); margin-bottom: 16px; text-transform: uppercase; letter-spacing: .05em; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 10px 14px; color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border); }
  td { padding: 12px 14px; border-bottom: 1px solid var(--border); }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(124,92,252,.04); }
  .table-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; margin-bottom: 24px; }

  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }
  .badge.green { background: rgba(0,212,170,.15); color: var(--accent2); }
  .badge.yellow { background: rgba(255,209,102,.15); color: var(--yellow); }
  .badge.red { background: rgba(255,77,109,.15); color: var(--red); }
  .badge.blue { background: rgba(78,168,222,.15); color: var(--blue); }

  .recs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .rec-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
  .rec-card h3 { font-size: 13px; font-weight: 700; margin-bottom: 12px; }
  .rec-item { font-size: 13px; line-height: 1.6; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .rec-item:last-child { border-bottom: none; }

  .period-tag { background: rgba(124,92,252,.15); color: var(--accent); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 12px; }
  .generated { color: var(--muted); font-size: 12px; padding: 20px 32px; text-align: center; border-top: 1px solid var(--border); margin-top: 20px; }

  @media (max-width: 768px) {
    .charts-row, .recs-grid { grid-template-columns: 1fr; }
    .panel { padding: 20px 16px; }
    .tabs { padding: 16px 16px 0; }
  }
</style>
</head>
<body>

<header>
  <h1>⚡ Atreus Digital — Meta Ads Dashboard</h1>
  <span id="header-period"></span>
</header>

<div class="tabs" id="tabs"></div>
<div id="panels"></div>
<div class="generated">Generado el __DATE__ · Atreus Digital</div>

<script>
const DATA = __DATA__;

function roas_badge(r) {
  if (r >= 4) return `<span class="badge green">${r}x</span>`;
  if (r >= 2) return `<span class="badge yellow">${r}x</span>`;
  if (r > 0) return `<span class="badge red">${r}x</span>`;
  return `<span style="color:var(--muted)">—</span>`;
}
function roas_color(r) { return r >= 4 ? 'green' : r >= 2 ? 'yellow' : 'red'; }
function fmt(n) { return '$' + n.toLocaleString('es-AR', {minimumFractionDigits:2, maximumFractionDigits:2}); }
function num(n) { return n.toLocaleString('es-AR'); }

function type_label(t) {
  if (t === 'ecommerce') return '🛍️ eCommerce';
  if (t === 'conversation') return '💬 Conversaciones';
  return '🛍️ eCommerce + 💬 Conversaciones';
}

function render_panel(acc, idx) {
  const s = acc.summary;
  const ig = acc.instagram;
  const type = acc.type;
  const campaigns = acc.campaigns;

  // Banner de tipo
  const banner = `<div class="type-banner ${type}">${type_label(type)}</div>`;

  // Métricas base (todos)
  let metrics_html = `
    <div class="section-title">Métricas generales</div>
    <div class="metrics-grid">
      <div class="metric-card"><div class="label">Inversión</div><div class="value">${fmt(s.spend)}</div></div>
      <div class="metric-card"><div class="label">Impresiones</div><div class="value">${num(s.impressions)}</div></div>
      <div class="metric-card"><div class="label">Clics</div><div class="value">${num(s.clicks)}</div></div>
      <div class="metric-card"><div class="label">CTR</div><div class="value">${s.ctr}%</div></div>
      <div class="metric-card"><div class="label">CPM</div><div class="value">${fmt(s.cpm)}</div></div>`;

  // Métrica principal según tipo
  if (type === 'ecommerce' || type === 'both') {
    metrics_html += `<div class="metric-card highlight"><div class="label">ROAS</div><div class="value ${roas_color(s.roas)}">${s.roas}x</div></div>`;
  }
  if (type === 'conversation' || type === 'both') {
    const cpconv = ig.cost_per_conversation > 0 ? fmt(ig.cost_per_conversation) : '—';
    const convs = ig.conversations > 0 ? num(ig.conversations) : '—';
    metrics_html += `
      <div class="metric-card highlight"><div class="label">Conversaciones</div><div class="value blue">${convs}</div></div>
      <div class="metric-card highlight"><div class="label">Costo por conv.</div><div class="value blue">${cpconv}</div></div>`;
  }
  metrics_html += `</div>`;

  // Métricas Instagram (todos)
  const cost_follow = ig.cost_per_follow > 0 ? fmt(ig.cost_per_follow) : '—';
  const follow_rate = ig.follow_rate_pct > 0 ? ig.follow_rate_pct + '%' : '—';
  const prof_visits = ig.instagram_profile_visits > 0 ? num(ig.instagram_profile_visits) : '—';
  const follows = ig.instagram_follows > 0 ? num(ig.instagram_follows) : '—';

  metrics_html += `
    <hr class="section-divider">
    <div class="section-title">Instagram</div>
    <div class="metrics-grid">
      <div class="metric-card"><div class="label">Visitas al perfil</div><div class="value purple">${prof_visits}</div></div>
      <div class="metric-card"><div class="label">Seguimientos</div><div class="value purple">${follows}</div></div>
      <div class="metric-card"><div class="label">Costo por seguidor</div><div class="value purple">${cost_follow}</div></div>
      <div class="metric-card"><div class="label">% seguidor</div><div class="value purple">${follow_rate}</div></div>
    </div>
    <hr class="section-divider">`;

  // Charts
  const camp_names = campaigns.map(c => c.name.length > 22 ? c.name.substring(0,22)+'…' : c.name);
  const camp_spend = campaigns.map(c => c.spend);
  const camp_roas = campaigns.map(c => c.roas);

  const charts = `
    <div class="section-title">Campañas — rendimiento</div>
    <div class="charts-row">
      <div class="chart-card"><h3>Inversión por campaña</h3><canvas id="chart-spend-${idx}" height="220"></canvas></div>
      <div class="chart-card"><h3>ROAS por campaña</h3><canvas id="chart-roas-${idx}" height="220"></canvas></div>
    </div>`;

  // Tabla campañas
  const camp_rows = campaigns.map(c => `
    <tr>
      <td>${c.name}</td>
      <td>${fmt(c.spend)}</td>
      <td>${num(c.impressions)}</td>
      <td>${c.ctr}%</td>
      <td>${fmt(c.cpc)}</td>
      <td>${c.purchases || '—'}</td>
      <td>${roas_badge(c.roas)}</td>
    </tr>`).join('');

  const camp_table = `
    <div class="table-card">
      <table>
        <thead><tr><th>Campaña</th><th>Inversión</th><th>Impresiones</th><th>CTR</th><th>CPC</th><th>Compras</th><th>ROAS</th></tr></thead>
        <tbody>${camp_rows}</tbody>
      </table>
    </div><hr class="section-divider">`;

  // Top 5 anuncios
  const ads_rows = (acc.top_ads || []).map((a, i) => `
    <tr>
      <td><strong>#${i+1}</strong></td>
      <td>${a.ad_name}</td>
      <td style="color:var(--muted);font-size:12px">${a.campaign_name}</td>
      <td>${fmt(a.spend)}</td>
      <td>${a.ctr}%</td>
      <td>${a.purchases || '—'}</td>
      <td>${roas_badge(a.roas)}</td>
    </tr>`).join('');

  const ads_table = acc.top_ads && acc.top_ads.length > 0 ? `
    <div class="section-title">🏆 Top 5 anuncios de la semana</div>
    <div class="table-card">
      <table>
        <thead><tr><th>#</th><th>Anuncio</th><th>Campaña</th><th>Inversión</th><th>CTR</th><th>Compras</th><th>ROAS</th></tr></thead>
        <tbody>${ads_rows}</tbody>
      </table>
    </div><hr class="section-divider">` : '';

  // Recomendaciones
  const actions_items = (acc.actions || []).map(a => `<div class="rec-item">${a}</div>`).join('') || '<div class="rec-item" style="color:var(--muted)">Sin datos suficientes.</div>';
  const creative_items = (acc.creative_recs || []).map(r => `<div class="rec-item">${r}</div>`).join('') || '<div class="rec-item" style="color:var(--muted)">Sin recomendaciones.</div>';

  const recs = `
    <div class="section-title">Análisis y recomendaciones</div>
    <div class="recs-grid">
      <div class="rec-card"><h3 style="color:var(--accent2)">📊 Qué haría con estos números</h3>${actions_items}</div>
      <div class="rec-card"><h3 style="color:var(--accent)">🎬 Creativos</h3>${creative_items}</div>
    </div>`;

  return {
    html: banner + metrics_html + charts + camp_table + ads_table + recs,
    spend_data: { names: camp_names, spend: camp_spend, roas: camp_roas }
  };
}

// Build UI
const tabsEl = document.getElementById('tabs');
const panelsEl = document.getElementById('panels');
document.getElementById('header-period').innerHTML = DATA.length > 0 ? `<span class="period-tag">${DATA[0].period}</span>` : '';

const charts_data = [];

DATA.forEach((acc, idx) => {
  const dotClass = acc.type;
  const tab = document.createElement('button');
  tab.className = 'tab' + (idx === 0 ? ' active' : '');
  tab.innerHTML = `${acc.name}<span class="type-dot ${dotClass}"></span>`;
  tab.onclick = () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + idx).classList.add('active');
  };
  tabsEl.appendChild(tab);

  const { html, spend_data } = render_panel(acc, idx);
  const panel = document.createElement('div');
  panel.className = 'panel' + (idx === 0 ? ' active' : '');
  panel.id = 'panel-' + idx;
  panel.innerHTML = html;
  panelsEl.appendChild(panel);
  charts_data.push({ idx, ...spend_data });
});

requestAnimationFrame(() => {
  charts_data.forEach(({ idx, names, spend, roas }) => {
    const spendCtx = document.getElementById('chart-spend-' + idx);
    const roasCtx = document.getElementById('chart-roas-' + idx);
    if (!spendCtx || !roasCtx) return;

    new Chart(spendCtx, {
      type: 'bar',
      data: { labels: names, datasets: [{ label: 'Inversión', data: spend, backgroundColor: 'rgba(124,92,252,0.7)', borderRadius: 6 }] },
      options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#888899', font: { size: 11 } }, grid: { color: '#2a2a3a' } }, y: { ticks: { color: '#888899', font: { size: 11 } }, grid: { color: '#2a2a3a' } } } }
    });

    const roas_colors = roas.map(r => r >= 4 ? 'rgba(0,212,170,0.7)' : r >= 2 ? 'rgba(255,209,102,0.7)' : 'rgba(255,77,109,0.7)');
    new Chart(roasCtx, {
      type: 'bar',
      data: { labels: names, datasets: [{ label: 'ROAS', data: roas, backgroundColor: roas_colors, borderRadius: 6 }] },
      options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#888899', font: { size: 11 } }, grid: { color: '#2a2a3a' } }, y: { ticks: { color: '#888899', font: { size: 11 } }, grid: { color: '#2a2a3a' } } } }
    });
  });
});
</script>
</body>
</html>"""


def build_dashboard(days_back: int = 7, output_path: str = None) -> str:
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)

    all_data = []
    for acc in accounts:
        print(f"→ Cargando {acc['name']} ({acc.get('type', 'ecommerce')})...")
        try:
            data = fetch_account_data(acc["account_id"], acc["name"], acc.get("type", "ecommerce"), days_back)
            all_data.append(data)
        except Exception as e:
            print(f"  ❌ Error en {acc['name']}: {e}")

    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(all_data, ensure_ascii=False))
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
    print(f"\n✅ Dashboard generado: {path}")
    os.system(f"open '{path}'")


if __name__ == "__main__":
    main()
