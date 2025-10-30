# Semantic validation (MVP)

This document describes what the validator (`amorph validate`) checks and its current limitations.

## What it validates today
- Program shape: accepts a statement list or `{ "program": [...] }` wrapper (`version` is ignored for validation).
- Symbol collection: gathers names and ids of top‑level functions.
- Function calls (`call`):
  - By `id`: id must be defined among top‑level `def`s.
  - By `name`: name must be defined among top‑level `def`s (forward references allowed).
- Operator arity (structural, not typed):
  - Fixed: `not`(1), `len`(1), `get`(2), `has`(2), `int`(1).
  - Ranged: `range`(1–2), `input`(0–1).
  - Namespaced operators accepted (e.g., `math.add`), normalized to suffix.
- Coverage: visits expressions in `let`, `set`, `return`, `expr`, `if.cond`, function bodies, and `then/else` blocks.
- Result: prints `OK` or `Invalid: <message>` and exits non‑zero on error.

## What it does not (yet) validate
- JSON Schema conformance (required keys, types): use `schema/amorph-0.1.schema.json` with a JSON Schema tool.
- Variable scope/binding, duplicate function names/ids, argument types, effect safety.
- Full arity for all core operators (covers a common subset).
- Lint rules (style, consistency between name/id calls).

## Proposed extensions
- Full arity for all operators and diagnostics with codes (`E_OP_ARITY`, `E_UNKNOWN_FUNC`, …) and AST paths.
- Duplicate detection (names/ids) and warnings on mixed `name`/`id` calls.
- Lint for `spread` (lists only) and fix suggestions.
- Structured JSON output (`--json`) with multiple errors and severity (error/warning).

## References
- Implementation: `amorph/validate.py`
- CLI: `amorph validate` (see `amorph/cli.py`)
