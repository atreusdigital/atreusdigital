"""
Genera reporte de performance de Meta Ads y lo sube a Notion.
Uso: python -m reports.meta_performance --account-name "Flower Time" --account-id act_XXXXXXX
     python -m reports.meta_performance --all
"""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from integrations.meta_ads.metrics import get_campaign_metrics, get_account_summary, extract_all_metrics, _extract_action, _extract_action_value
from shared.config import META_AD_ACCOUNT_ID
from shared.notion_publisher import publish_report

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"


def _period_label(days_back: int) -> str:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days_back - 1)
    return f"{start.strftime('%d %b')} al {end.strftime('%d %b %Y')}"


def _extract_roas(purchase_roas: list) -> float:
    if not purchase_roas:
        return 0.0
    for r in purchase_roas:
        if r.get("action_type") == "omni_purchase":
            return round(float(r.get("value", 0)), 2)
    return 0.0


def _extract_purchases(actions: list) -> int:
    return int(_extract_action(actions, "purchase"))


def _video_3sec(row: dict) -> float:
    v = row.get("video_3_sec_watched_actions", [])
    return float(v[0].get("value", 0)) if v else 0.0


def _analyze_campaigns(campaigns: list, account_type: str = "ecommerce") -> dict:
    actions = []
    creative_recs = []

    # Hook Rate analysis
    has_video = any(c.get("hook_rate", 0) > 0 for c in campaigns)
    if has_video:
        low_hook = [c for c in campaigns if 0 < c.get("hook_rate", 0) < 25]
        good_hook = [c for c in campaigns if c.get("hook_rate", 0) >= 40]
        if low_hook:
            names = ", ".join([f"'{c['name']}'" for c in low_hook[:2]])
            creative_recs.append(f"🎣 Hook Rate bajo en {names} (< 25%): los primeros 3 segundos no están deteniendo el scroll. Probar hook de pregunta directa, cifra impactante o situación de conflicto.")
        if good_hook:
            creative_recs.append(f"🏆 '{good_hook[0]['name']}' tiene excelente Hook Rate ({good_hook[0].get('hook_rate', 0)}%): analizar el opening y replicarlo en otras campañas.")

    # CTR analysis
    low_ctr = [c for c in campaigns if 0 < c.get("ctr", 0) < 1.5]
    high_ctr = sorted([c for c in campaigns if c.get("ctr", 0) >= 2.5], key=lambda x: x["ctr"], reverse=True)
    if low_ctr:
        names = ", ".join([f"'{c['name']}'" for c in low_ctr[:2]])
        creative_recs.append(f"📉 CTR bajo en {names}: el anuncio no genera suficiente intención de clic. Testear CTA más directo, cambiar imagen principal o usar formato carrusel.")
    if high_ctr:
        creative_recs.append(f"✅ '{high_ctr[0]['name']}' lidera en CTR ({high_ctr[0]['ctr']}%): el creativo y la audiencia están alineados. Escalar presupuesto con cuidado.")

    # Hold Rate (si hay video)
    if has_video:
        low_hold = [c for c in campaigns if 0 < c.get("hold_rate", 0) < 20]
        if low_hold:
            creative_recs.append(f"⏸️ Hold Rate bajo en {low_hold[0]['name']}: la gente engancha en el hook pero no termina el video. El desarrollo del mensaje pierde fuerza. Acortar el video o mover el CTA antes.")

    # Frecuencia
    high_freq = [c for c in campaigns if c.get("frequency", 0) > 3.5]
    if high_freq:
        names = ", ".join([f"'{c['name']}'" for c in high_freq[:2]])
        creative_recs.append(f"🔁 Frecuencia alta en {names}: la misma persona ve el anuncio +3.5 veces. Rotar creativos ya o expandir audiencia para evitar fatiga.")

    # Acciones por tipo
    if account_type in ("ecommerce", "both"):
        good = [c for c in campaigns if c.get("roas", 0) >= 4]
        ok = [c for c in campaigns if 2 <= c.get("roas", 0) < 4]
        bad = [c for c in campaigns if 0 < c.get("roas", 0) < 2]
        for c in good:
            actions.append(f"✅ Escalar '{c['name']}': ROAS {c['roas']}x — aumentar presupuesto 20-30% y testear nuevas audiencias similares.")
        for c in ok:
            actions.append(f"🔄 Optimizar '{c['name']}': ROAS {c['roas']}x — mejorar landing page y testear variaciones del creativo para subir conversión.")
        for c in bad:
            if c.get("spend", 0) > 0:
                actions.append(f"🔴 Pausar o reducir '{c['name']}': ROAS {c['roas']}x — por debajo del umbral mínimo. Revisar audiencia, oferta y landing antes de reinvertir.")

    if account_type in ("conversation", "both"):
        high_cpc_conv = sorted([c for c in campaigns if c.get("cost_per_conversation", 0) > 0], key=lambda x: x.get("cost_per_conversation", 0), reverse=True)
        low_cpc_conv = sorted([c for c in campaigns if c.get("cost_per_conversation", 0) > 0], key=lambda x: x.get("cost_per_conversation", 0))
        if high_cpc_conv:
            actions.append(f"💸 Costo por conversación alto en '{high_cpc_conv[0]['name']}': revisar el mensaje de apertura del bot/chat y la segmentación de audiencia.")
        if low_cpc_conv:
            actions.append(f"🚀 '{low_cpc_conv[0]['name']}' tiene el mejor costo por conversación: escalar este conjunto y replicar su creatividad en otras campañas.")

    if not actions:
        actions.append("📊 Sin datos suficientes para recomendaciones de acciones esta semana.")
    if not creative_recs:
        creative_recs.append("🎨 Mantener al menos 3 variantes de creativo activas por conjunto. Rotar los que llevan más de 3 semanas.")

    return {"actions": actions, "creative_recs": creative_recs}


def build_report(days_back: int = 7, account_name: str = "", account_id: str = "", account_type: str = "ecommerce") -> dict:
    summary_raw = get_account_summary(days_back, account_id=account_id or None)
    campaigns_raw = get_campaign_metrics(days_back, account_id=account_id or None)
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
            "reach": int(c.get("reach", 0)),
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
            "hold_rate": 0.0,
        })

    analysis = _analyze_campaigns(campaign_rows, account_type)

    return {
        "title": f"{account_name} — {_period_label(days_back)}",
        "period_days": days_back,
        "period_label": _period_label(days_back),
        "date": str(date.today()),
        "account_name": account_name,
        "account_type": account_type,
        "summary": {
            "spend": metrics["roas"] and round(float(summary_raw.get("spend", 0)), 2) or round(float(summary_raw.get("spend", 0)), 2),
            "impressions": int(summary_raw.get("impressions", 0)),
            "clicks": int(summary_raw.get("clicks", 0)),
            "ctr": round(float(summary_raw.get("ctr", 0)), 2),
            "cpm": round(float(summary_raw.get("cpm", 0)), 2),
            "roas": metrics["roas"],
            "hook_rate": metrics["hook_rate"],
            "hold_rate": metrics["hold_rate"],
            "frequency": metrics["frequency"],
            "reach": metrics["reach"],
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
        "analysis": analysis,
    }


def run_all(days_back: int = 7, dry_run: bool = False):
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    for acc in accounts:
        print(f"\n→ Procesando {acc['name']}...")
        try:
            report = build_report(days_back=days_back, account_name=acc["name"], account_id=acc["account_id"], account_type=acc.get("type", "ecommerce"))
            if dry_run:
                print(f"  ROAS: {report['summary']['roas']} | Inversión: ${report['summary'].get('spend', 0):,.2f}")
            else:
                url = publish_report(report)
                print(f"  ✅ {url}")
        except Exception as e:
            print(f"  ❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--account-name", type=str, default="")
    parser.add_argument("--account-id", type=str, default="")
    parser.add_argument("--account-type", type=str, default="ecommerce")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.all:
        run_all(days_back=args.days, dry_run=args.dry_run)
    else:
        report = build_report(days_back=args.days, account_name=args.account_name, account_id=args.account_id or META_AD_ACCOUNT_ID, account_type=args.account_type)
        if args.dry_run:
            import json as j
            print(j.dumps(report, indent=2, ensure_ascii=False))
        else:
            url = publish_report(report)
            print(f"Reporte publicado: {url}")


if __name__ == "__main__":
    main()
