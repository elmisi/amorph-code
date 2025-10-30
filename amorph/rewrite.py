from __future__ import annotations

import copy
import json
import sys
from typing import Any, Dict, List, Tuple
try:
    import jmespath  # type: ignore
except Exception:  # pragma: no cover
    jmespath = None

from .edits import deep_walk_expr
from .uid import add_uids, read_json, write_json


def is_placeholder(x: Any) -> bool:
    return isinstance(x, str) and len(x) > 1 and x.startswith("$")


def is_star_placeholder(x: Any) -> bool:
    return isinstance(x, str) and len(x) > 2 and x.startswith("$*")


def match(node: Any, pattern: Any, env: Dict[str, Any]) -> bool:
    # placeholder binds any subtree
    if is_placeholder(pattern):
        name = pattern[1:]
        if name in env:
            # must equal previously matched subtree
            return _equal_ast(env[name], node)
        env[name] = node
        return True
    # both scalars
    if not isinstance(pattern, (list, dict)):
        return node == pattern
    # list
    if isinstance(pattern, list):
        if not isinstance(node, list):
            return False
        # variable-length wildcard: single star placeholder matches the entire list
        if len(pattern) == 1 and is_star_placeholder(pattern[0]):
            name = pattern[0][2:]
            if name in env:
                return env[name] == node
            env[name] = node
            return True
        if len(pattern) != len(node):
            return False
        for p_i, n_i in zip(pattern, node):
            if not match(n_i, p_i, env):
                return False
        return True
    # dict: require all pattern keys exist and match
    if not isinstance(node, dict):
        return False
    for k, v in pattern.items():
        if k not in node:
            return False
        if not match(node[k], v, env):
            return False
    return True


def _equal_ast(a: Any, b: Any) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(_equal_ast(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(_equal_ast(a[k], b[k]) for k in a.keys())
    return a == b


def substitute(template: Any, env: Dict[str, Any]) -> Any:
    if is_placeholder(template):
        name = template[1:]
        return env.get(name)
    if isinstance(template, list):
        out: List[Any] = []
        for x in template:
            if is_star_placeholder(x):
                name = x[2:]
                vals = env.get(name, [])
                if isinstance(vals, list):
                    out.extend(vals)
                else:
                    out.append(vals)
            else:
                out.append(substitute(x, env))
        return out
    if isinstance(template, dict):
        return {k: substitute(v, env) for k, v in template.items()}
    return template


def _passes_select(node: Any, rule: Dict[str, Any], env: Dict[str, Any], root: Any) -> bool:
    # Optional JMESPath guard(s)
    sel = rule.get("select")
    sels = rule.get("where")
    prog_sel = rule.get("program_select")
    prog_sels = rule.get("program_where")
    where_ph: Dict[str, str] = rule.get("where_placeholders", {}) if isinstance(rule.get("where_placeholders"), dict) else {}
    def _truthy(res: Any) -> bool:
        if res is None:
            return False
        if res is False:
            return False
        if res == [] or res == {}:
            return False
        return True
    if (sel or sels or prog_sel or prog_sels or where_ph) and jmespath is None:
        return False
    if jmespath is not None:
        try:
            if isinstance(sel, str):
                if not _truthy(jmespath.search(sel, node)):
                    return False
            if isinstance(sels, list):
                for expr in sels:
                    if isinstance(expr, str):
                        if not _truthy(jmespath.search(expr, node)):
                            return False
            if isinstance(prog_sel, str):
                if not _truthy(jmespath.search(prog_sel, root)):
                    return False
            if isinstance(prog_sels, list):
                for expr in prog_sels:
                    if isinstance(expr, str):
                        if not _truthy(jmespath.search(expr, root)):
                            return False
            # placeholder-specific conditions
            for ph, expr in where_ph.items():
                if isinstance(ph, str) and isinstance(expr, str) and ph in env:
                    if not _truthy(jmespath.search(expr, env[ph])):
                        return False
        except Exception:
            return False
    return True


def rewrite_node(node: Any, rules: List[Dict[str, Any]], changed: List[int], root: Any, scopes: List[Dict[str, Any]] | None = None) -> Any:
    # First, attempt to rewrite the node itself
    for i, rule in enumerate(rules):
        env: Dict[str, Any] = {}
        pat = rule.get("match")
        rep = rule.get("replace")
        if pat is None or rep is None:
            continue
        # If rule defines apply_to (JMESPath), restrict rewrites to those nodes
        allowed: List[Any] | None = None
        if jmespath is not None and isinstance(rule.get("apply_to"), str):
            try:
                selected = jmespath.search(rule["apply_to"], root)
                if isinstance(selected, list):
                    allowed = selected
                else:
                    allowed = [selected] if selected is not None else []
            except Exception:
                allowed = []
        elif jmespath is not None and isinstance(rule.get("apply_to"), list):
            allowed = []
            for expr in rule["apply_to"]:
                if isinstance(expr, str):
                    try:
                        selected = jmespath.search(expr, root)
                        if isinstance(selected, list):
                            allowed.extend(selected)
                        elif selected is not None:
                            allowed.append(selected)
                    except Exception:
                        continue
        # Note: if jmespath is None and apply_to is set, skip the rule application
        if (rule.get("apply_to") and jmespath is None):
            continue

        within_scope = True if allowed is None else any(_equal_ast(node, sel) for sel in allowed)
        if within_scope and match(node, pat, env) and _passes_select(node, rule, env, root):
            changed[0] += 1
            return substitute(rep, env)
    # Otherwise, traverse recursively
    if isinstance(node, list):
        return [rewrite_node(x, rules, changed, root) for x in node]
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            out[k] = rewrite_node(v, rules, changed, root)
        return out
    return node


def apply_rewrite(program: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> int:
    changed = [0]
    # statements: try to rewrite whole statement, else rewrite expressions inside
    for idx, stmt in enumerate(program):
        new_stmt = rewrite_node(stmt, rules, changed, program)
        program[idx] = new_stmt
    return changed[0]


def main_rewrite(argv: List[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="amorph rewrite")
    p.add_argument("program")
    p.add_argument("rules")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args(argv)

    prog = read_json(args.program)
    rules = read_json(args.rules)
    if isinstance(prog, dict) and "program" in prog:
        prog_list = prog["program"]
    else:
        prog_list = prog
    if not isinstance(prog_list, list) or not isinstance(rules, list):
        print("Error: program must be list (or wrapper), rules must be list", file=sys.stderr)
        return 1
    add_uids(prog_list, deep=True)
    before = copy.deepcopy(prog)
    total = apply_rewrite(prog_list, rules)
    if args.limit is not None and total > args.limit:
        print(json.dumps({"replacements": total, "capped_by": args.limit, "preview": before if args.dry_run else None}, ensure_ascii=False))
        return 2
    if args.dry_run:
        print(json.dumps({"replacements": total, "preview": prog}, ensure_ascii=False, indent=2))
        return 0
    if isinstance(prog, dict):
        prog["program"] = prog_list
    write_json(args.program, prog)
    print(json.dumps({"replacements": total}))
    return 0
