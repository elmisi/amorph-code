**Amorph Code: an AI‑first language (MVP)**

- Goal: design a language primarily for AI/LLM agents, with canonical syntax/semantics that are easy to manipulate, refactor, and validate. Humans can read it, but structural manipulability is the priority.

**Principles**
- Canonical and structured: the program is an explicit JSON AST (no textual ambiguity or hidden implicits).
- Explicit references: variables are `{ "var": "x" }`. No sigils, no implicit scopes.
- Effects separated: side effects (e.g., `print`) are dedicated nodes. Prefer purity elsewhere.
- Determinism: no undefined ordering; lists represent execution sequences.
- Extensible: new operators and built‑ins are single‑key nodes without collisions.
- Validatable: JSON Schema provided for lint/validate.

**Fitness Criteria (for LLM/Agents)**
- Structural editability: everything addressable by path/UID, no fragile textual anchors.
- Deterministic and canonical: same semantics → same serialization; idempotent formatter.
- Multi‑level validation: JSON Schema + semantic lint; structured errors (codes + AST path).
- Locality and atomicity: minimal changes, applied transactionally with dry‑run and rollback.
- Stable references: optional UIDs on statements/defs; explicit symbol resolution.
- Explicit, traceable effects: separate IO; structured tracing.
- Safe extensibility: operator namespaces; language versioning.
- Compactness: human‑friendly form and minified form to reduce tokens.

**Language MVP (v0.1)**
- A program is a JSON array of statements.
- Supported statements:
  - `{"let": {"name": string, "value": expr}}` – declare/assign variable.
  - `{"set": {"name": string, "value": expr}}` – update existing variable.
  - `{"def": {"name": string, "params": [string], "body": [statement]}}` – define function.
  - `{"if": {"cond": expr, "then": [statement], "else": [statement]}}` – control flow.
  - `{"return": expr}` – return from function.
  - `{"print": [expr]}` or `{"print": expr}` – print effect.
  - `{"expr": expr}` – evaluate expression for effects.
- Optional statement metadata: `{"id": string}` next to the statement field (e.g., `{ "id": "s1", "let": {...} }`). Interpreter ignores it; tools (edit/trace) use it.
- Expressions:
  - JSON literals: numbers, strings, booleans, null, lists, and objects.
  - Variable: `{"var": "x"}`.
  - Call: `{"call": {"name": string, "args": [expr]}}` or `{"call": {"id": string, "args": [expr]}}`.
  - Operators: single‑key objects, e.g., `{"add": [...]}`, `{"mul": [...]}`, `{"eq": [...]}`, `{"lt": [...]}`.

**Built‑in operators (MVP)**
- Arithmetic: `add`, `sub`, `mul`, `div`, `mod`, `pow`.
- Comparisons: `eq`, `ne`, `lt`, `le`, `gt`, `ge`.
- Logic: `and`, `or`, `not` (short‑circuit at list level).
- Lists/objects: `list` (normalize), `len`, `get`, `has`.
- Sequences/concat: `range` (1 arg: 1..n; 2 args: a..b, also descending), `concat` (concat lists/strings).
- Minimal IO: `input` (0/1 arg, returns string), `print` (statement). `print` supports `{ "spread": expr }` to expand a list into arguments.
- Conversions: `int` (1 arg).

**Example** (`examples/hello.amr.json`)
[
  { "let": { "name": "x", "value": { "add": [1, 2] } } },
  { "def": { "name": "double", "params": ["n"], "body": [
    { "return": { "mul": [ { "var": "n" }, 2 ] } }
  ]}},
  { "let": { "name": "y", "value": { "call": { "name": "double", "args": [ { "var": "x" } ] } } } },
  { "print": [ { "var": "y" } ] }
]

Expected output: `6`

**Factorial with input** (`examples/factorial.amr.json`)
- Reads `n` from stdin: `{"int": {"input": "Enter n for factorial: "}}`
- Computes and prints `fact: n = res`.

**CLI**
- Run: `amorph run examples/hello.amr.json`
- Options: `--trace` for textual trace; `--trace-json` for JSON events (stderr) with AST path; `--quiet` to silence prints.
- Capability guards: `--deny-input` (block input effect), `--deny-print` (block print effect) for safer agent runs.
- Local alias: use `./bin/amorph` or add `./bin` to your `PATH`.

**Agent Tools**
- `amorph add-uid file [-i] [--deep]` – add missing UIDs to statements/defs; with `--deep` also inside function bodies and if blocks.
- `amorph edit program.json edits.json [--dry-run]` – apply declarative AST edits; optionally validate `edits.json` against `schema/edits-0.1.schema.json` when `jsonschema` is available.
  - Ops:
    - `add_function`: add a function `{name, params, body, id?}`.
    - `rename_function`: rename by `id` or `from` (if unique), update name‑based call‑sites.
    - `insert_before`: insert before node found by `target` (id) or `path`.
    - `insert_after`: like above, but after.
    - `replace_call`: replace calls matching by `name`/`id` with `set:{name?|id?, args?}`.
    - `delete_node`: delete node addressed by `target` (id) or `path`.
  - Output: structural diff/preview on dry‑run; writes file otherwise.
- `amorph rewrite program.json rules.json [--dry-run] [--limit N]` – pattern→replace rewrites with `$name` placeholders; supports JMESPath guards (`select`/`where`) and `apply_to` scoping. See `docs/REWRITE.md`.
- `amorph migrate-calls program.json [--dry-run]` – convert `call` by name to call by id where unambiguous.
- `amorph fmt file [-i]` – canonical formatting.
- `amorph minify in.json -o out.json` – compact keys (token‑friendly).
- `amorph unminify in.json -o out.json` – restore canonical keys.
- `amorph pack in.json -o out.acir [--format cbor|json]` – pack to ACIR (uses CBOR if available and not forced to json).
- `amorph unpack in.acir -o out.json [--format cbor|json]` – unpack ACIR back to canonical JSON.

**Structural addressing (AST path)**
- Some edit‑ops accept `path` to address nodes: key segments and array indices as `$[n]`.
- Example: `/$[1]/def/body/$[0]` → first statement in the body of the second top‑level def.

**Validate**
- `amorph validate file [--json]` – semantic validation: resolves function names/ids, checks core operator arity.
  - `--json` prints `{ ok, issues[] }` with codes, paths and hints; includes warnings like `W_PREFER_ID` and `W_MIXED_CALL_STYLE`.
  - Details and limits: see `docs/VALIDATION.md`.

**Bench**
- `amorph bench [paths...] [--json]` – metrics for files or directories (default `examples/`).
  - Per file: canonical/minified size and ratio, #statements, #functions, UID coverage, presence of `input`, validate/run timings (run skipped if `input`).
  - Aggregate and per‑file output; JSON with `--json`.

**Project structure**
- `amorph/` – Python interpreter and CLI.
- `examples/` – example programs.
- `schema/` – base JSON Schema for validation.
 - `docs/` – documentation.
 - `edits/` – sample edit‑ops (optional).

**Install (optional dependencies)**
- Install CLI + optional features (rewrite guards, ACIR CBOR, schema validation):
  - `pip install -r requirements.txt`
  - Guards in `rewrite` require `jmespath`; ACIR CBOR support requires `cbor2`; schema validation uses `jsonschema`.

**Why an AI‑first language?**
- Goal: reduce fragility of textual edits and maximize structural manipulability by agents/LLMs.
- Key benefits:
  - Programs as canonical AST → no ambiguity, local deltas, predictable diffs.
  - Declarative edit‑DSL with pre/post‑conditions → atomic changes, natural rollback (dry‑run).
  - Semantic validation and structured tracing → machine‑readable feedback and debuggability.
  - Minified “wire” form → fewer tokens, more useful context for LLMs.

**AI‑first architecture (ACIR/ASV)**
- ACIR (Amorph Core IR) – machine view: compact, stable, lossless format for agents.
  - Goal: maximize density (CBOR/opcodes, string‑table), UIDs everywhere, robust addressing.
  - Edits and runtime operate on ACIR; tools produce structural reports/diffs.
- ASV (Amorph Source View) – human view: canonical readable rendering (JSON/DSL) in 1‑to‑1 with ACIR.
  - Goal: review and PRs with clear diffs.
  - Round‑trip guaranteed ACIR↔ASV; comments/annotations live in a separate sidecar.

**Edit protocol “query+rewrite” (roadmap)**
- Query: select nodes by UID/path or JSONPath/JMESPath.
- Rewrite: declarative transforms with pre/post‑conditions and rollback.
- Output: structural report + textual patch on ASV for human review.

**Function reference policy**
- Internal (tools/edits): prefer `call` by `id` for robustness.
- External (human input): `name` allowed for readability; `validate` can warn on undesired mix.

**Canonical AST path for trace/edit**
- Top‑level: `/$[i]` for i‑th statement.
- Function body: `/fn[<id>]/body/$[j]` for j‑th statement in function `<id>`.
- Structural keys: `/if/then/$[k]`, `/if/else/$[k]`, etc.

**IO and channels**
- Runner with abstract IO: separate stdout/stderr/log channels; `--quiet` silences effects for tests/bench.

**Status & Plan**
- Done (current sprint):
  - Quiet IO + capability guards (`--deny-input`, `--deny-print`).
  - JSON trace with call_id and canonical paths.
  - Operator registry + semantic validate; `validate --json` with warnings (W_PREFER_ID, W_MIXED_CALL_STYLE).
  - Edit‑ops (add/rename/insert/replace/delete) + path schema.
  - Rewrite engine with placeholders, list wildcard `$*xs`, JMESPath guards (`select`/`where`/`where_placeholders`) and program scoping (`program_*`, `apply_to`).
  - Minify/unminify; ACIR pack/unpack (CBOR or minified JSON) preserving ids.
  - Bench metrics; examples (hello, factorial, matrix, countdown) and guarded rewrite rules.
- Next (short‑term):
  - Validator++: full operator coverage with coded diagnostics and suggestions; stricter policy checks; `--prefer-id` flag.
  - Rewrite++: richer placeholder conditions and ergonomic selectors; sample rule library.
  - ACIR polish: optional string‑table for frequent string literals; round‑trip tests.
  - Capability model: effect allowlists/profiles; per‑channel capture.
- Later:
  - Modules/imports, dataflow IR and parallel executor, transpilers (Python/TS).
