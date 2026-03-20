from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from shared.config import META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN, META_AD_ACCOUNT_ID


def init_meta_client():
    FacebookAdsApi.init(META_APP_ID, META_APP_SECRET, META_ACCESS_TOKEN)


def get_ad_account() -> AdAccount:
    init_meta_client()
    return AdAccount(META_AD_ACCOUNT_ID)
