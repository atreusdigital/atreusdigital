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


def _date_range(days_back: int) -> dict:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days_back - 1)
    return {"since": str(start), "until": str(end)}


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
    fields = [
        AdsInsights.Field.spend,
        AdsInsights.Field.impressions,
        AdsInsights.Field.clicks,
        AdsInsights.Field.ctr,
        AdsInsights.Field.cpm,
        AdsInsights.Field.actions,
        AdsInsights.Field.purchase_roas,
    ]
    insights = account.get_insights(fields=fields, params=params)
    rows = list(insights)
    return dict(rows[0]) if rows else {}
