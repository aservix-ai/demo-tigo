"""Central configuration: business scale, alarm thresholds and the expected
alarm manifest that the demo is rehearsed against.

Every magnitude is anchored to Millicom (Tigo) FY2024 public figures so the
numbers survive scrutiny from a telecom finance audience.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"

# --- Simulation ------------------------------------------------------------
SEED = 42
START_MONTH = "2024-01"
AS_OF = "2026-06"  # last closed month; FY2026 has 6 of 12 months booked
BUDGET_YEAR = 2026
MONTHS_ELAPSED = 6  # months of FY2026 actuals
MONTHS_REMAINING = 6

# Monthly service+equipment revenue per market, USD (Millicom-scale anchors).
COUNTRIES = {
    "Guatemala": 112_000_000,
    "Colombia": 106_000_000,
    "Panama": 56_000_000,
    "Bolivia": 43_000_000,
    "Paraguay": 40_000_000,
}

# Unique country codes for client/invoice ids (Panama and Paraguay would both
# slug to "PA" if derived from the name).
COUNTRY_CODE = {
    "Guatemala": "GT",
    "Colombia": "CO",
    "Panama": "PA",
    "Bolivia": "BO",
    "Paraguay": "PY",
}

# Revenue mix per segment (shares of total revenue; sums to 1.0).
SEGMENT_MIX = {
    "Mobile_Prepaid": 0.32,
    "Mobile_Postpaid": 0.18,
    "Home": 0.27,
    "B2B": 0.14,
    "Tigo_Money": 0.04,
    "Equipment": 0.05,
}
SERVICE_SEGMENTS = ["Mobile_Prepaid", "Mobile_Postpaid", "Home", "B2B", "Tigo_Money"]

# Direct cost (cost of sales) as a share of each segment's revenue.
# Drives gross margin: service GM ~74%, equipment ~3% (dilutive, shown apart).
DIRECT_COST_RATE = {
    "Mobile_Prepaid": 0.20,  # interconnection + dealer commissions
    "Mobile_Postpaid": 0.22,  # interconnection + roaming
    "Home": 0.38,  # content / programming
    "B2B": 0.30,  # interconnection + capacity
    "Tigo_Money": 0.22,  # transaction / settlement costs
    "Equipment": 0.97,  # device COGS
}
# Direct-cost category label per segment (for direct_costs.csv).
DIRECT_COST_CATEGORY = {
    "Mobile_Prepaid": "interconnection_commissions",
    "Mobile_Postpaid": "interconnection_roaming",
    "Home": "content_programming",
    "B2B": "interconnection_capacity",
    "Tigo_Money": "mfs_transaction",
    "Equipment": "device_cogs",
}

# OPEX categories as share of total revenue (sums to 0.272 -> EBITDA ~42%
# after the seeded 2026 overspends drag it ~1.5pp).
# Energy is ~20% of OPEX: the classic telecom volatility driver.
OPEX_RATE = {
    "network_om": 0.048,
    "energy": 0.055,
    "site_lease": 0.034,
    "personnel": 0.057,
    "sales_marketing": 0.042,
    "it_software": 0.018,
    "ga": 0.014,
    "bad_debt": 0.004,
}

# CAPEX categories as share of total revenue (sums to 0.125 -> ~12.5%).
CAPEX_RATE = {
    "ran_access": 0.045,
    "fiber_transport": 0.030,
    "core": 0.015,
    "it_digital": 0.015,
    "cpe": 0.012,
    "spectrum_licenses": 0.008,
}

MONTHLY_GROWTH = 0.0025  # ~3% annualized organic growth
BASELINE_NOISE = (
    0.012  # sigma of multiplicative noise; low so alarms never fire by accident
)
BUDGET_GROWTH = 1.04  # FY2026 budget = FY2025 actual x 1.04 per category

# --- B2B clients / receivables ----------------------------------------------
CLIENTS_PER_COUNTRY = {
    "Guatemala": 14,
    "Colombia": 14,
    "Panama": 11,
    "Bolivia": 11,
    "Paraguay": 10,
}
CREDIT_TERMS_DAYS = [30, 45, 60]

# --- LLM --------------------------------------------------------------------
MODEL_ID = "nvidia/nemotron-3-ultra-550b-a55b"
MAX_TOKENS = 16384
REASONING_BUDGET = 16384

# --- Alarm thresholds ---------------------------------------------------------
TH_BUDGET_CONSUMPTION_PCT = 85.0  # A1: YTD consumption > 85% with >= 2 months left
TH_RUNRATE_PCT = 105.0  # A2 (OPEX) / A3 (CAPEX): run-rate forecast > 105% of budget
TH_CAPEX_COMMITTED_PCT = 95.0  # A3: committed > 95% of annual budget
TH_MARGIN_GAP_PP = 2.0  # A4: GM% > 2pp below target, 2 consecutive months
TH_REVENUE_DECLINE_PCT = 5.0  # A5: MoM decline >= 5%, 2 consecutive months
TH_COST_SPIKE_MOM_PCT = 15.0  # A6: OPEX category MoM increase >= 15%
TH_DSO_RISE_RATIO = 1.10  # A7: DSO > 1.10 x avg of prior 3 months
TH_COLLECTIONS_MIN_PCT = 90.0  # A7: monthly cash collected < 90% of billings
TH_OVERDUE_VS_BILLING_PCT = (
    50.0  # A8: >60d overdue balance > 50% of avg monthly billing
)
TH_CONCENTRATION_PCT = 15.0  # A9: top client > 15% of country B2B revenue AND overdue

# The seeded government client behind alarms A8/A9 (fictional entity).
SEEDED_CLIENT_ID = "GT-B2B-001"
SEEDED_CLIENT_NAME = "Ministerio de Desarrollo Digital (Gobierno)"

# --- Expected alarm manifest --------------------------------------------------
# preflight asserts that alarms.scan() produces EXACTLY these ids, no more, no less.
EXPECTED_ALARMS = [
    "A1-Guatemala-sales_marketing",
    "A2-Colombia-energy",
    "A3-Colombia-fiber_transport",
    "A4-Paraguay-Home",
    "A5-Bolivia-Mobile_Prepaid",
    "A6-Panama-energy",
    "A7-Guatemala-B2B",
    f"A8-Guatemala-{SEEDED_CLIENT_ID}",
    f"A9-Guatemala-{SEEDED_CLIENT_ID}",
]

SEVERITY = {
    "A1": "high",
    "A2": "high",
    "A3": "high",
    "A4": "high",
    "A5": "medium",
    "A6": "medium",
    "A7": "high",
    "A8": "high",
    "A9": "medium",
}
