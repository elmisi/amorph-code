from __future__ import annotations

import copy
import json
import sys
from typing import Any, Dict, List, Tuple, Union

from .uid import add_uids, find_stmt_by_id, read_json, write_json


class EditError(Exception):
    def __init__(self, code: str, message: str, path: str | None = None):
        super().__init__(message)
        self.code = code
        self.path = path

    def to_json(self) -> Dict[str, Any]:
        return {"code": self.code, "message": str(self), "path": self.path}


def deep_walk_expr(expr: Any, fn) -> Any:
    if isinstance(expr, list):
        return [deep_walk_expr(e, fn) for e in expr]
    if isinstance(expr, dict):
        # do not treat statement-level metadata here; this walks expressions only
        new = {}
        for k, v in expr.items():
            new[k] = deep_walk_expr(v, fn)
        return fn(new)
    return fn(expr)


def op_add_function(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> None:
    name = spec.get("name")
    params = spec.get("params", [])
    body = spec.get("body", [])
    fn_id = spec.get("id")
    if not isinstance(name, str) or not isinstance(params, list) or not isinstance(body, list):
        raise EditError("E_BAD_SPEC", "add_function requires {name:str, params:list, body:list}")
    stmt: Dict[str, Any] = {"def": {"name": name, "params": params, "body": body}}
    if fn_id:
        stmt["def"]["id"] = fn_id
    program.append(stmt)


def op_rename_function(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> int:
    fn_id = spec.get("id")
    old = spec.get("from")
    new = spec.get("to")
    if not isinstance(new, str):
        raise EditError("E_BAD_SPEC", "rename_function requires {to:str} and either {id} or {from}")

    targets: List[Dict[str, Any]] = []
    if isinstance(fn_id, str):
        for stmt in program:
            if "def" in stmt and isinstance(stmt["def"], dict) and stmt["def"].get("id") == fn_id:
                targets.append(stmt["def"])
    elif isinstance(old, str):
        for stmt in program:
            if "def" in stmt and isinstance(stmt["def"], dict) and stmt["def"].get("name") == old:
                targets.append(stmt["def"])
        if len(targets) > 1:
            raise EditError("E_AMBIGUOUS", f"multiple functions named '{old}' found; use id")
    else:
        raise EditError("E_BAD_SPEC", "rename_function requires id or from")

    if not targets:
        raise EditError("E_NOT_FOUND", "function not found")

    changed = 0
    # decide which name to replace in call-sites
    name_old_for_calls: Union[str, None] = old if isinstance(old, str) else (targets[0].get("name") if targets else None)
    for t in targets:
        # rename def itself
        t["name"] = new
        changed += 1

    # update call sites
    def replace_calls(node: Any) -> Any:
        if isinstance(node, dict) and "call" in node:
            c = node["call"]
            if not isinstance(c, dict):
                return node
            # if calls by id match, keep; if calls by name match old_name, rename
            if c.get("id") and isinstance(fn_id, str) and c.get("id") == fn_id:
                return node
            if name_old_for_calls is not None and c.get("name") == name_old_for_calls:
                c = copy.deepcopy(c)
                c["name"] = new
                return {"call": c}
        return node

    for stmt in program:
        # update inside statement bodies
        if "def" in stmt:
            body = stmt["def"].get("body", [])
            for s in body:
                if "return" in s:
                    s["return"] = deep_walk_expr(s["return"], replace_calls)
                if "expr" in s:
                    s["expr"] = deep_walk_expr(s["expr"], replace_calls)
                if "let" in s:
                    v = s["let"].get("value")
                    if v is not None:
                        s["let"]["value"] = deep_walk_expr(v, replace_calls)
                if "set" in s:
                    v = s["set"].get("value")
                    if v is not None:
                        s["set"]["value"] = deep_walk_expr(v, replace_calls)
                if "if" in s:
                    cond = s["if"].get("cond")
                    if cond is not None:
                        s["if"]["cond"] = deep_walk_expr(cond, replace_calls)
        # also update top-level statements
        if "let" in stmt:
            v = stmt["let"].get("value")
            if v is not None:
                stmt["let"]["value"] = deep_walk_expr(v, replace_calls)
        if "expr" in stmt:
            stmt["expr"] = deep_walk_expr(stmt["expr"], replace_calls)
        if "return" in stmt:
            stmt["return"] = deep_walk_expr(stmt["return"], replace_calls)

    return changed


def op_insert_before(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> None:
    node = spec.get("node")
    if not isinstance(node, dict):
        raise EditError("E_BAD_SPEC", "insert_before requires {node:object} and target or path")
    if "target" in spec:
        target_id = spec.get("target")
        if not isinstance(target_id, str):
            raise EditError("E_BAD_SPEC", "insert_before.target must be string")
        parent, idx = find_stmt_by_id(program, target_id)
        parent.insert(idx, node)
        return
    if "path" in spec:
        parent, idx = find_by_path(program, spec["path"])
        parent.insert(idx, node)
        return
    raise EditError("E_BAD_SPEC", "insert_before requires target or path")


def op_insert_after(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> None:
    node = spec.get("node")
    if not isinstance(node, dict):
        raise EditError("E_BAD_SPEC", "insert_after requires {node:object} and target or path")
    if "target" in spec:
        target_id = spec.get("target")
        if not isinstance(target_id, str):
            raise EditError("E_BAD_SPEC", "insert_after.target must be string")
        parent, idx = find_stmt_by_id(program, target_id)
        parent.insert(idx + 1, node)
        return
    if "path" in spec:
        parent, idx = find_by_path(program, spec["path"])
        parent.insert(idx + 1, node)
        return
    raise EditError("E_BAD_SPEC", "insert_after requires target or path")


def apply_edits(program: List[Dict[str, Any]], edits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply edits. Returns a report with counts.
    Raises EditError on failure (transactional behavior is the responsibility of the caller).
    """
    report = {"applied": 0, "details": []}
    for i, edit in enumerate(edits):
        op = edit.get("op")
        spec = {k: v for k, v in edit.items() if k != "op"}
        if op == "add_function":
            op_add_function(program, spec)
            report["details"].append({"op": op, "index": i})
            report["applied"] += 1
        elif op == "rename_function":
            changed = op_rename_function(program, spec)
            report["details"].append({"op": op, "index": i, "changed": changed})
            report["applied"] += 1
        elif op == "insert_before":
            op_insert_before(program, spec)
            report["details"].append({"op": op, "index": i})
            report["applied"] += 1
        elif op == "insert_after":
            op_insert_after(program, spec)
            report["details"].append({"op": op, "index": i})
            report["applied"] += 1
        elif op == "replace_call":
            changed = op_replace_call(program, spec)
            report["details"].append({"op": op, "index": i, "changed": changed})
            report["applied"] += 1
        elif op == "delete_node":
            op_delete_node(program, spec)
            report["details"].append({"op": op, "index": i})
            report["applied"] += 1
        elif op == "rename_variable":
            # New refactoring operation
            from .refactor import op_rename_variable
            changed = op_rename_variable(program, spec)
            report["details"].append({"op": op, "index": i, "changed": changed})
            report["applied"] += 1
        elif op == "extract_function":
            # New refactoring operation
            from .refactor import op_extract_function
            op_extract_function(program, spec)
            report["details"].append({"op": op, "index": i})
            report["applied"] += 1
        else:
            raise EditError("E_UNKNOWN_OP", f"Unknown op: {op}")
    return report


def main_edit(argv: List[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="amorph edit")
    p.add_argument("program")
    p.add_argument("edits")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json-errors", action="store_true")
    args = p.parse_args(argv)

    try:
        program = read_json(args.program)
        edits = read_json(args.edits)
        if not isinstance(program, list) or not isinstance(edits, list):
            raise EditError("E_BAD_INPUT", "program and edits must be JSON arrays")
        # ensure uids exist for addressable insertions
        add_uids(program, deep=True)
        snapshot = copy.deepcopy(program)
        # optional schema validation if jsonschema available
        try:
            from jsonschema import Draft202012Validator as _V
            schema = read_json("schema/edits-0.1.schema.json")
            _V(schema).validate(edits)
        except Exception:
            pass
        report = apply_edits(program, edits)
        if args.dry_run:
            diff = {"report": report, "preview": program}
            json.dump(diff, sys.stdout, indent=2, ensure_ascii=False, sort_keys=True)
            print()
            return 0
        else:
            write_json(args.program, program)
            print(json.dumps(report))
            return 0
    except EditError as e:
        if args.json_errors:
            print(json.dumps({"error": e.to_json()}))
        else:
            print(f"Error [{e.code}]: {e}", file=sys.stderr)
        return 1


def parse_path(path: str) -> List[Union[Tuple[str, int], str]]:
    if not isinstance(path, str) or not path.startswith("/"):
        raise EditError("E_BAD_PATH", "path must start with '/'")
    segs = [s for s in path.split("/") if s]
    out: List[Union[Tuple[str, int], str]] = []
    for s in segs:
        if s.startswith("$[") and s.endswith("]"):
            num = s[2:-1]
            try:
                idx = int(num)
            except ValueError:
                raise EditError("E_BAD_PATH", f"invalid index in path: {s}")
            out.append(("$", idx))
        else:
            out.append(s)
    return out


def find_by_path(program: List[Dict[str, Any]], path: str) -> Tuple[List[Any], int]:
    toks = parse_path(path)
    cur: Any = program
    for i, tok in enumerate(toks):
        last = i == len(toks) - 1
        if isinstance(tok, tuple) and tok[0] == "$":
            if not isinstance(cur, list):
                raise EditError("E_BAD_PATH", f"expected list at step {i}")
            idx = tok[1]
            if last:
                return cur, idx
            try:
                cur = cur[idx]
            except Exception:
                raise EditError("E_BAD_PATH", f"index out of range at step {i}")
        else:
            # dict key
            if not isinstance(cur, dict):
                raise EditError("E_BAD_PATH", f"expected object at step {i}")
            key = tok  # type: ignore[assignment]
            if last:
                raise EditError("E_BAD_PATH", "path must end with array index segment like $[n]")
            try:
                cur = cur[key]  # type: ignore[index]
            except Exception:
                raise EditError("E_BAD_PATH", f"key missing at step {i}: {key}")
    raise EditError("E_BAD_PATH", "empty path")


def op_replace_call(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> int:
    """Replace calls that match by name or id; can set new name/id and/or replace args.
    spec: { match:{name?|id?}, set:{name?|id?, args?} }
    """
    match = spec.get("match", {})
    setv = spec.get("set", {})
    if not isinstance(match, dict) or not isinstance(setv, dict):
        raise EditError("E_BAD_SPEC", "replace_call requires {match:{}, set:{}}")
    m_name = match.get("name")
    m_id = match.get("id")
    if not isinstance(m_name, str) and not isinstance(m_id, str):
        raise EditError("E_BAD_SPEC", "match must include name or id")

    changed = 0

    def replace(node: Any) -> Any:
        nonlocal changed
        if isinstance(node, dict) and "call" in node and isinstance(node["call"], dict):
            c = node["call"]
            if (isinstance(m_id, str) and c.get("id") == m_id) or (isinstance(m_name, str) and c.get("name") == m_name):
                c = dict(c)
                if "name" in setv:
                    c["name"] = setv["name"]
                    c.pop("id", None)
                if "id" in setv:
                    c["id"] = setv["id"]
                    c.pop("name", None)
                if "args" in setv:
                    c["args"] = setv["args"]
                changed += 1
                return {"call": c}
        return node

    # walk program
    for stmt in program:
        # top level
        if "let" in stmt:
            v = stmt["let"].get("value")
            if v is not None:
                stmt["let"]["value"] = deep_walk_expr(v, replace)
        if "expr" in stmt:
            stmt["expr"] = deep_walk_expr(stmt["expr"], replace)
        if "return" in stmt:
            stmt["return"] = deep_walk_expr(stmt["return"], replace)
        if "def" in stmt:
            body = stmt["def"].get("body", [])
            for s in body:
                if "let" in s:
                    v = s["let"].get("value")
                    if v is not None:
                        s["let"]["value"] = deep_walk_expr(v, replace)
                if "expr" in s:
                    s["expr"] = deep_walk_expr(s["expr"], replace)
                if "return" in s:
                    s["return"] = deep_walk_expr(s["return"], replace)
                if "if" in s:
                    cond = s["if"].get("cond")
                    if cond is not None:
                        s["if"]["cond"] = deep_walk_expr(cond, replace)
    return changed


def op_delete_node(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> None:
    if "target" in spec:
        t = spec.get("target")
        if not isinstance(t, str):
            raise EditError("E_BAD_SPEC", "delete_node.target must be string")
        parent, idx = find_stmt_by_id(program, t)
        parent.pop(idx)
        return
    if "path" in spec:
        parent, idx = find_by_path(program, spec["path"])
        parent.pop(idx)
        return
    raise EditError("E_BAD_SPEC", "delete_node requires target or path")
