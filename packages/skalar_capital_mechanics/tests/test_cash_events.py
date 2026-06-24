"""Phase 4: downstream cash events, debt-taken derivation, netting, ledger."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from skalar_capital_mechanics import (
    CashEvent,
    CashEventKind,
    GCDates,
    build_downstream_cash_events,
    build_netting,
    build_transacted_ledger,
    derive_debt_taken,
)

JUN8 = date(2026, 6, 8)
JUN5 = date(2026, 6, 5)
JUN28 = date(2026, 6, 28)
JUL28 = date(2026, 7, 28)
AUG28 = date(2026, 8, 28)
SEP28 = date(2026, 9, 28)
OCT28 = date(2026, 10, 28)


def _june_downstream() -> list[CashEvent]:
    # The workbook's real Kindroid June cohort (Debt Given sheet).
    return build_downstream_cash_events(
        company_id="SK011",
        cohort_month=date(2026, 6, 1),
        counterparty="Kindroid",
        funding_amount=Decimal("160000"),
        funding_date=JUN8,
        sharing=[
            (JUL28, Decimal("84000")),
            (AUG28, Decimal("45000")),
            (SEP28, Decimal("30000")),
            (OCT28, Decimal("22500")),
        ],
        adjustments=[(JUN28, Decimal("-12000")), (JUL28, Decimal("6000"))],
    )


def test_downstream_signs_and_kinds() -> None:
    events = _june_downstream()
    fund = [e for e in events if e.kind is CashEventKind.FUND_DOWN]
    share = [e for e in events if e.kind is CashEventKind.SHARE_UP]
    adj = [e for e in events if e.kind is CashEventKind.ADJUST]

    assert len(fund) == 1
    assert fund[0].amount == Decimal("-160000")  # outflow < 0
    assert fund[0].date == JUN8
    assert [e.amount for e in share] == [Decimal(v) for v in ("84000", "45000", "30000", "22500")]
    assert all(e.amount > 0 for e in share)  # inflows > 0
    assert {e.amount for e in adj} == {Decimal("-12000"), Decimal("6000")}


def test_debt_taken_pfa_fa_and_remittance_basis() -> None:
    gc = GCDates(cohort_month=date(2026, 6, 1), funding_date=JUN5)
    derived = derive_debt_taken(_june_downstream(), gc)
    by_kind = {k: [e for e in derived if e.kind is k] for k in CashEventKind}

    # PFA = -0.95 x funding, dated at the GC trade date (workbook D6 = 152000 @ 2026-06-05).
    pfa = by_kind[CashEventKind.PFA]
    assert len(pfa) == 1
    assert pfa[0].amount == Decimal("152000.00")
    assert pfa[0].date == JUN5
    assert pfa[0].counterparty == "GC"

    # FA-up = 0.95 x adjustment, signed passthrough (workbook E6 = -11400, F6 = +5700).
    fa = {e.date: e.amount for e in by_kind[CashEventKind.FA_UP]}
    assert fa[JUN28] == Decimal("-11400.00")
    assert fa[JUL28] == Decimal("5700.00")

    # Remittance basis = -0.95 x sharing (uncapped; the workbook MAX cap is applied in Phase 5).
    rem = {e.date: e.amount for e in by_kind[CashEventKind.REMIT]}
    assert rem[JUL28] == Decimal("-79800.00")  # -0.95 x 84000
    assert rem[AUG28] == Decimal("-42750.00")  # -0.95 x 45000


def test_debt_taken_leverage_is_a_parameter() -> None:
    derived = derive_debt_taken(
        _june_downstream(),
        GCDates(cohort_month=date(2026, 6, 1), funding_date=JUN5),
        leverage=Decimal("0.50"),
    )
    pfa = next(e for e in derived if e.kind is CashEventKind.PFA)
    assert pfa.amount == Decimal("80000.00")  # 0.50 x 160000


def test_netting_collapses_same_date_events() -> None:
    cohort = date(2026, 6, 1)
    events = [
        CashEvent(company_id="SK011", cohort_month=cohort, date=JUN28, amount=Decimal("100"),
                  kind=CashEventKind.SHARE_UP, counterparty="Kindroid"),
        CashEvent(company_id="SK011", cohort_month=cohort, date=JUN28, amount=Decimal("-30"),
                  kind=CashEventKind.FUND_DOWN, counterparty="Kindroid"),
        CashEvent(company_id="SK011", cohort_month=cohort, date=JUL28, amount=Decimal("-50"),
                  kind=CashEventKind.FUND_DOWN, counterparty="Kindroid"),
        CashEvent(company_id="SK011", cohort_month=cohort, date=JUN28, amount=Decimal("200"),
                  kind=CashEventKind.PFA, counterparty="GC"),
    ]
    instructions = build_netting(events)
    # Three wires: (Kindroid, Jun28) nets 70 over 2 events; (GC, Jun28) 200; (Kindroid, Jul28) -50.
    kindroid_jun = next(i for i in instructions if i.counterparty == "Kindroid" and i.date == JUN28)
    assert kindroid_jun.net_amount == Decimal("70")
    assert kindroid_jun.event_count == 2
    assert kindroid_jun.direction == "receive"
    gc = next(i for i in instructions if i.counterparty == "GC")
    assert gc.net_amount == Decimal("200")
    kindroid_jul = next(i for i in instructions if i.counterparty == "Kindroid" and i.date == JUL28)
    assert kindroid_jul.direction == "pay"
    assert len(instructions) == 3


def test_transacted_ledger_types() -> None:
    rows = build_transacted_ledger(_june_downstream())
    types = {r.type for r in rows}
    assert types == {"Investment Request", "Under/Over", "Payment Due"}
    fund_row = next(r for r in rows if r.amount == Decimal("-160000"))
    assert fund_row.type == "Investment Request"
    assert fund_row.counterparty == "Kindroid"
    assert fund_row.loan_cohort == date(2026, 6, 1)
