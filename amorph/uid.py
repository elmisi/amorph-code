from __future__ import annotations

import json
import sys
import uuid as _uuid
from typing import Any, Dict, List, Tuple, Iterator


def gen_uid(prefix: str = "amr") -> str:
    return f"{prefix}_{_uuid.uuid4().hex[:8]}"


def iter_statements(program: List[Dict[str, Any]]) -> Iterator[Tuple[List[Dict[str, Any]], int, Dict[str, Any]]]:
    for idx, stmt in enumerate(program):
        yield program, idx, stmt


def add_uids(program: List[Dict[str, Any]], deep: bool = False) -> int:
    """Add missing 'id' to statements and function defs. If deep=True, also within function bodies and nested blocks.
    Returns count added.
    """
    def add_stmt_ids(block: List[Dict[str, Any]]) -> int:
        cnt = 0
        for stmt in block:
            if "id" not in stmt:
                stmt["id"] = gen_uid()
                cnt += 1
            # recurse into defs and control blocks
            if "def" in stmt and isinstance(stmt["def"], dict):
                spec = stmt["def"]
                if "id" not in spec:
                    spec["id"] = gen_uid("fn")
                    cnt += 1
                if deep:
                    body = spec.get("body", [])
                    if isinstance(body, list):
                        cnt += add_stmt_ids(body)
            if deep and "if" in stmt and isinstance(stmt["if"], dict):
                thenb = stmt["if"].get("then")
                elseb = stmt["if"].get("else")
                if isinstance(thenb, list):
                    cnt += add_stmt_ids(thenb)
                if isinstance(elseb, list):
                    cnt += add_stmt_ids(elseb)
        return cnt

    return add_stmt_ids(program)


def find_stmt_by_id(program: List[Dict[str, Any]], target_id: str) -> Tuple[List[Dict[str, Any]], int]:
    for parent, idx, stmt in iter_statements(program):
        if stmt.get("id") == target_id:
            return parent, idx
    raise KeyError(f"Statement id not found: {target_id}")


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: Any, indent: int = 2, sort_keys: bool = True) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, sort_keys=sort_keys)
        f.write("\n")


def main_add_uid(argv: List[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="amorph add-uid")
    p.add_argument("path")
    p.add_argument("-i", "--in-place", action="store_true")
    p.add_argument("--deep", action="store_true", help="Add IDs recursively in bodies and blocks")
    args = p.parse_args(argv)

    data = read_json(args.path)
    if not isinstance(data, list):
        print("Error: program must be a list", file=sys.stderr)
        return 1
    added = add_uids(data, deep=args.deep)
    if args.in_place:
        write_json(args.path, data)
    else:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False, sort_keys=True)
        print()
    print(f"Added {added} uid(s)", file=sys.stderr)
    return 0
