"""Smart edit suggestions for Amorph programs.

This module analyzes programs and suggests improvements:
- Add missing UIDs
- Migrate call styles
- Extract functions
- Rename variables
- Fix errors
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .refactor import (
    VariableAnalyzer,
    suggest_variable_rename,
    suggest_extract_function,
    analyze_free_variables
)
from .errors import AmorphRuntimeError


@dataclass
class EditSuggestion:
    """A suggested edit operation."""
    operation: str       # "rename_variable", "extract_function", etc.
    reason: str          # Why this is suggested
    edit_spec: Dict      # Ready-to-use edit operation
    priority: str        # "high" | "medium" | "low"
    estimated_impact: str  # "Breaking change" | "Safe" | "Optimization"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "operation": self.operation,
            "reason": self.reason,
            "edit_spec": self.edit_spec,
            "priority": self.priority,
            "estimated_impact": self.estimated_impact
        }


class SuggestionEngine:
    """Analyzes programs and suggests improvements."""

    def suggest_improvements(self, program: List[Dict[str, Any]]) -> List[EditSuggestion]:
        """Analyze program and suggest actionable improvements."""
        suggestions = []

        # Suggestion 1: Functions without id -> add id
        for i, stmt in enumerate(program):
            if "def" in stmt and isinstance(stmt["def"], dict):
                if "id" not in stmt["def"]:
                    fn_name = stmt["def"].get("name", "anonymous")
                    suggestions.append(EditSuggestion(
                        operation="add_uid",
                        reason=f"Function '{fn_name}' lacks stable id for robust references",
                        edit_spec={
                            "op": "add_uid",
                            "path": "/$[{i}]/def",
                            "deep": False
                        },
                        priority="medium",
                        estimated_impact="Safe"
                    ))

        # Suggestion 2: Statements without id -> add id
        missing_ids = sum(1 for stmt in program if "id" not in stmt)
        if missing_ids > 0:
            suggestions.append(EditSuggestion(
                operation="add_uid_all",
                reason=f"{missing_ids} statements lack ids for precise targeting",
                edit_spec={
                    "op": "add_uid",
                    "deep": True
                },
                priority="low",
                estimated_impact="Safe"
            ))

        # Suggestion 3: Mixed call style -> migrate to id
        has_name_calls = False
        has_id_calls = False

        def check_calls(expr):
            nonlocal has_name_calls, has_id_calls
            if isinstance(expr, dict):
                if "call" in expr and isinstance(expr["call"], dict):
                    if "name" in expr["call"]:
                        has_name_calls = True
                    if "id" in expr["call"]:
                        has_id_calls = True
                for v in expr.values():
                    check_calls(v)
            elif isinstance(expr, list):
                for item in expr:
                    check_calls(item)

        for stmt in program:
            check_calls(stmt)

        if has_name_calls and has_id_calls:
            suggestions.append(EditSuggestion(
                operation="migrate_calls",
                reason="Mixed call styles (name and id) found - inconsistent references",
                edit_spec={
                    "op": "migrate_calls",
                    "to": "id"
                },
                priority="medium",
                estimated_impact="Safe"
            ))

        # Suggestion 4: Variable renames
        var_rename_suggestions = suggest_variable_rename(program)
        for sug in var_rename_suggestions:
            suggestions.append(EditSuggestion(
                operation="rename_variable",
                reason=sug["reason"],
                edit_spec=sug,
                priority=sug["priority"],
                estimated_impact="Safe"
            ))

        # Suggestion 5: Extract function opportunities
        extract_suggestions = suggest_extract_function(program, min_statements=3)
        for sug in extract_suggestions:
            suggestions.append(EditSuggestion(
                operation="extract_function",
                reason=sug["reason"],
                edit_spec=sug,
                priority=sug["priority"],
                estimated_impact="Optimization"
            ))

        return suggestions


def suggest_fix_for_error(error: AmorphRuntimeError, program: List[Dict[str, Any]]) -> List[EditSuggestion]:
    """
    Suggest edits to fix a runtime error.

    Analyzes the error message and context to propose fixes.
    """
    suggestions = []
    error_msg = str(error)

    # Variable not found error
    if "Variable not found" in error_msg:
        var_name = error_msg.split(":")[-1].strip()

        # Suggestion 1: Add let statement
        suggestions.append(EditSuggestion(
            operation="insert_before",
            reason=f"Add missing variable '{var_name}'",
            edit_spec={
                "op": "insert_before",
                "path": error.context.path if hasattr(error, 'context') and error.context else "/$[0]",
                "node": {
                    "let": {
                        "name": var_name,
                        "value": None  # User needs to fill this
                    }
                }
            },
            priority="high",
            estimated_impact="Fixes error"
        ))

        # Suggestion 2: Check for similar variable names (typo detection)
        analyzer = VariableAnalyzer()
        refs = analyzer.analyze_program(program)

        for defined_var in refs.keys():
            # Simple similarity: check if only 1-2 chars different
            if len(var_name) > 2 and len(defined_var) > 2:
                diff = sum(c1 != c2 for c1, c2 in zip(var_name, defined_var))
                if diff <= 2 and abs(len(var_name) - len(defined_var)) <= 1:
                    suggestions.append(EditSuggestion(
                        operation="rename_usage",
                        reason=f"Did you mean '{defined_var}'? (similar to '{var_name}')",
                        edit_spec={
                            "op": "rename_variable",
                            "old_name": var_name,
                            "new_name": defined_var,
                            "scope": "all"
                        },
                        priority="medium",
                        estimated_impact="Fixes error if typo"
                    ))

    # Function not defined error
    if "Function not defined" in error_msg or "Function id not defined" in error_msg:
        # Extract function name
        parts = error_msg.split(":")
        if len(parts) > 1:
            fn_name = parts[-1].strip()

            suggestions.append(EditSuggestion(
                operation="add_function",
                reason=f"Add missing function '{fn_name}'",
                edit_spec={
                    "op": "add_function",
                    "name": fn_name,
                    "params": [],  # User needs to specify
                    "body": [{"return": None}]  # Stub
                },
                priority="high",
                estimated_impact="Fixes error"
            ))

    # Division by zero error
    if "division by zero" in error_msg.lower():
        suggestions.append(EditSuggestion(
            operation="add_check",
            reason="Add zero-check before division",
            edit_spec={
                "op": "wrap_in_if",  # This would need to be implemented
                "condition": {"ne": ["divisor", 0]},
                "error_handler": {"return": None}
            },
            priority="high",
            estimated_impact="Prevents error"
        ))

    return suggestions


def analyze_program_health(program: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze program and return health metrics.

    Returns metrics like:
    - Number of statements
    - Number of functions
    - Average function length
    - Variable usage statistics
    - Complexity metrics
    """
    metrics = {
        "total_statements": len(program),
        "total_functions": 0,
        "total_variables": 0,
        "functions_with_id": 0,
        "statements_with_id": 0,
        "avg_function_length": 0,
        "max_nesting_depth": 0,
        "unique_variables": set(),
        "call_style": "mixed"  # "name" | "id" | "mixed"
    }

    has_name_calls = False
    has_id_calls = False

    def measure_nesting(expr, depth=0):
        max_depth = depth
        if isinstance(expr, dict):
            for v in expr.values():
                max_depth = max(max_depth, measure_nesting(v, depth + 1))
        elif isinstance(expr, list):
            for item in expr:
                max_depth = max(max_depth, measure_nesting(item, depth + 1))
        return max_depth

    function_lengths = []

    for stmt in program:
        if "id" in stmt:
            metrics["statements_with_id"] += 1

        if "def" in stmt:
            metrics["total_functions"] += 1
            if "id" in stmt["def"]:
                metrics["functions_with_id"] += 1
            body_len = len(stmt["def"].get("body", []))
            function_lengths.append(body_len)

            # Check nesting in function body
            for s in stmt["def"].get("body", []):
                depth = measure_nesting(s)
                metrics["max_nesting_depth"] = max(metrics["max_nesting_depth"], depth)

        # Check for call styles
        def check_call_style(expr):
            nonlocal has_name_calls, has_id_calls
            if isinstance(expr, dict):
                if "call" in expr and isinstance(expr["call"], dict):
                    if "name" in expr["call"]:
                        has_name_calls = True
                    if "id" in expr["call"]:
                        has_id_calls = True
                for v in expr.values():
                    check_call_style(v)
            elif isinstance(expr, list):
                for item in expr:
                    check_call_style(item)

        check_call_style(stmt)

    # Analyze variables
    analyzer = VariableAnalyzer()
    refs = analyzer.analyze_program(program)
    metrics["total_variables"] = len(refs)
    metrics["unique_variables"] = list(refs.keys())

    # Average function length
    if function_lengths:
        metrics["avg_function_length"] = sum(function_lengths) / len(function_lengths)

    # Call style
    if has_name_calls and has_id_calls:
        metrics["call_style"] = "mixed"
    elif has_id_calls:
        metrics["call_style"] = "id"
    elif has_name_calls:
        metrics["call_style"] = "name"
    else:
        metrics["call_style"] = "none"

    return metrics
