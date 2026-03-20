"""
Resumen semanal de todos los clientes en #paid-media.
Incluye alerta de cuentas con gasto $0 (error de pago).
Uso: python -m reports.weekly_slack_summary
     python -m reports.weekly_slack_summary --days 7
"""
import argparse
import json
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from integrations.meta_ads.metrics import get_account_summary, get_campaign_metrics, extract_all_metrics
from shared.config import SLACK_BOT_TOKEN, ROAS_MIN, CPA_MAX
from reports.meta_performance import _period_label

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"

PAID_MEDIA_CHANNEL = "C06RU23C415"  # #paid-media

CLIENT_EMOJIS = {
    "Flower Time": "🌸", "Séfora Lencería": "👙", "IKA Indumentaria": "👗",
    "Meryjane Clothing": "👕", "Kitana Lencería": "🩱", "Salón del Peinador": "✂️",
    "Nonna Vita": "🍝", "Hey Donuts": "🍩", "Techos JAC": "🏠",
    "Dr. Gonzalo García": "👨‍⚕️", "DLD Translation HUB": "🌐",
    "Damian Pelu": "💈", "Casa Fuegos": "🔥",
}


def _fmt(n: float) -> str:
    return f"${round(n):,}".replace(",", ".")


def _roas_icon(roas: float) -> str:
    if roas >= 4:
        return "🟢"
    if roas >= 2:
        return "🟡"
    return "🔴"


def _cpa_icon(cost: float) -> str:
    if cost == 0:
        return "⚪"
    if cost <= CPA_MAX * 0.7:
        return "🟢"
    if cost <= CPA_MAX:
        return "🟡"
    return "🔴"


def fetch_client_metrics(account_id: str, account_type: str, days_back: int) -> dict:
    summary_raw = get_account_summary(days_back=days_back, account_id=account_id)
    metrics = extract_all_metrics(summary_raw)
    return {
        "spend": round(float(summary_raw.get("spend", 0)), 2),
        "impressions": int(summary_raw.get("impressions", 0)),
        "clicks": int(summary_raw.get("clicks", 0)),
        "ctr": round(float(summary_raw.get("ctr", 0)), 2),
        "cpm": round(float(summary_raw.get("cpm", 0)), 2),
        "frequency": metrics["frequency"],
        "roas": metrics["roas"],
        "purchases": metrics["purchases"],
        "purchase_value": metrics["purchase_value"],
        "ticket_promedio": metrics["ticket_promedio"],
        "conversations": metrics["conversations"],
        "cost_per_conversation": metrics["cost_per_conversation"],
    }


def build_summary_blocks(results: list[dict], days_back: int) -> list[dict]:
    period = _period_label(days_back)
    total_spend = sum(r["metrics"]["spend"] for r in results if r["metrics"])

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 Resumen semanal — {period}", "emoji": True}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"💰 *Inversión total:* {_fmt(total_spend)}"}
        },
        {"type": "divider"},
    ]

    # ── ALERTAS DE GASTO $0 ──
    zero_spend = [r for r in results if r["metrics"] and r["metrics"]["spend"] == 0]
    if zero_spend:
        names = "\n".join([f"• {r['name']}" for r in zero_spend])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🚨 *CUENTAS SIN GASTO — POSIBLE ERROR DE PAGO*\n{names}\n_Revisar método de pago en Meta Ads Manager._"
            }
        })
        blocks.append({"type": "divider"})

    # ── CLIENTES ECOMMERCE ──
    ecommerce = [r for r in results if r["type"] in ("ecommerce", "both") and r["metrics"]]
    if ecommerce:
        lines = []
        for r in ecommerce:
            m = r["metrics"]
            emoji = CLIENT_EMOJIS.get(r["name"], "📊")
            icon = _roas_icon(m["roas"])
            line = f"{icon} {emoji} *{r['name']}*  |  {_fmt(m['spend'])}  |  ROAS: {m['roas']}x"
            if m["purchases"] > 0:
                line += f"  |  🛒 {m['purchases']}  |  CTR: {m['ctr']}%  |  Frec: {m['frequency']}"
            else:
                line += f"  |  CTR: {m['ctr']}%  |  Frec: {m['frequency']}"
            lines.append(line)

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🛍️ eCommerce*\n" + "\n".join(lines)}
        })
        blocks.append({"type": "divider"})

    # ── CLIENTES CONVERSACIÓN ──
    conversation = [r for r in results if r["type"] in ("conversation", "both") and r["metrics"]]
    if conversation:
        lines = []
        for r in conversation:
            m = r["metrics"]
            emoji = CLIENT_EMOJIS.get(r["name"], "📊")
            icon = _cpa_icon(m["cost_per_conversation"])
            line = f"{icon} {emoji} *{r['name']}*  |  {_fmt(m['spend'])}  |  💬 {m['conversations']} convs"
            if m["conversations"] > 0:
                line += f"  |  CPA: {_fmt(m['cost_per_conversation'])}  |  CTR: {m['ctr']}%  |  Frec: {m['frequency']}"
            else:
                line += f"  |  CTR: {m['ctr']}%  |  Frec: {m['frequency']}"
            lines.append(line)

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*💬 Conversación*\n" + "\n".join(lines)}
        })
        blocks.append({"type": "divider"})

    # ── LEYENDA ──
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "🟢 Excelente  🟡 Aceptable  🔴 Revisar  ⚪ Sin datos"}]
    })

    return blocks


def run(days_back: int = 7, dry_run: bool = False):
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)

    results = []
    for acc in accounts:
        print(f"→ {acc['name']}...")
        try:
            metrics = fetch_client_metrics(acc["account_id"], acc.get("type", "ecommerce"), days_back)
            results.append({"name": acc["name"], "type": acc.get("type", "ecommerce"), "metrics": metrics})
        except Exception as e:
            print(f"  ❌ {e}")
            results.append({"name": acc["name"], "type": acc.get("type", "ecommerce"), "metrics": None})

    blocks = build_summary_blocks(results, days_back)

    if dry_run:
        for b in blocks:
            if b.get("type") == "section":
                print(b["text"]["text"])
            elif b.get("type") == "header":
                print(f"\n=== {b['text']['text']} ===")
        return

    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        client.chat_postMessage(
            channel=PAID_MEDIA_CHANNEL,
            blocks=blocks,
            text=f"Resumen semanal Meta Ads — {_period_label(days_back)}",
        )
        print(f"✅ Resumen enviado a #paid-media")
    except SlackApiError as e:
        print(f"❌ Error: {e.response['error']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(days_back=args.days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
