"""Deterministic data generator for the demo.

Generates 30 months (Jan 2024 - Jun 2026) of revenue, direct costs, OPEX,
CAPEX, budgets, targets, B2B clients and invoices for 5 Tigo markets, then
injects the anomalies that drive the 9 rehearsed alarms (see config.EXPECTED_ALARMS).

Everything uses numpy's seeded RNG: `python main.py data` produces byte-identical
CSVs on every run. The CSVs are committed; the live demo never regenerates them.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from . import config as cfg

MONTHS = pd.period_range(cfg.START_MONTH, cfg.AS_OF, freq="M")


def _month_index(period: pd.Period) -> int:
    return (period.year - MONTHS[0].year) * 12 + (period.month - MONTHS[0].month)


# ---------------------------------------------------------------------------
# B2B clients & invoices (B2B revenue is built bottom-up from invoices so the
# invoices <-> revenue tie-out holds to the dollar)
# ---------------------------------------------------------------------------

_SECTORS = ["banca", "retail", "manufactura", "logística", "energía", "agroindustria", "salud"]
_NAMES = [
    "Banco Continental del Istmo", "Distribuidora Andina de Alimentos",
    "Cementos del Pacífico", "Logística Interoceánica", "Energía Verde Latam",
    "Agroexportadora del Valle", "Clínicas Integradas", "Textiles Metropolitanos",
    "Cadena de Farmacias Salud+", "Aerolínea Regional Cóndor", "Minera Altiplano",
    "Supermercados La Cosecha", "Aseguradora del Sur", "Constructora Meridiano",
]


def _build_clients(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for country, n in cfg.CLIENTS_PER_COUNTRY.items():
        b2b_monthly = cfg.COUNTRIES[country] * cfg.SEGMENT_MIX["B2B"]
        if country == "Guatemala":
            # Seeded concentration: the government client takes 17.2% of B2B;
            # the rest decay linearly so no other client crosses the 15% rule.
            shares = [0.172]
            rest = np.array([float(n - 1 - i) for i in range(n - 1)])
            shares += list(rest / rest.sum() * (1 - 0.172))
        else:
            raw = np.array([1.0 / (i + 1.6) ** 0.9 for i in range(n)])
            shares = list(raw / raw.sum())  # top client lands near 11-12%
        for i, share in enumerate(shares):
            is_gov = country == "Guatemala" and i == 0
            client_id = f"{cfg.COUNTRY_CODE[country]}-B2B-{i + 1:03d}"
            assert not is_gov or client_id == cfg.SEEDED_CLIENT_ID
            name = (
                cfg.SEEDED_CLIENT_NAME
                if is_gov
                else f"{_NAMES[i % len(_NAMES)]} {country}"
            )
            rows.append({
                "client_id": client_id,
                "client_name": name,
                "country": country,
                "sector": "gobierno" if is_gov else _SECTORS[i % len(_SECTORS)],
                "credit_terms_days": 60 if is_gov else cfg.CREDIT_TERMS_DAYS[i % 3],
                "monthly_billing_usd": round(b2b_monthly * share, 2),
            })
    return pd.DataFrame(rows)


def _build_invoices(rng: np.random.Generator, clients: pd.DataFrame) -> pd.DataFrame:
    """Monthly invoice per client, plus the seeded unpaid government project
    invoices (A8) and Guatemala-wide payment-delay stress from Mar 2026 (A7)."""
    # Extra payment delay (days) for Guatemala invoices, by issue month.
    gt_stress = {"2026-03": 10, "2026-04": 16, "2026-05": 24, "2026-06": 28}
    rows = []
    for c in clients.itertuples():
        for m in MONTHS:
            t = _month_index(m)
            amount = c.monthly_billing_usd * (1 + cfg.MONTHLY_GROWTH) ** t
            amount *= rng.lognormal(0, 0.02)
            issue = pd.Timestamp(m.year, m.month, 5)
            due = issue + timedelta(days=int(c.credit_terms_days))
            delay = float(np.clip(rng.normal(6, 5), 0, 24))
            delay += gt_stress.get(str(m), 0) if c.country == "Guatemala" else 0
            paid = due + timedelta(days=round(delay))
            rows.append({
                "invoice_id": f"INV-{c.client_id}-{m}",
                "client_id": c.client_id,
                "country": c.country,
                "issue_date": issue.date(),
                "due_date": due.date(),
                "amount_usd": round(amount, 2),
                "paid_date": paid.date(),
            })

    # Seeded A8: three unpaid "connectivity project" invoices for the gov client.
    for m in ["2025-12", "2026-01", "2026-02"]:
        p = pd.Period(m, freq="M")
        issue = pd.Timestamp(p.year, p.month, 5)
        rows.append({
            "invoice_id": f"INV-{cfg.SEEDED_CLIENT_ID}-{m}-PROY",
            "client_id": cfg.SEEDED_CLIENT_ID,
            "country": "Guatemala",
            "issue_date": issue.date(),
            "due_date": (issue + timedelta(days=60)).date(),
            "amount_usd": 1_370_000.0,
            "paid_date": None,  # never paid -> >60d overdue bucket at AS_OF
        })

    inv = pd.DataFrame(rows)
    as_of_end = pd.Period(cfg.AS_OF, freq="M").end_time.normalize()
    paid_ts = pd.to_datetime(inv["paid_date"])
    inv["status"] = np.where(paid_ts.notna() & (paid_ts <= as_of_end), "paid", "open")
    return inv


# ---------------------------------------------------------------------------
# Revenue / direct costs / OPEX / CAPEX
# ---------------------------------------------------------------------------

def _build_revenue(rng: np.random.Generator, invoices: pd.DataFrame) -> pd.DataFrame:
    inv = invoices.copy()
    inv["month"] = pd.to_datetime(inv["issue_date"]).dt.to_period("M").astype(str)
    b2b = inv.groupby(["month", "country"])["amount_usd"].sum()

    rows = []
    for country, base in cfg.COUNTRIES.items():
        for m in MONTHS:
            t = _month_index(m)
            for seg, mix in cfg.SEGMENT_MIX.items():
                if seg == "B2B":
                    amount = float(b2b.loc[(str(m), country)])
                else:
                    amount = base * mix * (1 + cfg.MONTHLY_GROWTH) ** t
                    amount *= rng.lognormal(0, cfg.BASELINE_NOISE)
                rows.append({
                    "month": str(m),
                    "country": country,
                    "segment": seg,
                    "revenue_type": "equipment" if seg == "Equipment" else "service",
                    "revenue_usd": round(amount, 2),
                })
    df = pd.DataFrame(rows)

    # Seeded A5: Bolivia prepaid decline in the last two closed months.
    bo = (df["country"] == "Bolivia") & (df["segment"] == "Mobile_Prepaid")
    apr = df.loc[bo & (df["month"] == "2026-04"), "revenue_usd"].iloc[0]
    df.loc[bo & (df["month"] == "2026-05"), "revenue_usd"] = round(apr * 0.945, 2)
    df.loc[bo & (df["month"] == "2026-06"), "revenue_usd"] = round(apr * 0.945 * 0.948, 2)
    return df


def _build_direct_costs(rng: np.random.Generator, revenue: pd.DataFrame) -> pd.DataFrame:
    df = revenue.copy()
    df["rate"] = df["segment"].map(cfg.DIRECT_COST_RATE)
    noise = rng.lognormal(0, 0.006, size=len(df))
    df["amount_usd"] = df["revenue_usd"] * df["rate"] * noise

    # Seeded A4: Paraguay Home content-cost repricing -> GM ~3.3pp below target.
    py_home = (df["country"] == "Paraguay") & (df["segment"] == "Home")
    df.loc[py_home & df["month"].isin(["2026-05", "2026-06"]), "amount_usd"] *= 1.085

    df["category"] = df["segment"].map(cfg.DIRECT_COST_CATEGORY)
    df["amount_usd"] = df["amount_usd"].round(2)
    return df[["month", "country", "segment", "category", "amount_usd"]]


def _build_opex(rng: np.random.Generator, revenue: pd.DataFrame) -> pd.DataFrame:
    rev_by_cm = revenue.groupby(["month", "country"])["revenue_usd"].sum()
    rows = []
    for (month, country), rev in rev_by_cm.items():
        for cat, rate in cfg.OPEX_RATE.items():
            amount = rev * rate * rng.lognormal(0, 0.010)
            rows.append({"month": month, "country": country,
                         "category": cat, "amount_usd": amount})
    df = pd.DataFrame(rows)

    fy25 = df[df["month"].str.startswith("2025")]
    fy25_totals = fy25.groupby(["country", "category"])["amount_usd"].sum()

    # Seeded A1: Guatemala sales & marketing front-loaded to 88% of FY2026 budget.
    budget_gt_sm = fy25_totals.loc[("Guatemala", "sales_marketing")] * cfg.BUDGET_GROWTH
    weights = {"2026-01": 0.20, "2026-02": 0.19, "2026-03": 0.17,
               "2026-04": 0.13, "2026-05": 0.10, "2026-06": 0.09}  # sums to 0.88
    for month, w in weights.items():
        mask = ((df["month"] == month) & (df["country"] == "Guatemala")
                & (df["category"] == "sales_marketing"))
        df.loc[mask, "amount_usd"] = budget_gt_sm * w

    # Seeded A2: Colombia energy tariff escalation -> FY run-rate ~120% of budget.
    budget_co_en = fy25_totals.loc[("Colombia", "energy")] * cfg.BUDGET_GROWTH
    factors = {"2026-01": 1.00, "2026-02": 1.08, "2026-03": 1.16,
               "2026-04": 1.24, "2026-05": 1.31, "2026-06": 1.38}
    for month, f in factors.items():
        mask = ((df["month"] == month) & (df["country"] == "Colombia")
                & (df["category"] == "energy"))
        df.loc[mask, "amount_usd"] = (budget_co_en / 12) * f

    # Seeded A6: Panama energy spike (+19% MoM) in the last closed month.
    pa_en = (df["country"] == "Panama") & (df["category"] == "energy")
    may = df.loc[pa_en & (df["month"] == "2026-05"), "amount_usd"].iloc[0]
    df.loc[pa_en & (df["month"] == "2026-06"), "amount_usd"] = may * 1.19

    df["amount_usd"] = df["amount_usd"].round(2)
    return df


def _build_capex(rng: np.random.Generator, revenue: pd.DataFrame) -> pd.DataFrame:
    rev_by_cm = revenue.groupby(["month", "country"])["revenue_usd"].sum()
    rows = []
    for (month, country), rev in rev_by_cm.items():
        for cat, rate in cfg.CAPEX_RATE.items():
            spent = rev * rate * rng.lognormal(0, 0.015)
            rows.append({"month": month, "country": country, "category": cat,
                         "committed_usd": spent * 1.15, "spent_usd": spent})
    df = pd.DataFrame(rows)

    # Seeded A3: Colombia fiber buildout overrun — committed 96% of FY budget
    # by June, spend run-rate ~112%.
    fy25 = df[df["month"].str.startswith("2025")]
    budget_co_fiber = (
        fy25.groupby(["country", "category"])["spent_usd"].sum()
        .loc[("Colombia", "fiber_transport")] * cfg.BUDGET_GROWTH
    )
    spend_w = {"2026-01": 0.07, "2026-02": 0.08, "2026-03": 0.09,
               "2026-04": 0.10, "2026-05": 0.11, "2026-06": 0.11}  # sums to 0.56
    for month, w in spend_w.items():
        mask = ((df["month"] == month) & (df["country"] == "Colombia")
                & (df["category"] == "fiber_transport"))
        df.loc[mask, "spent_usd"] = budget_co_fiber * w
        df.loc[mask, "committed_usd"] = budget_co_fiber * 0.16  # 6 x 0.16 = 0.96

    df["committed_usd"] = df["committed_usd"].round(2)
    df["spent_usd"] = df["spent_usd"].round(2)
    return df


def _build_budgets(opex: pd.DataFrame, capex: pd.DataFrame) -> pd.DataFrame:
    """FY2026 budget = FY2025 actual x growth factor, per country x category.

    Note: 2025 actuals contain no anomalies, so budgets are a clean baseline.
    """
    rows = []
    fy25_opex = opex[opex["month"].str.startswith("2025")]
    for (country, cat), total in fy25_opex.groupby(["country", "category"])["amount_usd"].sum().items():
        rows.append({"year": cfg.BUDGET_YEAR, "country": country, "cost_type": "OPEX",
                     "category": cat, "annual_budget_usd": round(total * cfg.BUDGET_GROWTH, 2)})
    fy25_capex = capex[capex["month"].str.startswith("2025")]
    for (country, cat), total in fy25_capex.groupby(["country", "category"])["spent_usd"].sum().items():
        rows.append({"year": cfg.BUDGET_YEAR, "country": country, "cost_type": "CAPEX",
                     "category": cat, "annual_budget_usd": round(total * cfg.BUDGET_GROWTH, 2)})
    return pd.DataFrame(rows)


def _build_targets(revenue: pd.DataFrame, direct_costs: pd.DataFrame) -> pd.DataFrame:
    """GM targets per country x segment = FY2025 actual GM%, rounded."""
    rev25 = revenue[revenue["month"].str.startswith("2025")]
    dc25 = direct_costs[direct_costs["month"].str.startswith("2025")]
    rev_g = rev25.groupby(["country", "segment"])["revenue_usd"].sum()
    dc_g = dc25.groupby(["country", "segment"])["amount_usd"].sum()
    rows = []
    for key in rev_g.index:
        gm = (1 - dc_g[key] / rev_g[key]) * 100
        rows.append({"year": cfg.BUDGET_YEAR, "country": key[0], "segment": key[1],
                     "gm_target_pct": round(gm, 1)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------

def generate(verbose: bool = True) -> None:
    rng = np.random.default_rng(cfg.SEED)
    cfg.DATA_DIR.mkdir(exist_ok=True)

    clients = _build_clients(rng)
    invoices = _build_invoices(rng, clients)
    revenue = _build_revenue(rng, invoices)
    direct_costs = _build_direct_costs(rng, revenue)
    opex = _build_opex(rng, revenue)
    capex = _build_capex(rng, revenue)
    budgets = _build_budgets(opex, capex)
    targets = _build_targets(revenue, direct_costs)

    files = {
        "clients.csv": clients, "invoices.csv": invoices, "revenue.csv": revenue,
        "direct_costs.csv": direct_costs, "opex.csv": opex, "capex.csv": capex,
        "budgets.csv": budgets, "targets.csv": targets,
    }
    for name, df in files.items():
        df.to_csv(cfg.DATA_DIR / name, index=False)

    if verbose:
        _print_summary(revenue, direct_costs, opex, capex)


def _print_summary(revenue, direct_costs, opex, capex) -> None:
    """Consistency summary so seeded ratios can be eyeballed after generation."""
    ytd = lambda df: df[df["month"].str.startswith("2026")]
    rev = ytd(revenue)
    svc = rev[rev["revenue_type"] == "service"]["revenue_usd"].sum()
    eq = rev[rev["revenue_type"] == "equipment"]["revenue_usd"].sum()
    dc = ytd(direct_costs)
    svc_dc = dc[dc["segment"] != "Equipment"]["amount_usd"].sum()
    total_rev = svc + eq
    gp = total_rev - dc["amount_usd"].sum()
    op = ytd(opex)["amount_usd"].sum()
    cx = ytd(capex)["spent_usd"].sum()
    print(f"FY2026 YTD revenue        : ${total_rev / 1e6:,.1f}M")
    print(f"Service gross margin      : {(1 - svc_dc / svc) * 100:.1f}%  (target 72-78)")
    print(f"EBITDA margin             : {(gp - op) / total_rev * 100:.1f}%  (target 40-46)")
    print(f"CAPEX % of revenue        : {cx / total_rev * 100:.1f}%  (target 11-15)")


if __name__ == "__main__":
    generate()
