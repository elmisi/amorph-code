"""Type system for Amorph - Optional type inference and checking.

This module provides an optional type system for Amorph programs.
When enabled with --check-types, it performs static type analysis
and reports type errors before execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum, auto


class TypeKind(Enum):
    """Type categories."""
    INT = auto()
    FLOAT = auto()
    STR = auto()
    BOOL = auto()
    NULL = auto()
    LIST = auto()
    OBJECT = auto()
    FUNCTION = auto()
    ANY = auto()
    UNKNOWN = auto()


@dataclass
class Type:
    """Base type class."""
    kind: TypeKind

    def __str__(self) -> str:
        return self.kind.name.lower()

    def is_compatible_with(self, other: Type) -> bool:
        """Check if this type is compatible with other."""
        if self.kind == TypeKind.ANY or other.kind == TypeKind.ANY:
            return True
        if self.kind == TypeKind.UNKNOWN or other.kind == TypeKind.UNKNOWN:
            return True  # Unknown is compatible with anything (conservative)
        return self.kind == other.kind


@dataclass
class IntType(Type):
    """Integer type."""
    def __init__(self):
        super().__init__(TypeKind.INT)


@dataclass
class FloatType(Type):
    """Float type."""
    def __init__(self):
        super().__init__(TypeKind.FLOAT)


@dataclass
class StrType(Type):
    """String type."""
    def __init__(self):
        super().__init__(TypeKind.STR)


@dataclass
class BoolType(Type):
    """Boolean type."""
    def __init__(self):
        super().__init__(TypeKind.BOOL)


@dataclass
class NullType(Type):
    """Null type."""
    def __init__(self):
        super().__init__(TypeKind.NULL)


@dataclass
class ListType(Type):
    """List type with element type."""
    element_type: Type

    def __init__(self, element_type: Type):
        super().__init__(TypeKind.LIST)
        self.element_type = element_type

    def __str__(self) -> str:
        return f"list[{self.element_type}]"


@dataclass
class ObjectType(Type):
    """Object/dict type."""
    def __init__(self):
        super().__init__(TypeKind.OBJECT)


@dataclass
class FunctionType(Type):
    """Function type with parameter and return types."""
    param_types: List[Type]
    return_type: Type

    def __init__(self, param_types: List[Type], return_type: Type):
        super().__init__(TypeKind.FUNCTION)
        self.param_types = param_types
        self.return_type = return_type

    def __str__(self) -> str:
        params = ", ".join(str(t) for t in self.param_types)
        return f"({params}) -> {self.return_type}"


@dataclass
class AnyType(Type):
    """Any type - accepts anything."""
    def __init__(self):
        super().__init__(TypeKind.ANY)


@dataclass
class UnknownType(Type):
    """Unknown type - type cannot be inferred."""
    def __init__(self):
        super().__init__(TypeKind.UNKNOWN)


class TypeEnv:
    """Type environment for tracking variable types."""

    def __init__(self, parent: Optional[TypeEnv] = None):
        self.vars: Dict[str, Type] = {}
        self.parent = parent

    def define(self, name: str, typ: Type) -> None:
        """Define variable with type in current scope."""
        self.vars[name] = typ

    def lookup(self, name: str) -> Type:
        """Lookup variable type, searching parent scopes."""
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return UnknownType()  # Variable not found in type env

    def push_scope(self) -> TypeEnv:
        """Create child scope."""
        return TypeEnv(parent=self)


class TypeError:
    """Type error found during inference."""

    def __init__(self, code: str, message: str, path: str, hint: Optional[str] = None):
        self.code = code
        self.message = message
        self.path = path
        self.hint = hint

    def __repr__(self) -> str:
        return f"TypeError({self.code}: {self.message} at {self.path})"


class TypeInferencer:
    """Type inference engine for Amorph programs."""

    def __init__(self):
        self.errors: List[TypeError] = []
        self.functions: Dict[str, FunctionType] = {}

    def infer_expr(self, expr: Any, env: TypeEnv, path: str) -> Type:
        """Infer type of expression."""
        # Literals
        if isinstance(expr, int):
            return IntType()
        if isinstance(expr, float):
            return FloatType()
        if isinstance(expr, str):
            return StrType()
        if isinstance(expr, bool):
            return BoolType()
        if expr is None:
            return NullType()

        # List literal
        if isinstance(expr, list):
            if not expr:
                return ListType(UnknownType())
            # Infer element types
            elem_types = [self.infer_expr(e, env, f"{path}/$[{i}]") for i, e in enumerate(expr)]
            # For simplicity, use first element type
            return ListType(elem_types[0] if elem_types else UnknownType())

        # Dict expressions
        if isinstance(expr, dict):
            # Variable reference
            if "var" in expr:
                var_name = expr["var"]
                return env.lookup(var_name)

            # Function call
            if "call" in expr:
                # TODO: lookup function type and check args
                return UnknownType()

            # Operators
            if len(expr) == 1:
                op, val = next(iter(expr.items()))
                return self.infer_operator(op, val, env, path)

            # Object literal
            return ObjectType()

        return UnknownType()

    def infer_operator(self, op: str, val: Any, env: TypeEnv, path: str) -> Type:
        """Infer type of operator application."""
        op = op.split(".")[-1]  # Normalize namespaced operators

        # Arithmetic operators
        if op in ("add", "sub", "mul", "div", "mod", "pow"):
            # Check that all args are numeric
            if isinstance(val, list):
                arg_types = [self.infer_expr(v, env, f"{path}/{op}/$[{i}]") for i, v in enumerate(val)]
            else:
                arg_types = [self.infer_expr(val, env, f"{path}/{op}")]

            # Special case for add: can be int+int or str+str
            if op == "add":
                if all(t.kind == TypeKind.INT for t in arg_types):
                    return IntType()
                if all(t.kind in (TypeKind.INT, TypeKind.FLOAT) for t in arg_types):
                    return FloatType()
                if all(t.kind == TypeKind.STR for t in arg_types):
                    return StrType()
                # Type error
                self.errors.append(TypeError(
                    "E_TYPE_MISMATCH",
                    f"add expects all numeric or all string, got {[str(t) for t in arg_types]}",
                    path,
                    "Convert arguments to same type"
                ))
                return UnknownType()

            # Other arithmetic ops: numeric only
            if any(t.kind not in (TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN, TypeKind.ANY) for t in arg_types):
                self.errors.append(TypeError(
                    "E_TYPE_MISMATCH",
                    f"{op} expects numeric arguments, got {[str(t) for t in arg_types]}",
                    path
                ))
                return UnknownType()

            # Result type: float if any arg is float, else int
            if any(t.kind == TypeKind.FLOAT for t in arg_types):
                return FloatType()
            return IntType()

        # Comparison operators
        if op in ("eq", "ne", "lt", "le", "gt", "ge"):
            # Return boolean
            return BoolType()

        # Logic operators
        if op in ("and", "or"):
            return BoolType()

        if op == "not":
            return BoolType()

        # Collection operators
        if op == "list":
            # Returns a list
            return ListType(UnknownType())

        if op == "len":
            return IntType()

        if op == "get":
            # Returns unknown type (depends on container)
            return UnknownType()

        if op == "has":
            return BoolType()

        if op == "concat":
            # Can concatenate lists or strings
            return UnknownType()

        if op == "range":
            return ListType(IntType())

        if op == "input":
            return StrType()

        if op == "int":
            return IntType()

        # Unknown operator
        return UnknownType()

    def check_program(self, program: List[Dict[str, Any]]) -> List[TypeError]:
        """Check types in entire program and return errors."""
        self.errors = []
        env = TypeEnv()

        # First pass: collect function signatures
        for i, stmt in enumerate(program):
            if "def" in stmt and isinstance(stmt["def"], dict):
                d = stmt["def"]
                fn_name = d.get("name")
                params = d.get("params", [])
                # For now, assume all params and return are Any
                fn_type = FunctionType(
                    [AnyType() for _ in params],
                    AnyType()
                )
                if fn_name:
                    self.functions[fn_name] = fn_type

        # Second pass: check statements
        for i, stmt in enumerate(program):
            self.check_stmt(stmt, env, f"/$[{i}]")

        return self.errors

    def check_stmt(self, stmt: Dict[str, Any], env: TypeEnv, path: str) -> None:
        """Check types in a statement."""
        if "let" in stmt:
            spec = stmt["let"]
            name = spec.get("name")
            value = spec.get("value")
            if value is not None:
                typ = self.infer_expr(value, env, f"{path}/let/value")
                if name:
                    env.define(name, typ)

        if "set" in stmt:
            spec = stmt["set"]
            value = spec.get("value")
            if value is not None:
                self.infer_expr(value, env, f"{path}/set/value")

        if "return" in stmt:
            self.infer_expr(stmt["return"], env, f"{path}/return")

        if "expr" in stmt:
            self.infer_expr(stmt["expr"], env, f"{path}/expr")

        if "if" in stmt:
            spec = stmt["if"]
            if "cond" in spec:
                cond_type = self.infer_expr(spec["cond"], env, f"{path}/if/cond")
                # Condition should be boolean-compatible (for now, accept any)

            # Check then/else blocks
            if "then" in spec and isinstance(spec["then"], list):
                then_env = env.push_scope()
                for j, s in enumerate(spec["then"]):
                    self.check_stmt(s, then_env, f"{path}/if/then/$[{j}]")

            if "else" in spec and isinstance(spec["else"], list):
                else_env = env.push_scope()
                for j, s in enumerate(spec["else"]):
                    self.check_stmt(s, else_env, f"{path}/if/else/$[{j}]")

        if "def" in stmt:
            spec = stmt["def"]
            params = spec.get("params", [])
            body = spec.get("body", [])

            # Create new scope for function body
            fn_env = env.push_scope()
            for param in params:
                fn_env.define(param, AnyType())

            # Check body
            for j, s in enumerate(body):
                self.check_stmt(s, fn_env, f"{path}/def/body/$[{j}]")
