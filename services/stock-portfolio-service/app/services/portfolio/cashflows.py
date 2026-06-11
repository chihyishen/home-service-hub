import math
from datetime import date as date_type
from decimal import Decimal


def _calculate_xirr(cash_flows: list[tuple[date_type, Decimal]]) -> Decimal | None:
    """
    Compute XIRR from a list of (date, amount) pairs.
    Returns None if calculation is impossible or fails.
    - amounts < 0: outflows (buy)
    - amounts > 0: inflows (sell, dividend, terminal market value)

    Decimal/float boundary: ``pyxirr`` requires IEEE-754 ``float`` inputs and
    returns a ``float``. We coerce here with ``float(cf[1])`` and convert
    back via ``Decimal(str(round(result, 6)))``. For portfolio values within
    ~15 significant digits this is safe; the round at 6 decimal places is
    the canonical XIRR display precision (annualised return).
    """
    if len(cash_flows) < 2:
        return None

    dates = [cf[0] for cf in cash_flows]
    if len(set(dates)) < 2:
        return None

    if cash_flows[-1][1] <= Decimal("0"):
        return None

    try:
        from pyxirr import xirr as _xirr
        result = _xirr(
            [cf[0] for cf in cash_flows],
            [float(cf[1]) for cf in cash_flows],  # required: pyxirr is float-only
        )
        if result is None or not isinstance(result, float):
            return None
        if math.isnan(result) or math.isinf(result):
            return None
        return Decimal(str(round(result, 6)))
    except Exception:
        return None
