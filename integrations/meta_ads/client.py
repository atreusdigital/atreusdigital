import os
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from shared.config import META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN


def init_meta_client():
    FacebookAdsApi.init(META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN)


def get_ad_account(account_id: str = None) -> AdAccount:
    init_meta_client()
    aid = account_id or os.environ.get("META_AD_ACCOUNT_ID")
    return AdAccount(aid)
