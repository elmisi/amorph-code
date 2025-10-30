# Edit‑Ops (MVP)

`edits.json` format: array of operations validated by `schema/edits-0.1.schema.json`.

Supported operations:

- add_function
  - Payload: `{ "op":"add_function", "name": str, "params": [str], "body": [stmt], "id?": str }`
  - Effect: append a function definition to the program.

- rename_function
  - Payload: `{ "op":"rename_function", "id?": str, "from?": str, "to": str }`
  - Effect: rename the target `def`; update name‑based call sites (id‑based calls already robust).

- insert_before / insert_after
  - Payload: `{ "op":"insert_before|insert_after", "target?": id, "path?": str, "node": stmt }`
  - Effect: insert `node` relative to the addressed node.

- replace_call
  - Payload: `{ "op":"replace_call", "match": {"name?": str, "id?": str}, "set": {"name?": str, "id?": str, "args?": [expr]} }`
  - Effect: replace calls matching `match` with fields in `set`.

- delete_node
  - Payload: `{ "op":"delete_node", "target?": id, "path?": str }`
  - Effect: delete the addressed node.

AST path addressing:
- Syntax: `/`‑separated segments; array indices as `$[n]`.
- Segments allowed by schema: `$[n]`, `fn[<id-or-name>]`, or alphanum with `_`/`-`.
- Example: `/$[1]/def/body/$[0]` → first statement in second top‑level def’s body.

Usage tips:
- Always run with `--dry-run` first.
- Use `add-uid --deep` to stamp `id` everywhere before complex edits.
- Validate with `amorph validate` after modifications.
