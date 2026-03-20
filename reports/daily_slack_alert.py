"""
Envía alertas diarias de Meta Ads a cada canal de Slack del cliente.
Uso: python -m reports.daily_slack_alert
     python -m reports.daily_slack_alert --account-name "Nonna Vita"
"""
import argparse
import json
from pathlib import Path

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from integrations.meta_ads.metrics import get_account_summary, get_campaign_metrics, extract_all_metrics
from shared.config import SLACK_BOT_TOKEN, ROAS_MIN, CPA_MAX

ACCOUNTS_FILE = Path(__file__).parent.parent / "accounts.json"

SLACK_CHANNELS = {
    "Flower Time":        "C090N6MHZ8B",
    "Séfora Lencería":    "C09PQ6FQDS6",
    "IKA Indumentaria":   "C070NKGD919",
    "Meryjane Clothing":  "C06RYVCDDK3",
    "Kitana Lencería":    "C06RNQK36G4",
    "Salón del Peinador": "C08LMQRALMT",
    "Nonna Vita":         "C0AJBFPC7JN",
    "Hey Donuts":         "C08BJM55G4T",
    "Techos JAC":         "C06RZ096MPB",
    "Dr. Gonzalo García": "C0711NWE9SR",
    "DLD Translation HUB":"C09440C1URE",
    "Damian Pelu":        "C07MB10HTQT",
}

CLIENT_EMOJIS = {
    "Flower Time": "🌸", "Séfora Lencería": "👙", "IKA Indumentaria": "👗",
    "Meryjane Clothing": "👕", "Kitana Lencería": "🩱", "Salón del Peinador": "✂️",
    "Nonna Vita": "🍝", "Hey Donuts": "🍩", "Techos JAC": "🏠",
    "Dr. Gonzalo García": "👨‍⚕️", "DLD Translation HUB": "🌐",
    "Damian Pelu": "💈", "Casa Fuegos": "🔥",
}


def _fmt(n: float) -> str:
    return f"${round(n):,}".replace(",", ".")


def build_daily_message(account_name: str, account_id: str, account_type: str) -> list[dict]:
    emoji = CLIENT_EMOJIS.get(account_name, "📊")

    summary_raw = get_account_summary(days_back=1, account_id=account_id)
    campaigns_raw = get_campaign_metrics(days_back=1, account_id=account_id)
    metrics = extract_all_metrics(summary_raw)

    spend = round(float(summary_raw.get("spend", 0)), 2)
    ctr = round(float(summary_raw.get("ctr", 0)), 2)
    frequency = metrics["frequency"]
    roas = metrics["roas"]
    purchases = metrics["purchases"]
    conversations = metrics["conversations"]
    cost_per_conv = metrics["cost_per_conversation"]

    # ── MÉTRICAS CLAVE según tipo ──
    lines = [f"💰 *Inversión:* {_fmt(spend)}"]

    if account_type == "ecommerce":
        if purchases > 0:
            lines.append(f"🔁 *ROAS:* {roas}x  |  🛒 *Compras:* {purchases}  |  🎫 *Ticket:* {_fmt(metrics['ticket_promedio'])}")
        else:
            lines.append("🛒 *Compras:* 0")

    elif account_type == "conversation":
        if conversations > 0:
            lines.append(f"💬 *Conversaciones:* {conversations}  |  💸 *Costo/conv:* {_fmt(cost_per_conv)}")
        else:
            lines.append("💬 *Conversaciones:* 0")

    elif account_type == "both":
        if purchases > 0:
            lines.append(f"🔁 *ROAS:* {roas}x  |  🛒 *Compras:* {purchases}  |  🎫 *Ticket:* {_fmt(metrics['ticket_promedio'])}")
        if conversations > 0:
            lines.append(f"💬 *Conversaciones:* {conversations}  |  💸 *Costo/conv:* {_fmt(cost_per_conv)}")

    lines.append(f"📊 *CTR:* {ctr}%  |  🔁 *Frecuencia:* {frequency}")

    # ── ALERTAS ──
    alerts = []

    if spend == 0:
        alerts.append("🚨 *GASTO $0* — verificar campañas activas y método de pago.")

    if account_type in ("ecommerce", "both") and purchases > 0 and roas < ROAS_MIN:
        alerts.append(f"🔴 *ROAS bajo:* {roas}x (mínimo {ROAS_MIN}x)")

    if account_type in ("conversation", "both") and conversations > 0 and cost_per_conv > CPA_MAX:
        alerts.append(f"🔴 *Costo/conv alto:* {_fmt(cost_per_conv)} (máximo {_fmt(CPA_MAX)})")

    if ctr < 0.8 and spend > 0:
        alerts.append(f"📉 *CTR bajo:* {ctr}% — posible fatiga creativa o audiencia saturada.")

    high_freq = [c for c in campaigns_raw if round(float(c.get("frequency", 0)), 2) > 3.0]
    for c in high_freq:
        alerts.append(f"⚠️ *Frecuencia alta* en _{c.get('campaign_name', '')}_ ({round(float(c.get('frequency', 0)), 2)}x) — rotar creativos.")

    # ── BLOQUES ──
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} {account_name} — Reporte del día", "emoji": True}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)}
        },
    ]

    if alerts:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🔔 Alertas*\n" + "\n".join(alerts)}
        })

    return blocks


def send_alert(account_name: str, account_id: str, account_type: str, dry_run: bool = False):
    channel_id = SLACK_CHANNELS.get(account_name)
    if not channel_id:
        print(f"  ⚠️  Sin canal de Slack para {account_name}")
        return

    blocks = build_daily_message(account_name, account_id, account_type)

    if dry_run:
        print(f"\n--- {account_name} ---")
        for b in blocks:
            if b.get("type") == "section":
                print(b["text"]["text"])
        return

    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=f"Reporte diario — {account_name}",
        )
        print(f"  ✅ {account_name}")
    except SlackApiError as e:
        print(f"  ❌ {account_name}: {e.response['error']}")


def run_all(dry_run: bool = False):
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    for acc in accounts:
        print(f"→ {acc['name']}...")
        try:
            send_alert(acc["name"], acc["account_id"], acc.get("type", "ecommerce"), dry_run=dry_run)
        except Exception as e:
            print(f"  ❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", type=str, default="")
    parser.add_argument("--account-id", type=str, default="")
    parser.add_argument("--account-type", type=str, default="ecommerce")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.all:
        run_all(dry_run=args.dry_run)
    else:
        if not args.account_name or not args.account_id:
            parser.error("Requerido: --account-name y --account-id, o --all")
        send_alert(args.account_name, args.account_id, args.account_type, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
