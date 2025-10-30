from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from .uid import add_uids, read_json, write_json


def build_fn_maps(program: List[Dict[str, Any]]):
    by_name: Dict[str, str] = {}
    dup_names: Dict[str, int] = {}
    for stmt in program:
        d = stmt.get("def") if isinstance(stmt, dict) else None
        if isinstance(d, dict):
            name = d.get("name")
            fid = d.get("id")
            if isinstance(name, str) and isinstance(fid, str):
                if name in by_name and by_name[name] != fid:
                    dup_names[name] = dup_names.get(name, 1) + 1
                else:
                    by_name[name] = fid
    return by_name, dup_names


def migrate_calls_to_id(program: List[Dict[str, Any]]) -> int:
    add_uids(program, deep=True)
    by_name, dup_names = build_fn_maps(program)
    if dup_names:
        # ambiguous names exist; we will skip those names
        pass
    changed = 0

    def visit(node: Any) -> Any:
        nonlocal changed
        if isinstance(node, dict):
            if "call" in node and isinstance(node["call"], dict):
                c = node["call"]
                if "id" in c:
                    return node
                n = c.get("name")
                if isinstance(n, str) and n in by_name and n not in dup_names:
                    newc = dict(c)
                    newc["id"] = by_name[n]
                    newc.pop("name", None)
                    changed += 1
                    return {"call": newc}
        if isinstance(node, list):
            return [visit(x) for x in node]
        if isinstance(node, dict):
            return {k: visit(v) for k, v in node.items()}
        return node

    # transform program statements
    for i, stmt in enumerate(program):
        program[i] = visit(stmt)
    return changed


def main_migrate_calls(argv: List[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="amorph migrate-calls")
    p.add_argument("program")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--to", choices=["id", "name"], default="id")
    args = p.parse_args(argv)

    prog = read_json(args.program)
    plist = prog["program"] if isinstance(prog, dict) and "program" in prog else prog
    if not isinstance(plist, list):
        print("Error: program must be list or wrapper", file=sys.stderr)
        return 1
    before = json.dumps(plist, ensure_ascii=False)
    if args.to == "id":
        changed = migrate_calls_to_id(plist)
    else:
        changed = migrate_calls_to_name(plist)
    if args.dry_run:
        print(json.dumps({"changed": changed, "preview": prog}, ensure_ascii=False, indent=2))
        return 0
    if isinstance(prog, dict):
        prog["program"] = plist
    write_json(args.program, prog)
    print(json.dumps({"changed": changed}))
    return 0


def migrate_calls_to_name(program: List[Dict[str, Any]]) -> int:
    add_uids(program, deep=True)
    # build id->name map
    by_id: Dict[str, str] = {}
    for stmt in program:
        d = stmt.get("def") if isinstance(stmt, dict) else None
        if isinstance(d, dict):
            fid = d.get("id")
            name = d.get("name")
            if isinstance(fid, str) and isinstance(name, str):
                by_id[fid] = name
    changed = 0

    def visit(node: Any) -> Any:
        nonlocal changed
        if isinstance(node, dict):
            if "call" in node and isinstance(node["call"], dict):
                c = node["call"]
                if "id" in c and c["id"] in by_id:
                    newc = dict(c)
                    newc["name"] = by_id[newc["id"]]
                    newc.pop("id", None)
                    changed += 1
                    return {"call": newc}
        if isinstance(node, list):
            return [visit(x) for x in node]
        if isinstance(node, dict):
            return {k: visit(v) for k, v in node.items()}
        return node

    for i, stmt in enumerate(program):
        program[i] = visit(stmt)
    return changed
