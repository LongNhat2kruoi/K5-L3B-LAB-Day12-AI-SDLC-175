"""Độ tươi (contract v1.2): lưu bằng Fraction, bật khi và chỉ khi tuning có khối 'freshness'."""

import math
from fractions import Fraction

from .errors import BadInput

GRID = 240  # 240 đơn vị mỗi điểm tươi: 2 đơn vị/tick ở gather, 1 đơn vị/tick ở quán


def enabled(tuning) -> bool:
    return isinstance(tuning, dict) and "freshness" in tuning


def parse(v) -> Fraction:
    """Số JSON -> Fraction trong [0, 100], nắn về lưới 1/240 khi sai số < 1e-9 (đơn vị đã nhân 240)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise BadInput(f"fresh phải là số, đang là {v!r}")
    if isinstance(v, float) and not math.isfinite(v):
        raise BadInput(f"fresh phải hữu hạn, đang là {v!r}")
    f = Fraction(str(v))
    scaled = f * GRID
    if abs(scaled - round(scaled)) < Fraction(1, 1_000_000_000):
        f = Fraction(round(scaled), GRID)
    if not (0 <= f <= 100):
        raise BadInput(f"fresh phải trong [0, 100], đang là {v!r}")
    return f


def per_tick(tuning, where) -> Fraction:
    """Hao mỗi tick ở 'gather' hoặc 'quan' (decay_per_s / 60)."""
    if where not in ("gather", "quan"):
        raise ValueError(where)
    return Fraction(str(tuning["freshness"][f"{where}_decay_per_s"])) / 60


def threshold(tuning) -> Fraction:
    return Fraction(str(tuning["freshness"]["spoiled_below"]))


def to_json(f) -> float:
    return float(f)
