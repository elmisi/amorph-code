"""Tests for amorph.engine module - VM execution."""
import pytest
from amorph.engine import VM, run_program, _Return
from amorph.errors import AmorphRuntimeError, AmorphValidationError
from amorph.io import QuietIO


class TestArithmeticOperators:
    """Test arithmetic operators: add, sub, mul, div, mod, pow."""

    def test_add_two_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"add": [1, 2]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 3

    def test_add_multiple_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"add": [1, 2, 3, 4, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 15

    def test_add_with_zero(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"add": [0, 5, 0]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 5

    def test_sub_two_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"sub": [10, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 7

    def test_sub_multiple_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"sub": [100, 20, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 75

    def test_sub_negative_result(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"sub": [5, 10]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == -5

    def test_mul_two_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"mul": [3, 4]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 12

    def test_mul_multiple_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"mul": [2, 3, 4]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 24

    def test_mul_with_zero(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"mul": [5, 0, 10]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 0

    def test_mul_with_one(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"mul": [1, 7, 1]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 7

    def test_div_two_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"div": [10, 2]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 5

    def test_div_float_result(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"div": [10, 3]}}}]
        quiet_vm.run(program)
        assert abs(quiet_vm.get("x") - 3.333333) < 0.0001

    def test_div_by_zero_raises_error(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"div": [10, 0]}}}]
        with pytest.raises(ZeroDivisionError):
            quiet_vm.run(program)

    def test_mod_positive_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"mod": [10, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 1

    def test_mod_exact_division(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"mod": [10, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 0

    def test_pow_positive_exponent(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"pow": [2, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 8

    def test_pow_zero_exponent(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"pow": [5, 0]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 1

    def test_pow_negative_exponent(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"pow": [2, -1]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 0.5


class TestComparisonOperators:
    """Test comparison operators: eq, ne, lt, le, gt, ge."""

    def test_eq_equal_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"eq": [5, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_eq_different_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"eq": [5, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_eq_chain_all_equal(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"eq": [5, 5, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_eq_chain_not_all_equal(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"eq": [5, 5, 6]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_ne_different_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"ne": [5, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_ne_equal_numbers(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"ne": [5, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_lt_less_than(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"lt": [3, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_lt_not_less_than(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"lt": [5, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_lt_chain(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"lt": [1, 2, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_le_less_than_or_equal(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"le": [3, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_le_equal(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"le": [5, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_gt_greater_than(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"gt": [5, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_ge_greater_than_or_equal(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"ge": [5, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True


class TestLogicOperators:
    """Test logic operators: and, or, not."""

    def test_and_both_true(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"and": [True, True]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_and_first_false(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"and": [False, True]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_and_multiple_true(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"and": [True, True, True]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_and_with_lazy_evaluation(self, quiet_vm):
        # NOTE: Current implementation evaluates all args eagerly
        # True short-circuit would be an optimization for later
        program = [
            {"let": {"name": "flag", "value": False}},
            {"let": {"name": "x", "value": {"and": [{"var": "flag"}, True]}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_or_first_true(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"or": [True, False]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_or_both_false(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"or": [False, False]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_or_with_lazy_evaluation(self, quiet_vm):
        # NOTE: Current implementation evaluates all args eagerly
        program = [
            {"let": {"name": "flag", "value": True}},
            {"let": {"name": "x", "value": {"or": [{"var": "flag"}, False]}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_not_true(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"not": True}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_not_false(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"not": False}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_not_with_truthy_value(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"not": 5}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_not_with_falsy_value(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"not": 0}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True


class TestVariables:
    """Test variable operations: let, set, get."""

    def test_let_simple(self, quiet_vm):
        program = [{"let": {"name": "x", "value": 42}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 42

    def test_let_with_expression(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"add": [10, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 15

    def test_multiple_lets(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 10}},
            {"let": {"name": "y", "value": 20}},
            {"let": {"name": "z", "value": {"add": [{"var": "x"}, {"var": "y"}]}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 10
        assert quiet_vm.get("y") == 20
        assert quiet_vm.get("z") == 30

    def test_set_existing_variable(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 10}},
            {"set": {"name": "x", "value": 20}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 20

    def test_set_nonexistent_variable_raises_error(self, quiet_vm):
        program = [{"set": {"name": "undefined", "value": 10}}]
        with pytest.raises(AmorphRuntimeError, match="Variable not found"):
            quiet_vm.run(program)

    def test_get_undefined_variable_raises_error(self, quiet_vm):
        program = [{"expr": {"var": "undefined"}}]
        with pytest.raises(AmorphRuntimeError, match="Variable not found"):
            quiet_vm.run(program)

    def test_variable_in_expression(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 5}},
            {"let": {"name": "y", "value": {"mul": [{"var": "x"}, 2]}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("y") == 10

    def test_variable_shadowing_in_function(self, quiet_vm):
        # Function parameter shadows outer variable
        program = [
            {"let": {"name": "x", "value": 10}},
            {"def": {"name": "func", "params": ["x"], "body": [
                {"return": {"var": "x"}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "func", "args": [20]}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 10  # Outer x unchanged
        assert quiet_vm.get("result") == 20  # Function used parameter x

    def test_frame_stack_isolation(self, quiet_vm):
        # Variables in function don't leak to outer scope
        program = [
            {"def": {"name": "func", "params": [], "body": [
                {"let": {"name": "local", "value": 42}},
                {"return": {"var": "local"}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "func", "args": []}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("result") == 42
        with pytest.raises(AmorphRuntimeError, match="Variable not found"):
            quiet_vm.get("local")  # Should not exist in outer scope


class TestFunctions:
    """Test function definition and calling."""

    def test_simple_function_definition(self, quiet_vm):
        program = [
            {"def": {"name": "double", "params": ["n"], "body": [
                {"return": {"mul": [{"var": "n"}, 2]}}
            ]}}
        ]
        quiet_vm.run(program)
        # Function should be registered
        assert "double" in quiet_vm.funcs_by_name

    def test_simple_function_call(self, quiet_vm):
        program = [
            {"def": {"name": "double", "params": ["n"], "body": [
                {"return": {"mul": [{"var": "n"}, 2]}}
            ]}},
            {"let": {"name": "x", "value": {"call": {"name": "double", "args": [5]}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 10

    def test_function_with_multiple_params(self, quiet_vm):
        program = [
            {"def": {"name": "add", "params": ["a", "b"], "body": [
                {"return": {"add": [{"var": "a"}, {"var": "b"}]}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "add", "args": [3, 7]}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("result") == 10

    def test_function_call_by_id(self, quiet_vm):
        program = [
            {"def": {"name": "triple", "id": "fn_triple", "params": ["n"], "body": [
                {"return": {"mul": [{"var": "n"}, 3]}}
            ]}},
            {"let": {"name": "x", "value": {"call": {"id": "fn_triple", "args": [4]}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 12

    def test_recursive_function(self, quiet_vm):
        program = [
            {"def": {"name": "fact", "params": ["n"], "body": [
                {"if": {"cond": {"le": [{"var": "n"}, 1]}, "then": [
                    {"return": 1}
                ], "else": [
                    {"return": {"mul": [{"var": "n"}, {"call": {"name": "fact", "args": [{"sub": [{"var": "n"}, 1]}]}}]}}
                ]}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "fact", "args": [5]}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("result") == 120

    def test_function_arity_mismatch_raises_error(self, quiet_vm):
        program = [
            {"def": {"name": "add", "params": ["a", "b"], "body": [
                {"return": {"add": [{"var": "a"}, {"var": "b"}]}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "add", "args": [1]}}}}
        ]
        with pytest.raises(AmorphRuntimeError, match="expects 2 args, got 1"):
            quiet_vm.run(program)

    def test_undefined_function_raises_error(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"call": {"name": "undefined", "args": []}}}}]
        with pytest.raises((AmorphRuntimeError, AmorphValidationError)):
            quiet_vm.run(program)

    def test_forward_reference_with_call_after_def(self, quiet_vm):
        # Function must be defined before call execution
        program = [
            {"def": {"name": "double", "params": ["n"], "body": [
                {"return": {"mul": [{"var": "n"}, 2]}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "double", "args": [5]}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("result") == 10


class TestControlFlow:
    """Test control flow: if/then/else."""

    def test_if_true_executes_then(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 0}},
            {"if": {"cond": True, "then": [
                {"set": {"name": "x", "value": 10}}
            ], "else": [
                {"set": {"name": "x", "value": 20}}
            ]}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 10

    def test_if_false_executes_else(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 0}},
            {"if": {"cond": False, "then": [
                {"set": {"name": "x", "value": 10}}
            ], "else": [
                {"set": {"name": "x", "value": 20}}
            ]}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 20

    def test_if_without_else(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 0}},
            {"if": {"cond": True, "then": [
                {"set": {"name": "x", "value": 10}}
            ]}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 10

    def test_if_false_without_else_does_nothing(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 5}},
            {"if": {"cond": False, "then": [
                {"set": {"name": "x", "value": 10}}
            ]}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 5  # Unchanged

    def test_if_with_expression_condition(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 10}},
            {"let": {"name": "result", "value": 0}},
            {"if": {"cond": {"gt": [{"var": "x"}, 5]}, "then": [
                {"set": {"name": "result", "value": 1}}
            ], "else": [
                {"set": {"name": "result", "value": -1}}
            ]}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("result") == 1

    def test_nested_if(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 10}},
            {"let": {"name": "result", "value": 0}},
            {"if": {"cond": {"gt": [{"var": "x"}, 5]}, "then": [
                {"if": {"cond": {"lt": [{"var": "x"}, 15]}, "then": [
                    {"set": {"name": "result", "value": 1}}
                ]}}
            ]}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("result") == 1

    def test_return_in_if_exits_function(self, quiet_vm):
        program = [
            {"def": {"name": "abs", "params": ["n"], "body": [
                {"if": {"cond": {"lt": [{"var": "n"}, 0]}, "then": [
                    {"return": {"mul": [{"var": "n"}, -1]}}
                ]}},
                {"return": {"var": "n"}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "abs", "args": [-5]}}}}
        ]
        quiet_vm.run(program)
        assert quiet_vm.get("result") == 5


class TestCollections:
    """Test collection operators: list, len, get, has, concat, range."""

    def test_list_creation(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"list": [1, 2, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == [1, 2, 3]

    def test_list_literal(self, quiet_vm):
        program = [{"let": {"name": "x", "value": [1, 2, 3]}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == [1, 2, 3]

    def test_len_of_list(self, quiet_vm):
        # len expects a single argument (the list), not list elements
        program = [{"let": {"name": "lst", "value": [1, 2, 3, 4]}},
                   {"let": {"name": "x", "value": {"len": {"var": "lst"}}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 4

    def test_len_of_string(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"len": "hello"}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 5

    def test_get_from_list(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"get": [[10, 20, 30], 1]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 20

    def test_get_from_string(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"get": ["hello", 1]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == "e"

    def test_has_existing_index(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"has": [[1, 2, 3], 1]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is True

    def test_has_nonexistent_index(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"has": [[1, 2, 3], 10]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") is False

    def test_concat_lists(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"concat": [[1, 2], [3, 4], [5]]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == [1, 2, 3, 4, 5]

    def test_concat_strings(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"concat": ["hello", " ", "world"]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == "hello world"

    def test_range_single_arg(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"range": 5}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == [1, 2, 3, 4, 5]

    def test_range_two_args_ascending(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"range": [3, 7]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == [3, 4, 5, 6, 7]

    def test_range_two_args_descending(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"range": [7, 3]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == [7, 6, 5, 4, 3]

    def test_range_zero(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"range": 0}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == []

    def test_range_negative(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"range": -5}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == []


class TestIOOperations:
    """Test I/O operations: print, input."""

    def test_print_with_quiet_io(self, quiet_vm):
        program = [{"print": ["Hello, World!"]}]
        # Should not raise, output captured by QuietIO
        quiet_vm.run(program)

    def test_print_multiple_values(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 42}},
            {"print": ["The answer is", {"var": "x"}]}
        ]
        quiet_vm.run(program)

    def test_print_with_spread(self, quiet_vm):
        program = [
            {"let": {"name": "nums", "value": [1, 2, 3]}},
            {"print": [{"spread": {"var": "nums"}}]}
        ]
        quiet_vm.run(program)

    def test_print_denied_capability_raises_error(self):
        vm = VM(allow_print=False)
        program = [{"print": ["test"]}]
        with pytest.raises(AmorphRuntimeError, match="Effect denied: print"):
            vm.run(program)

    def test_input_denied_capability_raises_error(self):
        vm = VM(allow_input=False)
        program = [{"let": {"name": "x", "value": {"input": []}}}]
        with pytest.raises(AmorphRuntimeError, match="Effect denied: input"):
            vm.run(program)


class TestTracing:
    """Test tracing functionality."""

    def test_trace_flag_enabled(self):
        vm = VM(trace=True, quiet=True)
        program = [{"let": {"name": "x", "value": 5}}]
        # Should not raise, just outputs trace info
        vm.run(program)

    def test_trace_json_flag_enabled(self):
        vm = VM(trace_json=True, quiet=True)
        program = [{"let": {"name": "x", "value": 5}}]
        # Should emit JSON events to stderr
        vm.run(program)


class TestConversionOperators:
    """Test conversion operators: int."""

    def test_int_from_string(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"int": "42"}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 42

    def test_int_from_float(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"int": 3.7}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 3

    def test_int_invalid_string_raises_error(self, quiet_vm):
        program = [{"let": {"name": "x", "value": {"int": "not a number"}}}]
        with pytest.raises(AmorphRuntimeError, match="int parse failed"):
            quiet_vm.run(program)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_program(self, quiet_vm):
        program = []
        result = quiet_vm.run(program)
        assert result is None

    def test_program_with_wrapper_form(self, quiet_vm):
        program = {"version": "0.1", "program": [
            {"let": {"name": "x", "value": 42}}
        ]}
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 42

    def test_return_at_top_level(self, quiet_vm):
        program = [
            {"let": {"name": "x", "value": 10}},
            {"return": {"var": "x"}},
            {"let": {"name": "y", "value": 20}}  # Should not execute
        ]
        result = quiet_vm.run(program)
        assert result == 10
        with pytest.raises(AmorphRuntimeError):
            quiet_vm.get("y")  # Should not exist

    def test_deeply_nested_expression(self, quiet_vm):
        # Nested add: ((((1 + 2) + 3) + 4) + 5)
        program = [{"let": {"name": "x", "value": {"add": [{"add": [{"add": [{"add": [1, 2]}, 3]}, 4]}, 5]}}}]
        quiet_vm.run(program)
        assert quiet_vm.get("x") == 15

    def test_malformed_statement_raises_error(self, quiet_vm):
        program = [{"invalid_key": "value"}]
        with pytest.raises(AmorphValidationError):
            quiet_vm.run(program)
