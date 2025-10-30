## Current Status

Completed (this iteration):
- Quiet IO, capability guards (`--deny-input`, `--deny-print`).
- JSON trace (call_id, timestamps, canonical paths).
- Operator registry and semantic validator; `validate --json` with warnings.
- Edit‑ops (add/rename/insert/replace/delete) and path schema validation.
- Rewrite engine with placeholders, wildcard `$*xs`, JMESPath guards and `apply_to` scoping.
- Minify/unminify; ACIR pack/unpack (CBOR/minified JSON) preserving ids.
- Bench metrics; examples and guarded rewrite rules.

In progress / Next sprint:
- Validator++: full operator coverage with coded diagnostics and hints; `--prefer-id` control.
- Rewrite++: richer placeholder conditions and ergonomic selectors; curated rule sets.
- ACIR polish: optional string‑table expansion for string literals; additional round‑trip tests.
- Capability model: effect allowlists/profiles and per‑channel capture.

Longer term:
- Modules/imports, dataflow IR and parallel executor, transpilers (Python/TS).

