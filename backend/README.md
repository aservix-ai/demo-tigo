# Tigo — Financial Analysis AI Agent (VP Demo)

An AI agent (Python + LangChain + Claude) that analyzes **OPEX, CAPEX and
Revenue** for Tigo's five LatAm markets and delivers a **gross-margin report**
with deterministic **alarm detection**: budget near full spend, run-rate
overspend, CAPEX overrun, margin compression, revenue decline, cost spikes,
DSO deterioration, delinquent B2B clients and revenue concentration.

**Design principle:** every figure is computed by deterministic pandas code and
every alarm fires from an auditable Python rule (`demo/alarms.py`). The LLM
narrates, prioritizes and answers follow-up questions — it never does
arithmetic. The dataset is generated with a fixed seed and committed, so the
demo shows the **same 9 alarms on every run**.

Data ingest is simulated by design (`data/*.csv` stand in for ERP / billing /
AR extracts). To go live, replace the CSV loaders in `demo/finance.py` with
real SAP / billing / AR connectors — the finance engine, alarm rules and agent
are unchanged.

## Setup

```bash
.venv/bin/pip install -r requirements.txt   # pandas, rich, python-dotenv
cp .env.example .env                        # add your NVIDIA_API_KEY
.venv/bin/python main.py preflight          # must print READY FOR DEMO
.venv/bin/python main.py report --chat      # the demo command
```

## Commands

| Command | What it does |
|---|---|
| `python main.py report --chat` | KPI dashboard → streamed report with live tool-trace → alarm panel → saved markdown → interactive Q&A |
| `python main.py chat` | Interactive Q&A only |
| `python main.py preflight` | Pre-demo check: data integrity, exact alarm manifest, tools, live API ping |
| `python main.py data` | Regenerate the CSVs (byte-identical, seed=42). Never needed live. |

## Demo run-of-show (~7 min)

1. *(30s)* Open `data/` — "these CSVs simulate the ERP/billing/AR extracts;
   ingestion is mocked by design."
2. *(3 min)* `python main.py report --chat`:
   - Instant KPI dashboard (healthy headline: GM ~73%, EBITDA ~41%).
   - The agent visibly works the books (`→ consultando get_budget_consumption(...)`)
     while the report streams in Spanish.
   - The severity-colored alarm panel closes the arc: *the topline hides 9 issues*.
3. *(3 min)* Follow-up questions in the same session (rehearsed):
   - **"¿Por qué subió el DSO en Guatemala?"** — the agent drills into
     collections and names the delinquent government client ($4.1M >60 days).
   - **"¿Qué pasa si Colombia mantiene este ritmo de gasto en energía?"** —
     cites the ~120% run-rate and the mitigation recommendation.
   - **"¿Qué segmento está perdiendo margen y por qué?"** — Paraguay Home,
     content-cost repricing, −4pp vs target.
4. *(30s)* Open `reports/informe_margen_bruto_2026-06.md` — "the artifact your
   team would receive every morning."

## The 9 rehearsed alarms

| Id | Rule | Seeded story | Severity |
|---|---|---|---|
| A1-Guatemala-sales_marketing | Budget >85% consumed, ≥2 months left | S&M front-loaded to 88% by June | High |
| A2-Colombia-energy | OPEX run-rate >105% of budget | Energy tariff escalation → ~120% FY forecast | High |
| A3-Colombia-fiber_transport | CAPEX committed >95% / run-rate >105% | Fiber buildout: 96% committed, 112% run-rate | High |
| A4-Paraguay-Home | GM >2pp below target, 2 months | Content repricing → −4pp May+Jun | High |
| A7-Guatemala-B2B | DSO >1.1× 3-month avg or collections <90% | DSO 53→68 days; June collections 76% | High |
| A8-Guatemala-GT-B2B-001 | >60d overdue >50% of monthly billing | Gov client: $4.1M unpaid project invoices | High |
| A5-Bolivia-Mobile_Prepaid | MoM ≥−5%, 2 months | Prepaid −5.5% / −5.2% (competitive pressure) | Medium |
| A6-Panama-energy | OPEX MoM ≥+15% in closing month | Energy +19% MoM (generator fuel) | Medium |
| A9-Guatemala-GT-B2B-001 | Client >15% of B2B and overdue | Gov client = 19% of Guatemala B2B | Medium |

`preflight` asserts the scan produces exactly this manifest — nothing extra,
nothing missing.

## If the demo breaks live

The data is deterministic, so a previously saved run is **identical** to what
the live run would have produced. Open the committed
`reports/rehearsal_fallback.md` and present it. (Generate it during rehearsal:
run `python main.py report`, then
`cp reports/informe_margen_bruto_2026-06.md reports/rehearsal_fallback.md`.)

Other pre-demo insurance: run `python main.py preflight` the same morning
(validates data, alarms, tools, API key and network for pennies), and have a
phone hotspot tested as network backup.

## Architecture

```
data/*.csv  ──► demo/finance.py ──► demo/alarms.py ──► 9 alarms (pydantic)
 (simulated       (pandas: P&L,        (9 deterministic
  ERP/billing)     margins, DSO...)     FP&A rules)
                        │                     │
                        ▼                     ▼
                  demo/tools.py  ◄── the LLM only sees tool outputs
                        │
                  demo/agent.py   LangChain create_agent + nemotron-3-ultra-550b-a55b
                        │
                  demo/display.py rich terminal: dashboard, streaming, panels
```

- Model: `nemotron-3-ultra-550b-a55b`.
- Budgets use uniform monthly phasing (annual/12) — stated simplification.
- Report and alarms are in Spanish; code and docs in English.
