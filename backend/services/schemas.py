"""Tolerant field types: LLMs often return "250 kcal" instead of 250, or a string instead of a list."""
import re
from typing import Annotated, Optional

from pydantic import BeforeValidator


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", ""))
        return float(m.group()) if m else None
    return None


def _list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    if isinstance(v, (list, tuple)):
        out = []
        for item in v:
            if isinstance(item, dict):
                out.append(", ".join(str(x) for x in item.values() if x not in (None, "")))
            elif item not in (None, ""):
                out.append(str(item))
        return out
    return [str(v)]


def _str(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x) for x in v)
    return str(v)


Num = Annotated[Optional[float], BeforeValidator(_num)]
StrList = Annotated[list[str], BeforeValidator(_list)]
Txt = Annotated[str, BeforeValidator(_str)]


def clamp_pct(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    if 0 <= v <= 1:  # model gave a fraction
        v = v * 100
    return max(0.0, min(100.0, round(v, 1)))
