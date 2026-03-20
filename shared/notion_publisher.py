from notion_client import Client
from shared.config import NOTION_TOKEN, NOTION_REPORTS_DATABASE_ID


def _notion_client() -> Client:
    return Client(auth=NOTION_TOKEN)


def publish_report(report: dict) -> str:
    """Sube el reporte a Notion y retorna la URL de la página creada."""
    notion = _notion_client()
    summary = report["summary"]
    campaigns = report["campaigns"]

    # Construir tabla de campañas como texto
    campaign_lines = []
    for c in campaigns:
        campaign_lines.append(
            f"• {c['name']} — Inversión: ${c['spend']} | ROAS: {c['roas']} | CTR: {c['ctr']}% | Compras: {c['purchases']}"
        )
    campaigns_text = "\n".join(campaign_lines) if campaign_lines else "Sin datos de campañas."

    page = notion.pages.create(
        parent={"database_id": NOTION_REPORTS_DATABASE_ID},
        properties={
            "Name": {"title": [{"text": {"content": report["title"]}}]},
            "Fecha": {"date": {"start": report["date"]}},
            "Cliente": {"rich_text": [{"text": {"content": report.get("account_name", "")}}]},
            "ROAS": {"number": summary["roas"]},
            "Inversión": {"number": summary["spend"]},
        },
        children=[
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Resumen de cuenta"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": (
                        f"Inversión total: ${summary['spend']}\n"
                        f"Impresiones: {summary['impressions']:,}\n"
                        f"Clics: {summary['clicks']:,}\n"
                        f"CTR: {summary['ctr']}%\n"
                        f"CPM: ${summary['cpm']}\n"
                        f"ROAS: {summary['roas']}"
                    )}}]
                },
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Detalle por campaña"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": campaigns_text}}]},
            },
        ],
    )

    page_id = page["id"].replace("-", "")
    return f"https://notion.so/{page_id}"
