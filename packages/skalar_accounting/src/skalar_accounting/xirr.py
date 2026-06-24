"""XIRR with spreadsheet semantics (foundation §4): Actual/365, Newton + bisection fallback.

Returns the effective annual rate that zeroes the dated NPV, or ``None`` when no rate exists
(all flows the same sign) or the solve does not converge — the workbook's ``#NUM!`` cases.

The convergence tolerance scales with the flow magnitude (an absolute NPV residual is otherwise
meaningless across dollar scales), and every NPV evaluation is guarded so a pathological rate
near the ``-1`` singularity yields ``None`` rather than an exception.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

_NPV_TOL = 1e-10  # scaled by max |cashflow| to a relative residual tolerance
_STEP_TOL = 1e-12  # Newton step size below which we test for a genuine root
_MAX_NEWTON = 100
_MAX_BISECT = 200
_R_MIN = -0.999999  # rate must stay > -1 (1 + r in the denominator)


def _safe_npv(rate: float, amounts: Sequence[float], times: Sequence[float]) -> float | None:
    try:
        return float(sum(a / (1.0 + rate) ** t for a, t in zip(amounts, times, strict=True)))
    except (OverflowError, ZeroDivisionError, ValueError):
        return None


def _dnpv(rate: float, amounts: Sequence[float], times: Sequence[float]) -> float:
    return float(
        sum(-t * a / (1.0 + rate) ** (t + 1.0) for a, t in zip(amounts, times, strict=True))
    )


def xirr(cashflows: Sequence[tuple[date, Decimal]], *, guess: float = 0.1) -> float | None:
    """Effective annual XIRR of dated cash flows, or ``None`` if it does not converge."""
    if len(cashflows) < 2:
        return None
    flows = sorted(cashflows, key=lambda x: x[0])
    d0 = flows[0][0]
    amounts = [float(a) for _, a in flows]
    times = [(d - d0).days / 365.0 for d, _ in flows]
    if not (any(a > 0 for a in amounts) and any(a < 0 for a in amounts)):
        return None  # XIRR undefined without a sign change (#NUM!)

    max_abs = max(abs(a) for a in amounts)
    atol = _NPV_TOL * (max_abs if max_abs > 0.0 else 1.0)

    # Newton-Raphson from the guess, kept inside (-1, inf).
    rate = guess
    for _ in range(_MAX_NEWTON):
        value = _safe_npv(rate, amounts, times)
        if value is None:
            break
        if abs(value) < atol:
            return rate
        try:
            slope = _dnpv(rate, amounts, times)
        except (OverflowError, ZeroDivisionError, ValueError):
            break
        if slope == 0.0:
            break
        rate_next = rate - value / slope
        if rate_next <= _R_MIN:
            rate_next = (rate + _R_MIN) / 2.0  # damp toward the boundary
        if abs(rate_next - rate) < _STEP_TOL:
            final = _safe_npv(rate_next, amounts, times)
            if final is not None and abs(final) < atol:
                return rate_next  # a genuine root, not a stalled step
            break
        rate = rate_next

    return _bisect(amounts, times, atol)


def _bisect(amounts: Sequence[float], times: Sequence[float], atol: float) -> float | None:
    """Scan for a sign-change bracket in ``(-1, hi]`` and bisect it."""
    lo = _R_MIN
    f_lo = _safe_npv(lo, amounts, times)
    if f_lo is None:
        return None
    hi = lo
    step = 0.01
    bound = 100.0
    grid = lo + step
    while grid <= bound:
        f_grid = _safe_npv(grid, amounts, times)
        if f_grid is None:
            return None
        if f_lo * f_grid <= 0:
            hi = grid
            break
        lo, f_lo = grid, f_grid
        step *= 1.5  # widen as we move away from the singularity
        grid = lo + step
    else:
        return None
    for _ in range(_MAX_BISECT):
        mid = (lo + hi) / 2.0
        f_mid = _safe_npv(mid, amounts, times)
        if f_mid is None:
            return None
        if abs(f_mid) < atol:
            return mid
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0
