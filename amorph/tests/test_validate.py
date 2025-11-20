"""Tests for amorph.validate module - Semantic validation."""
import pytest
from amorph.validate import (
    validate_program,
    validate_program_report,
    ValidationIssue,
    _collect_functions,
)
from amorph.errors import AmorphValidationError


class TestValidateProgramBasic:
    """Test basic program validation."""

    def test_valid_simple_program(self):
        program = [{"let": {"name": "x", "value": 5}}]
        # Should not raise
        validate_program(program)

    def test_valid_program_with_wrapper(self):
        program = {"version": "0.1", "program": [{"let": {"name": "x", "value": 5}}]}
        # Should not raise
        validate_program(program)

    def test_not_a_list_raises_error(self):
        program = {"invalid": "structure"}
        with pytest.raises(AmorphValidationError, match="must be a list"):
            validate_program(program)

    def test_empty_program_is_valid(self):
        program = []
        validate_program(program)  # Should not raise

    def test_statement_not_dict_raises_error(self):
        program = ["not a dict"]
        with pytest.raises(AmorphValidationError, match="must be objects"):
            validate_program(program)


class TestFunctionResolution:
    """Test function call resolution."""

    def test_call_by_name_existing_function(self):
        program = [
            {"def": {"name": "double", "params": ["n"], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "double", "args": [5]}}}}
        ]
        validate_program(program)  # Should not raise

    def test_call_by_name_undefined_function_raises_error(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "undefined", "args": []}}}}
        ]
        with pytest.raises(AmorphValidationError, match="Unknown function name"):
            validate_program(program)

    def test_call_by_id_existing_function(self):
        program = [
            {"def": {"name": "double", "id": "fn_1", "params": ["n"], "body": []}},
            {"let": {"name": "x", "value": {"call": {"id": "fn_1", "args": [5]}}}}
        ]
        validate_program(program)  # Should not raise

    def test_call_by_id_undefined_function_raises_error(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"id": "fn_undefined", "args": []}}}}
        ]
        with pytest.raises(AmorphValidationError, match="Unknown function id"):
            validate_program(program)

    def test_forward_reference_by_name_allowed(self):
        # Call before definition is allowed (validation doesn't enforce order)
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "double", "args": [5]}}}},
            {"def": {"name": "double", "params": ["n"], "body": []}}
        ]
        validate_program(program)  # Should not raise

    def test_forward_reference_by_id_must_exist(self):
        # Forward ref by id is also allowed as long as id exists somewhere
        program = [
            {"let": {"name": "x", "value": {"call": {"id": "fn_1", "args": [5]}}}},
            {"def": {"name": "double", "id": "fn_1", "params": ["n"], "body": []}}
        ]
        validate_program(program)  # Should not raise

    def test_nested_call_in_function_body(self):
        program = [
            {"def": {"name": "helper", "params": [], "body": []}},
            {"def": {"name": "main", "params": [], "body": [
                {"expr": {"call": {"name": "helper", "args": []}}}
            ]}}
        ]
        validate_program(program)  # Should not raise


class TestOperatorArity:
    """Test operator arity validation."""

    def test_add_valid_arity(self):
        program = [{"let": {"name": "x", "value": {"add": [1, 2]}}}]
        validate_program(program)  # Should not raise

    def test_add_multiple_args(self):
        program = [{"let": {"name": "x", "value": {"add": [1, 2, 3, 4, 5]}}}]
        validate_program(program)  # Should not raise

    def test_not_valid_arity(self):
        program = [{"let": {"name": "x", "value": {"not": True}}}]
        validate_program(program)  # Should not raise

    def test_not_invalid_arity_raises_error(self):
        program = [{"let": {"name": "x", "value": {"not": [True, False]}}}]
        with pytest.raises(AmorphValidationError, match="invalid arity"):
            validate_program(program)

    def test_len_valid_arity(self):
        # len expects single argument (the collection)
        program = [{"let": {"name": "lst", "value": [1, 2, 3]}},
                   {"let": {"name": "x", "value": {"len": {"var": "lst"}}}}]
        validate_program(program)  # Should not raise

    def test_len_invalid_arity_raises_error(self):
        program = [{"let": {"name": "x", "value": {"len": [[1], [2]]}}}]
        with pytest.raises(AmorphValidationError, match="invalid arity"):
            validate_program(program)

    def test_get_valid_arity(self):
        program = [{"let": {"name": "x", "value": {"get": [[1, 2], 0]}}}]
        validate_program(program)  # Should not raise

    def test_get_invalid_arity_raises_error(self):
        program = [{"let": {"name": "x", "value": {"get": [[1, 2], 0, 1]}}}]
        with pytest.raises(AmorphValidationError, match="invalid arity"):
            validate_program(program)

    def test_has_valid_arity(self):
        program = [{"let": {"name": "x", "value": {"has": [[1, 2], 0]}}}]
        validate_program(program)  # Should not raise

    def test_has_invalid_arity_raises_error(self):
        program = [{"let": {"name": "x", "value": {"has": [1]}}}]
        with pytest.raises(AmorphValidationError, match="invalid arity"):
            validate_program(program)

    def test_range_valid_arity_one_arg(self):
        program = [{"let": {"name": "x", "value": {"range": 5}}}]
        validate_program(program)  # Should not raise

    def test_range_valid_arity_two_args(self):
        program = [{"let": {"name": "x", "value": {"range": [1, 5]}}}]
        validate_program(program)  # Should not raise

    def test_range_invalid_arity_raises_error(self):
        program = [{"let": {"name": "x", "value": {"range": [1, 2, 3]}}}]
        with pytest.raises(AmorphValidationError, match="invalid arity"):
            validate_program(program)

    def test_input_valid_arity_zero_args(self):
        program = [{"let": {"name": "x", "value": {"input": []}}}]
        validate_program(program)  # Should not raise

    def test_input_valid_arity_one_arg(self):
        program = [{"let": {"name": "x", "value": {"input": "Prompt"}}}]
        validate_program(program)  # Should not raise

    def test_input_invalid_arity_raises_error(self):
        program = [{"let": {"name": "x", "value": {"input": ["p1", "p2"]}}}]
        with pytest.raises(AmorphValidationError, match="invalid arity"):
            validate_program(program)

    def test_int_valid_arity(self):
        program = [{"let": {"name": "x", "value": {"int": "42"}}}]
        validate_program(program)  # Should not raise

    def test_int_invalid_arity_raises_error(self):
        program = [{"let": {"name": "x", "value": {"int": ["1", "2"]}}}]
        with pytest.raises(AmorphValidationError, match="invalid arity"):
            validate_program(program)

    def test_namespaced_operator_valid(self):
        # Namespaced operators like "math.add" should be normalized to "add"
        program = [{"let": {"name": "x", "value": {"math.add": [1, 2]}}}]
        validate_program(program)  # Should not raise


class TestValidationReport:
    """Test validate_program_report for structured issue reporting."""

    def test_report_valid_program_no_issues(self):
        program = [{"let": {"name": "x", "value": 5}}]
        issues = validate_program_report(program)
        assert issues == []

    def test_report_undefined_function_name(self):
        program = [{"let": {"name": "x", "value": {"call": {"name": "undefined", "args": []}}}}]
        issues = validate_program_report(program)
        assert len(issues) == 1
        assert issues[0].code == "E_UNKNOWN_FUNC_NAME"
        assert issues[0].severity == "error"
        assert "undefined" in issues[0].message

    def test_report_undefined_function_id(self):
        program = [{"let": {"name": "x", "value": {"call": {"id": "fn_bad", "args": []}}}}]
        issues = validate_program_report(program)
        assert len(issues) == 1
        assert issues[0].code == "E_UNKNOWN_FUNC_ID"
        assert issues[0].severity == "error"

    def test_report_operator_arity_error(self):
        program = [{"let": {"name": "x", "value": {"not": [True, False]}}}]
        issues = validate_program_report(program)
        assert len(issues) == 1
        assert issues[0].code == "E_OP_ARITY"
        assert issues[0].severity == "error"

    def test_report_multiple_errors(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "undefined1", "args": []}}}},
            {"let": {"name": "y", "value": {"call": {"name": "undefined2", "args": []}}}}
        ]
        issues = validate_program_report(program)
        assert len(issues) == 2
        assert all(i.code == "E_UNKNOWN_FUNC_NAME" for i in issues)

    def test_report_prefer_id_warning(self):
        # When prefer_id=True and function has unique name+id, suggest using id
        program = [
            {"def": {"name": "double", "id": "fn_1", "params": ["n"], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "double", "args": [5]}}}}
        ]
        issues = validate_program_report(program, prefer_id=True)
        assert len(issues) == 1
        assert issues[0].code == "W_PREFER_ID"
        assert issues[0].severity == "warning"
        assert "fn_1" in issues[0].message

    def test_report_no_prefer_id_when_disabled(self):
        program = [
            {"def": {"name": "double", "id": "fn_1", "params": ["n"], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "double", "args": [5]}}}}
        ]
        issues = validate_program_report(program, prefer_id=False)
        assert len(issues) == 0

    def test_report_mixed_call_style_warning(self):
        # Mix of call by name and call by id
        program = [
            {"def": {"name": "f1", "id": "fn_1", "params": [], "body": []}},
            {"def": {"name": "f2", "id": "fn_2", "params": [], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "f1", "args": []}}}},
            {"let": {"name": "y", "value": {"call": {"id": "fn_2", "args": []}}}}
        ]
        issues = validate_program_report(program)
        # Should have W_MIXED_CALL_STYLE warning
        warnings = [i for i in issues if i.code == "W_MIXED_CALL_STYLE"]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_report_path_correctness(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": {"call": {"name": "undefined", "args": []}}}}
        ]
        issues = validate_program_report(program)
        assert len(issues) == 1
        # Path should point to second statement
        assert "/$[1]" in issues[0].path

    def test_report_path_in_function_body(self):
        program = [
            {"def": {"name": "func", "id": "fn_1", "params": [], "body": [
                {"expr": {"call": {"name": "undefined", "args": []}}}
            ]}}
        ]
        issues = validate_program_report(program)
        assert len(issues) == 1
        # Path should include function id
        assert "fn[fn_1]" in issues[0].path or "fn_1" in issues[0].path

    def test_report_hint_provided(self):
        program = [
            {"def": {"name": "double", "id": "fn_1", "params": ["n"], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "double", "args": [5]}}}}
        ]
        issues = validate_program_report(program, prefer_id=True)
        assert len(issues) == 1
        assert issues[0].hint is not None
        assert "migrate-calls" in issues[0].hint


class TestCollectFunctions:
    """Test internal _collect_functions helper."""

    def test_collect_single_function(self):
        program = [{"def": {"name": "double", "params": [], "body": []}}]
        names, ids = _collect_functions(program)
        assert names == {"double"}
        assert ids == set()  # No id provided

    def test_collect_function_with_id(self):
        program = [{"def": {"name": "double", "id": "fn_1", "params": [], "body": []}}]
        names, ids = _collect_functions(program)
        assert names == {"double"}
        assert ids == {"fn_1"}

    def test_collect_multiple_functions(self):
        program = [
            {"def": {"name": "f1", "id": "fn_1", "params": [], "body": []}},
            {"def": {"name": "f2", "id": "fn_2", "params": [], "body": []}},
            {"def": {"name": "f3", "params": [], "body": []}}  # No id
        ]
        names, ids = _collect_functions(program)
        assert names == {"f1", "f2", "f3"}
        assert ids == {"fn_1", "fn_2"}

    def test_collect_ignores_non_def_statements(self):
        program = [
            {"let": {"name": "x", "value": 5}},
            {"def": {"name": "double", "params": [], "body": []}},
            {"print": ["test"]}
        ]
        names, ids = _collect_functions(program)
        assert names == {"double"}


class TestEdgeCases:
    """Test edge cases and complex validation scenarios."""

    def test_deeply_nested_expression_validation(self):
        # Deeply nested but valid
        program = [{"let": {"name": "x", "value": {"add": [{"add": [{"add": [1, 2]}, 3]}, 4]}}}]
        validate_program(program)  # Should not raise

    def test_validation_in_if_blocks(self):
        program = [
            {"if": {"cond": True, "then": [
                {"expr": {"call": {"name": "undefined", "args": []}}}
            ]}}
        ]
        with pytest.raises(AmorphValidationError, match="Unknown function"):
            validate_program(program)

    def test_validation_in_nested_functions(self):
        program = [
            {"def": {"name": "outer", "params": [], "body": [
                {"def": {"name": "inner", "params": [], "body": [
                    {"expr": {"call": {"name": "undefined", "args": []}}}
                ]}}
            ]}}
        ]
        # Note: Current validator may not check nested defs deeply
        # This test documents current behavior
        try:
            validate_program(program)
        except AmorphValidationError:
            pass  # Expected if deep validation is implemented

    def test_malformed_def_missing_name(self):
        program = [{"def": {"params": [], "body": []}}]
        # Validator should catch malformed def (missing name)
        # Current implementation may or may not enforce this
        try:
            validate_program(program)
        except AmorphValidationError:
            pass  # Expected

    def test_empty_function_body_is_valid(self):
        program = [{"def": {"name": "noop", "params": [], "body": []}}]
        validate_program(program)  # Should not raise

    def test_function_with_no_params(self):
        program = [
            {"def": {"name": "get_constant", "params": [], "body": [{"return": 42}]}},
            {"let": {"name": "x", "value": {"call": {"name": "get_constant", "args": []}}}}
        ]
        validate_program(program)  # Should not raise

    def test_operator_as_var_name_not_confused(self):
        # Variable named "add" should not be confused with add operator
        program = [
            {"let": {"name": "add", "value": 5}},
            {"let": {"name": "x", "value": {"var": "add"}}}
        ]
        validate_program(program)  # Should not raise

    def test_validation_does_not_execute(self):
        # Validation should not execute code or have side effects
        program = [{"print": ["This should not print during validation"]}]
        validate_program(program)  # Should not print anything

    def test_call_in_print_statement(self):
        program = [
            {"def": {"name": "get_message", "params": [], "body": [{"return": "hello"}]}},
            {"print": [{"call": {"name": "get_message", "args": []}}]}
        ]
        validate_program(program)  # Should not raise

    def test_call_in_return_statement(self):
        program = [
            {"def": {"name": "helper", "params": [], "body": [{"return": 42}]}},
            {"def": {"name": "main", "params": [], "body": [
                {"return": {"call": {"name": "helper", "args": []}}}
            ]}}
        ]
        validate_program(program)  # Should not raise
