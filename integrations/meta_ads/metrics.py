from datetime import date, timedelta
from facebook_business.adobjects.adsinsights import AdsInsights
from integrations.meta_ads.client import get_ad_account


FIELDS = [
    AdsInsights.Field.campaign_name,
    AdsInsights.Field.spend,
    AdsInsights.Field.impressions,
    AdsInsights.Field.reach,
    AdsInsights.Field.clicks,
    AdsInsights.Field.ctr,
    AdsInsights.Field.cpc,
    AdsInsights.Field.cpm,
    AdsInsights.Field.actions,
    AdsInsights.Field.action_values,
    AdsInsights.Field.cost_per_action_type,
    AdsInsights.Field.purchase_roas,
]

SUMMARY_FIELDS = [
    AdsInsights.Field.spend,
    AdsInsights.Field.impressions,
    AdsInsights.Field.reach,
    AdsInsights.Field.clicks,
    AdsInsights.Field.ctr,
    AdsInsights.Field.cpm,
    AdsInsights.Field.frequency,
    AdsInsights.Field.actions,
    AdsInsights.Field.action_values,
    AdsInsights.Field.cost_per_action_type,
    AdsInsights.Field.purchase_roas,
]


def _date_range(days_back: int) -> dict:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days_back - 1)
    return {"since": str(start), "until": str(end)}


def _extract_action(actions: list, action_type: str) -> float:
    if not actions:
        return 0.0
    for a in actions:
        if a.get("action_type") == action_type:
            return float(a.get("value", 0))
    return 0.0


def _extract_action_value(action_values: list, action_type: str) -> float:
    if not action_values:
        return 0.0
    for a in action_values:
        if a.get("action_type") == action_type:
            return float(a.get("value", 0))
    return 0.0


def extract_all_metrics(summary: dict) -> dict:
    actions = summary.get("actions", [])
    action_values = summary.get("action_values", [])
    spend = float(summary.get("spend", 0))
    impressions = int(summary.get("impressions", 0))
    reach = int(summary.get("reach", 0))

    # Video
    video_3sec_list = summary.get("video_3_sec_watched_actions", [])
    video_3sec = float(video_3sec_list[0].get("value", 0)) if video_3sec_list else 0.0
    hook_rate = round((video_3sec / impressions) * 100, 2) if impressions > 0 else 0.0

    thruplay_list = summary.get("video_thruplay_watched_actions", [])
    thruplay = float(thruplay_list[0].get("value", 0)) if thruplay_list else 0.0
    hold_rate = round((thruplay / video_3sec) * 100, 2) if video_3sec > 0 else 0.0

    # eCommerce
    purchases = int(_extract_action(actions, "purchase"))
    purchase_value = _extract_action_value(action_values, "purchase")
    ticket_promedio = round(purchase_value / purchases, 2) if purchases > 0 else 0.0
    roas_list = summary.get("purchase_roas", [])
    roas = 0.0
    for r in roas_list:
        if r.get("action_type") == "omni_purchase":
            roas = round(float(r.get("value", 0)), 2)

    # Conversaciones
    conversations = int(_extract_action(actions, "onsite_conversion.messaging_conversation_started_7d"))
    cost_per_conv = round(spend / conversations, 2) if conversations > 0 else 0.0

    # Instagram (desde ads — solo trackea interacciones generadas por los propios anuncios)
    profile_visits = int(_extract_action(actions, "instagram_profile_visit"))
    follows = int(_extract_action(actions, "follow"))
    cost_per_follow = round(spend / follows, 2) if follows > 0 else 0.0
    follow_rate = round((follows / impressions) * 100, 3) if impressions > 0 else 0.0

    # Frecuencia
    frequency = round(float(summary.get("frequency", 0)), 2)

    return {
        # Performance
        "roas": roas,
        "hook_rate": hook_rate,
        "hold_rate": hold_rate,
        "frequency": frequency,
        "reach": reach,
        # eCommerce
        "purchases": purchases,
        "purchase_value": round(purchase_value, 2),
        "ticket_promedio": ticket_promedio,
        # Conversaciones
        "conversations": conversations,
        "cost_per_conversation": cost_per_conv,
        # Instagram (desde ads)
        "instagram_profile_visits": profile_visits,
        "instagram_follows": follows,
        "cost_per_follow": cost_per_follow,
        "follow_rate_pct": follow_rate,
    }


def get_campaign_metrics(days_back: int = 30, account_id: str = None) -> list[dict]:
    account = get_ad_account(account_id)
    params = {
        "time_range": _date_range(days_back),
        "level": "campaign",
        "breakdowns": [],
    }
    insights = account.get_insights(fields=FIELDS, params=params)
    return [dict(row) for row in insights]


def get_account_summary(days_back: int = 30, account_id: str = None) -> dict:
    account = get_ad_account(account_id)
    params = {
        "time_range": _date_range(days_back),
        "level": "account",
    }
    insights = account.get_insights(fields=SUMMARY_FIELDS, params=params)
    rows = list(insights)
    return dict(rows[0]) if rows else {}
