"""Golden fixture: the exact cash-event inputs + expected outputs of docs/Accounting Model.xlsx.

Real Kindroid June + July 2026 loans, both books, captured verbatim from the workbook (see the
``skalar-workbook-eir-oracle`` memory). Inputs are the inflow/outflow series; expected values are
the workbook's computed principal / interest / outstanding / summary / XIRR.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from skalar_accounting import Book, BookFlow, BookKind, DayCount

D = Decimal

GIVEN_DATES = [
    date(2026, 6, 8), date(2026, 6, 28), date(2026, 7, 28), date(2026, 8, 28),
    date(2026, 9, 28), date(2026, 10, 28), date(2026, 11, 28),
]
TAKEN_DATES = [
    date(2026, 6, 5), date(2026, 6, 28), date(2026, 7, 28), date(2026, 8, 28),
    date(2026, 9, 28), date(2026, 10, 28), date(2026, 11, 28),
]

GIVEN_RATE = D("0.25")
TAKEN_RATE = D("0.16")


def _book(name: str, kind: BookKind, rate: Decimal, dates: list[date], inflows: list[str],
          outflows: list[str]) -> Book:
    day_count = DayCount.MONTH_DAYS_365 if kind is BookKind.DEBT_GIVEN else DayCount.ACTUAL_365
    flows = tuple(
        BookFlow(date=d, inflow=D(i), outflow=D(o))
        for d, i, o in zip(dates, inflows, outflows, strict=True)
    )
    return Book(name=name, kind=kind, rate=rate, day_count=day_count, flows=flows)


def june_debt_given() -> Book:
    return _book(
        "June 2026 Loan", BookKind.DEBT_GIVEN, GIVEN_RATE, GIVEN_DATES,
        inflows=["0", "0", "84000", "45000", "30000", "22500", "0"],
        outflows=["-160000", "-12000", "6000", "0", "0", "0", "0"],
    )


def july_debt_given() -> Book:
    return _book(
        "July 2026 Loan", BookKind.DEBT_GIVEN, GIVEN_RATE, GIVEN_DATES,
        inflows=["0", "0", "0", "0", "0", "0", "0"],
        outflows=["0", "-200000", "0", "0", "0", "0", "0"],
    )


def june_debt_taken() -> Book:
    # outflows are the *uncapped* remittance basis (-0.95 x downstream sharing); the EIR caps them.
    return _book(
        "June 2026 Loan", BookKind.DEBT_TAKEN, TAKEN_RATE, TAKEN_DATES,
        inflows=["152000", "-11400", "5700", "0", "0", "0", "0"],
        outflows=["0", "0", "-79800", "-42750", "-28500", "-21375", "0"],
    )


def july_debt_taken() -> Book:
    return _book(
        "July 2026 Loan", BookKind.DEBT_TAKEN, TAKEN_RATE, TAKEN_DATES,
        inflows=["0", "190000", "0", "0", "0", "0", "0"],
        outflows=["0", "0", "0", "0", "0", "0", "0"],
    )


# --- Expected workbook outputs (floats, as the workbook stores them) ---

JUNE_GIVEN_PRINCIPAL = [
    0.0, -2961.565918961598, 80652.52237240798, 43310.414369959064,
    29167.08495894129, 15831.54421765326, 0.0,
]
JUNE_GIVEN_INTEREST = [
    0.0, 2961.565918961598, 3347.477627592016, 1689.585630040936,
    832.9150410587099, 6668.45578234674, 0.0,
]
JUNE_GIVEN_OUTSTANDING = [
    -160000.0, -174961.5659189616, -88309.04354655361, -44998.62917659455,
    -15831.54421765326, 0.0, 0.0,
]
JUNE_GIVEN_XIRR = 0.5099311411380766

JUNE_TAKEN_PRINCIPAL = [
    0.0, 1428.2474347176612, -78056.80002143868, -41866.195441810094,
    -27805.251971468882, 0.0, 0.0,
]
JUNE_TAKEN_INTEREST = [
    0.0, -1428.2474347176612, -1743.1999785613152, -883.804558189906,
    -352.71850013724907, 0.0, 0.0,
]
JUNE_TAKEN_OUTFLOW = [0.0, 0.0, -79800.0, -42750.0, -28157.97047160613, 0.0, 0.0]
JUNE_TAKEN_OUTSTANDING = [
    152000.0, 142028.24743471766, 69671.44741327898, 27805.251971468882, 0.0, 0.0, 0.0,
]
JUNE_TAKEN_XIRR = 0.15999999642372145

# Consolidated (June + July).
GIVEN_CONS_PRINCIPAL = [
    0.0, -2961.565918961598, 76825.99326013139, 39410.67363244697,
    25322.115951065316, 11783.626693606879, -3991.064656345785,
]
GIVEN_CONS_INTEREST = [
    0.0, 2961.565918961598, 7174.006739868608, 5589.3263675530325,
    4677.884048934684, 10716.373306393121, 3991.064656345785,
]
GIVEN_CONS_OUTSTANDING = [
    -160000.0, -374961.5659189616, -292135.5726588302, -252724.89902638324,
    -227402.78307531792, -215619.15638171104, -219610.22103805683,
]
TAKEN_CONS_INTEREST = [
    0.0, -1428.2474347176612, -4075.186762238882, -3323.5972267248435,
    -2823.460717756454, -2420.8787037541333, -2532.793991017883,
]
TAKEN_CONS_OUTSTANDING = [
    152000.0, 332028.24743471766, 262003.43419695654, 222577.0314236814,
    197242.5216698317, 199663.40037358584, 202196.19436460373,
]
TAKEN_CONS_XIRR = -0.9903501344844701

SUMMARY_REVENUE = GIVEN_CONS_INTEREST
SUMMARY_COGS = TAKEN_CONS_INTEREST
SUMMARY_CASH_IMPACT = [
    -8000.0, -33400.0, 15899.99999999997, 2250.0, 1842.0295283938758, 22500.0, 0.0,
]
