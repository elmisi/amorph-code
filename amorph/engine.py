from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .errors import AmorphRuntimeError, AmorphValidationError, ErrorContext
from .validate import validate_program
from .io import IOBase, StdIO, QuietIO


@dataclass
class Frame:
    vars: Dict[str, Any]


class VM:
    def __init__(self, trace: bool = False, trace_json: bool = False, io: Optional[IOBase] = None, quiet: bool = False, allow_print: bool = True, allow_input: bool = True, rich_errors: bool = False):
        self.stack: List[Frame] = [Frame(vars={})]
        # function registries by name and by id (if provided)
        self.funcs_by_name: Dict[str, Dict[str, Any]] = {}
        self.funcs_by_id: Dict[str, Dict[str, Any]] = {}
        self.trace = trace
        self.trace_json = trace_json
        self.quiet = quiet
        self.allow_print = allow_print
        self.allow_input = allow_input
        self.rich_errors = rich_errors
        if io is not None:
            self.io = io
        else:
            self.io = QuietIO() if quiet else StdIO()
        self._call_seq = 0
        # Context tracking for rich errors
        self.current_path: List[Tuple[str, int]] = []
        self.call_stack_names: List[str] = []

    # --------------- Utilities ---------------
    def _log(self, *args: Any) -> None:
        if self.trace:
            print("[trace]", *args)

    def _emit(self, event: Dict[str, Any]) -> None:
        if self.trace_json:
            import json as _json, time as _time
            event = dict(event)
            event.setdefault("ts", _time.time())
            print(_json.dumps(event, ensure_ascii=False), flush=True, file=sys.stderr)

    def push(self) -> None:
        self.stack.append(Frame(vars={}))

    def pop(self) -> None:
        self.stack.pop()

    def define(self, name: str, value: Any) -> None:
        self.stack[-1].vars[name] = value
        self._log("let", name, "=", value)

    def set(self, name: str, value: Any) -> None:
        for frame in reversed(self.stack):
            if name in frame.vars:
                frame.vars[name] = value
                self._log("set", name, "=", value)
                return
        raise AmorphRuntimeError(f"Variable not found: {name}")

    def get(self, name: str) -> Any:
        for frame in reversed(self.stack):
            if name in frame.vars:
                return frame.vars[name]

        # Create rich error if enabled
        if self.rich_errors:
            context = ErrorContext(
                path=_path_to_string(self.current_path),
                call_stack=self.call_stack_names.copy()
            )
            raise AmorphRuntimeError(f"Variable not found: {name}", context)
        else:
            raise AmorphRuntimeError(f"Variable not found: {name}")

    # --------------- Execution ---------------
    def run(self, program: Any) -> Any:
        # wrapper form support: {version?, program:[...]}
        if isinstance(program, dict) and "program" in program:
            header = dict(program)
            program = header.get("program")
            self._emit({"event": "start", "version": header.get("version")})
        validate_program(program)
        if not isinstance(program, list):
            raise AmorphValidationError("Program must be a JSON array of statements")
        result = None
        for idx, stmt in enumerate(program):
            result = self.exec_stmt(stmt, path=[("$", idx)])
            if isinstance(result, _Return):
                return result.value
        return result

    def exec_block(self, block: List[Dict[str, Any]], path_prefix: List[Tuple[str, int]]) -> Any:
        self.push()
        try:
            result = None
            for idx, stmt in enumerate(block):
                result = self.exec_stmt(stmt, path=path_prefix + [("$", idx)])
                if isinstance(result, _Return):
                    return result
            return result
        finally:
            self.pop()

    def exec_stmt(self, stmt: Dict[str, Any], path: List[Tuple[str, int]]) -> Any:
        if not isinstance(stmt, dict):
            raise AmorphValidationError(f"Statement must be object, got: {type(stmt)}")

        # Track current path for error reporting
        self.current_path = path

        # path string for trace
        path_str = _path_to_string(path)
        stmt_kinds = ["let", "set", "def", "if", "return", "print", "expr"]
        kind = next((k for k in stmt_kinds if k in stmt), next(iter(stmt.keys())) if stmt else "?")
        self._emit({"event": "stmt_start", "kind": kind, "path": path_str})

        if "let" in stmt:
            spec = stmt["let"]
            if not isinstance(spec, dict) or "name" not in spec or "value" not in spec:
                raise AmorphValidationError("let requires {name, value}")
            name = spec["name"]
            value = self.eval_expr(spec["value"])
            self.define(name, value)
            self._emit({"event": "stmt_end", "path": path_str})
            return None

        if "set" in stmt:
            spec = stmt["set"]
            if not isinstance(spec, dict) or "name" not in spec or "value" not in spec:
                raise AmorphValidationError("set requires {name, value}")
            name = spec["name"]
            value = self.eval_expr(spec["value"])
            self.set(name, value)
            self._emit({"event": "stmt_end", "path": path_str})
            return None

        if "def" in stmt:
            spec = stmt["def"]
            if not isinstance(spec, dict):
                raise AmorphValidationError("def requires object")
            name = spec.get("name")
            params = spec.get("params", [])
            body = spec.get("body", [])
            if not isinstance(name, str) or not isinstance(params, list) or not isinstance(body, list):
                raise AmorphValidationError("def requires {name:str, params:list, body:list}")
            fn_id = spec.get("id") or f"fn_runtime_{len(self.funcs_by_id)+1}"
            fn_obj = {"id": fn_id, "name": name, "params": params, "body": body}
            self.funcs_by_name[name] = fn_obj
            self.funcs_by_id[fn_id] = fn_obj
            self._log("def", name, "params=", params)
            self._emit({"event": "stmt_end", "path": path_str})
            return None

        if "if" in stmt:
            spec = stmt["if"]
            if not isinstance(spec, dict) or "cond" not in spec:
                raise AmorphValidationError("if requires {cond, then?, else?}")
            cond = self.eval_expr(spec["cond"]) 
            branch = spec.get("then") if cond else spec.get("else")
            if branch is None:
                self._emit({"event": "stmt_end", "path": path_str})
                return None
            if not isinstance(branch, list):
                raise AmorphValidationError("then/else must be list of statements")
            res = self.exec_block(branch, path_prefix=path + [("branch", 1 if cond else 0)])
            # if res is _Return, propagate as-is
            if isinstance(res, _Return):
                return res
            self._emit({"event": "stmt_end", "path": path_str})
            return res

        if "return" in stmt:
            val = self.eval_expr(stmt["return"]) 
            self._emit({"event": "stmt_end", "path": path_str, "return": True})
            return _Return(val)

        if "print" in stmt:
            if not self.allow_print:
                raise AmorphRuntimeError("Effect denied: print")
            payload = stmt["print"]
            vals: List[Any] = []
            def _push(v: Any):
                vals.append(self.eval_expr(v))
            if isinstance(payload, list):
                for x in payload:
                    if isinstance(x, dict) and "spread" in x:
                        seq = self.eval_expr(x["spread"]) 
                        if not isinstance(seq, list):
                            raise AmorphValidationError("spread expects a list expression")
                        vals.extend(seq)
                    else:
                        _push(x)
            else:
                if isinstance(payload, dict) and "spread" in payload:
                    seq = self.eval_expr(payload["spread"]) 
                    if not isinstance(seq, list):
                        raise AmorphValidationError("spread expects a list expression")
                    vals.extend(seq)
                else:
                    _push(payload)
            self.io.write(*vals)
            self._emit({"event": "stmt_end", "path": path_str})
            return None

        if "expr" in stmt:
            _ = self.eval_expr(stmt["expr"])  # discard
            self._emit({"event": "stmt_end", "path": path_str})
            return None

        raise AmorphValidationError(f"Unknown statement: {list(stmt.keys())}")

    # --------------- Expressions ---------------
    def eval_expr(self, expr: Any) -> Any:
        # Literals and structured literals
        if isinstance(expr, (int, float, str, bool)) or expr is None:
            return expr
        if isinstance(expr, list):
            return [self.eval_expr(x) for x in expr]
        if isinstance(expr, dict):
            # Variable
            if "var" in expr:
                name = expr["var"]
                if not isinstance(name, str):
                    raise AmorphValidationError("var name must be string")
                return self.get(name)

            # Function call
            if "call" in expr:
                spec = expr["call"]
                if not isinstance(spec, dict) or ("name" not in spec and "id" not in spec):
                    raise AmorphValidationError("call requires {name|id, args?}")
                name = spec.get("name")
                fn_id = spec.get("id")
                args = [self.eval_expr(a) for a in spec.get("args", [])]
                return self.call_func(name=name, fn_id=fn_id, args=args)

            # Operators (single-key object)
            if len(expr) == 1:
                op, val = next(iter(expr.items()))
                return self.apply_op(op, val)

            # Otherwise treat as object-literal with evaluated values
            return {k: self.eval_expr(v) for k, v in expr.items()}

        raise AmorphValidationError(f"Invalid expression type: {type(expr)}")

    # --------------- Functions & Operators ---------------
    def call_func(self, name: Optional[str], fn_id: Optional[str], args: List[Any]) -> Any:
        # Builtins can be added here later if needed
        if fn_id is not None:
            fn = self.funcs_by_id.get(fn_id)
            if fn is None:
                if self.rich_errors:
                    context = ErrorContext(
                        path=_path_to_string(self.current_path),
                        call_stack=self.call_stack_names.copy()
                    )
                    raise AmorphRuntimeError(f"Function id not defined: {fn_id}", context)
                raise AmorphRuntimeError(f"Function id not defined: {fn_id}")
        else:
            if name not in self.funcs_by_name:
                if self.rich_errors:
                    context = ErrorContext(
                        path=_path_to_string(self.current_path),
                        call_stack=self.call_stack_names.copy()
                    )
                    raise AmorphRuntimeError(f"Function not defined: {name}", context)
                raise AmorphRuntimeError(f"Function not defined: {name}")
            fn = self.funcs_by_name[name]  # type: ignore[index]
        params = fn["params"]
        body = fn["body"]
        fn_name = fn.get("name")

        # Track call stack for error reporting
        if self.rich_errors:
            fn_display = name or fn_id or "anonymous"
            self.call_stack_names.append(fn_display)
        self._call_seq += 1
        call_id = self._call_seq
        self._emit({"event": "call_start", "call_id": call_id, "function": {"name": fn_name, "id": fn.get("id")}, "args": args})
        if len(params) != len(args):
            raise AmorphRuntimeError(
                f"Function {name} expects {len(params)} args, got {len(args)}"
            )
        self.push()
        try:
            for p, a in zip(params, args):
                self.define(p, a)
            result = None
            fnid = fn.get("id")
            for idx, stmt in enumerate(body):
                result = self.exec_stmt(stmt, path=[("fn", fnid), ("body", idx)])
                if isinstance(result, _Return):
                    self._emit({"event": "return", "call_id": call_id, "function": {"name": fn_name, "id": fn.get("id")}, "value": result.value})
                    return result.value
            return result
        finally:
            if self.rich_errors and self.call_stack_names:
                self.call_stack_names.pop()
            self.pop()

    def apply_op(self, op: str, val: Any) -> Any:
        # namespaced operators: use suffix after last dot
        op = op.split(".")[-1]
        # Normalize list args
        if op == "not":
            args = [self.eval_expr(val)]
        elif isinstance(val, list):
            args = [self.eval_expr(x) for x in val]
        else:
            args = [self.eval_expr(val)]

        self._log("op", op, args)
        self._emit({"event": "op", "op": op, "args": args})

        if op == "add":
            return _fold(args, 0, lambda a, b: a + b)
        if op == "sub":
            return _fold_left(args, lambda a, b: a - b)
        if op == "mul":
            return _fold(args, 1, lambda a, b: a * b)
        if op == "div":
            return _fold_left(args, lambda a, b: a / b)
        if op == "mod":
            return _fold_left(args, lambda a, b: a % b)
        if op == "pow":
            return _fold_left(args, lambda a, b: a ** b)

        if op == "eq":
            return _all_pairs(args, lambda a, b: a == b)
        if op == "ne":
            return _all_pairs(args, lambda a, b: a != b)
        if op == "lt":
            return _all_pairs(args, lambda a, b: a < b)
        if op == "le":
            return _all_pairs(args, lambda a, b: a <= b)
        if op == "gt":
            return _all_pairs(args, lambda a, b: a > b)
        if op == "ge":
            return _all_pairs(args, lambda a, b: a >= b)

        if op == "not":
            if len(args) != 1:
                raise AmorphRuntimeError("not expects 1 arg")
            return not bool(args[0])
        if op == "and":
            for a in args:
                if not a:
                    return False
            return True
        if op == "or":
            for a in args:
                if a:
                    return True
            return False

        if op == "list":
            return list(args)
        if op == "concat":
            return _fold_left(args, lambda a, b: a + b)
        if op == "len":
            if len(args) != 1:
                raise AmorphRuntimeError("len expects 1 arg")
            return len(args[0])
        if op == "get":
            if len(args) != 2:
                raise AmorphRuntimeError("get expects 2 args")
            container, key = args
            return container[key]
        if op == "has":
            if len(args) != 2:
                raise AmorphRuntimeError("has expects 2 args")
            container, key = args
            try:
                _ = container[key]
                return True
            except Exception:
                return False

        if op == "range":
            if len(args) == 1:
                n = int(args[0])
                if n < 0:
                    return []
                return list(range(1, n + 1))
            if len(args) == 2:
                a, b = int(args[0]), int(args[1])
                if a <= b:
                    return list(range(a, b + 1))
                else:
                    return list(range(a, b - 1, -1))
            raise AmorphRuntimeError("range expects 1 or 2 args")

        if op == "input":
            if not self.allow_input:
                raise AmorphRuntimeError("Effect denied: input")
            if len(args) == 0:
                return self.io.read()
            if len(args) == 1:
                return self.io.read(str(args[0]))
            raise AmorphRuntimeError("input expects 0 or 1 arg")

        if op == "int":
            if len(args) != 1:
                raise AmorphRuntimeError("int expects 1 arg")
            try:
                return int(args[0])
            except Exception as e:
                raise AmorphRuntimeError(f"int parse failed: {e}")

        raise AmorphRuntimeError(f"Unknown operator: {op}")


@dataclass
class _Return:
    value: Any


def _fold(args: List[Any], init: Any, fn):
    acc = init
    for a in args:
        acc = fn(acc, a)
    return acc


def _fold_left(args: List[Any], fn):
    if not args:
        raise AmorphRuntimeError("operation expects at least 1 arg")
    acc = args[0]
    for a in args[1:]:
        acc = fn(acc, a)
    return acc


def _all_pairs(args: List[Any], pred):
    if len(args) < 2:
        return True
    for i in range(len(args) - 1):
        if not pred(args[i], args[i + 1]):
            return False
    return True


def run_program(program: List[Dict[str, Any]], trace: bool = False, trace_json: bool = False, quiet: bool = False, allow_print: bool = True, allow_input: bool = True) -> Any:
    vm = VM(trace=trace, trace_json=trace_json, quiet=quiet, allow_print=allow_print, allow_input=allow_input)
    return vm.run(program)


def run_file(path: str, trace: bool = False, trace_json: bool = False, quiet: bool = False, allow_print: bool = True, allow_input: bool = True) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        program = json.load(f)
    vm = VM(trace=trace, trace_json=trace_json, quiet=quiet, allow_print=allow_print, allow_input=allow_input)
    return vm.run(program)


def _path_to_string(path: List[Tuple[str, int]]) -> str:
    parts: List[str] = []
    for key, idx in path:
        if key == "$":
            parts.append(f"$[{idx}]")
        elif key == "fn":
            # idx may carry the function id (string) in our convention
            parts.append(f"fn[{idx}]")
        else:
            parts.append(key)
    return "/" + "/".join(parts)
