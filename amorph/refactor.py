"""Refactoring operations for Amorph programs.

This module provides advanced refactoring capabilities including:
- Variable reference tracking and renaming
- Function extraction
- Code analysis for refactoring opportunities
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple
import copy

from .edits import EditError, deep_walk_expr


@dataclass
class VariableReference:
    """A reference to a variable in the program."""
    var_name: str
    path: str
    ref_type: str  # "definition" | "read" | "write"
    scope_id: str  # function id or "global"
    statement_idx: int  # Index in containing list


class VariableAnalyzer:
    """Analyzes variable usage in programs."""

    def __init__(self):
        self.references: Dict[str, List[VariableReference]] = {}

    def analyze_program(self, program: List[Dict[str, Any]]) -> Dict[str, List[VariableReference]]:
        """Map variable names to all their references."""
        self.references = {}

        for i, stmt in enumerate(program):
            self._analyze_stmt(stmt, "global", [("$", i)], i)

        return self.references

    def _path_to_string(self, path: List[Tuple[str, int]]) -> str:
        """Convert path to string representation."""
        parts = []
        for key, idx in path:
            if key == "$":
                parts.append(f"$[{idx}]")
            elif key == "fn":
                parts.append(f"fn[{idx}]")
            else:
                parts.append(key)
        return "/" + "/".join(parts)

    def _add_ref(self, var_name: str, path: List, ref_type: str, scope: str, stmt_idx: int):
        """Add a variable reference."""
        if var_name not in self.references:
            self.references[var_name] = []

        ref = VariableReference(
            var_name=var_name,
            path=self._path_to_string(path),
            ref_type=ref_type,
            scope_id=scope,
            statement_idx=stmt_idx
        )
        self.references[var_name].append(ref)

    def _analyze_expr(self, expr: Any, scope: str, path: List, stmt_idx: int):
        """Analyze expression for variable references."""
        if isinstance(expr, dict):
            # Variable reference
            if "var" in expr:
                var_name = expr["var"]
                self._add_ref(var_name, path + [("var", -1)], "read", scope, stmt_idx)

            # Recursively check other keys
            for k, v in expr.items():
                if k != "var":
                    self._analyze_expr(v, scope, path + [(k, -1)], stmt_idx)

        elif isinstance(expr, list):
            for i, item in enumerate(expr):
                self._analyze_expr(item, scope, path + [("$", i)], stmt_idx)

    def _analyze_stmt(self, stmt: Dict[str, Any], scope: str, path: List, stmt_idx: int):
        """Analyze statement for variable references."""
        if not isinstance(stmt, dict):
            return

        # let statement - definition
        if "let" in stmt and isinstance(stmt["let"], dict):
            spec = stmt["let"]
            var_name = spec.get("name")
            value = spec.get("value")

            if var_name:
                self._add_ref(var_name, path + [("let", -1), ("name", -1)], "definition", scope, stmt_idx)

            if value is not None:
                self._analyze_expr(value, scope, path + [("let", -1), ("value", -1)], stmt_idx)

        # set statement - write
        if "set" in stmt and isinstance(stmt["set"], dict):
            spec = stmt["set"]
            var_name = spec.get("name")
            value = spec.get("value")

            if var_name:
                self._add_ref(var_name, path + [("set", -1), ("name", -1)], "write", scope, stmt_idx)

            if value is not None:
                self._analyze_expr(value, scope, path + [("set", -1), ("value", -1)], stmt_idx)

        # def statement - new scope
        if "def" in stmt and isinstance(stmt["def"], dict):
            spec = stmt["def"]
            fn_id = spec.get("id", spec.get("name", "anonymous"))
            params = spec.get("params", [])
            body = spec.get("body", [])

            # Parameters are definitions in function scope
            for j, param in enumerate(params):
                param_path = path + [("def", -1), ("params", j)]
                self._add_ref(param, param_path, "definition", fn_id, stmt_idx)

            # Analyze body in function scope
            for j, s in enumerate(body):
                self._analyze_stmt(s, fn_id, path + [("def", -1), ("body", j)], j)

        # if statement - analyze blocks
        if "if" in stmt and isinstance(stmt["if"], dict):
            spec = stmt["if"]

            if "cond" in spec:
                self._analyze_expr(spec["cond"], scope, path + [("if", -1), ("cond", -1)], stmt_idx)

            if "then" in spec and isinstance(spec["then"], list):
                for j, s in enumerate(spec["then"]):
                    self._analyze_stmt(s, scope, path + [("if", -1), ("then", j)], j)

            if "else" in spec and isinstance(spec["else"], list):
                for j, s in enumerate(spec["else"]):
                    self._analyze_stmt(s, scope, path + [("if", -1), ("else", j)], j)

        # return statement
        if "return" in stmt:
            self._analyze_expr(stmt["return"], scope, path + [("return", -1)], stmt_idx)

        # expr statement
        if "expr" in stmt:
            self._analyze_expr(stmt["expr"], scope, path + [("expr", -1)], stmt_idx)

        # print statement
        if "print" in stmt:
            payload = stmt["print"]
            if isinstance(payload, list):
                for i, item in enumerate(payload):
                    self._analyze_expr(item, scope, path + [("print", -1), ("$", i)], stmt_idx)
            else:
                self._analyze_expr(payload, scope, path + [("print", -1)], stmt_idx)


def op_rename_variable(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> int:
    """
    Rename variable across all references in scope.

    spec: {
        "old_name": str,
        "new_name": str,
        "scope": str | "all",     # function id or "all"
        "path"?: str              # optional: limit to subtree
    }

    Returns: number of references changed
    """
    old_name = spec.get("old_name")
    new_name = spec.get("new_name")
    scope = spec.get("scope", "all")
    limit_path = spec.get("path")

    if not old_name or not new_name:
        raise EditError("E_BAD_SPEC", "rename_variable requires old_name and new_name")

    if not isinstance(old_name, str) or not isinstance(new_name, str):
        raise EditError("E_BAD_SPEC", "old_name and new_name must be strings")

    # Analyze to find all references
    analyzer = VariableAnalyzer()
    refs = analyzer.analyze_program(program)

    if old_name not in refs:
        raise EditError("E_NOT_FOUND", f"Variable '{old_name}' not found in program")

    # Filter by scope
    target_refs = refs[old_name]
    if scope != "all":
        target_refs = [r for r in target_refs if r.scope_id == scope]

    if limit_path:
        target_refs = [r for r in target_refs if r.path.startswith(limit_path)]

    if not target_refs:
        raise EditError("E_NOT_FOUND", f"Variable '{old_name}' not found in scope '{scope}'")

    # Perform rename
    changed = 0

    def rename_in_expr(expr):
        nonlocal changed
        if isinstance(expr, dict):
            if "var" in expr and expr["var"] == old_name:
                expr["var"] = new_name
                changed += 1
            for v in expr.values():
                rename_in_expr(v)
        elif isinstance(expr, list):
            for item in expr:
                rename_in_expr(item)

    def rename_in_stmt(stmt, current_scope):
        nonlocal changed
        if not isinstance(stmt, dict):
            return

        # Only rename if in target scope
        if scope == "all" or current_scope == scope:
            # let statement
            if "let" in stmt and stmt["let"].get("name") == old_name:
                stmt["let"]["name"] = new_name
                changed += 1

            # set statement
            if "set" in stmt and stmt["set"].get("name") == old_name:
                stmt["set"]["name"] = new_name
                changed += 1

            # Expressions in let/set
            if "let" in stmt and "value" in stmt["let"]:
                rename_in_expr(stmt["let"]["value"])

            if "set" in stmt and "value" in stmt["set"]:
                rename_in_expr(stmt["set"]["value"])

            # return statement
            if "return" in stmt:
                rename_in_expr(stmt["return"])

            # expr statement
            if "expr" in stmt:
                rename_in_expr(stmt["expr"])

            # print statement
            if "print" in stmt:
                rename_in_expr(stmt["print"])

            # if statement
            if "if" in stmt:
                if "cond" in stmt["if"]:
                    rename_in_expr(stmt["if"]["cond"])
                if "then" in stmt["if"]:
                    for s in stmt["if"]["then"]:
                        rename_in_stmt(s, current_scope)
                if "else" in stmt["if"]:
                    for s in stmt["if"]["else"]:
                        rename_in_stmt(s, current_scope)

        # def statement - recurse into function scope
        if "def" in stmt:
            fn_id = stmt["def"].get("id", stmt["def"].get("name", "anonymous"))
            # Rename parameters if in function scope
            if (scope == "all" or fn_id == scope) and "params" in stmt["def"]:
                for i, param in enumerate(stmt["def"]["params"]):
                    if param == old_name:
                        stmt["def"]["params"][i] = new_name
                        changed += 1

            # Recurse into body
            if "body" in stmt["def"]:
                for s in stmt["def"]["body"]:
                    rename_in_stmt(s, fn_id)

    for stmt in program:
        rename_in_stmt(stmt, "global")

    return changed


def op_extract_function(program: List[Dict[str, Any]], spec: Dict[str, Any]) -> None:
    """
    Extract statements into a new function.

    spec: {
        "function_name": str,
        "function_id": str,
        "statements": [int, ...],       # Indices of statements to extract
        "parameters": [str, ...],        # Variables to parameterize
        "insert_at": int,                # Where to insert new function
        "replace_with_call": bool        # Replace extracted code with call
    }
    """
    fn_name = spec.get("function_name")
    fn_id = spec.get("function_id")
    stmt_indices = spec.get("statements", [])
    parameters = spec.get("parameters", [])
    insert_at = spec.get("insert_at", 0)
    replace_with_call = spec.get("replace_with_call", True)

    if not fn_name or not isinstance(fn_name, str):
        raise EditError("E_BAD_SPEC", "extract_function requires function_name")

    if not isinstance(stmt_indices, list) or not stmt_indices:
        raise EditError("E_BAD_SPEC", "extract_function requires non-empty statements list")

    if not isinstance(parameters, list):
        raise EditError("E_BAD_SPEC", "parameters must be a list")

    # Validate indices
    for idx in stmt_indices:
        if not isinstance(idx, int) or idx < 0 or idx >= len(program):
            raise EditError("E_BAD_SPEC", f"Invalid statement index: {idx}")

    # Indices must be consecutive
    sorted_indices = sorted(stmt_indices)
    for i in range(len(sorted_indices) - 1):
        if sorted_indices[i+1] != sorted_indices[i] + 1:
            raise EditError("E_BAD_SPEC", "Statement indices must be consecutive")

    # Extract statements
    extracted_stmts = [copy.deepcopy(program[i]) for i in sorted_indices]

    # Create function body
    # If last statement is not a return, keep as-is
    # Otherwise, function returns the value
    body = extracted_stmts

    # Create function definition
    fn_def = {
        "def": {
            "name": fn_name,
            "params": parameters,
            "body": body
        }
    }
    if fn_id:
        fn_def["def"]["id"] = fn_id

    # Insert function at specified position
    program.insert(insert_at, fn_def)

    # Replace extracted statements with call (if requested)
    if replace_with_call:
        # Build call statement
        call_expr = {
            "call": {
                "name": fn_name,
                "args": [{"var": param} for param in parameters]
            }
        }
        if fn_id:
            call_expr["call"]["id"] = fn_id
            del call_expr["call"]["name"]

        call_stmt = {"expr": call_expr}

        # Adjust indices (function was inserted)
        adjusted_indices = [i + 1 if i >= insert_at else i for i in sorted_indices]

        # Replace first extracted statement with call
        program[adjusted_indices[0]] = call_stmt

        # Delete remaining extracted statements (in reverse to preserve indices)
        for i in reversed(adjusted_indices[1:]):
            program.pop(i)


def find_variable_references(program: List[Dict[str, Any]], var_name: str, scope: str = "all") -> List[VariableReference]:
    """Find all references to a variable."""
    analyzer = VariableAnalyzer()
    refs = analyzer.analyze_program(program)

    if var_name not in refs:
        return []

    result = refs[var_name]
    if scope != "all":
        result = [r for r in result if r.scope_id == scope]

    return result


def analyze_free_variables(statements: List[Dict[str, Any]]) -> Set[str]:
    """
    Analyze statements to find free variables (used but not defined).
    These become parameters when extracting to a function.
    """
    defined = set()
    used = set()

    def collect_vars_in_expr(expr):
        if isinstance(expr, dict):
            if "var" in expr:
                used.add(expr["var"])
            for v in expr.values():
                collect_vars_in_expr(v)
        elif isinstance(expr, list):
            for item in expr:
                collect_vars_in_expr(item)

    for stmt in statements:
        if not isinstance(stmt, dict):
            continue

        # Collect used variables first
        if "let" in stmt and "value" in stmt["let"]:
            collect_vars_in_expr(stmt["let"]["value"])
        if "set" in stmt and "value" in stmt["set"]:
            collect_vars_in_expr(stmt["set"]["value"])
        if "return" in stmt:
            collect_vars_in_expr(stmt["return"])
        if "expr" in stmt:
            collect_vars_in_expr(stmt["expr"])
        if "if" in stmt and "cond" in stmt["if"]:
            collect_vars_in_expr(stmt["if"]["cond"])

        # Then mark as defined
        if "let" in stmt and "name" in stmt["let"]:
            defined.add(stmt["let"]["name"])

    # Free variables = used but not defined in this block
    return used - defined


def suggest_variable_rename(program: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Suggest variable renames for better clarity.
    Returns list of suggested edit operations.
    """
    suggestions = []

    # Find single-letter variable names that could be renamed
    analyzer = VariableAnalyzer()
    refs = analyzer.analyze_program(program)

    for var_name, ref_list in refs.items():
        # Suggest renaming single-letter vars that are used multiple times
        if len(var_name) == 1 and len(ref_list) > 3:
            suggestions.append({
                "op": "rename_variable",
                "old_name": var_name,
                "new_name": f"{var_name}_descriptive",  # Placeholder
                "scope": "all",
                "reason": f"Single-letter variable '{var_name}' used {len(ref_list)} times",
                "priority": "medium"
            })

    return suggestions


def suggest_extract_function(program: List[Dict[str, Any]], min_statements: int = 3) -> List[Dict[str, Any]]:
    """
    Suggest extracting repeated code into functions.
    Returns list of suggested edit operations.
    """
    suggestions = []

    # Simple heuristic: sequences of 3+ consecutive statements could be extracted
    for i in range(len(program) - min_statements + 1):
        sequence = program[i:i+min_statements]

        # Check if sequence is all non-def statements
        if all("def" not in stmt for stmt in sequence):
            # Analyze free variables
            free_vars = analyze_free_variables(sequence)

            suggestions.append({
                "op": "extract_function",
                "function_name": f"extracted_function_{i}",
                "statements": list(range(i, i + min_statements)),
                "parameters": list(free_vars),
                "insert_at": i,
                "replace_with_call": True,
                "reason": f"Sequence of {min_statements} statements at /$[{i}] could be extracted",
                "priority": "low"
            })

    return suggestions
