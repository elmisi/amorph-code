# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres (aspirationally) to Semantic Versioning.

## [Unreleased]

### Added
- ACIR pack/unpack with string table and tagged arrays (CBOR when available) preserving statement/def ids.
- Rewrite engine guards and scoping: `select`/`where`, `program_select`/`program_where`, `where_placeholders`, and `apply_to` (JMESPath).
- Capability guards for effects in VM and CLI flags: `--deny-input`, `--deny-print`.
- Validator structured JSON report (`validate --json`) with issue codes, severities, hints; warnings `W_PREFER_ID` and `W_MIXED_CALL_STYLE`.
- Edit path schema validation (regex) and documentation of allowed path segments.
- Migrate calls CLI: `migrate-calls --to id|name` to normalize call style.
- Bench CLI with quiet run; clean JSON metrics.
- Examples: arithmetic simplifications rewrite rules and guarded rewrite rules.
- English documentation: README, EDIT-OPS, FORMATS, REWRITE, VALIDATION, STATUS.
- requirements.txt with optional deps: `jsonschema`, `cbor2`, `jmespath`.

### Changed
- Trace JSON now includes `call_id`, timestamps, and canonical function body paths `/fn[<id>]/body/$[i]`.
- Interpreter IO routed via abstract IO (StdIO/QuietIO); `--quiet` silences prints.
- Operator arity validation centralized in operator registry.

### Fixed
- Bench no longer polluted by program prints (uses quiet IO).

## [0.1.0] - 2025-10-30

### Added
- Initial MVP: JSON AST language with statements (let/set/def/if/return/print/expr) and core operators (arith/logic/compare/collections/range/concat/input/int).
- Python interpreter with CLI `run` and `--trace`/`--trace-json`.
- UID utilities (`add-uid --deep`), declarative edit-ops (add/rename/insert/replace_call/delete_node), formatter/minifier, JSON Schema for programs and edits, and example programs (hello, factorial, fib, matrix, countdown).

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/v0.1.0
