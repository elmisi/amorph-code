# Amorph v0.2 - Quick Start Guide

Get started with Amorph in 5 minutes!

## Installation

```bash
# Clone repository
git clone <your-repo-url>
cd amorph-code

# Install
pip install -e .

# Optional dependencies (recommended)
pip install -r requirements.txt

# Development tools (if you want to run tests)
pip install pytest pytest-cov
```

## Your First Program

Create `hello.json`:
```json
[
  {"let": {"name": "message", "value": "Hello, Amorph!"}},
  {"print": [{"var": "message"}]}
]
```

Run it:
```bash
amorph run hello.json
# Output: Hello, Amorph!
```

## Core Commands

### 1. Run Programs

```bash
# Basic run
amorph run program.json

# With tracing
amorph run program.json --trace

# Quiet mode (no output)
amorph run program.json --quiet
```

### 2. Validate Programs (v0.2 Enhanced!)

```bash
# Basic validation
amorph validate program.json

# With type checking
amorph validate program.json --check-types --json

# With scope analysis
amorph validate program.json --check-scopes --json

# All checks
amorph validate program.json --check-types --check-scopes --json
```

**Example output**:
```json
{
  "ok": false,
  "issues": [
    {
      "code": "E_TYPE_MISMATCH",
      "message": "add expects all numeric or all string, got ['int', 'str']",
      "path": "/$[0]/let/value",
      "severity": "error",
      "hint": "Convert arguments to same type"
    }
  ]
}
```

### 3. Format & Minify

```bash
# Format canonically
amorph fmt program.json -i

# Minify (reduce size)
amorph minify program.json -o program.min.json

# Unminify
amorph unminify program.min.json -o program.json
```

### 4. Refactoring (v0.2 New!)

#### Rename Variable

Create `rename.json`:
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

Apply:
```bash
amorph edit program.json rename.json
# All references to 'x' are now 'counter'!
```

#### Get Smart Suggestions

```bash
amorph suggest program.json

# Output:
# Found 2 suggestions:
#
# 1. [MEDIUM] add_uid
#    Reason: Function 'calculate' lacks stable id
#    Impact: Safe
#
# 2. [LOW] extract_function
#    Reason: Sequence of 3 statements could be extracted
#    Impact: Optimization
```

### 5. Add UIDs

```bash
# Add UIDs to top-level statements and function defs
amorph add-uid program.json -i

# Add UIDs everywhere (deep)
amorph add-uid program.json -i --deep
```

## Common Workflows

### Workflow 1: Write and Validate

```bash
# 1. Write program
cat > program.json << 'EOF'
[
  {"let": {"name": "x", "value": 10}},
  {"print": [{"var": "x"}]}
]
EOF

# 2. Validate
amorph validate program.json --check-types --check-scopes
# Output: OK

# 3. Run
amorph run program.json
# Output: 10
```

### Workflow 2: Safe Refactoring

```bash
# 1. Get suggestions
amorph suggest program.json --json > suggestions.json

# 2. Create edit from suggestion
cat > edit.json << 'EOF'
[
  {
    "op": "rename_variable",
    "old_name": "x",
    "new_name": "count",
    "scope": "all"
  }
]
EOF

# 3. Preview changes
amorph edit program.json edit.json --dry-run

# 4. Apply
amorph edit program.json edit.json

# 5. Validate result
amorph validate program.json --check-scopes
```

### Workflow 3: Fix Type Errors

```bash
# 1. Write program with type error
cat > bad_types.json << 'EOF'
[{"let": {"name": "x", "value": {"add": [1, "text"]}}}]
EOF

# 2. Check types
amorph validate bad_types.json --check-types --json
# Shows: E_TYPE_MISMATCH with hint

# 3. Fix based on hint
# Edit to use all numbers or all strings

# 4. Validate again
amorph validate fixed.json --check-types
# Output: OK
```

## Language Basics

### Statements

```json
// Variable declaration
{"let": {"name": "x", "value": 5}}

// Variable update
{"set": {"name": "x", "value": 10}}

// Function definition
{"def": {"name": "double", "params": ["n"], "body": [
  {"return": {"mul": [{"var": "n"}, 2]}}
]}}

// Function call by name
{"let": {"name": "result", "value": {"call": {"name": "double", "args": [5]}}}}

// Function call by id (robust!)
{"let": {"name": "result", "value": {"call": {"id": "fn_double", "args": [5]}}}}

// Conditional
{"if": {"cond": {"gt": [{"var": "x"}, 0]}, "then": [
  {"print": ["positive"]}
], "else": [
  {"print": ["negative or zero"]}
]}}

// Return from function
{"return": {"var": "result"}}

// Print (side effect)
{"print": ["Hello", {"var": "name"}]}

// Expression for side effects
{"expr": {"call": {"name": "func", "args": []}}}
```

### Operators

```json
// Arithmetic
{"add": [1, 2, 3]}        // 6
{"sub": [10, 3]}          // 7
{"mul": [2, 3, 4]}        // 24
{"div": [10, 2]}          // 5
{"mod": [10, 3]}          // 1
{"pow": [2, 3]}           // 8

// Comparison
{"eq": [5, 5]}            // true
{"lt": [3, 5]}            // true
{"le": [5, 5]}            // true

// Logic
{"and": [true, true]}     // true
{"or": [false, true]}     // true
{"not": false}            // true

// Collections
{"list": [1, 2, 3]}       // [1, 2, 3]
{"len": [1, 2, 3]}        // 3
{"get": [[1, 2, 3], 1]}   // 2
{"has": [[1, 2], 1]}      // true
{"concat": [[1], [2]]}    // [1, 2]

// Sequences
{"range": 5}              // [1, 2, 3, 4, 5]
{"range": [3, 7]}         // [3, 4, 5, 6, 7]

// Conversion
{"int": "42"}             // 42
```

## Examples

### Factorial (Recursive)

See `examples/factorial.amr.json`:
```json
[
  {"def": {"name": "fact", "id": "fn_fact", "params": ["n"], "body": [
    {"if": {"cond": {"le": [{"var": "n"}, 1]}, "then": [
      {"return": 1}
    ], "else": [
      {"return": {"mul": [
        {"var": "n"},
        {"call": {"id": "fn_fact", "args": [{"sub": [{"var": "n"}, 1]}]}}
      ]}}
    ]}}
  ]}},
  {"let": {"name": "result", "value": {"call": {"id": "fn_fact", "args": [5]}}}},
  {"print": ["factorial(5) =", {"var": "result"}]}
]
```

Run:
```bash
amorph run examples/factorial.amr.json
# Output: factorial(5) = 120
```

## Testing Your Changes

```bash
# Run all tests
pytest

# Run specific test module
pytest amorph/tests/test_engine.py

# With coverage
pytest --cov=amorph --cov-report=term

# Watch mode (runs on file changes)
pip install pytest-watch
ptw
```

## Getting Help

```bash
# General help
amorph --help

# Command-specific help
amorph validate --help
amorph edit --help
amorph suggest --help

# Documentation
cat docs/VALIDATION.md
cat docs/EDIT-OPS.md
cat docs/REFACTORING.md
cat WHATSNEW_v0.2.md
```

## Next Steps

1. **Read**: `WHATSNEW_v0.2.md` for all new features
2. **Try**: `examples/` directory programs
3. **Experiment**: Create your own programs
4. **Refactor**: Use `rename_variable` and `extract_function`
5. **Contribute**: See `CONTRIBUTING.md` (if available)

## Common Issues

### Issue: Type Error
```
E_TYPE_MISMATCH: add expects all numeric or all string
```
**Fix**: Ensure all arguments to `add` are same type (all int/float OR all string)

### Issue: Undefined Variable
```
E_UNDEFINED_VAR: Variable 'x' used before definition
```
**Fix**: Add `{"let": {"name": "x", "value": ...}}` before usage

### Issue: Function Not Found
```
Function not defined: my_function
```
**Fix**: Define function before calling, or check for typos

## Resources

- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory
- **Tests**: `amorph/tests/` (great learning resource!)
- **Roadmap**: `docs/ROADMAP_v0.2.md`
- **What's New**: `WHATSNEW_v0.2.md`

---

**Happy coding with Amorph!** 🚀
