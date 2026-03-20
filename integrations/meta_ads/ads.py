from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights
from integrations.meta_ads.client import get_ad_account
from integrations.meta_ads.metrics import _date_range


AD_FIELDS = [
    AdsInsights.Field.ad_id,
    AdsInsights.Field.ad_name,
    AdsInsights.Field.adset_name,
    AdsInsights.Field.campaign_name,
    AdsInsights.Field.spend,
    AdsInsights.Field.impressions,
    AdsInsights.Field.clicks,
    AdsInsights.Field.ctr,
    AdsInsights.Field.cpc,
    AdsInsights.Field.actions,
    AdsInsights.Field.cost_per_action_type,
    AdsInsights.Field.purchase_roas,
]


def _extract_purchases(actions):
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == "purchase":
            return int(float(a.get("value", 0)))
    return 0


def _extract_roas(purchase_roas):
    if not purchase_roas:
        return 0.0
    for r in purchase_roas:
        if r.get("action_type") == "omni_purchase":
            return round(float(r.get("value", 0)), 2)
    return 0.0


def get_top_ads(days_back: int = 7, top_n: int = 5) -> list[dict]:
    account = get_ad_account()
    params = {
        "time_range": _date_range(days_back),
        "level": "ad",
    }
    insights = account.get_insights(fields=AD_FIELDS, params=params)
    ads = []
    for row in insights:
        r = dict(row)
        spend = round(float(r.get("spend", 0)), 2)
        if spend == 0:
            continue
        ads.append({
            "ad_id": r.get("ad_id", ""),
            "ad_name": r.get("ad_name", ""),
            "adset_name": r.get("adset_name", ""),
            "campaign_name": r.get("campaign_name", ""),
            "spend": spend,
            "impressions": int(r.get("impressions", 0)),
            "clicks": int(r.get("clicks", 0)),
            "ctr": round(float(r.get("ctr", 0)), 2),
            "cpc": round(float(r.get("cpc", 0)), 2),
            "purchases": _extract_purchases(r.get("actions", [])),
            "roas": _extract_roas(r.get("purchase_roas", [])),
        })

    # Top 5 por ROAS (con mínimo de gasto para evitar outliers)
    min_spend = max(s["spend"] for s in ads) * 0.05 if ads else 0
    filtered = [a for a in ads if a["spend"] >= min_spend]
    return sorted(filtered, key=lambda x: x["roas"], reverse=True)[:top_n]
