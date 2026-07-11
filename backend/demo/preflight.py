"""Pre-demo verification: run `python main.py preflight` the morning of the demo.

Checks, in order: API key present, data files intact, financial consistency,
the exact rehearsed alarm manifest, tool serializability, and a 5-token live
API ping. Prints a green READY panel or a red panel naming the failing check.
"""

import json
import os

from rich.console import Console
from rich.panel import Panel

from . import alarms as al
from . import config as cfg
from . import finance as fin

console = Console()

EXPECTED_ROWS = {
    "revenue.csv": 900, "direct_costs.csv": 900, "opex.csv": 1200,
    "capex.csv": 900, "budgets.csv": 70, "targets.csv": 30,
    "clients.csv": 60, "invoices.csv": 1803,
}


def _check_api_key() -> str | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return ("ANTHROPIC_API_KEY no está definida. Copia .env.example a .env "
                "y coloca tu clave de https://console.anthropic.com/")
    return None


def _check_files() -> str | None:
    import pandas as pd
    for name, expected in EXPECTED_ROWS.items():
        path = cfg.DATA_DIR / name
        if not path.exists():
            return f"Falta {path}. Ejecuta: python main.py data"
        rows = len(pd.read_csv(path))
        if rows != expected:
            return f"{name}: {rows} filas (esperadas {expected}). Regenera con: python main.py data"
    return None


def _check_consistency() -> str | None:
    p = fin.pnl_summary()["ytd"]
    checks = [
        ("GM servicio", p["service_gross_margin_pct"], 72, 78),
        ("Margen EBITDA", p["ebitda_margin_pct"], 40, 46),
        ("CAPEX % ingresos", fin.capex_summary()["capex_pct_of_revenue_ytd"], 11, 15),
    ]
    for label, value, lo, hi in checks:
        if not lo <= value <= hi:
            return f"{label} = {value} fuera del rango [{lo}, {hi}]"

    # B2B revenue must equal the sum of invoices, to the cent.
    d = fin.load()
    inv = d["invoices"].copy()
    inv["month"] = inv["issue_date"].dt.to_period("M").astype(str)
    inv_sum = inv.groupby(["month", "country"])["amount_usd"].sum()
    rev = d["revenue"]
    b2b = rev[rev["segment"] == "B2B"].set_index(["month", "country"])["revenue_usd"]
    if not ((inv_sum - b2b).abs() < 0.01).all():
        return "Ingresos B2B no cuadran con la suma de facturas (tie-out roto)"
    return None


def _check_alarms() -> str | None:
    got = [a.id for a in al.scan()]
    expected = set(cfg.EXPECTED_ALARMS)
    if set(got) != expected:
        return (f"Alertas no coinciden con el manifiesto ensayado. "
                f"Faltan: {expected - set(got) or '—'} · Sobran: {set(got) - expected or '—'}")
    return None


def _check_tools() -> str | None:
    from .tools import ALL_TOOLS
    for t in ALL_TOOLS:
        args = {"alarm_id": cfg.EXPECTED_ALARMS[0]} if t.name == "get_alarm_detail" else {}
        try:
            json.dumps(t.invoke(args), allow_nan=False)
        except Exception as e:  # noqa: BLE001 — any failure must abort the demo
            return f"Herramienta {t.name} falló: {e}"

    # Adversarial arguments the LLM plausibly produces live: accented /
    # lowercase countries, Spanish cost types, invalid alarm ids. Tools must
    # answer with data or a friendly error dict — never raise.
    from .tools import (get_alarm_detail, get_budget_consumption,
                        get_capex_status, get_pnl_summary, get_revenue_trend)
    adversarial = [
        (get_pnl_summary, {"country": "Panamá"}, False),
        (get_capex_status, {"country": "panama"}, False),
        (get_budget_consumption, {"country": "Perú"}, True),
        (get_budget_consumption, {"cost_type": "capital"}, True),
        (get_revenue_trend, {"segment": "prepago", "country": "Bolivia"}, True),
        (get_alarm_detail, {"alarm_id": "A99-Inventada"}, True),
    ]
    for t, args, expect_error in adversarial:
        try:
            out = t.invoke(args)
            json.dumps(out, allow_nan=False)
        except Exception as e:  # noqa: BLE001
            return f"Herramienta {t.name}({args}) lanzó excepción: {e}"
        if expect_error and "error" not in out:
            return f"Herramienta {t.name}({args}) debía devolver un error amigable"
    return None


def _check_api_ping() -> str | None:
    from langchain_anthropic import ChatAnthropic
    # Ping both the cheap model and the actual demo model — a key restricted
    # to one of them would otherwise pass preflight and fail on stage.
    for model_id in (cfg.PING_MODEL_ID, cfg.MODEL_ID):
        try:
            ChatAnthropic(model=model_id, max_tokens=8).invoke("ping")
        except Exception as e:  # noqa: BLE001
            return f"Ping a la API de Anthropic falló ({model_id}): {e}"
    return None


CHECKS = [
    ("API key en entorno", _check_api_key),
    ("Archivos de datos", _check_files),
    ("Consistencia financiera", _check_consistency),
    ("Manifiesto de alertas (9 exactas)", _check_alarms),
    ("Herramientas del agente", _check_tools),
    ("Ping a la API de Anthropic", _check_api_ping),
]


def run() -> int:
    console.print("[bold]Preflight — verificación previa a la demo[/bold]\n")
    for label, check in CHECKS:
        error = check()
        if error:
            console.print(f"  [red]✗[/red] {label}")
            console.print(Panel(f"[red]{error}[/red]",
                                title="[bold red]NO LISTO PARA LA DEMO[/bold red]",
                                border_style="red"))
            return 1
        console.print(f"  [green]✓[/green] {label}")
    console.print(Panel("[bold green]READY FOR DEMO[/bold green] — "
                        "datos íntegros, 9 alertas ensayadas, API accesible.",
                        border_style="green"))
    return 0
