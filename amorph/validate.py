from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple
from dataclasses import dataclass

from .errors import AmorphValidationError
from .op_registry import check_arity, normalize


@dataclass
class ValidationIssue:
    code: str
    message: str
    path: str
    severity: str = "error"  # error|warning
    hint: str | None = None


FIXED_ARITY = {
    "not": 1,
    "len": 1,
    "get": 2,
    "has": 2,
    "int": 1,
}

RANGE_ARITY = {
    "range": (1, 2),
    "input": (0, 1),
}


def _normalize_op(op: str) -> str:
    return op.split(".")[-1]


def _collect_functions(program: List[Dict[str, Any]]) -> tuple[Set[str], Set[str]]:
    names: Set[str] = set()
    ids: Set[str] = set()
    for stmt in program:
        if "def" in stmt and isinstance(stmt["def"], dict):
            spec = stmt["def"]
            n = spec.get("name")
            if isinstance(n, str):
                names.add(n)
            i = spec.get("id")
            if isinstance(i, str):
                ids.add(i)
    return names, ids


def _walk_expr(expr: Any, fn) -> Any:
    if isinstance(expr, list):
        for e in expr:
            _walk_expr(e, fn)
        return expr
    if isinstance(expr, dict):
        for k, v in expr.items():
            _walk_expr(v, fn)
        fn(expr)
        return expr
    return expr


def validate_program(program: Any) -> None:
    if isinstance(program, dict) and "program" in program:
        program = program["program"]
    if not isinstance(program, list):
        raise AmorphValidationError("Program must be a list or a {program:[...]} object")

    fn_names, fn_ids = _collect_functions(program)

    def check_node(node: Dict[str, Any]) -> None:
        # calls
        if "call" in node and isinstance(node["call"], dict):
            c = node["call"]
            if "id" in c:
                i = c["id"]
                if not isinstance(i, str) or i not in fn_ids:
                    raise AmorphValidationError(f"Unknown function id in call: {i}")
            elif "name" in c:
                n = c["name"]
                if not isinstance(n, str) or n not in fn_names:
                    # allow forward refs; still check that name is defined somewhere
                    if n not in fn_names:
                        raise AmorphValidationError(f"Unknown function name in call: {n}")

        # operators arity (structural)
        if len(node) == 1 and not ("var" in node or "call" in node):
            op, val = next(iter(node.items()))
            cnt = len(val) if isinstance(val, list) else 1
            if not check_arity(op, cnt):
                name = normalize(op)
                raise AmorphValidationError(f"Operator {op} invalid arity: {cnt}")

    for stmt in program:
        if not isinstance(stmt, dict):
            raise AmorphValidationError("Statements must be objects")
        # walk immediate fields that are expressions or blocks
        if "let" in stmt and isinstance(stmt["let"], dict):
            v = stmt["let"].get("value")
            if v is not None:
                _walk_expr(v, check_node)
        if "set" in stmt and isinstance(stmt["set"], dict):
            v = stmt["set"].get("value")
            if v is not None:
                _walk_expr(v, check_node)
        if "return" in stmt:
            _walk_expr(stmt["return"], check_node)
        if "expr" in stmt:
            _walk_expr(stmt["expr"], check_node)
        if "if" in stmt and isinstance(stmt["if"], dict):
            c = stmt["if"].get("cond")
            if c is not None:
                _walk_expr(c, check_node)
            for key in ("then", "else"):
                block = stmt["if"].get(key)
                if isinstance(block, list):
                    for s in block:
                        if "return" in s:
                            _walk_expr(s["return"], check_node)
                        if "expr" in s:
                            _walk_expr(s["expr"], check_node)
                        if "let" in s:
                            v = s["let"].get("value")
                            if v is not None:
                                _walk_expr(v, check_node)
        if "def" in stmt and isinstance(stmt["def"], dict):
            body = stmt["def"].get("body", [])
            if isinstance(body, list):
                for s in body:
                    if "return" in s:
                        _walk_expr(s["return"], check_node)
                    if "expr" in s:
                        _walk_expr(s["expr"], check_node)
                    if "let" in s:
                        v = s["let"].get("value")
                        if v is not None:
                            _walk_expr(v, check_node)


def validate_program_report(program: Any, prefer_id: bool = False) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    def push(code: str, msg: str, path: List[Tuple[str, int]]):
        issues.append(ValidationIssue(code=code, message=msg, path=_path_to_string(path)))

    # unwrap
    header = None
    if isinstance(program, dict) and "program" in program:
        header = program
        program = header.get("program")
    if not isinstance(program, list):
        issues.append(ValidationIssue(code="E_PROGRAM_SHAPE", message="Program must be a list or {program:[...]} wrapper", path="/"))
        return issues

    fn_names, fn_ids = _collect_functions(program)
    # Build name->id map to support prefer_id warnings for unique names
    name_to_id: Dict[str, str] = {}
    name_dups: Dict[str, int] = {}
    for stmt in program:
        if "def" in stmt and isinstance(stmt["def"], dict):
            d = stmt["def"]
            n = d.get("name")
            i = d.get("id")
            if isinstance(n, str) and isinstance(i, str):
                if n in name_to_id and name_to_id[n] != i:
                    name_dups[n] = name_dups.get(n, 1) + 1
                else:
                    name_to_id[n] = i

    def check_expr(node: Any, path: List[Tuple[str, int]]):
        if isinstance(node, dict):
            if "call" in node and isinstance(node["call"], dict):
                c = node["call"]
                if "id" in c:
                    i = c["id"]
                    if not isinstance(i, str) or i not in fn_ids:
                        push("E_UNKNOWN_FUNC_ID", f"Unknown function id in call: {i}", path)
                elif "name" in c:
                    n = c["name"]
                    if not isinstance(n, str) or n not in fn_names:
                        push("E_UNKNOWN_FUNC_NAME", f"Unknown function name in call: {n}", path)
                    elif prefer_id and n in name_to_id and n not in name_dups:
                        issues.append(ValidationIssue(code="W_PREFER_ID", message=f"Call by name can use id {name_to_id[n]}", path=_path_to_string(path), severity="warning", hint="Run: amorph migrate-calls <file> --to=id"))
            if len(node) == 1 and not ("var" in node or "call" in node):
                op, val = next(iter(node.items()))
                cnt = len(val) if isinstance(val, list) else 1
                if not check_arity(op, cnt):
                    push("E_OP_ARITY", f"Operator {op} invalid arity: {cnt}", path)
            for k, v in node.items():
                check_expr(v, path + [(k, -1)])
        elif isinstance(node, list):
            for idx, x in enumerate(node):
                check_expr(x, path + [("$", idx)])

    mixed_style = False
    saw_name = False
    saw_id = False
    for i, stmt in enumerate(program):
        p = [("$", i)]
        if not isinstance(stmt, dict):
            push("E_STMT_SHAPE", "Statement must be object", p)
            continue
        # detect mixed call styles at top-level traversal
        def _mark_calls(node: Any):
            nonlocal saw_name, saw_id
            if isinstance(node, dict):
                if "call" in node and isinstance(node["call"], dict):
                    c = node["call"]
                    if "id" in c:
                        saw_id = True
                    if "name" in c:
                        saw_name = True
                for v in node.values():
                    _mark_calls(v)
            elif isinstance(node, list):
                for x in node:
                    _mark_calls(x)

        _mark_calls(stmt)
        if "let" in stmt and isinstance(stmt["let"], dict):
            v = stmt["let"].get("value")
            if v is not None:
                check_expr(v, p + [("let", -1), ("value", -1)])
        if "set" in stmt and isinstance(stmt["set"], dict):
            v = stmt["set"].get("value")
            if v is not None:
                check_expr(v, p + [("set", -1), ("value", -1)])
        if "return" in stmt:
            check_expr(stmt["return"], p + [("return", -1)])
        if "expr" in stmt:
            check_expr(stmt["expr"], p + [("expr", -1)])
        if "if" in stmt and isinstance(stmt["if"], dict):
            c = stmt["if"].get("cond")
            if c is not None:
                check_expr(c, p + [("if", -1), ("cond", -1)])
            for key in ("then", "else"):
                block = stmt["if"].get(key)
                if isinstance(block, list):
                    for j, s in enumerate(block):
                        q = p + [("if", -1), (key, -1), ("$", j)]
                        if "return" in s:
                            check_expr(s["return"], q + [("return", -1)])
                        if "expr" in s:
                            check_expr(s["expr"], q + [("expr", -1)])
                        if "let" in s:
                            v = s["let"].get("value")
                            if v is not None:
                                check_expr(v, q + [("let", -1), ("value", -1)])
        if "def" in stmt and isinstance(stmt["def"], dict):
            d = stmt["def"]
            body = d.get("body", [])
            fid = d.get("id") or d.get("name") or "?"
            if isinstance(body, list):
                for j, s in enumerate(body):
                    q = [("fn", fid), ("body", j)]
                    if "return" in s:
                        check_expr(s["return"], q + [("return", -1)])
                    if "expr" in s:
                        check_expr(s["expr"], q + [("expr", -1)])
                    if "let" in s:
                        v = s["let"].get("value")
                        if v is not None:
                            check_expr(v, q + [("let", -1), ("value", -1)])
    if saw_name and saw_id:
        issues.append(ValidationIssue(code="W_MIXED_CALL_STYLE", message="Mixed call styles (name and id) found", path="/", severity="warning", hint="Unify with: amorph migrate-calls <file> --to=id"))

    return issues


def _path_to_string(path: List[Tuple[str, int]]) -> str:
    parts: List[str] = []
    for key, idx in path:
        if key == "$":
            parts.append(f"$[{idx}]")
        elif key == "fn":
            parts.append(f"fn[{idx}]")
        else:
            parts.append(key)
    return "/" + "/".join(parts)
