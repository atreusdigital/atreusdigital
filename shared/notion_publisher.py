from notion_client import Client
from shared.config import NOTION_TOKEN, NOTION_REPORTS_DATABASE_ID

NICOLAS_ID = "46859857-ad41-4cfa-a6f1-4104103d4cc7"

CLIENT_EMOJIS = {
    "Flower Time": "🌸",
    "Séfora Lencería": "👙",
    "IKA Indumentaria": "👗",
    "Meryjane Clothing": "👕",
    "Kitana Lencería": "🩱",
    "Salón del Peinador": "✂️",
    "Nonna Vita": "🍝",
    "Hey Donuts": "🍩",
    "Techos JAC": "🏠",
    "Dr. Gonzalo García": "👨‍⚕️",
    "DLD Translation HUB": "🌐",
    "Damian Pelu": "💈",
    "Casa Fuegos": "🔥",
}


def _client() -> Client:
    return Client(auth=NOTION_TOKEN)


def _h2(text: str) -> dict:
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": text}}]}}


def _h3(text: str) -> dict:
    return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": text}}]}}


def _p(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text}}]}}


def _bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]}}


def _callout(text: str, emoji: str = "📌") -> dict:
    return {"object": "block", "type": "callout", "callout": {"rich_text": [{"text": {"content": text}}], "icon": {"type": "emoji", "emoji": emoji}}}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _fmt(n: float) -> str:
    return f"${round(n):,}".replace(",", ".")


def _fmt_dec(n: float) -> str:
    return f"${n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def publish_report(report: dict) -> str:
    notion = _client()
    name = report.get("account_name", "")
    emoji = CLIENT_EMOJIS.get(name, "📊")
    period = report.get("period_label", "")
    account_type = report.get("account_type", "ecommerce")

    title = f"{emoji} {name} — {period}"

    s = report.get("summary", {})
    ec = report.get("ecommerce", {})
    cv = report.get("conversation", {})
    ig = report.get("instagram", {})
    campaigns = report.get("campaigns", [])
    analysis = report.get("analysis", {})

    # ── BLOQUE DE ENCABEZADO ──
    assigned_text = f"Nicolás Danduono" + (" · Rocío Emme" if False else "")
    header_info = (
        f"👤 A cargo de: Nicolás Danduono\n"
        f"🏢 Cliente: {name}\n"
        f"✅ Estado: Completado\n"
        f"📅 Período: {period}\n"
        f"📋 Tipo: Informe Semanal"
    )

    # ── MÉTRICAS GENERALES ──
    gen_lines = (
        f"💰 Inversión: {_fmt(s.get('spend', 0))}\n"
        f"👁️ Impresiones: {round(s.get('impressions', 0)):,}\n"
        f"🖱️ Clics: {round(s.get('clicks', 0)):,}\n"
        f"📊 CTR: {s.get('ctr', 0)}%\n"
        f"📢 CPM: {_fmt(s.get('cpm', 0))}\n"
        f"🔁 Frecuencia: {s.get('frequency', 0)}"
    )

    blocks = [
        _callout(header_info, emoji),
        _divider(),
        _h2("📈 Métricas generales"),
        _p(gen_lines),
    ]

    # ── eCOMMERCE ──
    if account_type in ("ecommerce", "both") and ec.get("purchases", 0) > 0:
        roas = s.get("roas", 0)
        ec_lines = (
            f"🔁 ROAS: {roas}x\n"
            f"🛒 Compras: {ec.get('purchases', 0)}\n"
            f"🎫 Ticket promedio: {_fmt(ec.get('ticket_promedio', 0))}\n"
            f"💵 Revenue total: {_fmt(ec.get('purchase_value', 0))}"
        )
        blocks += [_divider(), _h2("🛍️ eCommerce"), _p(ec_lines)]

    # ── CONVERSACIONES ──
    if account_type in ("conversation", "both") and cv.get("conversations", 0) > 0:
        cv_lines = (
            f"💬 Conversaciones iniciadas: {cv.get('conversations', 0)}\n"
            f"💸 Costo por conversación: {_fmt(cv.get('cost_per_conversation', 0))}"
        )
        blocks += [_divider(), _h2("💬 Conversaciones"), _p(cv_lines)]

    # ── INSTAGRAM (solo si hay datos) ──
    ig_visits = ig.get("profile_visits", 0)
    ig_follows = ig.get("follows", 0)
    if ig_visits > 0 or ig_follows > 0:
        ig_lines = ""
        if ig_visits > 0:
            ig_lines += f"👁️ Visitas al perfil: {ig_visits}\n"
        if ig_follows > 0:
            ig_lines += f"➕ Seguimientos: {ig_follows}\n"
            ig_lines += f"💰 Costo/seguidor: {_fmt(ig.get('cost_per_follow', 0))}\n"
            ig_lines += f"📊 % seguidor: {ig.get('follow_rate_pct', 0)}%"
        blocks += [_divider(), _h2("📱 Instagram (desde anuncios)"), _p(ig_lines.strip())]

    # ── CAMPAÑAS ──
    blocks += [_divider(), _h2("📊 Detalle por campañas")]
    for c in campaigns:
        roas_icon = "🟢" if c.get("roas", 0) >= 4 else ("🟡" if c.get("roas", 0) >= 2 else "🔴")
        camp_line = f"{roas_icon} {c['name']}"
        detail = f"   Inversión: {_fmt(c['spend'])} | CTR: {c['ctr']}% | CPC: {_fmt(c['cpc'])}"
        if c.get("purchases", 0) > 0:
            detail += f" | Compras: {c['purchases']} | ROAS: {c.get('roas', 0)}x"
            if c.get("ticket_promedio", 0) > 0:
                detail += f" | Ticket: {_fmt(c['ticket_promedio'])}"
        if c.get("conversations", 0) > 0:
            detail += f" | Convs: {c['conversations']} | Costo/conv: {_fmt(c.get('cost_per_conversation', 0))}"
        blocks += [_bullet(camp_line), _p(detail)]

    # ── ANÁLISIS ──
    if analysis.get("actions"):
        blocks += [_divider(), _h2("📌 Qué haría con estos números")]
        for a in analysis["actions"]:
            blocks.append(_bullet(a))

    if analysis.get("creative_recs"):
        blocks += [_divider(), _h2("🎬 Recomendaciones de creativos")]
        for r in analysis["creative_recs"]:
            blocks.append(_bullet(r))

    # ── PROPIEDADES ──
    properties = {
        "title": {"title": [{"text": {"content": title}}]},
    }

    # Intentar asignar propiedades opcionales si existen en la DB
    try:
        page = notion.pages.create(
            parent={"database_id": NOTION_REPORTS_DATABASE_ID},
            properties=properties,
            children=blocks,
        )
    except Exception:
        # Fallback sin propiedades extra
        page = notion.pages.create(
            parent={"database_id": NOTION_REPORTS_DATABASE_ID},
            properties={"title": {"title": [{"text": {"content": title}}]}},
            children=blocks,
        )

    # Agregar asignados como mención si es posible
    try:
        page_id = page["id"]
        notion.pages.update(
            page_id=page_id,
            properties={
                "Asignado a": {"people": [{"id": NICOLAS_ID}]},
                "Cliente": {"rich_text": [{"text": {"content": name}}]},
                "Estado": {"select": {"name": "Completado"}},
                "Período": {"rich_text": [{"text": {"content": period}}]},
                "Tipo": {"select": {"name": "Informe Semanal"}},
            }
        )
    except Exception:
        pass  # Si las propiedades no existen en la DB, se ignora

    page_id = page["id"].replace("-", "")
    return f"https://notion.so/{page_id}"
