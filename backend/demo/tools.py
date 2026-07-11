"""LangChain tools exposed to the agent.

Thin wrappers over the finance/alarm engines. Every tool returns a compact,
JSON-serializable dict with amounts pre-converted to USD millions ("_musd"
suffix) so the model can quote figures directly without arithmetic.
"""

import math
import unicodedata

from langchain.tools import tool

from . import alarms as al
from . import config as cfg
from . import finance as fin


def _canon(s: str) -> str:
    """Accent-insensitive, case-insensitive canonical form ('Panamá' -> 'panama')."""
    stripped = "".join(c for c in unicodedata.normalize("NFKD", s)
                       if not unicodedata.combining(c))
    return stripped.casefold().strip().replace(" ", "_").replace("-", "_")


_COUNTRY_LOOKUP = {_canon(c): c for c in cfg.COUNTRIES}
_SEGMENT_LOOKUP = {_canon(s): s for s in cfg.SEGMENT_MIX}


def _norm_country(country: str | None) -> tuple[str | None, dict | None]:
    """Map free-form LLM input to a canonical country, or an error payload."""
    if country is None:
        return None, None
    match = _COUNTRY_LOOKUP.get(_canon(country))
    if match is None:
        return None, {"error": f"país desconocido: '{country}'",
                      "paises_validos": list(cfg.COUNTRIES)}
    return match, None


def _norm_segment(segment: str | None) -> tuple[str | None, dict | None]:
    if segment is None:
        return None, None
    match = _SEGMENT_LOOKUP.get(_canon(segment))
    if match is None:
        return None, {"error": f"segmento desconocido: '{segment}'",
                      "segmentos_validos": list(cfg.SEGMENT_MIX)}
    return match, None


def _norm_cost_type(cost_type: str | None) -> tuple[str | None, dict | None]:
    if cost_type is None:
        return None, None
    ct = _canon(cost_type).upper()
    if ct not in ("OPEX", "CAPEX"):
        return None, {"error": f"tipo de costo desconocido: '{cost_type}'",
                      "tipos_validos": ["OPEX", "CAPEX"]}
    return ct, None


def _musd(x: float) -> float | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(x / 1e6, 2)


def _convert_musd(obj):
    """Recursively convert *_usd fields to *_musd and NaN to None so every
    payload is strict-JSON serializable."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k.endswith("_usd"):
                out[k[:-4] + "_musd"] = (
                    {kk: _musd(vv) for kk, vv in v.items()} if isinstance(v, dict) else _musd(v)
                )
            else:
                out[k] = _convert_musd(v)
        return out
    if isinstance(obj, list):
        return [_convert_musd(x) for x in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj


@tool(parse_docstring=True)
def get_pnl_summary(country: str | None = None) -> dict:
    """Resumen P&L del mes de cierre y acumulado del año (YTD): ingresos
    (servicio/equipos), costos directos, margen bruto, OPEX por categoría,
    EBITDA y comparación interanual. Montos en millones de USD.

    Args:
        country: País (Guatemala, Colombia, Panama, Bolivia, Paraguay) o None para consolidado.
    """
    country, err = _norm_country(country)
    if err:
        return err
    return _convert_musd(fin.pnl_summary(country))


@tool(parse_docstring=True)
def get_margin_by_segment(country: str | None = None, months: int = 6) -> dict:
    """Margen bruto por segmento y país vs objetivo: GM% actual, objetivo,
    variación en puntos porcentuales (pp) y tendencia mensual.

    Args:
        country: País o None para todos.
        months: Meses de tendencia a incluir (default 6).
    """
    country, err = _norm_country(country)
    if err:
        return err
    months = max(2, min(int(months), 12))
    gm = fin.margin_by_segment(country, months)
    out = []
    for (ctry, seg), grp in gm.groupby(["country", "segment"]):
        grp = grp.sort_values("month")
        last = grp.iloc[-1]
        out.append({
            "country": ctry, "segment": seg,
            "gm_pct": last["gm_pct"], "gm_target_pct": last["gm_target_pct"],
            "variance_pp": last["variance_pp"],
            "gm_trend_pct": grp["gm_pct"].tolist(),
        })
    return {"as_of": cfg.AS_OF, "months": months, "segments": out}


@tool(parse_docstring=True)
def get_budget_consumption(cost_type: str | None = None, country: str | None = None) -> dict:
    """Consumo de presupuesto anual por país y categoría: presupuesto, gasto YTD,
    % consumido y run-rate proyectado de fin de año (%). Para CAPEX incluye
    además el monto y % comprometido (POs emitidas). Montos en millones de USD.

    Args:
        cost_type: "OPEX", "CAPEX" o None para ambos.
        country: País o None para todos.
    """
    country, err = _norm_country(country)
    if err:
        return err
    cost_type, err = _norm_cost_type(cost_type)
    if err:
        return err
    bc = fin.budget_consumption(cost_type, country)
    return {
        "as_of": cfg.AS_OF, "months_elapsed": cfg.MONTHS_ELAPSED,
        "months_remaining": cfg.MONTHS_REMAINING,
        "rows": _convert_musd(bc.drop(columns=["months_remaining"]).to_dict(orient="records")),
    }


@tool(parse_docstring=True)
def get_capex_status(country: str | None = None) -> dict:
    """Estado de CAPEX: % de los ingresos YTD, presupuesto vs comprometido vs
    ejecutado por categoría. Recordatorio: CAPEX se capitaliza (no afecta
    EBITDA, afecta flujo de caja). Montos en millones de USD.

    Args:
        country: País o None para consolidado.
    """
    country, err = _norm_country(country)
    if err:
        return err
    return _convert_musd(fin.capex_summary(country))


@tool(parse_docstring=True)
def get_collections_status(country: str | None = None) -> dict:
    """Estado de cobranza B2B: antigüedad de cartera (aging), DSO mensual y
    ratio de cobranza (cobrado/facturado) de los últimos 3 meses. Montos en
    millones de USD.

    Args:
        country: País o None para consolidado.
    """
    country, err = _norm_country(country)
    if err:
        return err
    return _convert_musd(fin.collections_summary(country))


@tool(parse_docstring=True)
def get_top_overdue_clients(limit: int = 5) -> dict:
    """Clientes B2B con mayor saldo vencido: monto vencido total y a >60 días,
    días máximos de mora, facturación mensual y % del B2B del país que
    representan. Montos en millones de USD.

    Args:
        limit: Número de clientes a devolver (default 5).
    """
    limit = max(1, min(int(limit), 20))
    top = fin.top_overdue_clients(limit)
    return {"as_of": cfg.AS_OF,
            "clients": _convert_musd(top.to_dict(orient="records"))}


@tool(parse_docstring=True)
def get_revenue_trend(segment: str | None = None, country: str | None = None,
                      months: int = 6) -> dict:
    """Tendencia mensual de ingresos con variación MoM %, por país y segmento.
    Segmentos: Mobile_Prepaid, Mobile_Postpaid, Home, B2B, Tigo_Money, Equipment.
    Filtra por país y/o segmento siempre que sea posible.

    Args:
        segment: Segmento o None para todos.
        country: País o None para todos.
        months: Meses de historia (default 6, máx. 12 recomendado).
    """
    country, err = _norm_country(country)
    if err:
        return err
    segment, err = _norm_segment(segment)
    if err:
        return err
    months = max(2, min(int(months), 12))
    tr = fin.revenue_trend(segment, country, months)
    return {"rows": _convert_musd(tr.to_dict(orient="records"))}


@tool(parse_docstring=True)
def scan_alarms() -> dict:
    """Ejecuta el motor determinístico de alertas (9 reglas FP&A) y devuelve
    todas las alertas activas con severidad, evidencia y acción recomendada.
    ESTA ES LA ÚNICA FUENTE VÁLIDA DE ALERTAS.
    """
    alarms = al.scan()
    by_sev: dict[str, int] = {}
    for a in alarms:
        by_sev[a.severity] = by_sev.get(a.severity, 0) + 1
    return {
        "as_of": cfg.AS_OF, "alarm_count": len(alarms), "by_severity": by_sev,
        "alarms": _convert_musd([a.model_dump() for a in alarms]),
    }


@tool(parse_docstring=True)
def get_alarm_detail(alarm_id: str) -> dict:
    """Detalle de evidencia de una alerta específica (para preguntas de
    seguimiento): series subyacentes, presupuesto, clientes o tendencias según
    el tipo de alerta.

    Args:
        alarm_id: Id de la alerta, p. ej. "A7-Guatemala-B2B".
    """
    alarm = next((a for a in al.scan() if a.id == alarm_id), None)
    if alarm is None:
        return {"error": f"alerta '{alarm_id}' no encontrada",
                "available": [a.id for a in al.scan()]}
    detail: dict = {"alarm": _convert_musd(alarm.model_dump())}
    if alarm.rule_id in ("A1", "A2", "A6"):
        tr = fin.opex_trend(alarm.country, months=7)
        tr = tr[tr["category"] == alarm.entity]
        detail["monthly_series"] = _convert_musd(tr.to_dict(orient="records"))
    elif alarm.rule_id == "A3":
        bc = fin.budget_consumption("CAPEX", alarm.country)
        detail["capex_rows"] = _convert_musd(bc.to_dict(orient="records"))
    elif alarm.rule_id == "A4":
        gm = fin.margin_by_segment(alarm.country, months=6)
        gm = gm[gm["segment"] == alarm.entity]
        detail["gm_trend"] = gm.to_dict(orient="records")
    elif alarm.rule_id == "A5":
        tr = fin.revenue_trend(alarm.entity, alarm.country, months=8)
        detail["revenue_trend"] = _convert_musd(tr.to_dict(orient="records"))
    elif alarm.rule_id == "A7":
        detail["collections"] = _convert_musd(fin.collections_summary(alarm.country))
        detail["top_overdue_clients"] = _convert_musd(
            fin.top_overdue_clients(5).to_dict(orient="records"))
    elif alarm.rule_id in ("A8", "A9"):
        detail["top_overdue_clients"] = _convert_musd(
            fin.top_overdue_clients(5).to_dict(orient="records"))
    return detail


ALL_TOOLS = [
    get_pnl_summary, get_margin_by_segment, get_budget_consumption,
    get_capex_status, get_collections_status, get_top_overdue_clients,
    get_revenue_trend, scan_alarms, get_alarm_detail,
]
