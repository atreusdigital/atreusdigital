from notion_client import Client
from shared.config import NOTION_TOKEN, NOTION_REPORTS_DATABASE_ID


def _notion_client() -> Client:
    return Client(auth=NOTION_TOKEN)


def _text(content: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": content}}]}}


def _heading(content: str, level: int = 2) -> dict:
    t = f"heading_{level}"
    return {"object": "block", "type": t, t: {"rich_text": [{"text": {"content": content}}]}}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _bullet(content: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": content}}]}}


def publish_report(report: dict) -> str:
    notion = _notion_client()
    summary = report["summary"]
    campaigns = report["campaigns"]
    analysis = report.get("analysis", {})

    # Resumen general
    resumen_text = (
        f"📅 Período: {report.get('period_label', 'últimos ' + str(report['period_days']) + ' días')}\n"
        f"💰 Inversión total: ${summary['spend']:,.2f}\n"
        f"👁️  Impresiones: {summary['impressions']:,}\n"
        f"🖱️  Clics: {summary['clicks']:,}\n"
        f"📊 CTR: {summary['ctr']}%\n"
        f"📢 CPM: ${summary['cpm']:,.2f}\n"
        f"🔁 ROAS general: {summary['roas']}"
    )

    # Detalle por campaña
    campaign_lines = []
    for c in campaigns:
        roas_flag = "🟢" if c["roas"] >= 4.0 else ("🟡" if c["roas"] >= 2.0 else "🔴")
        campaign_lines.append(
            f"{roas_flag} {c['name']}\n"
            f"   Inversión: ${c['spend']:,.2f} | ROAS: {c['roas']} | CTR: {c['ctr']}% | CPC: ${c['cpc']} | Compras: {c['purchases']}"
        )
    campaigns_text = "\n\n".join(campaign_lines) if campaign_lines else "Sin datos de campañas."

    blocks = [
        _heading("Resumen de cuenta"),
        _text(resumen_text),
        _divider(),
        _heading("Detalle por campaña"),
        _text(campaigns_text),
        _divider(),
    ]

    # Análisis y acciones recomendadas
    if analysis.get("actions"):
        blocks.append(_heading("Qué haría con estos números"))
        for action in analysis["actions"]:
            blocks.append(_bullet(action))
        blocks.append(_divider())

    # Recomendaciones de creativos
    if analysis.get("creative_recs"):
        blocks.append(_heading("Recomendaciones de creativos"))
        for rec in analysis["creative_recs"]:
            blocks.append(_bullet(rec))

    page = notion.pages.create(
        parent={"database_id": NOTION_REPORTS_DATABASE_ID},
        properties={
            "title": {"title": [{"text": {"content": report["title"]}}]},
        },
        children=blocks,
    )

    page_id = page["id"].replace("-", "")
    return f"https://notion.so/{page_id}"
