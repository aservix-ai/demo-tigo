"""Tigo VP demo — CLI entry point.

Commands:
  python main.py data       regenerate the simulated CSVs (deterministic, seed=42)
  python main.py report     stream the full gross-margin report (add --chat for Q&A)
  python main.py chat       interactive Q&A only
  python main.py preflight  pre-demo verification (run the morning of the demo)
"""

import argparse
import os
import sys

from dotenv import load_dotenv


def _require_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel(
            "[red]ANTHROPIC_API_KEY no está definida.[/red]\n"
            "Copia [bold].env.example[/bold] a [bold].env[/bold] y coloca tu clave "
            "de https://console.anthropic.com/",
            border_style="red", title="Configuración requerida"))
        sys.exit(1)


def _require_data() -> None:
    from demo import config as cfg
    if not (cfg.DATA_DIR / "revenue.csv").exists():
        from rich.console import Console
        Console().print("[red]No hay datos en data/.[/red] "
                        "Genera los datos con: [bold]python main.py data[/bold]")
        sys.exit(1)


def cmd_data(_args) -> None:
    from demo import datagen
    datagen.generate()


def cmd_report(args) -> None:
    _require_api_key()
    _require_data()
    from rich.panel import Panel

    from demo import display
    from demo.agent import REPORT_REQUEST, build_agent

    display.banner()
    display.dashboard()

    agent = build_agent()
    display.console.print("[dim]El agente está analizando OPEX, CAPEX, ingresos y "
                          "cobranza...[/dim]\n")
    report_md = ""
    try:
        report_md = display.stream_turn(agent, REPORT_REQUEST)
    except KeyboardInterrupt:
        display.console.print("\n[dim]Informe interrumpido.[/dim]")
    except Exception as e:  # noqa: BLE001 — the show must go on
        display.console.print(Panel(
            f"[red]El agente falló: {e}[/red]\n"
            "Las alertas de abajo son deterministas y siguen siendo válidas. "
            "Si la API no responde, presenta reports/rehearsal_fallback.md.",
            border_style="red"))

    # Alarm panels come from the Python rule engine — they render even if the
    # LLM narrative failed.
    display.alarm_panels()

    if report_md.strip():
        path = display.save_report(report_md)
        display.console.print(f"\n[green]Informe guardado en[/green] [bold]{path}[/bold]")
    else:
        display.console.print("\n[yellow]No se generó narrativa del informe; "
                              "no se guardó archivo.[/yellow]")

    if args.chat:
        display.chat_loop(agent)


def cmd_chat(_args) -> None:
    _require_api_key()
    _require_data()
    from demo import display
    from demo.agent import build_agent

    display.banner()
    display.chat_loop(build_agent())


def cmd_preflight(_args) -> None:
    from demo import preflight
    sys.exit(preflight.run())


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Demo Tigo — agente de análisis financiero")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("data", help="regenerar datos simulados").set_defaults(func=cmd_data)
    p_report = sub.add_parser("report", help="informe completo de margen bruto")
    p_report.add_argument("--chat", action="store_true",
                          help="entrar a modo interactivo al terminar el informe")
    p_report.set_defaults(func=cmd_report)
    sub.add_parser("chat", help="modo interactivo de preguntas").set_defaults(func=cmd_chat)
    sub.add_parser("preflight", help="verificación previa a la demo").set_defaults(func=cmd_preflight)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
