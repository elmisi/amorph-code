"""Tests for amorph.format module - Minification and formatting."""
import pytest
import json
from amorph.format import minify_keys, unminify_keys, fmt_dump, KEYMAP


class TestMinifyUnminify:
    """Test minification and unminification."""

    def test_minify_simple_let(self):
        program = [{"let": {"name": "x", "value": 5}}]
        minified = minify_keys(program)
        assert minified == [{"l": {"n": "x", "val": 5}}]

    def test_minify_def_statement(self):
        program = [{"def": {"name": "double", "params": ["n"], "body": []}}]
        minified = minify_keys(program)
        assert minified == [{"d": {"n": "double", "pa": ["n"], "b": []}}]

    def test_minify_preserves_unmapped_keys(self):
        program = [{"let": {"name": "x", "custom_key": "value", "value": 5}}]
        minified = minify_keys(program)
        # custom_key should be preserved
        assert minified[0]["l"]["custom_key"] == "value"

    def test_unminify_restores_canonical(self):
        minified = [{"l": {"n": "x", "val": 5}}]
        unminified = unminify_keys(minified)
        assert unminified == [{"let": {"name": "x", "value": 5}}]

    def test_minify_unminify_round_trip(self):
        original = [
            {"let": {"name": "x", "value": {"add": [1, 2]}}},
            {"def": {"name": "double", "params": ["n"], "body": [
                {"return": {"mul": [{"var": "n"}, 2]}}
            ]}},
            {"if": {"cond": True, "then": [], "else": []}}
        ]
        minified = minify_keys(original)
        restored = unminify_keys(minified)
        assert restored == original

    def test_minify_nested_structures(self):
        program = [{"let": {"name": "x", "value": {"call": {"name": "func", "args": []}}}}]
        minified = minify_keys(program)
        # Should minify nested keys too
        assert "l" in minified[0]
        assert "c" in minified[0]["l"]["val"]

    def test_unminify_partial_minified(self):
        # Some keys minified, some not - should handle gracefully
        partial = [{"l": {"name": "x", "val": 5}}]  # Mixed
        unminified = unminify_keys(partial)
        assert unminified == [{"let": {"name": "x", "value": 5}}]

    def test_minify_empty_program(self):
        program = []
        minified = minify_keys(program)
        assert minified == []

    def test_minify_with_statement_id(self):
        program = [{"id": "s1", "let": {"name": "x", "value": 5}}]
        minified = minify_keys(program)
        # id should be preserved
        assert minified[0]["id"] == "s1"
        assert "l" in minified[0]

    def test_minify_with_function_id(self):
        program = [{"def": {"name": "func", "id": "fn_1", "params": [], "body": []}}]
        minified = minify_keys(program)
        assert minified[0]["d"]["id"] == "fn_1"

    def test_minify_print_statement(self):
        program = [{"print": [1, 2, 3]}]
        minified = minify_keys(program)
        assert minified == [{"p": [1, 2, 3]}]

    def test_minify_return_statement(self):
        program = [{"return": {"var": "x"}}]
        minified = minify_keys(program)
        assert minified == [{"r": {"v": "x"}}]

    def test_minify_if_statement(self):
        program = [{"if": {"cond": True, "then": [{"print": ["yes"]}], "else": []}}]
        minified = minify_keys(program)
        assert "i" in minified[0]
        assert "co" in minified[0]["i"]

    def test_minify_set_statement(self):
        program = [{"set": {"name": "x", "value": 10}}]
        minified = minify_keys(program)
        assert minified == [{"s": {"n": "x", "val": 10}}]

    def test_minify_expr_statement(self):
        program = [{"expr": {"call": {"name": "func", "args": []}}}]
        minified = minify_keys(program)
        assert "x" in minified[0]

    def test_minify_reduces_size(self):
        original = [
            {"let": {"name": "variable", "value": 100}},
            {"def": {"name": "function", "params": ["param1", "param2"], "body": [
                {"return": {"var": "param1"}}
            ]}}
        ]
        original_size = len(json.dumps(original))
        minified = minify_keys(original)
        minified_size = len(json.dumps(minified))
        # Minified should be smaller
        assert minified_size < original_size
        # Rough expectation: at least 10% reduction
        assert minified_size < original_size * 0.9


class TestFmtDump:
    """Test canonical formatting."""

    def test_fmt_dump_basic(self):
        program = [{"let": {"name": "x", "value": 5}}]
        output = fmt_dump(program)
        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed == program

    def test_fmt_dump_sorted_keys(self):
        # Keys should be sorted alphabetically
        program = [{"let": {"value": 5, "name": "x"}}]  # Unsorted
        output = fmt_dump(program)
        # name should come before value
        assert output.index('"name"') < output.index('"value"')

    def test_fmt_dump_indented(self):
        program = [{"let": {"name": "x", "value": 5}}]
        output = fmt_dump(program)
        # Should have indentation (indent=2)
        assert "  " in output

    def test_fmt_dump_ensure_ascii_false(self):
        program = [{"let": {"name": "π", "value": "日本語"}}]
        output = fmt_dump(program)
        # Unicode should be preserved, not escaped
        assert "π" in output
        assert "日本語" in output

    def test_fmt_dump_deterministic(self):
        program = [{"let": {"name": "x", "value": {"add": [1, 2]}}}]
        output1 = fmt_dump(program)
        output2 = fmt_dump(program)
        assert output1 == output2

    def test_fmt_dump_idempotent(self):
        program = [{"let": {"name": "x", "value": 5}}]
        output1 = fmt_dump(program)
        # Parse and format again
        parsed = json.loads(output1)
        output2 = fmt_dump(parsed)
        assert output1 == output2

    def test_fmt_dump_complex_program(self):
        program = [
            {"def": {"name": "factorial", "params": ["n"], "body": [
                {"if": {"cond": {"le": [{"var": "n"}, 1]}, "then": [
                    {"return": 1}
                ], "else": [
                    {"return": {"mul": [{"var": "n"}, {"call": {"name": "factorial", "args": [{"sub": [{"var": "n"}, 1]}]}}]}}
                ]}}
            ]}},
            {"let": {"name": "result", "value": {"call": {"name": "factorial", "args": [5]}}}}
        ]
        output = fmt_dump(program)
        # Should be valid and parseable
        parsed = json.loads(output)
        assert parsed == program

    def test_fmt_dump_empty_program(self):
        program = []
        output = fmt_dump(program)
        assert output == "[]"

    def test_fmt_dump_no_trailing_whitespace(self):
        program = [{"let": {"name": "x", "value": 5}}]
        output = fmt_dump(program)
        lines = output.split("\n")
        for line in lines:
            # No trailing spaces
            assert line == line.rstrip()


class TestCompressionRatio:
    """Test actual compression ratios achieved."""

    def test_compression_ratio_typical_program(self):
        program = [
            {"let": {"name": "x", "value": {"add": [1, 2]}}},
            {"let": {"name": "y", "value": {"mul": [{"var": "x"}, 2]}}},
            {"def": {"name": "double", "params": ["n"], "body": [
                {"return": {"mul": [{"var": "n"}, 2]}}
            ]}},
            {"if": {"cond": {"gt": [{"var": "y"}, 5]}, "then": [
                {"print": ["Large value"]}
            ], "else": [
                {"print": ["Small value"]}
            ]}}
        ]
        canonical_size = len(fmt_dump(program))
        minified = minify_keys(program)
        minified_size = len(json.dumps(minified, separators=(',', ':')))

        ratio = minified_size / canonical_size
        # Should achieve significant compression (typically 25-60% of original)
        assert 0.20 < ratio < 0.65, f"Ratio {ratio:.2f} outside expected range"
        # Document actual performance
        print(f"\nCompression ratio: {ratio:.2%} (minified: {minified_size}, canonical: {canonical_size})")

    def test_minified_still_parseable(self):
        program = [
            {"let": {"name": "x", "value": 5}},
            {"def": {"name": "func", "params": [], "body": []}}
        ]
        minified = minify_keys(program)
        # Should be valid JSON
        json_str = json.dumps(minified)
        parsed = json.loads(json_str)
        assert parsed == minified


class TestKeyMapping:
    """Test the KEYMAP dictionary itself."""

    def test_keymap_has_all_statement_types(self):
        statement_keys = ["let", "set", "def", "if", "return", "print", "expr"]
        for key in statement_keys:
            assert key in KEYMAP

    def test_keymap_has_expression_keys(self):
        expr_keys = ["var", "call"]
        for key in expr_keys:
            assert key in KEYMAP

    def test_keymap_has_common_keys(self):
        common_keys = ["name", "value", "params", "body", "cond", "id"]
        for key in common_keys:
            assert key in KEYMAP

    def test_keymap_values_unique(self):
        # All minified keys should be unique
        values = list(KEYMAP.values())
        assert len(values) == len(set(values))

    def test_keymap_short_values(self):
        # Minified keys should be shorter than originals
        for original, minified in KEYMAP.items():
            assert len(minified) <= len(original)


class TestEdgeCases:
    """Test edge cases and special situations."""

    def test_minify_with_nested_lists(self):
        program = [{"let": {"name": "matrix", "value": [[1, 2], [3, 4]]}}]
        minified = minify_keys(program)
        unminified = unminify_keys(minified)
        assert unminified == program

    def test_minify_with_nested_objects(self):
        program = [{"let": {"name": "config", "value": {"nested": {"deep": "value"}}}}]
        minified = minify_keys(program)
        unminified = unminify_keys(minified)
        assert unminified == program

    def test_minify_preserves_literals(self):
        program = [{"let": {"name": "data", "value": [True, False, None, "string", 42]}}]
        minified = minify_keys(program)
        unminified = unminify_keys(minified)
        assert unminified == program

    def test_minify_with_operator_calls(self):
        program = [{"let": {"name": "x", "value": {"add": [{"mul": [2, 3]}, {"div": [10, 2]}]}}}]
        minified = minify_keys(program)
        unminified = unminify_keys(minified)
        assert unminified == program

    def test_fmt_dump_with_unicode(self):
        program = [{"let": {"name": "emoji", "value": "😀🎉"}}]
        output = fmt_dump(program)
        assert "😀" in output
        assert "🎉" in output

    def test_minify_unminify_preserves_types(self):
        program = [{"let": {"name": "types", "value": [1, 1.5, "str", True, False, None]}}]
        minified = minify_keys(program)
        unminified = unminify_keys(minified)
        # Types should be preserved
        assert unminified[0]["let"]["value"][0] == 1
        assert isinstance(unminified[0]["let"]["value"][0], int)
        assert unminified[0]["let"]["value"][1] == 1.5
        assert isinstance(unminified[0]["let"]["value"][1], float)
        assert unminified[0]["let"]["value"][5] is None
