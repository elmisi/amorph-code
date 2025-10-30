from __future__ import annotations

from typing import Dict, Tuple, Union


# AritySpec = int (fixed) or tuple(min,max or None for unbounded)
AritySpec = Union[int, Tuple[int, int]]


# Registry: normalized op name (suffix without namespace) -> arity spec
OP_ARITY: Dict[str, AritySpec] = {
    # arithmetic
    "add": (2, 999999),
    "sub": (2, 999999),
    "mul": (2, 999999),
    "div": (2, 999999),
    "mod": 2,
    "pow": 2,
    # comparisons
    "eq": (2, 999999),
    "ne": (2, 999999),
    "lt": (2, 999999),
    "le": (2, 999999),
    "gt": (2, 999999),
    "ge": (2, 999999),
    # logic
    "not": 1,
    "and": (0, 999999),
    "or": (0, 999999),
    # collections
    "list": (0, 999999),
    "concat": (2, 999999),
    "len": 1,
    "get": 2,
    "has": 2,
    # sequences/io/convert
    "range": (1, 2),
    "input": (0, 1),
    "int": 1,
}


def normalize(op: str) -> str:
    return op.split(".")[-1]


def check_arity(op: str, arg_count: int) -> bool:
    name = normalize(op)
    spec = OP_ARITY.get(name)
    if spec is None:
        return True  # unknown operators allowed for extensibility
    if isinstance(spec, int):
        return arg_count == spec
    lo, hi = spec
    return (arg_count >= lo) and (arg_count <= hi)

