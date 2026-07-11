"""Deterministic alarm engine: 9 FP&A rules evaluated at the closing month.

Each rule is a pure function over the finance engine. The LLM only narrates
and prioritizes what scan() returns — it can never invent or suppress an alarm.
Evidence and recommended actions are written in Spanish because the report is
delivered in Spanish.
"""

from typing import cast

from pydantic import BaseModel

from . import config as cfg
from . import finance as fin


class Alarm(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    severity: str
    country: str
    entity: str
    metrics: dict
    threshold: str
    evidence: str
    recommended_action: str


def _mk(
    rule_id: str,
    rule_name: str,
    # country/entity arrive as pandas scalars (itertuples/groupby keys), typed
    # Scalar/Hashable by the stubs — accept anything and coerce to str here.
    country: object,
    entity: object,
    metrics: dict,
    threshold: str,
    evidence: str,
    action: str,
) -> Alarm:
    return Alarm(
        id=f"{rule_id}-{country}-{entity}",
        rule_id=rule_id,
        rule_name=rule_name,
        severity=cfg.SEVERITY[rule_id],
        country=str(country),
        entity=str(entity),
        metrics=metrics,
        threshold=threshold,
        evidence=evidence,
        recommended_action=action,
    )


# --- A1: budget near full spend ---------------------------------------------


def rule_budget_consumption() -> list[Alarm]:
    out = []
    bc = fin.budget_consumption()
    hot = bc[
        (bc["consumption_pct"] > cfg.TH_BUDGET_CONSUMPTION_PCT)
        & (bc["months_remaining"] >= 2)
    ]
    for r in hot.itertuples():
        out.append(
            _mk(
                "A1",
                "Presupuesto cerca de agotarse",
                r.country,
                r.category,
                {
                    "consumption_pct": r.consumption_pct,
                    "annual_budget_usd": r.annual_budget_usd,
                    "ytd_actual_usd": r.ytd_actual_usd,
                    "months_remaining": r.months_remaining,
                },
                f"consumo > {cfg.TH_BUDGET_CONSUMPTION_PCT:.0f}% con >= 2 meses restantes",
                (
                    f"{r.country}: {r.category} ({r.cost_type}) lleva {r.consumption_pct:.1f}% "
                    f"del presupuesto anual consumido a junio, con {r.months_remaining} "
                    f"meses restantes."
                ),
                "Congelar compromisos no esenciales y solicitar reasignación "
                "presupuestaria antes del Q3.",
            )
        )
    return out


def _a1_flagged() -> set[tuple[str, str]]:
    bc = fin.budget_consumption()
    hot = bc[bc["consumption_pct"] > cfg.TH_BUDGET_CONSUMPTION_PCT]
    return {(str(r.country), str(r.category)) for r in hot.itertuples()}


# --- A2: OPEX run-rate overspend ----------------------------------------------


def rule_opex_runrate() -> list[Alarm]:
    out = []
    skip = _a1_flagged()  # already reported as A1; don't double-alarm
    bc = fin.budget_consumption("OPEX")
    hot = bc[bc["run_rate_fy_pct"] > cfg.TH_RUNRATE_PCT]
    for r in hot.itertuples():
        if (r.country, r.category) in skip:
            continue
        out.append(
            _mk(
                "A2",
                "Run-rate proyecta sobregasto OPEX",
                r.country,
                r.category,
                {
                    "run_rate_fy_pct": r.run_rate_fy_pct,
                    "consumption_pct": r.consumption_pct,
                    "annual_budget_usd": r.annual_budget_usd,
                },
                f"run-rate anualizado > {cfg.TH_RUNRATE_PCT:.0f}% del presupuesto",
                (
                    f"{r.country}: {r.category} proyecta cerrar el año en {r.run_rate_fy_pct:.1f}% "
                    f"del presupuesto si mantiene el ritmo actual "
                    f"(consumo YTD {r.consumption_pct:.1f}%)."
                ),
                "Renegociar tarifas/contratos y definir plan de mitigación con el país "
                "antes del cierre de Q3.",
            )
        )
    return out


# --- A3: CAPEX overrun ---------------------------------------------------------


def rule_capex_overrun() -> list[Alarm]:
    out = []
    skip = _a1_flagged()
    bc = fin.budget_consumption("CAPEX")
    hot = bc[
        (bc["committed_pct"] > cfg.TH_CAPEX_COMMITTED_PCT)
        | (bc["run_rate_fy_pct"] > cfg.TH_RUNRATE_PCT)
    ]
    for r in hot.itertuples():
        if (r.country, r.category) in skip:
            continue
        out.append(
            _mk(
                "A3",
                "CAPEX comprometido/proyectado sobre presupuesto",
                r.country,
                r.category,
                {
                    "committed_pct": r.committed_pct,
                    "run_rate_fy_pct": r.run_rate_fy_pct,
                    "annual_budget_usd": r.annual_budget_usd,
                    "ytd_spent_usd": r.ytd_actual_usd,
                },
                (
                    f"comprometido > {cfg.TH_CAPEX_COMMITTED_PCT:.0f}% o run-rate > "
                    f"{cfg.TH_RUNRATE_PCT:.0f}% del presupuesto"
                ),
                (
                    f"{r.country}: {r.category} tiene {r.committed_pct:.1f}% del presupuesto anual "
                    f"ya comprometido (POs emitidas) y un run-rate de gasto "
                    f"de {r.run_rate_fy_pct:.1f}%."
                ),
                "Revisar el plan de despliegue con Ingeniería: repriorizar fases o "
                "ampliar presupuesto vía CAPEX committee.",
            )
        )
    return out


# --- A4: margin compression ----------------------------------------------------


def rule_margin_compression() -> list[Alarm]:
    out = []
    gm = fin.margin_by_segment(months=2)
    gm = gm[gm["segment"].isin(cfg.SERVICE_SEGMENTS)]
    for (country, segment), grp in gm.groupby(["country", "segment"]):
        if len(grp) == 2 and (grp["variance_pp"] <= -cfg.TH_MARGIN_GAP_PP).all():
            last = grp.sort_values("month").iloc[-1]
            out.append(
                _mk(
                    "A4",
                    "Compresión de margen bruto vs objetivo",
                    country,
                    segment,
                    {
                        "gm_pct": last["gm_pct"],
                        "gm_target_pct": last["gm_target_pct"],
                        "variance_pp": last["variance_pp"],
                        "months_below": grp["month"].tolist(),
                    },
                    f"GM% > {cfg.TH_MARGIN_GAP_PP:.0f}pp bajo objetivo, 2 meses consecutivos",
                    (
                        f"{country} {segment}: margen bruto {last['gm_pct']:.1f}% vs objetivo "
                        f"{last['gm_target_pct']:.1f}% ({last['variance_pp']:+.1f}pp) "
                        f"por segundo mes consecutivo."
                    ),
                    "Revisar costos directos del segmento (contratos de "
                    "contenido/interconexión) y evaluar repricing.",
                )
            )
    return out


# --- A5: revenue decline --------------------------------------------------------


def rule_revenue_decline() -> list[Alarm]:
    out = []
    tr = fin.revenue_trend(months=3)
    tr = tr[tr["segment"].isin(cfg.SERVICE_SEGMENTS)]
    for (country, segment), seg_rows in tr.groupby(["country", "segment"]):
        grp = seg_rows.sort_values("month")
        last2 = grp["mom_pct"].tail(2)
        if len(last2) == 2 and (last2 <= -cfg.TH_REVENUE_DECLINE_PCT).all():
            out.append(
                _mk(
                    "A5",
                    "Caída sostenida de ingresos",
                    country,
                    segment,
                    {
                        "mom_pct_last2": last2.tolist(),
                        "revenue_last_month_usd": float(grp["revenue_usd"].iloc[-1]),
                    },
                    f"caída MoM >= {cfg.TH_REVENUE_DECLINE_PCT:.0f}% por 2 meses consecutivos",
                    (
                        f"{country} {segment}: ingresos cayeron {last2.iloc[0]:.1f}% y "
                        f"{last2.iloc[1]:.1f}% MoM en los últimos dos meses."
                    ),
                    "Analizar churn/competencia en el mercado y activar plan "
                    "comercial de retención.",
                )
            )
    return out


# --- A6: cost spike --------------------------------------------------------------


def rule_cost_spike() -> list[Alarm]:
    out = []
    op = fin.opex_trend(months=2)
    for (country, category), cat_rows in op.groupby(["country", "category"]):
        grp = cat_rows.sort_values("month")
        if len(grp) < 2:
            continue
        prev, last = grp["amount_usd"].iloc[-2], grp["amount_usd"].iloc[-1]
        mom = (last / prev - 1) * 100
        if mom >= cfg.TH_COST_SPIKE_MOM_PCT:
            out.append(
                _mk(
                    "A6",
                    "Pico de costo mensual",
                    country,
                    category,
                    {
                        "mom_pct": round(mom, 1),
                        "last_month_usd": round(last, 0),
                        "prev_month_usd": round(prev, 0),
                    },
                    f"incremento MoM >= {cfg.TH_COST_SPIKE_MOM_PCT:.0f}% en el mes de cierre",
                    (
                        f"{country}: {category} subió {mom:+.1f}% MoM en {cfg.AS_OF} "
                        f"(${last / 1e6:.2f}M vs ${prev / 1e6:.2f}M)."
                    ),
                    "Validar si es un one-off (tarifa/estacionalidad) y ajustar "
                    "el forecast de OPEX del país.",
                )
            )
    return out


# --- A7: DSO rise / collection shortfall ------------------------------------------


def rule_collections() -> list[Alarm]:
    out = []
    for country in cfg.COUNTRIES:
        dso = fin.dso_series(country, months=4)
        current = dso["dso_days"].iloc[-1]
        prev_avg = dso["dso_days"].iloc[:-1].mean()
        cs = fin.collections_summary(country)
        ratio_now = list(cs["collections_ratio_pct_last_3m"].values())[-1]
        dso_breach = prev_avg > 0 and current > cfg.TH_DSO_RISE_RATIO * prev_avg
        coll_breach = ratio_now < cfg.TH_COLLECTIONS_MIN_PCT
        if dso_breach or coll_breach:
            out.append(
                _mk(
                    "A7",
                    "Deterioro de cobranza / DSO",
                    country,
                    "B2B",
                    {
                        "dso_days_now": current,
                        "dso_days_prev3_avg": round(prev_avg, 1),
                        "collections_ratio_pct": ratio_now,
                        "open_ar_usd": cs["open_ar_total_usd"],
                    },
                    (
                        f"DSO > {cfg.TH_DSO_RISE_RATIO:.2f}x promedio 3m previo, o cobranza "
                        f"mensual < {cfg.TH_COLLECTIONS_MIN_PCT:.0f}% de la facturación"
                    ),
                    (
                        f"{country} B2B: DSO subió a {current:.0f} días (promedio previo "
                        f"{prev_avg:.0f}) y la cobranza de {cfg.AS_OF} fue {ratio_now:.0f}% "
                        f"de lo facturado."
                    ),
                    "Escalar gestión de cobranza con los clientes morosos principales "
                    "y revisar provisiones de incobrables.",
                )
            )
    return out


# --- A8: overdue B2B client ---------------------------------------------------------


def rule_overdue_client() -> list[Alarm]:
    out = []
    top = fin.top_overdue_clients(limit=10)
    hot = top[
        (top["overdue_over60_usd"] > 0)
        & (top["overdue_vs_monthly_billing_pct"] > cfg.TH_OVERDUE_VS_BILLING_PCT)
    ]
    for r in hot.itertuples():
        over60_usd = cast(float, r.overdue_over60_usd)
        max_days = int(cast(float, r.max_overdue_days))
        out.append(
            _mk(
                "A8",
                "Cliente B2B con mora crítica",
                r.country,
                r.client_id,
                {
                    "client_name": r.client_name,
                    "sector": r.sector,
                    "overdue_over60_usd": over60_usd,
                    "overdue_total_usd": r.overdue_usd,
                    "max_overdue_days": max_days,
                    "monthly_billing_usd": r.monthly_billing_usd,
                },
                f"mora > 60 días superior al {cfg.TH_OVERDUE_VS_BILLING_PCT:.0f}% "
                f"de su facturación mensual",
                (
                    f"{r.client_name} ({r.country}): ${over60_usd / 1e6:.1f}M vencidos "
                    f"a más de 60 días ({r.overdue_vs_monthly_billing_pct:.0f}% de su facturación "
                    f"mensual, máx. {max_days} días)."
                ),
                "Reunión ejecutiva de cobranza, plan de pagos formal y evaluar "
                "suspensión parcial de servicios no críticos.",
            )
        )
    return out


# --- A9: client concentration ---------------------------------------------------------


def rule_concentration() -> list[Alarm]:
    out = []
    top = fin.top_overdue_clients(limit=10)
    hot = top[
        (top["share_of_country_b2b_pct"] > cfg.TH_CONCENTRATION_PCT)
        & (top["overdue_usd"] > 0)
    ]
    for r in hot.itertuples():
        out.append(
            _mk(
                "A9",
                "Concentración de ingresos B2B en cliente moroso",
                r.country,
                r.client_id,
                {
                    "client_name": r.client_name,
                    "share_of_country_b2b_pct": r.share_of_country_b2b_pct,
                    "overdue_usd": r.overdue_usd,
                },
                f"cliente > {cfg.TH_CONCENTRATION_PCT:.0f}% del B2B del país y en mora",
                (
                    f"{r.client_name} representa {r.share_of_country_b2b_pct:.1f}% "
                    f"del ingreso B2B de {r.country} y mantiene saldos vencidos — "
                    f"riesgo combinado de ingreso y crédito."
                ),
                "Diversificar cartera B2B del país y condicionar renovaciones "
                "a regularización de pagos.",
            )
        )
    return out


RULES = [
    rule_budget_consumption,
    rule_opex_runrate,
    rule_capex_overrun,
    rule_margin_compression,
    rule_revenue_decline,
    rule_cost_spike,
    rule_collections,
    rule_overdue_client,
    rule_concentration,
]

_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def scan() -> list[Alarm]:
    alarms: list[Alarm] = []
    for rule in RULES:
        alarms.extend(rule())
    return sorted(alarms, key=lambda a: (_SEV_ORDER[a.severity], a.id))


if __name__ == "__main__":
    found = scan()
    print(f"{len(found)} alarms:")
    for a in found:
        print(f"  [{a.severity:<6}] {a.id}: {a.evidence}")
    expected, got = set(cfg.EXPECTED_ALARMS), {a.id for a in found}
    print(
        "\nmanifest match:",
        "OK"
        if expected == got
        else f"MISMATCH missing={expected - got} extra={got - expected}",
    )
