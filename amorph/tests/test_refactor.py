"""Tests for amorph.refactor module - Variable refactoring."""
import pytest
from amorph.refactor import (
    VariableAnalyzer,
    op_rename_variable,
    op_extract_function,
    find_variable_references,
    analyze_free_variables,
)
from amorph.edits import EditError


class TestVariableAnalyzer:
    """Test variable reference analysis."""

    def test_analyze_simple_let(self):
        program = [{"let": {"name": "x", "value": 5}}]
        analyzer = VariableAnalyzer()
        refs = analyzer.analyze_program(program)

        assert "x" in refs
        assert len(refs["x"]) == 1
        assert refs["x"][0].ref_type == "definition"
        assert refs["x"][0].scope_id == "global"

    def test_analyze_variable_usage(self):
        program = [
            {"let": {"name": "x", "value": 5}},
            {"let": {"name": "y", "value": {"var": "x"}}}
        ]
        analyzer = VariableAnalyzer()
        refs = analyzer.analyze_program(program)

        assert "x" in refs
        assert len(refs["x"]) == 2  # 1 definition + 1 read
        assert refs["x"][0].ref_type == "definition"
        assert refs["x"][1].ref_type == "read"

    def test_analyze_set_statement(self):
        program = [
            {"let": {"name": "x", "value": 0}},
            {"set": {"name": "x", "value": 10}}
        ]
        analyzer = VariableAnalyzer()
        refs = analyzer.analyze_program(program)

        assert len(refs["x"]) == 2
        assert refs["x"][0].ref_type == "definition"
        assert refs["x"][1].ref_type == "write"

    def test_analyze_function_parameters(self):
        program = [
            {"def": {"name": "func", "id": "fn_1", "params": ["a", "b"], "body": [
                {"return": {"add": [{"var": "a"}, {"var": "b"}]}}
            ]}}
        ]
        analyzer = VariableAnalyzer()
        refs = analyzer.analyze_program(program)

        assert "a" in refs
        assert "b" in refs
        # Each param: 1 definition + 1 read
        assert len(refs["a"]) == 2
        assert refs["a"][0].ref_type == "definition"
        assert refs["a"][1].ref_type == "read"
        assert refs["a"][0].scope_id == "fn_1"

    def test_analyze_nested_scopes(self):
        program = [
            {"let": {"name": "global_var", "value": 1}},
            {"def": {"name": "func", "params": ["local_var"], "body": [
                {"let": {"name": "inner_var", "value": {"var": "local_var"}}},
                {"return": {"add": [{"var": "inner_var"}, {"var": "global_var"}]}}
            ]}}
        ]
        analyzer = VariableAnalyzer()
        refs = analyzer.analyze_program(program)

        assert "global_var" in refs
        assert "local_var" in refs
        assert "inner_var" in refs

        # Check scopes
        global_refs = [r for r in refs["global_var"] if r.scope_id == "global"]
        assert len(global_refs) >= 1


class TestRenameVariable:
    """Test variable renaming operation."""

    def test_rename_simple(self):
        program = [
            {"let": {"name": "x", "value": 5}},
            {"let": {"name": "y", "value": {"var": "x"}}}
        ]
        spec = {"old_name": "x", "new_name": "count", "scope": "all"}
        changed = op_rename_variable(program, spec)

        assert changed == 2  # definition + usage
        assert program[0]["let"]["name"] == "count"
        assert program[1]["let"]["value"]["var"] == "count"

    def test_rename_multiple_usages(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": {"var": "x"}}},
            {"let": {"name": "z", "value": {"add": [{"var": "x"}, {"var": "y"}]}}},
            {"set": {"name": "x", "value": 10}}
        ]
        spec = {"old_name": "x", "new_name": "counter", "scope": "all"}
        changed = op_rename_variable(program, spec)

        assert changed >= 3  # At least definition + 2 usages + set
        assert program[0]["let"]["name"] == "counter"
        assert program[1]["let"]["value"]["var"] == "counter"
        assert program[2]["let"]["value"]["add"][0]["var"] == "counter"
        assert program[3]["set"]["name"] == "counter"

    def test_rename_in_function_scope(self):
        program = [
            {"let": {"name": "x", "value": 1}},  # Global x
            {"def": {"name": "func", "id": "fn_1", "params": ["x"], "body": [  # Local x (parameter)
                {"return": {"var": "x"}}
            ]}}
        ]
        # Rename only in function scope
        spec = {"old_name": "x", "new_name": "param", "scope": "fn_1"}
        changed = op_rename_variable(program, spec)

        assert changed >= 1
        # Global x unchanged
        assert program[0]["let"]["name"] == "x"
        # Function parameter renamed
        assert program[1]["def"]["params"][0] == "param"
        assert program[1]["def"]["body"][0]["return"]["var"] == "param"

    def test_rename_nonexistent_variable_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]
        spec = {"old_name": "nonexistent", "new_name": "new", "scope": "all"}

        with pytest.raises(EditError):
            op_rename_variable(program, spec)

    def test_rename_missing_params_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]

        # Missing new_name
        with pytest.raises(EditError):
            op_rename_variable(program, {"old_name": "x", "scope": "all"})

        # Missing old_name
        with pytest.raises(EditError):
            op_rename_variable(program, {"new_name": "y", "scope": "all"})


class TestExtractFunction:
    """Test function extraction operation."""

    def test_extract_simple_sequence(self):
        program = [
            {"let": {"name": "a", "value": 1}},
            {"let": {"name": "b", "value": 2}},
            {"let": {"name": "c", "value": 3}},
            {"print": ["done"]}
        ]
        spec = {
            "function_name": "initialize",
            "function_id": "fn_init",
            "statements": [0, 1, 2],  # First 3 statements
            "parameters": [],
            "insert_at": 0,
            "replace_with_call": True
        }
        op_extract_function(program, spec)

        # Should have: function def + call/expr + print
        # Total: 3 items (def at 0, call at 1, print at 2)
        assert len(program) >= 2
        assert "def" in program[0]
        assert program[0]["def"]["name"] == "initialize"
        assert program[0]["def"]["id"] == "fn_init"
        assert len(program[0]["def"]["body"]) == 3

    def test_extract_with_parameters(self):
        program = [
            {"let": {"name": "x", "value": 10}},  # Free variable
            {"let": {"name": "y", "value": {"mul": [{"var": "x"}, 2]}}},
            {"let": {"name": "z", "value": {"add": [{"var": "y"}, 1]}}}
        ]
        # Extract statements 1-2 which use x
        spec = {
            "function_name": "process",
            "statements": [1, 2],
            "parameters": ["x"],  # x is free variable
            "insert_at": 1,
            "replace_with_call": True
        }
        op_extract_function(program, spec)

        # Should have: let x, def process, call process
        assert len(program) == 3
        assert "def" in program[1]
        assert program[1]["def"]["params"] == ["x"]

    def test_extract_missing_function_name_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]
        spec = {"statements": [0], "parameters": []}

        with pytest.raises(EditError):
            op_extract_function(program, spec)

    def test_extract_invalid_indices_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]
        spec = {
            "function_name": "func",
            "statements": [0, 2],  # Non-consecutive
            "parameters": []
        }

        with pytest.raises(EditError):
            op_extract_function(program, spec)


class TestFindVariableReferences:
    """Test finding variable references."""

    def test_find_simple(self):
        program = [
            {"let": {"name": "x", "value": 5}},
            {"let": {"name": "y", "value": {"var": "x"}}}
        ]
        refs = find_variable_references(program, "x")

        assert len(refs) == 2
        assert refs[0].var_name == "x"

    def test_find_in_specific_scope(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"def": {"name": "func", "id": "fn_1", "params": ["x"], "body": [
                {"return": {"var": "x"}}
            ]}}
        ]
        # Find only in function scope
        refs = find_variable_references(program, "x", scope="fn_1")

        assert len(refs) >= 1
        assert all(r.scope_id == "fn_1" for r in refs)

    def test_find_nonexistent_variable(self):
        program = [{"let": {"name": "x", "value": 1}}]
        refs = find_variable_references(program, "nonexistent")

        assert refs == []


class TestAnalyzeFreeVariables:
    """Test free variable analysis."""

    def test_no_free_variables(self):
        statements = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": {"var": "x"}}}
        ]
        free = analyze_free_variables(statements)

        assert free == set()  # x is defined before use

    def test_free_variable_simple(self):
        statements = [
            {"let": {"name": "y", "value": {"var": "x"}}}  # x not defined
        ]
        free = analyze_free_variables(statements)

        assert free == {"x"}

    def test_multiple_free_variables(self):
        statements = [
            {"let": {"name": "result", "value": {"add": [{"var": "a"}, {"var": "b"}]}}}
        ]
        free = analyze_free_variables(statements)

        assert free == {"a", "b"}

    def test_defined_then_used_not_free(self):
        statements = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}},
            {"let": {"name": "z", "value": {"add": [{"var": "x"}, {"var": "y"}]}}}
        ]
        free = analyze_free_variables(statements)

        assert free == set()  # All defined before use
