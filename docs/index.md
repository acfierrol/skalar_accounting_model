# Skalar Capital Mechanics & Accounting Model

One monorepo, two deliverables with a strict one-way dependency:

1. **Capital-mechanics engine** (`skalar_capital_mechanics`) — reads Skalar's BigQuery
   operational data and constructs the cash model: cohorts, collections, reference income,
   sharing, return caps (MOIC/payback), threshold tests & breaches, funding compliance,
   wind-down, and the per-vintage **cash events** (signed, dated inflows/outflows).
2. **Accounting model** (`skalar_accounting`) — consumes those cash events and produces the
   cash-basis accounting report via the **effective-interest (EIR / amortized-cost) method**:
   per-vintage *debt given* (downstream) and *debt taken* (upstream) books, consolidation, and a
   summary (Revenue, Cost of Capital, outstanding principal, period cash impact).

The engine is the source of truth for *what happened*; accounting is the source of truth for
*how it is booked*. **Accounting imports the engine; the engine never imports accounting.**

## Definition of done

From the inputs for SK011 (Kindroid), the pipeline reproduces `docs/Accounting Model.xlsx`
— June + July 2026 loans, both books, consolidation, and summary — within tolerance. This
**golden reconciliation test** (`packages/skalar_accounting/tests/test_golden.py`) is the
acceptance oracle, and it passes to sub-micro-dollar.

## Where to go next

- [Architecture](architecture.md) — packages, the pipeline, and the EIR spec.
- [How to run](how-to-run.md) — the CLI and the common commands.
- [Parameter reference](parameters.md) — the per-cohort deal parameters.
- [Methodology](capital_mechanics_documentation/skalar_cash_model_kb.md) — the authoritative KB.
