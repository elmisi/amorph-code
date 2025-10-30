# Amorph Language Suitability (AI‑first)

This document assesses how well the current MVP meets the design criteria for a language primarily authored and manipulated by LLM/agents.

## Criteria → Current status

- Structural editability: OK
  - JSON AST, canonical form; `id` on statements/defs (deep), addressing via `path`.
  - Edit‑ops: `add_function`, `rename_function`, `insert_before/after`, `replace_call`, `delete_node` with `--dry-run`.
- Determinism: OK
  - `amorph fmt` ensures deterministic key ordering/indentation; minify is deterministic.
- Validation: PARTIAL
  - Semantic validator (`amorph validate`): resolves calls by `name/id`, checks common operator arities.
  - Extensible to types/effects checks.
- Stable references: PARTIAL/OK
  - `id` for statements and functions (deep); optional call by `id`.
  - `rename_function` by `id` or `name` (if unique).
- Explicit effects: OK
  - `print`, `input` primitives; capability/sandbox on roadmap.
- Observability: PARTIAL
  - `--trace-json` emits NDJSON events with `ts`, `path`, `kind/op`.
  - Can improve with reduced payloads, step ids, call/return correlation.
- Compactness: PARTIAL
  - Minify/unminify with short keys; binary form (CBOR) and string tables planned.
- Extensibility: OK
  - Namespaced operators (`math.add` → `add` in core); standard library on roadmap.

## Suggested metrics

- Edit success: (#applied edits)/(#requested edits). Automate report from `amorph edit`.
- Token ratio: bytes (minified)/(canonical) and estimated LLM tokens on corpora.
- Idempotency: `fmt` and `minify/unminify` round‑trip must preserve AST.
- Latency: average `validate`/`run` time on S/M/L programs.

## Risks and mitigations

- JSON overfitting: keep canonical AST but design an intermediate IR (graph) for optimizations/transpilation.
- Uncontrolled side‑effects: introduce capability‑based effects.
- Modularity: import mechanism with stable names and content hashing.

## Short roadmap

1. Extended semantic validator (all operator arities, unresolved symbols with suggestions).
2. Additional edit‑ops: `replace_op`, `move_node`, `wrap_in_if`, assisted `extract_function`.
3. Dataflow IR + parallel executor; `map`, `reduce`, `pipe` primitives.
4. Optional types and light inference; effect system and capabilities.
5. Transpiler to Python/TS; JS runtime for browsers.
