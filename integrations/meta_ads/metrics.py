from datetime import date, timedelta
from facebook_business.adobjects.adsinsights import AdsInsights
from integrations.meta_ads.client import get_ad_account


FIELDS = [
    AdsInsights.Field.campaign_name,
    AdsInsights.Field.spend,
    AdsInsights.Field.impressions,
    AdsInsights.Field.clicks,
    AdsInsights.Field.ctr,
    AdsInsights.Field.cpc,
    AdsInsights.Field.cpm,
    AdsInsights.Field.actions,
    AdsInsights.Field.cost_per_action_type,
    AdsInsights.Field.purchase_roas,
]

SUMMARY_FIELDS = [
    AdsInsights.Field.spend,
    AdsInsights.Field.impressions,
    AdsInsights.Field.clicks,
    AdsInsights.Field.ctr,
    AdsInsights.Field.cpm,
    AdsInsights.Field.actions,
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


def _extract_cost_per_action(cost_list: list, action_type: str) -> float:
    if not cost_list:
        return 0.0
    for a in cost_list:
        if a.get("action_type") == action_type:
            return round(float(a.get("value", 0)), 2)
    return 0.0


def extract_instagram_metrics(summary: dict) -> dict:
    actions = summary.get("actions", [])
    cost_per = summary.get("cost_per_action_type", [])
    spend = float(summary.get("spend", 0))
    impressions = int(summary.get("impressions", 0))

    profile_visits = int(_extract_action(actions, "instagram_profile_visit"))
    follows = int(_extract_action(actions, "follow"))
    conversations = int(_extract_action(actions, "onsite_conversion.messaging_conversation_started_7d"))

    cost_per_follow = round(spend / follows, 2) if follows > 0 else 0.0
    cost_per_conv = round(spend / conversations, 2) if conversations > 0 else 0.0
    follow_rate = round((follows / impressions) * 100, 3) if impressions > 0 else 0.0

    return {
        "instagram_profile_visits": profile_visits,
        "instagram_follows": follows,
        "cost_per_follow": cost_per_follow,
        "follow_rate_pct": follow_rate,
        "conversations": conversations,
        "cost_per_conversation": cost_per_conv,
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
