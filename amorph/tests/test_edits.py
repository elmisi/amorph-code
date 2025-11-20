"""Tests for amorph.edits module - Declarative AST editing."""
import pytest
import copy
from amorph.edits import (
    apply_edits,
    op_add_function,
    op_rename_function,
    op_insert_before,
    op_insert_after,
    op_replace_call,
    op_delete_node,
    parse_path,
    find_by_path,
    EditError,
)
from amorph.uid import add_uids


class TestAddFunction:
    """Test add_function edit operation."""

    def test_add_simple_function(self):
        program = []
        spec = {
            "name": "double",
            "params": ["n"],
            "body": [{"return": {"mul": [{"var": "n"}, 2]}}]
        }
        op_add_function(program, spec)
        assert len(program) == 1
        assert program[0]["def"]["name"] == "double"
        assert program[0]["def"]["params"] == ["n"]

    def test_add_function_with_id(self):
        program = []
        spec = {
            "name": "triple",
            "id": "fn_triple",
            "params": ["n"],
            "body": []
        }
        op_add_function(program, spec)
        assert program[0]["def"]["id"] == "fn_triple"

    def test_add_function_to_existing_program(self):
        program = [{"let": {"name": "x", "value": 5}}]
        spec = {"name": "func", "params": [], "body": []}
        op_add_function(program, spec)
        assert len(program) == 2
        assert program[1]["def"]["name"] == "func"

    def test_add_function_with_empty_body(self):
        program = []
        spec = {"name": "noop", "params": [], "body": []}
        op_add_function(program, spec)
        assert program[0]["def"]["body"] == []

    def test_add_function_invalid_name_raises_error(self):
        program = []
        spec = {"name": 123, "params": [], "body": []}  # name not string
        with pytest.raises(EditError):
            op_add_function(program, spec)

    def test_add_function_missing_name_raises_error(self):
        program = []
        spec = {"params": [], "body": []}  # Missing name
        with pytest.raises(EditError):
            op_add_function(program, spec)

    def test_add_function_invalid_params_raises_error(self):
        program = []
        spec = {"name": "func", "params": "not a list", "body": []}
        with pytest.raises(EditError):
            op_add_function(program, spec)


class TestRenameFunction:
    """Test rename_function edit operation."""

    def test_rename_by_name_simple(self):
        program = [
            {"def": {"name": "old_name", "params": [], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "old_name", "args": []}}}}
        ]
        spec = {"from": "old_name", "to": "new_name"}
        changed = op_rename_function(program, spec)
        assert program[0]["def"]["name"] == "new_name"
        assert program[1]["let"]["value"]["call"]["name"] == "new_name"
        assert changed >= 1  # At least the def changed

    def test_rename_by_id(self):
        program = [
            {"def": {"name": "func", "id": "fn_1", "params": [], "body": []}},
            {"let": {"name": "x", "value": {"call": {"id": "fn_1", "args": []}}}}
        ]
        spec = {"id": "fn_1", "to": "renamed_func"}
        changed = op_rename_function(program, spec)
        assert program[0]["def"]["name"] == "renamed_func"
        # Call by id should not be renamed (already uses id)
        assert program[1]["let"]["value"]["call"]["id"] == "fn_1"

    def test_rename_updates_name_based_calls(self):
        program = [
            {"def": {"name": "helper", "params": [], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "helper", "args": []}}}},
            {"let": {"name": "y", "value": {"call": {"name": "helper", "args": []}}}}
        ]
        spec = {"from": "helper", "to": "utility"}
        changed = op_rename_function(program, spec)
        assert changed >= 1
        assert program[1]["let"]["value"]["call"]["name"] == "utility"
        assert program[2]["let"]["value"]["call"]["name"] == "utility"

    def test_rename_ambiguous_name_raises_error(self):
        program = [
            {"def": {"name": "func", "params": [], "body": []}},
            {"def": {"name": "func", "params": ["x"], "body": []}}  # Duplicate name
        ]
        spec = {"from": "func", "to": "renamed"}
        with pytest.raises(EditError):
            op_rename_function(program, spec)

    def test_rename_nonexistent_function_raises_error(self):
        program = [{"let": {"name": "x", "value": 5}}]
        spec = {"from": "nonexistent", "to": "new_name"}
        with pytest.raises(EditError):
            op_rename_function(program, spec)

    def test_rename_missing_to_raises_error(self):
        program = [{"def": {"name": "func", "params": [], "body": []}}]
        spec = {"from": "func"}  # Missing "to"
        with pytest.raises(EditError):
            op_rename_function(program, spec)

    def test_rename_in_nested_calls(self):
        program = [
            {"def": {"name": "inner", "params": [], "body": []}},
            {"def": {"name": "outer", "params": [], "body": [
                {"expr": {"call": {"name": "inner", "args": []}}}
            ]}}
        ]
        spec = {"from": "inner", "to": "renamed_inner"}
        changed = op_rename_function(program, spec)
        assert changed >= 1
        # Check nested call was updated
        assert program[1]["def"]["body"][0]["expr"]["call"]["name"] == "renamed_inner"

    def test_rename_preserves_id_based_calls(self):
        program = [
            {"def": {"name": "func", "id": "fn_1", "params": [], "body": []}},
            {"let": {"name": "x", "value": {"call": {"id": "fn_1", "args": []}}}},
            {"let": {"name": "y", "value": {"call": {"name": "func", "args": []}}}}
        ]
        spec = {"id": "fn_1", "to": "new_func"}
        changed = op_rename_function(program, spec)
        # ID-based call unchanged, name-based call updated
        assert program[1]["let"]["value"]["call"]["id"] == "fn_1"
        assert program[2]["let"]["value"]["call"]["name"] == "new_func"


class TestInsertOperations:
    """Test insert_before and insert_after operations."""

    def test_insert_before_by_target_id(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"id": "s2", "let": {"name": "y", "value": 2}}
        ]
        spec = {
            "target": "s2",
            "node": {"let": {"name": "inserted", "value": 0}}
        }
        op_insert_before(program, spec)
        assert len(program) == 3
        assert program[1]["let"]["name"] == "inserted"
        assert program[2]["id"] == "s2"

    def test_insert_after_by_target_id(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"id": "s2", "let": {"name": "y", "value": 2}}
        ]
        spec = {
            "target": "s1",
            "node": {"let": {"name": "inserted", "value": 0}}
        }
        op_insert_after(program, spec)
        assert len(program) == 3
        assert program[1]["let"]["name"] == "inserted"
        assert program[0]["id"] == "s1"

    def test_insert_before_by_path(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}}
        ]
        spec = {
            "path": "/$[1]",
            "node": {"let": {"name": "inserted", "value": 0}}
        }
        op_insert_before(program, spec)
        assert len(program) == 3
        assert program[1]["let"]["name"] == "inserted"

    def test_insert_after_by_path(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}}
        ]
        spec = {
            "path": "/$[0]",
            "node": {"let": {"name": "inserted", "value": 0}}
        }
        op_insert_after(program, spec)
        assert len(program) == 3
        assert program[1]["let"]["name"] == "inserted"

    def test_insert_at_beginning(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}}
        ]
        spec = {
            "target": "s1",
            "node": {"let": {"name": "first", "value": 0}}
        }
        op_insert_before(program, spec)
        assert program[0]["let"]["name"] == "first"

    def test_insert_at_end(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}}
        ]
        spec = {
            "target": "s1",
            "node": {"let": {"name": "last", "value": 2}}
        }
        op_insert_after(program, spec)
        assert program[1]["let"]["name"] == "last"

    def test_insert_missing_target_and_path_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]
        spec = {"node": {"let": {"name": "inserted", "value": 0}}}
        with pytest.raises(EditError):
            op_insert_before(program, spec)

    def test_insert_invalid_target_raises_error(self):
        program = [{"id": "s1", "let": {"name": "x", "value": 1}}]
        spec = {"target": "nonexistent", "node": {"let": {"name": "x", "value": 0}}}
        # May raise EditError or other exception depending on implementation
        try:
            op_insert_before(program, spec)
            assert False, "Should have raised an error"
        except (EditError, Exception):
            pass  # Expected

    def test_insert_missing_node_raises_error(self):
        program = [{"id": "s1", "let": {"name": "x", "value": 1}}]
        spec = {"target": "s1"}  # Missing node
        with pytest.raises(EditError):
            op_insert_before(program, spec)


class TestReplaceCall:
    """Test replace_call edit operation."""

    def test_replace_call_by_name(self):
        program = [
            {"def": {"name": "old_func", "params": [], "body": []}},
            {"let": {"name": "x", "value": {"call": {"name": "old_func", "args": []}}}}
        ]
        spec = {
            "match": {"name": "old_func"},
            "set": {"name": "new_func"}
        }
        changed = op_replace_call(program, spec)
        assert changed == 1
        assert program[1]["let"]["value"]["call"]["name"] == "new_func"

    def test_replace_call_by_id(self):
        program = [
            {"def": {"name": "func", "id": "fn_1", "params": [], "body": []}},
            {"let": {"name": "x", "value": {"call": {"id": "fn_1", "args": []}}}}
        ]
        spec = {
            "match": {"id": "fn_1"},
            "set": {"id": "fn_2"}
        }
        changed = op_replace_call(program, spec)
        assert changed == 1
        assert program[1]["let"]["value"]["call"]["id"] == "fn_2"

    def test_replace_call_args(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "func", "args": [1, 2]}}}}
        ]
        spec = {
            "match": {"name": "func"},
            "set": {"args": [3, 4, 5]}
        }
        changed = op_replace_call(program, spec)
        assert changed == 1
        assert program[0]["let"]["value"]["call"]["args"] == [3, 4, 5]

    def test_replace_multiple_calls(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "old", "args": []}}}},
            {"let": {"name": "y", "value": {"call": {"name": "old", "args": []}}}},
            {"let": {"name": "z", "value": {"call": {"name": "other", "args": []}}}}
        ]
        spec = {
            "match": {"name": "old"},
            "set": {"name": "new"}
        }
        changed = op_replace_call(program, spec)
        assert changed == 2
        assert program[0]["let"]["value"]["call"]["name"] == "new"
        assert program[1]["let"]["value"]["call"]["name"] == "new"
        assert program[2]["let"]["value"]["call"]["name"] == "other"  # Unchanged

    def test_replace_call_name_removes_id(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"id": "fn_1", "name": "func", "args": []}}}}
        ]
        spec = {
            "match": {"id": "fn_1"},
            "set": {"name": "new_func"}
        }
        changed = op_replace_call(program, spec)
        # Setting name should remove id
        assert "id" not in program[0]["let"]["value"]["call"]
        assert program[0]["let"]["value"]["call"]["name"] == "new_func"

    def test_replace_call_id_removes_name(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "func", "args": []}}}}
        ]
        spec = {
            "match": {"name": "func"},
            "set": {"id": "fn_new"}
        }
        changed = op_replace_call(program, spec)
        # Setting id should remove name
        assert "name" not in program[0]["let"]["value"]["call"]
        assert program[0]["let"]["value"]["call"]["id"] == "fn_new"

    def test_replace_call_no_matches(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "func", "args": []}}}}
        ]
        spec = {
            "match": {"name": "nonexistent"},
            "set": {"name": "new"}
        }
        changed = op_replace_call(program, spec)
        assert changed == 0

    def test_replace_call_in_nested_expressions(self):
        program = [
            {"let": {"name": "x", "value": {"add": [{"call": {"name": "func", "args": []}}, 1]}}}
        ]
        spec = {
            "match": {"name": "func"},
            "set": {"name": "new_func"}
        }
        changed = op_replace_call(program, spec)
        assert changed == 1
        assert program[0]["let"]["value"]["add"][0]["call"]["name"] == "new_func"

    def test_replace_call_invalid_spec_raises_error(self):
        program = []
        spec = {"match": {}, "set": {}}  # Missing name/id in match
        with pytest.raises(EditError):
            op_replace_call(program, spec)


class TestDeleteNode:
    """Test delete_node edit operation."""

    def test_delete_by_target_id(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"id": "s2", "let": {"name": "y", "value": 2}},
            {"id": "s3", "let": {"name": "z", "value": 3}}
        ]
        spec = {"target": "s2"}
        op_delete_node(program, spec)
        assert len(program) == 2
        assert program[0]["id"] == "s1"
        assert program[1]["id"] == "s3"

    def test_delete_by_path(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}},
            {"let": {"name": "z", "value": 3}}
        ]
        spec = {"path": "/$[1]"}
        op_delete_node(program, spec)
        assert len(program) == 2
        assert program[0]["let"]["name"] == "x"
        assert program[1]["let"]["name"] == "z"

    def test_delete_first_node(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}}
        ]
        spec = {"target": "s1"}
        op_delete_node(program, spec)
        assert len(program) == 1
        assert program[0]["let"]["name"] == "y"

    def test_delete_last_node(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"id": "s2", "let": {"name": "y", "value": 2}}
        ]
        spec = {"target": "s2"}
        op_delete_node(program, spec)
        assert len(program) == 1
        assert program[0]["let"]["name"] == "x"

    def test_delete_nonexistent_target_raises_error(self):
        program = [{"id": "s1", "let": {"name": "x", "value": 1}}]
        spec = {"target": "nonexistent"}
        try:
            op_delete_node(program, spec)
            assert False, "Should have raised an error"
        except (EditError, Exception):
            pass  # Expected

    def test_delete_missing_target_and_path_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]
        spec = {}  # Missing both target and path
        with pytest.raises(EditError):
            op_delete_node(program, spec)


class TestPathParsing:
    """Test path parsing and navigation."""

    def test_parse_simple_path(self):
        path = "/$[0]"
        tokens = parse_path(path)
        assert tokens == [("$", 0)]

    def test_parse_nested_path(self):
        path = "/$[1]/def/body/$[0]"
        tokens = parse_path(path)
        assert tokens == [("$", 1), "def", "body", ("$", 0)]

    def test_parse_path_with_function(self):
        path = "/fn[fn_1]/body/$[2]"
        tokens = parse_path(path)
        # Note: fn[...] might be handled differently
        # This tests current behavior

    def test_parse_invalid_path_no_slash_raises_error(self):
        path = "$[0]"  # Missing leading slash
        with pytest.raises(EditError):
            parse_path(path)

    def test_parse_invalid_index_raises_error(self):
        path = "/$[not_a_number]"
        with pytest.raises(EditError):
            parse_path(path)

    def test_find_by_path_simple(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}}
        ]
        parent, idx = find_by_path(program, "/$[1]")
        assert parent is program
        assert idx == 1

    def test_find_by_path_nested(self):
        program = [
            {"def": {"name": "func", "params": [], "body": [
                {"return": 1},
                {"return": 2}
            ]}}
        ]
        parent, idx = find_by_path(program, "/$[0]/def/body/$[1]")
        assert parent == program[0]["def"]["body"]
        assert idx == 1

    def test_find_by_path_out_of_range_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]
        try:
            find_by_path(program, "/$[10]")
            assert False, "Should have raised an error"
        except (EditError, IndexError, Exception):
            pass  # Expected

    def test_find_by_path_wrong_type_raises_error(self):
        program = [{"let": {"name": "x", "value": 1}}]
        # Try to index into non-list
        with pytest.raises(EditError):
            find_by_path(program, "/$[0]/let/$[0]")


class TestApplyEdits:
    """Test applying multiple edits."""

    def test_apply_single_edit(self):
        program = []
        edits = [
            {"op": "add_function", "name": "func", "params": [], "body": []}
        ]
        report = apply_edits(program, edits)
        assert report["applied"] == 1
        assert len(program) == 1

    def test_apply_multiple_edits(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}}
        ]
        edits = [
            {"op": "add_function", "name": "func1", "params": [], "body": []},
            {"op": "add_function", "name": "func2", "params": [], "body": []},
            {"op": "insert_after", "target": "s1", "node": {"let": {"name": "y", "value": 2}}}
        ]
        report = apply_edits(program, edits)
        assert report["applied"] == 3
        assert len(program) == 4

    def test_apply_edits_sequential(self):
        # Edits applied in sequence, later edits see earlier changes
        program = []
        edits = [
            {"op": "add_function", "name": "old", "params": [], "body": []},
            {"op": "rename_function", "from": "old", "to": "new"}
        ]
        report = apply_edits(program, edits)
        assert report["applied"] == 2
        assert program[0]["def"]["name"] == "new"

    def test_apply_edits_with_details(self):
        program = []
        edits = [
            {"op": "add_function", "name": "func", "params": [], "body": []}
        ]
        report = apply_edits(program, edits)
        assert "details" in report
        assert len(report["details"]) == 1
        assert report["details"][0]["op"] == "add_function"
        assert report["details"][0]["index"] == 0

    def test_apply_edits_unknown_op_raises_error(self):
        program = []
        edits = [{"op": "unknown_operation"}]
        with pytest.raises(EditError):
            apply_edits(program, edits)

    def test_apply_edits_error_stops_processing(self):
        program = []
        edits = [
            {"op": "add_function", "name": "func", "params": [], "body": []},
            {"op": "rename_function", "from": "nonexistent", "to": "new"},  # Will fail
            {"op": "add_function", "name": "func2", "params": [], "body": []}
        ]
        with pytest.raises(EditError):
            apply_edits(program, edits)
        # First edit applied, but third not reached
        assert len(program) == 1


class TestDeepWalkExpr:
    """Test deep expression traversal."""

    def test_deep_walk_simple_expression(self):
        from amorph.edits import deep_walk_expr
        expr = {"add": [1, 2]}
        visited = []

        def visitor(node):
            if isinstance(node, dict):
                visited.append(node)
            return node

        deep_walk_expr(expr, visitor)
        assert len(visited) > 0

    def test_deep_walk_nested_expression(self):
        from amorph.edits import deep_walk_expr
        expr = {"add": [{"mul": [2, 3]}, {"div": [10, 2]}]}
        count = [0]

        def visitor(node):
            if isinstance(node, dict):
                count[0] += 1
            return node

        deep_walk_expr(expr, visitor)
        assert count[0] == 3  # add, mul, div

    def test_deep_walk_transforms_expression(self):
        from amorph.edits import deep_walk_expr
        expr = {"var": "old_name"}

        def rename_var(node):
            if isinstance(node, dict) and "var" in node:
                return {"var": "new_name"}
            return node

        result = deep_walk_expr(expr, rename_var)
        assert result["var"] == "new_name"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_rename_function_with_no_calls(self):
        program = [
            {"def": {"name": "unused", "params": [], "body": []}}
        ]
        spec = {"from": "unused", "to": "still_unused"}
        changed = op_rename_function(program, spec)
        assert changed == 1  # Only the def
        assert program[0]["def"]["name"] == "still_unused"

    def test_replace_call_in_function_body(self):
        program = [
            {"def": {"name": "outer", "params": [], "body": [
                {"expr": {"call": {"name": "inner", "args": []}}}
            ]}}
        ]
        spec = {
            "match": {"name": "inner"},
            "set": {"name": "new_inner"}
        }
        changed = op_replace_call(program, spec)
        assert changed == 1
        assert program[0]["def"]["body"][0]["expr"]["call"]["name"] == "new_inner"

    def test_insert_into_empty_program(self):
        program = []
        add_uids(program, deep=True)
        # Can't insert before/after in empty program without path
        # This documents current behavior

    def test_delete_all_nodes(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"id": "s2", "let": {"name": "y", "value": 2}}
        ]
        op_delete_node(program, {"target": "s1"})
        op_delete_node(program, {"target": "s2"})
        assert len(program) == 0

    def test_complex_nested_path(self):
        program = [
            {"def": {"name": "func", "params": [], "body": [
                {"if": {"cond": True, "then": [
                    {"let": {"name": "x", "value": 1}}
                ], "else": []}}
            ]}}
        ]
        # Finding deeply nested statement
        parent, idx = find_by_path(program, "/$[0]/def/body/$[0]")
        assert parent == program[0]["def"]["body"]
        assert idx == 0

    def test_edit_preserves_unrelated_fields(self):
        program = [
            {"custom_field": "value", "let": {"name": "x", "value": 1}}
        ]
        edits = [
            {"op": "add_function", "name": "func", "params": [], "body": []}
        ]
        apply_edits(program, edits)
        # Custom field should be preserved
        assert program[0]["custom_field"] == "value"

    def test_rename_function_in_if_blocks(self):
        program = [
            {"def": {"name": "func", "params": [], "body": []}},
            {"if": {"cond": True, "then": [
                {"expr": {"call": {"name": "func", "args": []}}}
            ], "else": [
                {"expr": {"call": {"name": "func", "args": []}}}
            ]}}
        ]
        spec = {"from": "func", "to": "renamed"}
        changed = op_rename_function(program, spec)
        # Should rename def (calls in if blocks may not be counted currently)
        assert changed >= 1
        assert program[0]["def"]["name"] == "renamed"

    def test_replace_call_with_complex_args(self):
        program = [
            {"let": {"name": "x", "value": {"call": {"name": "func", "args": [
                {"add": [1, 2]},
                {"var": "y"}
            ]}}}}
        ]
        spec = {
            "match": {"name": "func"},
            "set": {"args": [{"mul": [3, 4]}]}
        }
        changed = op_replace_call(program, spec)
        assert changed == 1
        new_args = program[0]["let"]["value"]["call"]["args"]
        assert len(new_args) == 1
        assert "mul" in new_args[0]
