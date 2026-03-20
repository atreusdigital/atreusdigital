"""
Genera reporte de performance de Meta Ads y lo sube a Notion.
Uso: python -m reports.meta_performance --days 30 --account act_XXXXXXX
"""
import argparse
from datetime import date
from integrations.meta_ads.metrics import get_campaign_metrics, get_account_summary
from shared.notion_publisher import publish_report


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


def build_report(days_back: int = 30, account_name: str = "") -> dict:
    summary = get_account_summary(days_back)
    campaigns = get_campaign_metrics(days_back)

    total_spend = float(summary.get("spend", 0))
    total_impressions = int(summary.get("impressions", 0))
    total_clicks = int(summary.get("clicks", 0))
    ctr = round(float(summary.get("ctr", 0)), 2)
    cpm = round(float(summary.get("cpm", 0)), 2)
    roas = _extract_roas(summary.get("purchase_roas", []))

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

    return {
        "title": f"Meta Ads — {account_name or 'Reporte'} ({date.today().strftime('%B %Y')})",
        "period_days": days_back,
        "date": str(date.today()),
        "account_name": account_name,
        "summary": {
            "spend": round(total_spend, 2),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": ctr,
            "cpm": cpm,
            "roas": roas,
        },
        "campaigns": campaign_rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--account", type=str, default="")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar reporte sin subir a Notion")
    args = parser.parse_args()

    report = build_report(days_back=args.days, account_name=args.account)

    if args.dry_run:
        import json
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        url = publish_report(report)
        print(f"Reporte publicado en Notion: {url}")


if __name__ == "__main__":
    main()
