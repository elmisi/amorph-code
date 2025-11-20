# Refactoring Operations (v0.2)

Amorph v0.2 introduces powerful refactoring operations that automatically update all references when renaming or extracting code.

## Overview

New refactoring operations:
- `rename_variable`: Rename variable + update all references in scope
- `extract_function`: Extract statements into new function
- Smart suggestions via `amorph suggest`

---

## rename_variable

Rename a variable and automatically update all references.

### Syntax

```json
{
  "op": "rename_variable",
  "old_name": "x",
  "new_name": "count",
  "scope": "all" | "<function_id>",
  "path"?: "/<optional_subtree_path>"
}
```

### Parameters

- `old_name` (required): Current variable name
- `new_name` (required): New variable name
- `scope` (optional, default "all"): Scope to rename in
  - `"all"`: Rename in all scopes
  - `"<function_id>"`: Rename only in specific function
- `path` (optional): Limit to subtree at path

### Examples

#### Example 1: Rename in global scope

**Input program.json**:
```json
[
  {"let": {"name": "x", "value": 10}},
  {"let": {"name": "y", "value": {"mul": [{"var": "x"}, 2]}}},
  {"print": [{"var": "x"}]}
]
```

**Edit rename.json**:
```json
[
  {
    "op": "rename_variable",
    "old_name": "x",
    "new_name": "counter",
    "scope": "all"
  }
]
```

**Apply**:
```bash
amorph edit program.json rename.json
# Output: {"applied": 1, "details": [{"op": "rename_variable", "changed": 3}]}
```

**Result**: All 3 references to `x` updated (definition + 2 usages).

#### Example 2: Rename in function scope only

**Input**:
```json
[
  {"let": {"name": "x", "value": 1}},
  {"def": {"name": "func", "id": "fn_1", "params": ["x"], "body": [
    {"return": {"var": "x"}}
  ]}}
]
```

**Edit**:
```json
[
  {
    "op": "rename_variable",
    "old_name": "x",
    "new_name": "param",
    "scope": "fn_1"
  }
]
```

**Result**: Only function parameter and its usage renamed. Global `x` unchanged.

### How It Works

1. **Analysis**: Scans entire program to find all references
2. **Filtering**: Filters by scope (global vs function)
3. **Renaming**: Updates all filtered references
4. **Reports**: Returns count of changed references

### Reference Types

- `definition`: `let` statement
- `write`: `set` statement
- `read`: `{"var": "name"}` expression

---

## extract_function

Extract a sequence of statements into a new function.

### Syntax

```json
{
  "op": "extract_function",
  "function_name": "extracted_func",
  "function_id"?: "fn_extracted",
  "statements": [1, 2, 3],
  "parameters": ["free_var1", "free_var2"],
  "insert_at": 0,
  "replace_with_call": true
}
```

### Parameters

- `function_name` (required): Name for new function
- `function_id` (optional): ID for new function
- `statements` (required): Indices of statements to extract (must be consecutive)
- `parameters` (required): Variables to become parameters
- `insert_at` (required): Where to insert new function
- `replace_with_call` (optional, default true): Replace extracted code with call

### Example

**Input**:
```json
[
  {"let": {"name": "x", "value": 10}},
  {"let": {"name": "y", "value": {"mul": [{"var": "x"}, 2]}}},
  {"let": {"name": "z", "value": {"add": [{"var": "y"}, 5]}}},
  {"print": [{"var": "z"}]}
]
```

**Edit**:
```json
[
  {
    "op": "extract_function",
    "function_name": "calculate",
    "function_id": "fn_calc",
    "statements": [1, 2],
    "parameters": ["x"],
    "insert_at": 1,
    "replace_with_call": true
  }
]
```

**Result**:
```json
[
  {"let": {"name": "x", "value": 10}},
  {"def": {"name": "calculate", "id": "fn_calc", "params": ["x"], "body": [
    {"let": {"name": "y", "value": {"mul": [{"var": "x"}, 2]}}},
    {"let": {"name": "z", "value": {"add": [{"var": "y"}, 5]}}}
  ]}},
  {"expr": {"call": {"id": "fn_calc", "args": [{"var": "x"}]}}},
  {"print": [{"var": "z"}]}
]
```

### Free Variable Analysis

Use `analyze_free_variables()` to find which variables need to be parameters:

```python
from amorph.refactor import analyze_free_variables

statements = [
  {"let": {"name": "y", "value": {"mul": [{"var": "x"}, 2]}}}
]

free = analyze_free_variables(statements)
# Returns: {"x"} - x is used but not defined in this block
```

---

## Smart Suggestions

The `amorph suggest` command analyzes programs and suggests improvements.

### Usage

```bash
# Get suggestions
amorph suggest program.json

# JSON output
amorph suggest program.json --json
```

### Example Output

```
Found 3 suggestions:

1. [MEDIUM] add_uid
   Reason: Function 'calculate' lacks stable id for robust references
   Impact: Safe

2. [LOW] add_uid_all
   Reason: 5 statements lack ids for precise targeting
   Impact: Safe

3. [LOW] extract_function
   Reason: Sequence of 3 statements at /$[2] could be extracted
   Impact: Optimization
```

### JSON Output

```bash
amorph suggest program.json --json
```

```json
{
  "total": 2,
  "suggestions": [
    {
      "operation": "rename_variable",
      "reason": "Single-letter variable 'x' used 5 times",
      "edit_spec": {
        "op": "rename_variable",
        "old_name": "x",
        "new_name": "x_descriptive",
        "scope": "all"
      },
      "priority": "medium",
      "estimated_impact": "Safe"
    }
  ]
}
```

### Applying Suggestions

```bash
# 1. Get suggestions
amorph suggest program.json --json > suggestions.json

# 2. Extract edit_spec from suggestion
jq '.suggestions[0].edit_spec' suggestions.json > edit.json

# 3. Wrap in array
echo "[$(cat edit.json)]" > edits.json

# 4. Apply
amorph edit program.json edits.json
```

---

## Variable Reference Tracking

Find all references to a variable programmatically:

```python
from amorph.refactor import find_variable_references

program = [...]
refs = find_variable_references(program, "x", scope="all")

for ref in refs:
    print(f"{ref.ref_type} at {ref.path} in {ref.scope_id}")

# Output:
# definition at /$[0]/let/name in global
# read at /$[1]/let/value/var in global
# write at /$[2]/set/name in global
```

---

## Integration with Validation

Refactoring operations integrate with validation:

```bash
# 1. Analyze program
amorph validate program.json --check-scopes --json

# 2. If undefined variable found, suggest fix
# E_UNDEFINED_VAR: Variable 'count' used before definition

# 3. Use rename to fix typo (if it was supposed to be 'counter')
echo '[{"op": "rename_variable", "old_name": "count", "new_name": "counter", "scope": "all"}]' > fix.json
amorph edit program.json fix.json
```

---

## Best Practices

### When to Use rename_variable

✅ **Good uses**:
- Renaming for clarity (x → counter)
- Fixing typos (coutner → counter)
- Following naming conventions
- Resolving shadowing issues

❌ **Avoid**:
- Renaming across unrelated scopes
- Renaming without understanding usage
- Mass renames without testing

### When to Use extract_function

✅ **Good uses**:
- Repeated code sequences
- Complex logic that deserves a name
- Reducing function length
- Improving testability

❌ **Avoid**:
- Extracting single statements
- Breaking logical cohesion
- Creating functions with many parameters (>5)

---

## Error Handling

### Common Errors

**E_NOT_FOUND**: Variable not found
```
Variable 'x' not found in program
→ Check spelling, ensure variable exists
```

**E_BAD_SPEC**: Invalid specification
```
rename_variable requires old_name and new_name
→ Provide both parameters
```

**E_NOT_FOUND (scope)**: Variable not in specified scope
```
Variable 'x' not found in scope 'fn_1'
→ Check scope parameter, variable may be in different scope
```

---

## Advanced Usage

### Rename with Path Limitation

Rename only in specific subtree:

```json
{
  "op": "rename_variable",
  "old_name": "x",
  "new_name": "count",
  "scope": "all",
  "path": "/$[2]/def/body"
}
```

Only renames references within `/$[2]/def/body`.

### Extract with Custom Parameters

```json
{
  "op": "extract_function",
  "function_name": "process",
  "statements": [5, 6, 7, 8],
  "parameters": ["input_data", "config"],
  "insert_at": 5,
  "replace_with_call": true
}
```

Creates function with 2 parameters from free variables.

---

## See Also

- `docs/EDIT-OPS.md`: Other edit operations
- `docs/VALIDATION.md`: Validation system
- `WHATSNEW_v0.2.md`: All v0.2 features
