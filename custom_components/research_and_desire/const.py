"""Constants for the Research and Desire integration."""

DOMAIN = "research_and_desire"
API_BASE_URL = "https://dashboard.researchanddesire.com/api/v1"
CONF_API_KEY = "api_key"
DEFAULT_SCAN_INTERVAL = 60
PLATFORMS = ["sensor", "event"]

PRODUCT_DTT = "dtt"
PRODUCT_OSSM = "ossm"
PRODUCT_LKBX = "lkbx"
PRODUCTS = [PRODUCT_DTT, PRODUCT_OSSM, PRODUCT_LKBX]
