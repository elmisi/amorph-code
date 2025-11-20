"""Shared fixtures and configuration for Amorph tests."""
import pytest
import json
from typing import Any, Dict, List
from pathlib import Path

from amorph.engine import VM
from amorph.io import QuietIO


@pytest.fixture
def quiet_vm():
    """VM with quiet I/O for testing."""
    return VM(quiet=True, io=QuietIO())


@pytest.fixture
def traced_vm():
    """VM with tracing enabled for debugging tests."""
    return VM(trace=True, quiet=True)


@pytest.fixture
def simple_program():
    """Simple program: let x = 1 + 2, print x."""
    return [
        {"let": {"name": "x", "value": {"add": [1, 2]}}},
        {"print": [{"var": "x"}]}
    ]


@pytest.fixture
def factorial_program():
    """Factorial function with recursion."""
    return [
        {"def": {"name": "fact", "params": ["n"], "body": [
            {"if": {"cond": {"le": [{"var": "n"}, 1]}, "then": [
                {"return": 1}
            ], "else": [
                {"return": {"mul": [{"var": "n"}, {"call": {"name": "fact", "args": [{"sub": [{"var": "n"}, 1]}]}}]}}
            ]}}
        ]}},
        {"let": {"name": "result", "value": {"call": {"name": "fact", "args": [5]}}}},
        {"print": [{"var": "result"}]}
    ]


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def malformed_fixtures_dir(fixtures_dir):
    """Return path to malformed fixtures directory."""
    return fixtures_dir / "malformed"


def load_fixture(fixtures_dir: Path, filename: str) -> Any:
    """Load a JSON fixture file."""
    with open(fixtures_dir / filename) as f:
        return json.load(f)
