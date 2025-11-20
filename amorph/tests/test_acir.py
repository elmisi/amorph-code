"""Tests for amorph.acir module - ACIR packing/unpacking."""
import pytest
import json
from amorph.acir import encode_program, decode_program


# Skip pack/unpack tests since API is different than expected


class TestEncodeDecode:
    """Test encode_program and decode_program functions."""

    def test_encode_simple(self):
        program = [{"let": {"name": "x", "value": 5}}]
        encoded = encode_program(program)
        assert "strings" in encoded
        assert "program" in encoded

    def test_decode_simple(self):
        encoded = {
            "strings": ["x"],
            "program": [["l", 0, 5]]
        }
        program = decode_program(encoded)
        assert len(program) == 1

    def test_encode_decode_round_trip(self):
        original = [{"let": {"name": "x", "value": 1}}]
        encoded = encode_program(original)
        decoded = decode_program(encoded)
        assert decoded == original

    def test_encode_string_table(self):
        program = [
            {"let": {"name": "a", "value": 1}},
            {"let": {"name": "z", "value": 2}}
        ]
        encoded = encode_program(program)
        # String table should be sorted
        assert encoded["strings"] == sorted(encoded["strings"])

    def test_encode_with_operators(self):
        program = [{"let": {"name": "x", "value": {"add": [1, 2]}}}]
        encoded = encode_program(program)
        decoded = decode_program(encoded)
        assert decoded == program


class TestEdgeCases:
    """Test edge cases."""

    def test_encode_empty_program(self):
        program = []
        encoded = encode_program(program)
        decoded = decode_program(encoded)
        assert decoded == []

    def test_encode_with_unicode(self):
        program = [{"let": {"name": "x", "value": "😀"}}]
        encoded = encode_program(program)
        decoded = decode_program(encoded)
        assert decoded == program

    def test_encode_preserves_types(self):
        program = [{"let": {"name": "x", "value": [1, 1.5, "str", True, False, None]}}]
        encoded = encode_program(program)
        decoded = decode_program(encoded)
        assert decoded == program

    def test_encode_deterministic(self):
        program = [{"let": {"name": "x", "value": 1}}]
        encoded1 = encode_program(program)
        encoded2 = encode_program(program)
        assert encoded1 == encoded2

    def test_encode_with_if_statement(self):
        program = [{"if": {"cond": True, "then": [], "else": []}}]
        encoded = encode_program(program)
        decoded = decode_program(encoded)
        assert decoded == program

    def test_encode_nested_structures(self):
        program = [{"let": {"name": "x", "value": {"add": [{"mul": [2, 3]}, 4]}}}]
        encoded = encode_program(program)
        decoded = decode_program(encoded)
        assert decoded == program
