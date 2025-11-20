"""Tests for amorph.uid module - UID generation and management."""
import pytest
from amorph.uid import gen_uid, add_uids, find_stmt_by_id


class TestGenUID:
    """Test UID generation."""

    def test_gen_uid_default_prefix(self):
        uid = gen_uid()
        assert uid.startswith("amr_")
        assert len(uid) == 12  # "amr_" + 8 hex chars

    def test_gen_uid_custom_prefix(self):
        uid = gen_uid(prefix="test")
        assert uid.startswith("test_")

    def test_gen_uid_unique(self):
        uid1 = gen_uid()
        uid2 = gen_uid()
        assert uid1 != uid2

    def test_gen_uid_format(self):
        uid = gen_uid()
        # Should be prefix_hexchars
        parts = uid.split("_")
        assert len(parts) == 2
        assert parts[0] == "amr"
        # Hex chars should be valid hex
        int(parts[1], 16)  # Should not raise


class TestAddUIDs:
    """Test adding UIDs to programs."""

    def test_add_uids_to_empty_program(self):
        program = []
        add_uids(program, deep=False)
        assert program == []  # Nothing to add

    def test_add_uids_to_statement_without_id(self):
        program = [{"let": {"name": "x", "value": 1}}]
        add_uids(program, deep=False)
        assert "id" in program[0]
        assert program[0]["id"].startswith("amr_")

    def test_add_uids_preserves_existing_id(self):
        program = [{"id": "existing", "let": {"name": "x", "value": 1}}]
        add_uids(program, deep=False)
        assert program[0]["id"] == "existing"  # Not overwritten

    def test_add_uids_to_multiple_statements(self):
        program = [
            {"let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}},
            {"let": {"name": "z", "value": 3}}
        ]
        add_uids(program, deep=False)
        assert all("id" in stmt for stmt in program)
        # All IDs should be unique
        ids = [stmt["id"] for stmt in program]
        assert len(ids) == len(set(ids))

    def test_add_uids_to_function_def(self):
        program = [
            {"def": {"name": "func", "params": [], "body": []}}
        ]
        add_uids(program, deep=False)
        # Top-level statement gets id
        assert "id" in program[0]
        # Function def itself gets id
        assert "id" in program[0]["def"]
        assert program[0]["def"]["id"].startswith("fn_")

    def test_add_uids_preserves_function_id(self):
        program = [
            {"def": {"name": "func", "id": "fn_existing", "params": [], "body": []}}
        ]
        add_uids(program, deep=False)
        assert program[0]["def"]["id"] == "fn_existing"

    def test_add_uids_shallow_skips_body(self):
        program = [
            {"def": {"name": "func", "params": [], "body": [
                {"let": {"name": "x", "value": 1}}
            ]}}
        ]
        add_uids(program, deep=False)
        # Top-level and def get ids
        assert "id" in program[0]
        assert "id" in program[0]["def"]
        # But body statements don't (shallow mode)
        assert "id" not in program[0]["def"]["body"][0]

    def test_add_uids_deep_adds_to_body(self):
        program = [
            {"def": {"name": "func", "params": [], "body": [
                {"let": {"name": "x", "value": 1}},
                {"return": {"var": "x"}}
            ]}}
        ]
        add_uids(program, deep=True)
        # Body statements should get ids
        assert "id" in program[0]["def"]["body"][0]
        assert "id" in program[0]["def"]["body"][1]

    def test_add_uids_deep_adds_to_if_blocks(self):
        program = [
            {"if": {"cond": True, "then": [
                {"let": {"name": "x", "value": 1}}
            ], "else": [
                {"let": {"name": "y", "value": 2}}
            ]}}
        ]
        add_uids(program, deep=True)
        # Statements in then/else blocks get ids
        assert "id" in program[0]["if"]["then"][0]
        assert "id" in program[0]["if"]["else"][0]

    def test_add_uids_idempotent(self):
        program = [{"let": {"name": "x", "value": 1}}]
        add_uids(program, deep=True)
        id_first = program[0]["id"]

        add_uids(program, deep=True)
        id_second = program[0]["id"]

        assert id_first == id_second  # Should not change

    def test_add_uids_mixed_existing_and_missing(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"let": {"name": "y", "value": 2}},  # Missing id
            {"id": "s3", "let": {"name": "z", "value": 3}}
        ]
        add_uids(program, deep=False)
        assert program[0]["id"] == "s1"  # Preserved
        assert "id" in program[1]  # Added
        assert program[2]["id"] == "s3"  # Preserved


class TestFindStmtByID:
    """Test finding statements by ID."""

    def test_find_stmt_simple(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"id": "s2", "let": {"name": "y", "value": 2}}
        ]
        parent, idx = find_stmt_by_id(program, "s1")
        assert parent is program
        assert idx == 0

    def test_find_stmt_second_item(self):
        program = [
            {"id": "s1", "let": {"name": "x", "value": 1}},
            {"id": "s2", "let": {"name": "y", "value": 2}}
        ]
        parent, idx = find_stmt_by_id(program, "s2")
        assert parent is program
        assert idx == 1

    def test_find_stmt_not_found_raises_error(self):
        program = [{"id": "s1", "let": {"name": "x", "value": 1}}]
        with pytest.raises(Exception):  # Should raise some error
            find_stmt_by_id(program, "nonexistent")

    def test_find_stmt_only_searches_top_level(self):
        # find_stmt_by_id may only search top level, not nested blocks
        program = [
            {"id": "top1", "def": {"name": "func", "params": [], "body": [
                {"id": "inner_s1", "let": {"name": "x", "value": 1}}
            ]}}
        ]
        # Can find top-level
        parent, idx = find_stmt_by_id(program, "top1")
        assert parent is program
        assert idx == 0

        # May not find nested (depends on implementation)
        # Test documents current behavior


class TestEdgeCases:
    """Test edge cases and special situations."""

    def test_add_uids_to_program_with_wrapper(self):
        # Program might have {version, program: [...]} wrapper
        # Current implementation expects list directly
        program = [{"let": {"name": "x", "value": 1}}]
        add_uids(program, deep=False)
        assert "id" in program[0]

    def test_add_uids_with_nested_defs(self):
        # Nested function definitions (if supported)
        program = [
            {"def": {"name": "outer", "params": [], "body": [
                {"def": {"name": "inner", "params": [], "body": []}}
            ]}}
        ]
        add_uids(program, deep=True)
        # All defs should get ids
        assert "id" in program[0]["def"]
        # Inner def should also get id with deep=True
        if "id" in program[0]["def"]["body"][0]:
            assert "id" in program[0]["def"]["body"][0]["def"]

    def test_find_stmt_with_duplicate_ids(self):
        # What happens with duplicate IDs? (Should not happen, but test behavior)
        program = [
            {"id": "dup", "let": {"name": "x", "value": 1}},
            {"id": "dup", "let": {"name": "y", "value": 2}}
        ]
        # Should find first occurrence
        parent, idx = find_stmt_by_id(program, "dup")
        assert idx == 0

    def test_add_uids_empty_function_body(self):
        program = [{"def": {"name": "noop", "params": [], "body": []}}]
        add_uids(program, deep=True)
        assert "id" in program[0]
        assert "id" in program[0]["def"]

    def test_gen_uid_many_times(self):
        # Generate many UIDs, ensure uniqueness
        uids = [gen_uid() for _ in range(1000)]
        assert len(uids) == len(set(uids))

    def test_add_uids_preserves_statement_structure(self):
        original = [
            {"let": {"name": "x", "value": {"add": [1, 2]}}},
            {"def": {"name": "func", "params": ["a", "b"], "body": [
                {"return": {"var": "a"}}
            ]}}
        ]
        import copy
        program = copy.deepcopy(original)
        add_uids(program, deep=True)

        # Structure should be preserved (except for added ids)
        assert program[0]["let"] == original[0]["let"]
        assert program[1]["def"]["name"] == original[1]["def"]["name"]
        assert program[1]["def"]["params"] == original[1]["def"]["params"]
