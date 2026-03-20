"""
Genera reporte de performance de Meta Ads y lo sube a Notion.
Uso: python -m reports.meta_performance --account-name "Flower Time" --account-id act_XXXXXXX
     python -m reports.meta_performance --all   (corre todas las cuentas en accounts.json)
"""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from integrations.meta_ads.metrics import get_campaign_metrics, get_account_summary
from shared.config import META_AD_ACCOUNT_ID
from shared.notion_publisher import publish_report


ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"

ROAS_GOOD = 4.0
ROAS_OK = 2.0
CTR_LOW = 1.5


def _extract_purchases(actions: list) -> int:
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") == "purchase":
            return int(action.get("value", 0))
    return 0


def _extract_roas(purchase_roas: list) -> float:
    if not purchase_roas:
        return 0.0
    for r in purchase_roas:
        if r.get("action_type") == "omni_purchase":
            return round(float(r.get("value", 0)), 2)
    return 0.0


def _period_label(days_back: int) -> str:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days_back - 1)
    return f"{start.strftime('%d %b')} al {end.strftime('%d %b %Y')}"


def _analyze_campaigns(campaigns: list) -> dict:
    good = [c for c in campaigns if c["roas"] >= ROAS_GOOD]
    ok = [c for c in campaigns if ROAS_OK <= c["roas"] < ROAS_GOOD]
    bad = [c for c in campaigns if c["roas"] < ROAS_OK and c["spend"] > 0]

    actions = []
    for c in good:
        actions.append(f"✅ Escalar '{c['name']}': ROAS {c['roas']}x — aumentar presupuesto 20-30%, el algoritmo está en zona ganadora.")
    for c in ok:
        actions.append(f"🔄 Optimizar '{c['name']}': ROAS {c['roas']}x — testear nuevos creativos y audiencias para mejorar eficiencia.")
    for c in bad:
        actions.append(f"🔴 Revisar '{c['name']}': ROAS {c['roas']}x — pausar o reducir presupuesto al mínimo mientras se diagnostica.")

    creative_recs = []
    low_ctr = [c for c in campaigns if c["ctr"] < CTR_LOW and c["spend"] > 0]
    if low_ctr:
        names = ", ".join([f"'{c['name']}'" for c in low_ctr])
        creative_recs.append(f"📉 CTR bajo en {names}: los hooks no están generando suficiente interés. Probar hooks de problema directo o testimonios reales en los primeros 3 segundos.")

    high_cpc = sorted(campaigns, key=lambda x: x["cpc"], reverse=True)
    if high_cpc and high_cpc[0]["cpc"] > 200:
        creative_recs.append(f"💸 CPC alto en '{high_cpc[0]['name']}' (${high_cpc[0]['cpc']}): probar formato carrusel o video corto nativo para bajar el costo por clic.")

    best_ctr = sorted([c for c in campaigns if c["spend"] > 0], key=lambda x: x["ctr"], reverse=True)
    if best_ctr:
        creative_recs.append(f"🏆 '{best_ctr[0]['name']}' tiene el mejor CTR ({best_ctr[0]['ctr']}%): analizar qué formato/hook usa y replicarlo en otras campañas.")

    creative_recs.append("🎬 Recomendación general: mantener al menos 3 creativos activos por conjunto de anuncios. Rotar el que lleva más de 3 semanas activo aunque esté funcionando.")

    return {
        "good": good,
        "ok": ok,
        "bad": bad,
        "actions": actions,
        "creative_recs": creative_recs,
    }


def build_report(days_back: int = 7, account_name: str = "", account_id: str = "") -> dict:
    import os
    if account_id:
        os.environ["META_AD_ACCOUNT_ID"] = account_id

    summary = get_account_summary(days_back)
    campaigns = get_campaign_metrics(days_back)

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
    period_label = _period_label(days_back)

    return {
        "title": f"{account_name} — {period_label}",
        "period_days": days_back,
        "period_label": period_label,
        "date": str(date.today()),
        "account_name": account_name,
        "summary": {
            "spend": round(float(summary.get("spend", 0)), 2),
            "impressions": int(summary.get("impressions", 0)),
            "clicks": int(summary.get("clicks", 0)),
            "ctr": round(float(summary.get("ctr", 0)), 2),
            "cpm": round(float(summary.get("cpm", 0)), 2),
            "roas": _extract_roas(summary.get("purchase_roas", [])),
        },
        "campaigns": campaign_rows,
        "analysis": analysis,
    }


def run_all(days_back: int = 7, dry_run: bool = False):
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)

    for acc in accounts:
        print(f"\n→ Procesando {acc['name']}...")
        try:
            report = build_report(days_back=days_back, account_name=acc["name"], account_id=acc["account_id"])
            if dry_run:
                print(f"  ROAS: {report['summary']['roas']} | Inversión: ${report['summary']['spend']:,.2f}")
            else:
                url = publish_report(report)
                print(f"  ✅ Publicado: {url}")
        except Exception as e:
            print(f"  ❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--account-name", type=str, default="")
    parser.add_argument("--account-id", type=str, default="")
    parser.add_argument("--all", action="store_true", help="Correr todas las cuentas en accounts.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.all:
        run_all(days_back=args.days, dry_run=args.dry_run)
    else:
        account_id = args.account_id or META_AD_ACCOUNT_ID
        report = build_report(days_back=args.days, account_name=args.account_name, account_id=account_id)
        if args.dry_run:
            import json as json_mod
            print(json_mod.dumps(report, indent=2, ensure_ascii=False))
        else:
            url = publish_report(report)
            print(f"Reporte publicado: {url}")


if __name__ == "__main__":
    main()
