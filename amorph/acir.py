from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional


def _is_op_object(obj: Dict[str, Any]) -> bool:
    return isinstance(obj, dict) and len(obj) == 1 and ("var" not in obj and "call" not in obj)


def _collect_strings(node: Any, acc: set[str]) -> None:
    if isinstance(node, dict):
        # Statement id metadata
        if isinstance(node.get("id"), str):
            acc.add(node["id"])
        # Operators: collect op names
        if _is_op_object(node):
            op = next(iter(node.keys()))
            acc.add(op)
        # Specific constructs
        if "var" in node and isinstance(node["var"], str):
            acc.add(node["var"])
        if "call" in node and isinstance(node["call"], dict):
            c = node["call"]
            if isinstance(c.get("name"), str):
                acc.add(c["name"])
            if isinstance(c.get("id"), str):
                acc.add(c["id"])
        if "let" in node and isinstance(node["let"], dict):
            s = node["let"]
            if isinstance(s.get("name"), str):
                acc.add(s["name"])
        if "set" in node and isinstance(node["set"], dict):
            s = node["set"]
            if isinstance(s.get("name"), str):
                acc.add(s["name"])
        if "def" in node and isinstance(node["def"], dict):
            d = node["def"]
            if isinstance(d.get("name"), str):
                acc.add(d["name"])
            if isinstance(d.get("id"), str):
                acc.add(d["id"])
            params = d.get("params", [])
            if isinstance(params, list):
                for p in params:
                    if isinstance(p, str):
                        acc.add(p)
        # Object literal keys
        for k, v in node.items():
            if k not in ("let", "set", "def", "if", "return", "print", "expr", "var", "call"):
                # treat as generic object or nested structures
                pass
            _collect_strings(v, acc)
    elif isinstance(node, list):
        for x in node:
            _collect_strings(x, acc)
    else:
        # literals: optionally collect string literals (skip to keep simple)
        pass


def _sym(s: str, table: Dict[str, int]) -> int:
    return table[s]


def _enc_expr(expr: Any, table: Dict[str, int]) -> Any:
    if isinstance(expr, (int, float, bool)) or expr is None:
        return expr
    if isinstance(expr, str):
        return expr  # leave string literals as-is
    if isinstance(expr, list):
        return [_enc_expr(x, table) for x in expr]
    if isinstance(expr, dict):
        # var
        if "var" in expr:
            name = expr["var"]
            return ["v", _sym(name, table)]
        # call
        if "call" in expr and isinstance(expr["call"], dict):
            c = expr["call"]
            args = [_enc_expr(a, table) for a in c.get("args", [])]
            if "id" in c:
                return ["c", 1, _sym(c["id"], table), args]
            else:
                return ["c", 0, _sym(c["name"], table), args]
        # operator
        if _is_op_object(expr):
            op, val = next(iter(expr.items()))
            args = val if isinstance(val, list) else [val]
            return ["o", _sym(op, table), [_enc_expr(a, table) for a in args]]
        # print spread wrapper in expressions (rare): keep as tagged
        if "spread" in expr:
            return ["spread", _enc_expr(expr["spread"], table)]
        # generic object literal
        items = []
        for k, v in expr.items():
            if not isinstance(k, str):
                raise ValueError("Object literal keys must be strings")
            items.append([_sym(k, table), _enc_expr(v, table)])
        return ["obj", items]
    raise ValueError("Invalid expression type for encoding")


def _enc_stmt(stmt: Dict[str, Any], table: Dict[str, int]) -> Any:
    sid = -1
    if isinstance(stmt.get("id"), str):
        sid = _sym(stmt["id"], table)
    if "let" in stmt:
        s = stmt["let"]
        out = ["l", _sym(s["name"], table), _enc_expr(s["value"], table)]
        return out + [sid] if sid >= 0 else out
    if "set" in stmt:
        s = stmt["set"]
        out = ["s", _sym(s["name"], table), _enc_expr(s["value"], table)]
        return out + [sid] if sid >= 0 else out
    if "def" in stmt:
        s = stmt["def"]
        name = _sym(s["name"], table)
        params = [_sym(p, table) for p in s.get("params", [])]
        body = [_enc_stmt(x, table) for x in s.get("body", [])]
        fid = _sym(s["id"], table) if isinstance(s.get("id"), str) else -1
        out = ["d", name, params, body, fid]
        return out + [sid] if sid >= 0 else out
    if "if" in stmt:
        s = stmt["if"]
        cond = _enc_expr(s["cond"], table)
        thenb = [_enc_stmt(x, table) for x in s.get("then", [])]
        elseb = [_enc_stmt(x, table) for x in s.get("else", [])]
        out = ["i", cond, thenb, elseb]
        return out + [sid] if sid >= 0 else out
    if "return" in stmt:
        out = ["r", _enc_expr(stmt["return"], table)]
        return out + [sid] if sid >= 0 else out
    if "print" in stmt:
        payload = stmt["print"]
        out: List[Any] = []
        if isinstance(payload, list):
            for x in payload:
                if isinstance(x, dict) and "spread" in x:
                    out.append(["spread", _enc_expr(x["spread"], table)])
                else:
                    out.append(_enc_expr(x, table))
        else:
            out.append(_enc_expr(payload, table))
        outn = ["p", out]
        return outn + [sid] if sid >= 0 else outn
    if "expr" in stmt:
        out = ["x", _enc_expr(stmt["expr"], table)]
        return out + [sid] if sid >= 0 else out
    raise ValueError(f"Unknown statement: {list(stmt.keys())}")


def encode_program(program: List[Dict[str, Any]]) -> Dict[str, Any]:
    strings: set[str] = set()
    _collect_strings(program, strings)
    # stable ordering for deterministic output
    string_list = sorted(strings)
    table = {s: i for i, s in enumerate(string_list)}
    enc = [_enc_stmt(stmt, table) for stmt in program]
    return {"acir": 1, "strings": string_list, "program": enc}


def _unsym(idx: int, strings: List[str]) -> str:
    return strings[idx]


def _dec_expr(node: Any, strings: List[str]) -> Any:
    if isinstance(node, (int, float, bool)) or node is None or isinstance(node, str):
        return node
    if isinstance(node, list):
        if not node:
            return []
        tag = node[0]
        if tag == "v":
            return {"var": _unsym(node[1], strings)}
        if tag == "c":
            mode, sym, args = node[1], node[2], node[3]
            call = {"args": [_dec_expr(a, strings) for a in args]}
            if mode == 1:
                call["id"] = _unsym(sym, strings)
            else:
                call["name"] = _unsym(sym, strings)
            return {"call": call}
        if tag == "o":
            op = _unsym(node[1], strings)
            args = node[2]
            vals = [_dec_expr(a, strings) for a in args]
            # if one arg, allow non-list form
            return {op: vals if len(vals) != 1 else vals[0]}
        if tag == "spread":
            return {"spread": _dec_expr(node[1], strings)}
        if tag == "obj":
            out: Dict[str, Any] = {}
            for ksym, v in node[1]:
                out[_unsym(ksym, strings)] = _dec_expr(v, strings)
            return out
        # generic list
        return [_dec_expr(x, strings) for x in node]
    if isinstance(node, dict):
        # shouldn't happen in acir, but pass-through
        return {k: _dec_expr(v, strings) for k, v in node.items()}
    return node


def _dec_stmt(node: Any, strings: List[str]) -> Dict[str, Any]:
    tag = node[0]
    sid: Optional[int] = None
    # expected base lengths per tag
    base_len = {"l": 3, "s": 3, "d": 5, "i": 4, "r": 2, "p": 2, "x": 2}.get(tag, None)
    if base_len is not None and len(node) == base_len + 1 and isinstance(node[-1], int):
        sid = node[-1]
    if tag == "l":
        out = {"let": {"name": _unsym(node[1], strings), "value": _dec_expr(node[2], strings)}}
        if sid is not None and sid >= 0:
            out["id"] = _unsym(sid, strings)
        return out
    if tag == "s":
        out = {"set": {"name": _unsym(node[1], strings), "value": _dec_expr(node[2], strings)}}
        if sid is not None and sid >= 0:
            out["id"] = _unsym(sid, strings)
        return out
    if tag == "d":
        name = _unsym(node[1], strings)
        params = [_unsym(p, strings) for p in node[2]]
        body = [_dec_stmt(x, strings) for x in node[3]]
        fid = node[4]
        d = {"name": name, "params": params, "body": body}
        if isinstance(fid, int) and fid >= 0:
            d["id"] = _unsym(fid, strings)
        out = {"def": d}
        if sid is not None and sid >= 0:
            out["id"] = _unsym(sid, strings)
        return out
    if tag == "i":
        out = {"if": {"cond": _dec_expr(node[1], strings), "then": [_dec_stmt(x, strings) for x in node[2]], "else": [_dec_stmt(x, strings) for x in node[3]]}}
        if sid is not None and sid >= 0:
            out["id"] = _unsym(sid, strings)
        return out
    if tag == "r":
        out = {"return": _dec_expr(node[1], strings)}
        if sid is not None and sid >= 0:
            out["id"] = _unsym(sid, strings)
        return out
    if tag == "p":
        args = []
        for a in node[1]:
            if isinstance(a, list) and a and a[0] == "spread":
                args.append({"spread": _dec_expr(a[1], strings)})
            else:
                args.append(_dec_expr(a, strings))
        out = {"print": args if len(args) != 1 else args[0]}
        if sid is not None and sid >= 0:
            out["id"] = _unsym(sid, strings)
        return out
    if tag == "x":
        out = {"expr": _dec_expr(node[1], strings)}
        if sid is not None and sid >= 0:
            out["id"] = _unsym(sid, strings)
        return out
    raise ValueError(f"Unknown acir stmt tag: {tag}")


def decode_program(acir: Dict[str, Any]) -> List[Dict[str, Any]]:
    strings = acir.get("strings", [])
    enc = acir.get("program", [])
    return [_dec_stmt(x, strings) for x in enc]


def pack(data: Any, prefer_cbor: bool = True) -> Tuple[bytes, str]:
    """Pack a program into ACIR. Returns (bytes, format). If cbor2 is available and prefer_cbor, uses cbor."""
    if isinstance(data, dict) and "program" in data:
        program = data["program"]
    else:
        program = data
    if not isinstance(program, list):
        raise ValueError("Program must be a list or {program:[...]} wrapper")
    acir = encode_program(program)
    if prefer_cbor:
        try:
            import cbor2  # type: ignore
            return cbor2.dumps(acir), "cbor"
        except Exception:
            pass
    # fallback to JSON bytes (minified)
    import json
    return json.dumps(acir, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"), "json"


def unpack(buf: bytes, fmt: Optional[str] = None) -> Any:
    """Unpack ACIR bytes back into canonical program JSON (ASV)."""
    acir: Dict[str, Any]
    if fmt == "cbor":
        import cbor2  # type: ignore
        acir = cbor2.loads(buf)
    elif fmt == "json" or fmt is None:
        import json
        try:
            acir = json.loads(buf.decode("utf-8"))
        except Exception:
            # try CBOR as fallback
            import cbor2  # type: ignore
            acir = cbor2.loads(buf)
    else:
        raise ValueError("Unknown format")
    program = decode_program(acir)
    return program
