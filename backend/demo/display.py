"""Terminal presentation layer (rich).

The KPI dashboard and the alarm panels are rendered directly from the pandas
engines — they cannot disagree with the data regardless of what the LLM writes.
The agent's narrative streams token-by-token into a Live markdown region with
a visible tool-call trace.
"""

from langchain_core.messages import AIMessageChunk
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from . import alarms as al
from . import config as cfg
from . import finance as fin

console = Console()

_SPARK = "▁▂▃▄▅▆▇█"
_SEV_STYLE = {"critical": "bold white on red", "high": "bold red", "medium": "yellow"}
_SEV_LABEL = {"critical": "CRÍTICA", "high": "ALTA", "medium": "MEDIA"}


def sparkline(values: list[float]) -> str:
    lo, hi = min(values), max(values)
    if hi == lo:
        return _SPARK[3] * len(values)
    return "".join(_SPARK[int((v - lo) / (hi - lo) * 7)] for v in values)


def banner() -> None:
    console.print(Panel(
        "[bold cyan]TIGO — Agente de Análisis Financiero[/bold cyan]\n"
        "[dim]OPEX · CAPEX · Ingresos · Margen bruto · Alertas   |   "
        "datos simulados · cierre junio 2026[/dim]",
        border_style="cyan", padding=(1, 4),
    ))


def dashboard() -> None:
    """Deterministic KPI view rendered before the first API call."""
    p = fin.pnl_summary()
    ytd = p["ytd"]

    tiles = Table.grid(expand=True, padding=(0, 2))
    for _ in range(4):
        tiles.add_column(justify="center", ratio=1)

    def tile(label: str, value: str) -> Panel:
        return Panel(f"[bold white]{value}[/bold white]\n[dim]{label}[/dim]",
                     border_style="bright_black", padding=(0, 1))

    capex = fin.capex_summary()
    tiles.add_row(
        tile("Ingresos YTD 2026", f"${ytd['total_revenue_usd'] / 1e6:,.0f}M"),
        tile("Margen bruto servicio", f"{ytd['service_gross_margin_pct']:.1f}%"),
        tile("Margen EBITDA", f"{ytd['ebitda_margin_pct']:.1f}%"),
        tile("CAPEX % ingresos", f"{capex['capex_pct_of_revenue_ytd']:.1f}%"),
    )
    console.print(tiles)

    table = Table(title="Panorama por país — YTD junio 2026",
                  header_style="bold cyan", border_style="bright_black")
    table.add_column("País")
    table.add_column("Ingresos ($M)", justify="right")
    table.add_column("GM servicio", justify="right")
    table.add_column("EBITDA", justify="right")
    table.add_column("Tendencia 6m", justify="center")

    trend = fin.revenue_trend(months=6)
    for country in cfg.COUNTRIES:
        cp = fin.pnl_summary(country)["ytd"]
        series = (trend[trend["country"] == country]
                  .groupby("month")["revenue_usd"].sum().sort_index().tolist())
        table.add_row(
            country,
            f"{cp['total_revenue_usd'] / 1e6:,.0f}",
            f"{cp['service_gross_margin_pct']:.1f}%",
            f"{cp['ebitda_margin_pct']:.1f}%",
            f"[cyan]{sparkline(series)}[/cyan]",
        )
    console.print(table)
    console.print()


def _msg_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))


def stream_turn(agent, user_input: str, thread_id: str = "demo") -> str:
    """Stream one agent turn: live markdown for tokens + dim trace lines for
    tool calls. Returns the final assistant message text."""
    config = {"configurable": {"thread_id": thread_id}}
    buffer = ""
    with Live(console=console, refresh_per_second=8, vertical_overflow="visible") as live:
        for mode, data in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config,
            stream_mode=["updates", "messages"],
        ):
            if mode == "messages":
                token, _meta = data
                # Only render the model's own tokens; "messages" mode also
                # emits ToolMessages (raw JSON payloads) that must not show.
                if isinstance(token, AIMessageChunk) and token.text:
                    buffer += token.text
                    live.update(Markdown(buffer))
            elif mode == "updates":
                for _node, update in (data or {}).items():
                    for msg in (update or {}).get("messages", []):
                        for tc in getattr(msg, "tool_calls", None) or []:
                            args = ", ".join(f"{k}={v}" for k, v in tc["args"].items())
                            # escape(): LLM-generated args must not be parsed
                            # as rich markup (e.g. a stray "[/dim]").
                            live.console.print(
                                f"  [dim cyan]→ consultando "
                                f"{escape(tc['name'])}({escape(args)})[/dim cyan]")
                            if buffer and not buffer.endswith("\n\n"):
                                buffer += "\n\n"

    state = agent.get_state(config)
    final = state.values["messages"][-1]
    return _msg_text(final)


def alarm_panels() -> None:
    """Severity-colored panels rendered straight from the rule engine."""
    alarms = al.scan()
    console.print()
    console.rule(f"[bold red]⚠ ALERTAS DETECTADAS: {len(alarms)}[/bold red]")
    for a in alarms:
        style = _SEV_STYLE[a.severity]
        body = Group(
            f"[white]{a.evidence}[/white]",
            f"[dim]Umbral: {a.threshold}[/dim]",
            f"[green]Acción: {a.recommended_action}[/green]",
        )
        console.print(Panel(
            body,
            title=(
                f"[{style}] {_SEV_LABEL[a.severity]} [/{style}] "
                f"[bold]{a.id}[/bold] · {a.rule_name}"
            ),
            title_align="left", border_style="red" if a.severity != "medium" else "yellow",
        ))


def save_report(markdown_text: str) -> str:
    cfg.REPORTS_DIR.mkdir(exist_ok=True)
    path = cfg.REPORTS_DIR / f"informe_margen_bruto_{cfg.AS_OF}.md"
    path.write_text(markdown_text, encoding="utf-8")
    return str(path)


def chat_loop(agent, thread_id: str = "demo") -> None:
    console.print("\n[bold cyan]Modo interactivo[/bold cyan] "
                  "[dim](escribe tu pregunta; 'salir' para terminar)[/dim]\n")
    while True:
        try:
            question = Prompt.ask("[bold]Tú[/bold]")
        except (KeyboardInterrupt, EOFError):
            break
        if not question.strip() or question.strip().lower() in {"salir", "exit", "quit"}:
            break
        console.print()
        try:
            stream_turn(agent, question, thread_id)
        except KeyboardInterrupt:
            console.print("\n[dim]Respuesta interrumpida.[/dim]")
        except Exception as e:
            console.print(Panel(f"[red]Error en la consulta: {escape(str(e))}[/red]\n"
                                "Puedes reformular la pregunta e intentar de nuevo.",
                                border_style="red"))
        console.print()
    console.print("[dim]Sesión terminada.[/dim]")
