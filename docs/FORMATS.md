# Formats and Serializations

## Canonical form (human‑friendly)

- JSON AST with explicit keys and deterministic ordering (`amorph fmt`).
- Examples under `examples/`.

## Versioned wrapper (experimental)

- Alternative to top‑level array: `{ "version": "0.2", "program": [ ... ] }`.
- Allows meta‑info and future extensions (capabilities, imports, etc.).

## Minify/Unminify (token‑friendly)

- Short‑key mapping (see `amorph/format.py`).
- Round‑trip guaranteed: `minify` + `unminify` preserve the AST.

Commands:
- `amorph minify in.json -o out.json`
- `amorph unminify in.json -o restored.json`

## Future: binary form

- Goal: CBOR/MessagePack to reduce bytes/tokens, with shared string table and op‑codes.
- Requirements: 1‑1 correspondence with canonical AST, deterministic serialization.
