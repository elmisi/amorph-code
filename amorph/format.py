from __future__ import annotations

import json
from typing import Any


def fmt_dump(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)


KEYMAP = {
    # statements and fields
    "let": "l",
    "set": "s",
    "def": "d",
    "if": "i",
    "then": "t",
    "else": "e",
    "return": "r",
    "print": "p",
    "expr": "x",
    "var": "v",
    "call": "c",
    "name": "n",
    "value": "val",
    "params": "pa",
    "body": "b",
    "cond": "co",
    "id": "id",
}

REV_KEYMAP = {v: k for k, v in KEYMAP.items()}


def _transform_keys(obj: Any, mapping: dict[str, str]) -> Any:
    if isinstance(obj, dict):
        return {mapping.get(k, k): _transform_keys(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_transform_keys(x, mapping) for x in obj]
    return obj


def minify_keys(program: Any) -> Any:
    return _transform_keys(program, KEYMAP)


def unminify_keys(program: Any) -> Any:
    return _transform_keys(program, REV_KEYMAP)

