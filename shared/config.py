import os
from dotenv import load_dotenv

load_dotenv()

META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
META_AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_REPORTS_DATABASE_ID = os.getenv("NOTION_REPORTS_DATABASE_ID")

ROAS_MIN = float(os.getenv("ROAS_MIN", 2.0))
CPA_MAX = float(os.getenv("CPA_MAX", 500))
