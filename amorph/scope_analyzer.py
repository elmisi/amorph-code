"""Scope analysis for Amorph programs - Detect undefined/unused variables."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from .validate import ValidationIssue


@dataclass
class Scope:
    """Represents a lexical scope."""
    variables: Set[str]
    parent: Scope | None = None

    def define(self, name: str) -> None:
        """Define variable in this scope."""
        self.variables.add(name)

    def is_defined(self, name: str) -> bool:
        """Check if variable is defined in this or parent scopes."""
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.is_defined(name)
        return False

    def is_defined_locally(self, name: str) -> bool:
        """Check if variable is defined only in this scope."""
        return name in self.variables

    def push_scope(self) -> Scope:
        """Create child scope."""
        return Scope(variables=set(), parent=self)


class ScopeAnalyzer:
    """Analyzes variable scoping in Amorph programs."""

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def analyze(self, program: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Analyze program for scope issues."""
        self.issues = []
        global_scope = Scope(variables=set())

        for i, stmt in enumerate(program):
            self._analyze_stmt(stmt, global_scope, [("$", i)])

        return self.issues

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

    def _analyze_expr(self, expr: Any, scope: Scope, path: List[Tuple[str, int]]) -> None:
        """Analyze expression for variable references."""
        if isinstance(expr, dict):
            # Variable reference
            if "var" in expr:
                var_name = expr["var"]
                if not scope.is_defined(var_name):
                    self.issues.append(ValidationIssue(
                        code="E_UNDEFINED_VAR",
                        message=f"Variable '{var_name}' used before definition",
                        path=self._path_to_string(path),
                        severity="error",
                        hint=f"Add 'let {var_name}' before use or check for typos"
                    ))

            # Recursively check nested expressions
            for k, v in expr.items():
                if k != "var":  # Already handled
                    self._analyze_expr(v, scope, path + [(k, -1)])

        elif isinstance(expr, list):
            for i, item in enumerate(expr):
                self._analyze_expr(item, scope, path + [("$", i)])

    def _analyze_stmt(self, stmt: Dict[str, Any], scope: Scope, path: List[Tuple[str, int]]) -> None:
        """Analyze statement for scope issues."""
        if not isinstance(stmt, dict):
            return

        # let statement
        if "let" in stmt and isinstance(stmt["let"], dict):
            spec = stmt["let"]
            var_name = spec.get("name")
            value = spec.get("value")

            # Check for shadowing
            if var_name and scope.is_defined_locally(var_name):
                self.issues.append(ValidationIssue(
                    code="W_VARIABLE_SHADOW",
                    message=f"Variable '{var_name}' shadows outer definition",
                    path=self._path_to_string(path),
                    severity="warning",
                    hint="Use different name or rename outer variable"
                ))

            # Analyze value expression
            if value is not None:
                self._analyze_expr(value, scope, path + [("let", -1), ("value", -1)])

            # Define in scope after analyzing value (can't use self in definition)
            if var_name:
                scope.define(var_name)

        # set statement
        if "set" in stmt and isinstance(stmt["set"], dict):
            spec = stmt["set"]
            var_name = spec.get("name")
            value = spec.get("value")

            # Check that variable was defined
            if var_name and not scope.is_defined(var_name):
                self.issues.append(ValidationIssue(
                    code="E_UNDEFINED_VAR",
                    message=f"Cannot set undefined variable '{var_name}'",
                    path=self._path_to_string(path),
                    severity="error",
                    hint=f"Use 'let' to define '{var_name}' first"
                ))

            # Analyze value
            if value is not None:
                self._analyze_expr(value, scope, path + [("set", -1), ("value", -1)])

        # def statement
        if "def" in stmt and isinstance(stmt["def"], dict):
            spec = stmt["def"]
            fn_name = spec.get("name")
            params = spec.get("params", [])
            body = spec.get("body", [])

            # Create new scope for function body
            fn_scope = scope.push_scope()

            # Add parameters to function scope
            for param in params:
                fn_scope.define(param)

            # Analyze body
            fn_id = spec.get("id", fn_name)
            for j, s in enumerate(body):
                self._analyze_stmt(s, fn_scope, [("fn", fn_id), ("body", j)])

        # if statement
        if "if" in stmt and isinstance(stmt["if"], dict):
            spec = stmt["if"]

            # Analyze condition
            if "cond" in spec:
                self._analyze_expr(spec["cond"], scope, path + [("if", -1), ("cond", -1)])

            # Analyze then block (new scope)
            if "then" in spec and isinstance(spec["then"], list):
                then_scope = scope.push_scope()
                for j, s in enumerate(spec["then"]):
                    self._analyze_stmt(s, then_scope, path + [("if", -1), ("then", -1), ("$", j)])

            # Analyze else block (new scope)
            if "else" in spec and isinstance(spec["else"], list):
                else_scope = scope.push_scope()
                for j, s in enumerate(spec["else"]):
                    self._analyze_stmt(s, else_scope, path + [("if", -1), ("else", -1), ("$", j)])

        # return statement
        if "return" in stmt:
            self._analyze_expr(stmt["return"], scope, path + [("return", -1)])

        # expr statement
        if "expr" in stmt:
            self._analyze_expr(stmt["expr"], scope, path + [("expr", -1)])

        # print statement
        if "print" in stmt:
            payload = stmt["print"]
            if isinstance(payload, list):
                for i, item in enumerate(payload):
                    self._analyze_expr(item, scope, path + [("print", -1), ("$", i)])
            else:
                self._analyze_expr(payload, scope, path + [("print", -1)])


def analyze_scopes(program: List[Dict[str, Any]]) -> List[ValidationIssue]:
    """Analyze program for scope issues (undefined vars, shadowing)."""
    analyzer = ScopeAnalyzer()
    return analyzer.analyze(program)
