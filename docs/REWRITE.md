# Rewrite: pattern → replace (MVP)

Le regole di riscrittura permettono di applicare trasformazioni strutturali all’AST con placeholder, utili per semplificazioni o migrazioni.

## Regole

Format: array of objects with `match` and `replace` fields. Optional guards (JMESPath) restrict applicability:
- `select`: JMESPath run on the current node.
- `where`: array of JMESPath expressions run on the current node (all must be truthy).
- `program_select`: JMESPath run on the root program (scope control).
- `program_where`: array of JMESPath expressions run on the root program.
- `where_placeholders`: object mapping placeholder names to JMESPath expressions evaluated on the bound placeholder subtree.
- `apply_to`: JMESPath (string or array) selecting program subtrees eligible for rewrite (limits where a rule can apply).

- Placeholders: strings `"$name"` capture any subtree and can be reused in the `replace` template.
- Matching:
  - Lists: same length, element‑wise match (placeholders allowed).
  - Objects: pattern keys must exist and match (subset matching; extra node keys are retained).
  - Scalars: equality.

Example (arithmetic simplifications):
[
  { "match": {"add": ["$x", 0] }, "replace": "$x" },
  { "match": {"add": [0, "$x"] }, "replace": "$x" },
  { "match": {"mul": ["$x", 1] }, "replace": "$x" },
  { "match": {"mul": [1, "$x"] }, "replace": "$x" }
]

CLI:
- Preview: `amorph rewrite program.json rules.json --dry-run`
- Apply: `amorph rewrite program.json rules.json`
- Limit replacements: `--limit N`

Notes:
- Rewrites apply recursively on statements and expressions.
- Variable‑length list wildcard supported: use `$*xs` inside a list pattern to match any list of elements; in `replace`, `$*xs` expands to those elements.
- Matching is intentionally simple; future extensions may add `where` conditions.
Guards with JMESPath:
- `select`: a single JMESPath expression evaluated against the current node; must be truthy to apply.
- `where`: an array of JMESPath expressions; all must be truthy to apply.

Example:
[
  { "match": {"call": {"name": "double"}}, "replace": {"call": {"id": "$id", "args": "$*args"}}, "select": "call.name == 'double'" }
]
