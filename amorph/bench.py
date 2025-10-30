from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .format import minify_keys
from .uid import read_json
from .validate import validate_program
from .engine import VM


def _dump_canonical(data: Any) -> bytes:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _dump_minified(data: Any) -> bytes:
    minified = minify_keys(data)
    return json.dumps(minified, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _contains_input(node: Any) -> bool:
    if isinstance(node, list):
        return any(_contains_input(x) for x in node)
    if isinstance(node, dict):
        # operator-only object
        if len(node) == 1 and "input" in node:
            return True
        return any(_contains_input(v) for v in node.values())
    return False


def _count(program: List[Dict[str, Any]]) -> Dict[str, int]:
    stmts = len(program)
    funcs = 0
    uid_stmt = 0
    uid_fn = 0
    for stmt in program:
        if isinstance(stmt, dict):
            if "id" in stmt:
                uid_stmt += 1
            if "def" in stmt and isinstance(stmt["def"], dict):
                funcs += 1
                if "id" in stmt["def"]:
                    uid_fn += 1
    return {"stmts_top": stmts, "func_count": funcs, "uid_stmt_count": uid_stmt, "uid_fn_count": uid_fn}


@dataclass
class BenchResult:
    path: str
    size_bytes_canonical: int
    size_bytes_minified: int
    ratio_min_over_canon: float
    stmts_top: int
    func_count: int
    uid_stmt_count: int
    uid_fn_count: int
    has_input: bool
    validate_ms: float
    run_ms: Optional[float] = None

    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        # round floats
        d["ratio_min_over_canon"] = round(d["ratio_min_over_canon"], 3)
        d["validate_ms"] = round(d["validate_ms"], 3)
        if d["run_ms"] is not None:
            d["run_ms"] = round(d["run_ms"], 3)
        return d


def bench_file(path: str) -> BenchResult:
    data = read_json(path)
    program = data["program"] if isinstance(data, dict) and "program" in data else data

    # sizes
    canon_bytes = len(_dump_canonical(program))
    min_bytes = len(_dump_minified(program))

    # counts
    counts = _count(program if isinstance(program, list) else [])

    # detect input usage
    has_input = _contains_input(program)

    # validate time
    t0 = time.perf_counter()
    validate_program(data)
    t1 = time.perf_counter()
    validate_ms = (t1 - t0) * 1000.0

    # run time (skip if interactive via input)
    run_ms: Optional[float] = None
    if not has_input:
        vm = VM(trace=False, trace_json=False, quiet=True)
        t2 = time.perf_counter()
        vm.run(data)
        t3 = time.perf_counter()
        run_ms = (t3 - t2) * 1000.0

    return BenchResult(
        path=path,
        size_bytes_canonical=canon_bytes,
        size_bytes_minified=min_bytes,
        ratio_min_over_canon=(min_bytes / canon_bytes) if canon_bytes else 0.0,
        stmts_top=counts["stmts_top"],
        func_count=counts["func_count"],
        uid_stmt_count=counts["uid_stmt_count"],
        uid_fn_count=counts["uid_fn_count"],
        has_input=has_input,
        validate_ms=validate_ms,
        run_ms=run_ms,
    )


def find_program_files(paths: List[str]) -> List[str]:
    out: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for f in files:
                    if f.endswith(".json"):
                        out.append(os.path.join(root, f))
        elif os.path.isfile(p):
            out.append(p)
    # prefer .amr.json first
    out.sort(key=lambda s: (0 if s.endswith(".amr.json") else 1, s))
    return out


def bench(paths: Optional[List[str]] = None) -> Dict[str, Any]:
    if not paths:
        paths = ["examples"]
    files = find_program_files(paths)
    results: List[BenchResult] = []
    for f in files:
        try:
            results.append(bench_file(f))
        except Exception as e:
            results.append(BenchResult(
                path=f,
                size_bytes_canonical=0,
                size_bytes_minified=0,
                ratio_min_over_canon=0.0,
                stmts_top=0,
                func_count=0,
                uid_stmt_count=0,
                uid_fn_count=0,
                has_input=False,
                validate_ms=0.0,
                run_ms=None,
            ))
    # aggregates
    agg = {
        "files": len(results),
        "avg_ratio": round(sum(r.ratio_min_over_canon for r in results if r.size_bytes_canonical) / max(1, sum(1 for r in results if r.size_bytes_canonical)), 3),
        "avg_validate_ms": round(sum(r.validate_ms for r in results) / max(1, len(results)), 3),
        "avg_run_ms": round(sum((r.run_ms or 0.0) for r in results) / max(1, sum(1 for r in results if r.run_ms is not None)), 3) if any(r.run_ms is not None for r in results) else None,
    }
    return {"aggregate": agg, "results": [r.to_json() for r in results]}
