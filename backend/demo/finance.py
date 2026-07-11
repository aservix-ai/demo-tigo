"""Finance engine: every metric the agent reports is computed here with pandas.

The LLM never does arithmetic — these functions are the single source of truth
for P&L, margins, budget consumption, run-rates, DSO, aging and collections.
All monetary outputs are USD unless a function converts to millions for display.
"""

from functools import lru_cache
from typing import cast

import pandas as pd

from . import config as cfg

AS_OF_PERIOD = pd.Period(cfg.AS_OF, freq="M")
AS_OF_END = AS_OF_PERIOD.end_time.normalize()
FY = str(cfg.BUDGET_YEAR)


@lru_cache(maxsize=1)
def load() -> dict:
    d = {name: pd.read_csv(cfg.DATA_DIR / f"{name}.csv") for name in
         ["revenue", "direct_costs", "opex", "capex", "budgets", "targets",
          "clients", "invoices"]}
    inv = d["invoices"]
    for col in ["issue_date", "due_date", "paid_date"]:
        inv[col] = pd.to_datetime(inv[col])
    return d


def _f(df: pd.DataFrame, country: str | None = None) -> pd.DataFrame:
    return df[df["country"] == country] if country else df


# ---------------------------------------------------------------------------
# P&L / margins
# ---------------------------------------------------------------------------

def pnl_summary(country: str | None = None) -> dict:
    """Month + FY-YTD P&L: revenue, direct costs, gross profit/margin, OPEX by
    category, EBITDA — with prior-year comparison."""
    d = load()
    rev, dc, op = _f(d["revenue"], country), _f(d["direct_costs"], country), _f(d["opex"], country)

    def slice_(df, months):
        return df[df["month"].isin(months)]

    ytd_months = [
        str(pd.Period(f"{FY}-{m:02d}", freq="M")) for m in range(1, AS_OF_PERIOD.month + 1)
    ]
    py_months = [m.replace(FY, str(cfg.BUDGET_YEAR - 1)) for m in ytd_months]

    def block(months):
        r, c, o = slice_(rev, months), slice_(dc, months), slice_(op, months)
        svc = r[r["revenue_type"] == "service"]["revenue_usd"].sum()
        eq = r[r["revenue_type"] == "equipment"]["revenue_usd"].sum()
        svc_dc = c[c["segment"] != "Equipment"]["amount_usd"].sum()
        total_dc = c["amount_usd"].sum()
        gp = svc + eq - total_dc
        opex_by_cat = o.groupby("category")["amount_usd"].sum().round(0).to_dict()
        opex_total = o["amount_usd"].sum()
        return {
            "service_revenue_usd": round(svc, 0),
            "equipment_revenue_usd": round(eq, 0),
            "total_revenue_usd": round(svc + eq, 0),
            "direct_costs_usd": round(total_dc, 0),
            "gross_profit_usd": round(gp, 0),
            "gross_margin_pct": round(gp / (svc + eq) * 100, 1),
            "service_gross_margin_pct": round((1 - svc_dc / svc) * 100, 1),
            "opex_by_category_usd": opex_by_cat,
            "opex_total_usd": round(opex_total, 0),
            "ebitda_usd": round(gp - opex_total, 0),
            "ebitda_margin_pct": round((gp - opex_total) / (svc + eq) * 100, 1),
        }

    ytd, py = block(ytd_months), block(py_months)
    return {
        "scope": country or "consolidado",
        "as_of": cfg.AS_OF,
        "month": block([cfg.AS_OF]),
        "ytd": ytd,
        "yoy_revenue_growth_pct": round(
            (ytd["total_revenue_usd"] / py["total_revenue_usd"] - 1) * 100, 1),
        "yoy_ebitda_margin_delta_pp": round(
            ytd["ebitda_margin_pct"] - py["ebitda_margin_pct"], 1),
    }


def margin_by_segment(country: str | None = None, months: int = 6) -> pd.DataFrame:
    """GM% per country x segment for the last `months` closed months, with
    target and variance in percentage points."""
    d = load()
    window = [str(AS_OF_PERIOD - i) for i in range(months - 1, -1, -1)]
    rev = _f(d["revenue"], country)
    dc = _f(d["direct_costs"], country)
    rev = rev[rev["month"].isin(window)]
    dc = dc[dc["month"].isin(window)]

    g_rev = rev.groupby(["country", "segment", "month"])["revenue_usd"].sum()
    g_dc = dc.groupby(["country", "segment", "month"])["amount_usd"].sum()
    gm = ((1 - g_dc / g_rev) * 100).rename("gm_pct").reset_index()

    targets = d["targets"][["country", "segment", "gm_target_pct"]]
    gm = gm.merge(targets, on=["country", "segment"], how="left")
    gm["variance_pp"] = (gm["gm_pct"] - gm["gm_target_pct"]).round(1)
    gm["gm_pct"] = gm["gm_pct"].round(1)
    return gm


# ---------------------------------------------------------------------------
# Budget consumption / run-rate
# ---------------------------------------------------------------------------

def budget_consumption(cost_type: str | None = None, country: str | None = None) -> pd.DataFrame:
    """Per country x category: annual budget, YTD actual, consumption %,
    run-rate FY forecast %. CAPEX rows also carry committed amounts."""
    d = load()
    budgets = d["budgets"]
    if cost_type:
        budgets = budgets[budgets["cost_type"] == cost_type.upper()]
    budgets = _f(budgets, country)

    op = d["opex"][d["opex"]["month"].str.startswith(FY)]
    cx = d["capex"][d["capex"]["month"].str.startswith(FY)]
    opex_ytd = op.groupby(["country", "category"])["amount_usd"].sum()
    capex_ytd = cx.groupby(["country", "category"])["spent_usd"].sum()
    capex_committed = cx.groupby(["country", "category"])["committed_usd"].sum()

    rows = []
    for b in budgets.itertuples():
        key = (b.country, b.category)
        budget_usd = cast(float, b.annual_budget_usd)
        ytd = float((opex_ytd if b.cost_type == "OPEX" else capex_ytd).get(key, 0.0))
        run_rate_fy = ytd / cfg.MONTHS_ELAPSED * 12
        row = {
            "country": b.country, "cost_type": b.cost_type, "category": b.category,
            "annual_budget_usd": budget_usd,
            "ytd_actual_usd": round(ytd, 0),
            "consumption_pct": round(ytd / budget_usd * 100, 1),
            "run_rate_fy_pct": round(run_rate_fy / budget_usd * 100, 1),
            "months_remaining": cfg.MONTHS_REMAINING,
        }
        if b.cost_type == "CAPEX":
            committed = float(capex_committed.get(key, 0.0))
            row["committed_usd"] = round(committed, 0)
            row["committed_pct"] = round(committed / budget_usd * 100, 1)
        rows.append(row)
    # Explicit columns so an unmatched filter degrades to an empty-but-typed
    # frame instead of a column-less one (which breaks downstream access).
    columns = ["country", "cost_type", "category", "annual_budget_usd",
               "ytd_actual_usd", "consumption_pct", "run_rate_fy_pct",
               "months_remaining", "committed_usd", "committed_pct"]
    df = pd.DataFrame(rows, columns=columns)
    if not df["committed_usd"].notna().any():
        df = df.drop(columns=["committed_usd", "committed_pct"])
    return df


def capex_summary(country: str | None = None) -> dict:
    d = load()
    bc = budget_consumption("CAPEX", country)
    rev = _f(d["revenue"], country)
    rev_ytd = rev[rev["month"].str.startswith(FY)]["revenue_usd"].sum()
    capex_pct = round(bc["ytd_actual_usd"].sum() / rev_ytd * 100, 1) if rev_ytd else 0.0
    return {
        "scope": country or "consolidado",
        "capex_pct_of_revenue_ytd": capex_pct,
        "guardrail_pct_of_revenue": "11-15",
        "note": "CAPEX se capitaliza: no afecta EBITDA, afecta flujo de caja.",
        "by_category": bc.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# OPEX trend (for cost-spike detection & drill-downs)
# ---------------------------------------------------------------------------

def opex_trend(country: str | None = None, months: int = 7) -> pd.DataFrame:
    d = load()
    window = [str(AS_OF_PERIOD - i) for i in range(months - 1, -1, -1)]
    op = _f(d["opex"], country)
    op = op[op["month"].isin(window)]
    return op.groupby(["country", "category", "month"])["amount_usd"].sum().reset_index()


def revenue_trend(segment: str | None = None, country: str | None = None,
                  months: int = 12) -> pd.DataFrame:
    d = load()
    window = [str(AS_OF_PERIOD - i) for i in range(months - 1, -1, -1)]
    rev = _f(d["revenue"], country)
    if segment:
        rev = rev[rev["segment"] == segment]
    out = rev[rev["month"].isin(window)]
    out = out.groupby(["country", "segment", "month"])["revenue_usd"].sum().reset_index()
    out["mom_pct"] = (
        out.sort_values("month")
        .groupby(["country", "segment"])["revenue_usd"]
        .pct_change() * 100
    ).round(1)
    return out


# ---------------------------------------------------------------------------
# Receivables: DSO, aging, collections
# ---------------------------------------------------------------------------

def _open_invoices(inv: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    issued = inv[inv["issue_date"] <= as_of]
    return issued[issued["paid_date"].isna() | (issued["paid_date"] > as_of)]


def dso_series(country: str | None = None, months: int = 6) -> pd.DataFrame:
    """B2B DSO per month-end: open AR / (trailing 90d billings / 90)."""
    d = load()
    inv = _f(d["invoices"], country)
    rows = []
    for i in range(months - 1, -1, -1):
        p = AS_OF_PERIOD - i
        end = p.end_time.normalize()
        ar = _open_invoices(inv, end)["amount_usd"].sum()
        billed_90 = inv[(inv["issue_date"] > end - pd.Timedelta(days=90))
                        & (inv["issue_date"] <= end)]["amount_usd"].sum()
        rows.append({"month": str(p), "ar_usd": round(ar, 0),
                     "dso_days": round(ar / (billed_90 / 90), 1) if billed_90 else 0.0})
    return pd.DataFrame(rows)


def collections_summary(country: str | None = None) -> dict:
    """Aging buckets at AS_OF, DSO trend and cash-collected vs billed ratio."""
    d = load()
    inv = _f(d["invoices"], country)
    open_inv = _open_invoices(inv, AS_OF_END).copy()
    overdue_days = (AS_OF_END - open_inv["due_date"]).dt.days
    buckets = {
        "current": open_inv[overdue_days <= 0]["amount_usd"].sum(),
        "1-30": open_inv[(overdue_days > 0) & (overdue_days <= 30)]["amount_usd"].sum(),
        "31-60": open_inv[(overdue_days > 30) & (overdue_days <= 60)]["amount_usd"].sum(),
        "61-90": open_inv[(overdue_days > 60) & (overdue_days <= 90)]["amount_usd"].sum(),
        "90+": open_inv[overdue_days > 90]["amount_usd"].sum(),
    }

    def month_ratio(p: pd.Period) -> float:
        start, end = p.start_time, p.end_time.normalize()
        billed = inv[(inv["issue_date"] >= start) & (inv["issue_date"] <= end)]["amount_usd"].sum()
        collected = inv[inv["paid_date"].notna()
                        & (inv["paid_date"] >= start)
                        & (inv["paid_date"] <= end)]["amount_usd"].sum()
        return round(collected / billed * 100, 1) if billed else 0.0

    dso = dso_series(country)
    return {
        "scope": country or "consolidado",
        "as_of": cfg.AS_OF,
        "aging_usd": {k: round(v, 0) for k, v in buckets.items()},
        "open_ar_total_usd": round(open_inv["amount_usd"].sum(), 0),
        "dso_by_month": dso.to_dict(orient="records"),
        "collections_ratio_pct_last_3m": {
            str(AS_OF_PERIOD - i): month_ratio(AS_OF_PERIOD - i) for i in range(2, -1, -1)
        },
    }


def top_overdue_clients(limit: int = 5) -> pd.DataFrame:
    """Clients ranked by overdue balance, with >60d exposure and B2B share."""
    d = load()
    inv, clients = d["invoices"], d["clients"]
    open_inv = _open_invoices(inv, AS_OF_END).copy()
    open_inv["overdue_days"] = (AS_OF_END - open_inv["due_date"]).dt.days
    overdue = open_inv[open_inv["overdue_days"] > 0]

    # Group by (country, client_id): ids are unique per country by generation,
    # but keying on both makes the analysis robust to id reuse across markets.
    agg = overdue.groupby(["country", "client_id"]).agg(
        overdue_usd=("amount_usd", "sum"),
        max_overdue_days=("overdue_days", "max"),
    )
    over60 = (overdue[overdue["overdue_days"] > 60]
              .groupby(["country", "client_id"])["amount_usd"].sum()
              .rename("overdue_over60_usd"))
    agg = agg.join(over60).fillna({"overdue_over60_usd": 0.0}).reset_index()
    agg = agg.merge(clients, on=["country", "client_id"])

    # Share of the country's B2B billings over the last 6 months.
    window_start = (AS_OF_PERIOD - 5).start_time
    recent = inv[inv["issue_date"] >= window_start]
    client_billed = recent.groupby(["country", "client_id"])["amount_usd"].sum()
    country_billed = recent.groupby("country")["amount_usd"].sum()
    keys = list(zip(agg["country"], agg["client_id"], strict=True))
    agg["monthly_billing_usd"] = [round(client_billed.get(k, 0.0) / 6, 0) for k in keys]
    agg["share_of_country_b2b_pct"] = [
        round(client_billed.get(k, 0.0) / country_billed[k[0]] * 100, 1) for k in keys]
    agg["overdue_vs_monthly_billing_pct"] = (
        agg["overdue_over60_usd"] / agg["monthly_billing_usd"] * 100).round(0)
    cols = ["client_id", "client_name", "country", "sector", "credit_terms_days",
            "overdue_usd", "overdue_over60_usd", "max_overdue_days",
            "monthly_billing_usd", "share_of_country_b2b_pct",
            "overdue_vs_monthly_billing_pct"]
    return agg.sort_values("overdue_usd", ascending=False).head(limit)[cols]
