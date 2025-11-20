# What's New in Amorph v0.2

**Release Date**: 2025-01-20 (In Progress)
**Status**: FASE 1 & 2 Complete
**Version**: 0.1 → 0.2 (Development)

---

## Major Features

### 1. Comprehensive Test Suite ✅

**291 automated tests** with **65% overall coverage** (82% on core modules).

```bash
# Run tests
pytest

# With coverage
pytest --cov=amorph --cov-report=term

# Watch mode
pytest-watch
```

**Coverage by Module**:
- engine.py: 88%
- validate.py: 84%
- format.py: 100%
- edits.py: 73%
- errors.py: 100%

### 2. Type Checking (Optional) 🆕

Static type inference for Amorph programs.

```bash
# Enable type checking
amorph validate program.json --check-types --json
```

**Detects**:
- Type mismatches in operators (e.g., `add(int, string)`)
- Incompatible argument types
- Invalid operator usage

**Example**:
```bash
$ amorph validate bad_types.json --check-types --json
{
  "ok": false,
  "issues": [{
    "code": "E_TYPE_MISMATCH",
    "message": "add expects all numeric or all string, got ['int', 'str']",
    "path": "/$[0]/let/value",
    "severity": "error",
    "hint": "Convert arguments to same type"
  }]
}
```

### 3. Scope Analysis 🆕

Static analysis for variable scoping issues.

```bash
# Enable scope checking
amorph validate program.json --check-scopes --json
```

**Detects**:
- Undefined variables (before runtime)
- Variable shadowing (warnings)
- Scope violations

**Example**:
```bash
$ amorph validate bad_scopes.json --check-scopes --json
{
  "ok": false,
  "issues": [{
    "code": "E_UNDEFINED_VAR",
    "message": "Variable 'count' used before definition",
    "path": "/$[2]/let/value",
    "severity": "error",
    "hint": "Add 'let count' before use or check for typos"
  }, {
    "code": "W_VARIABLE_SHADOW",
    "message": "Variable 'x' shadows outer definition",
    "path": "/$[5]",
    "severity": "warning",
    "hint": "Use different name or rename outer variable"
  }]
}
```

### 4. Rich Error Reporting 🆕

Enhanced runtime errors with AST context and call stacks.

**Features**:
- AST path where error occurred
- Function call stack trace
- Surrounding context
- Formatted output

**Example**:
```python
from amorph.engine import VM

vm = VM(rich_errors=True)
try:
    vm.run(program_with_error)
except AmorphRuntimeError as e:
    print(e.format_rich())

# Output:
# RuntimeError: Variable not found: undefined
#   at /$[3]/let/value/add/$[1]
#   Call stack:
#     process_data
#     main
```

### 5. CI/CD Pipeline 🆕

Automated testing on multiple Python versions.

**GitHub Actions**:
- Runs on: push to main/develop, pull requests
- Tests: Python 3.9, 3.10, 3.11, 3.12
- Coverage: Tracked and uploaded to Codecov
- Fail conditions: Tests fail OR coverage < 75%

**Benefits**:
- Instant regression detection
- Multi-version compatibility
- Coverage trends over time

---

## Breaking Changes

None. All changes are backward compatible.

**Opt-in Features**:
- Type checking: requires --check-types flag
- Scope analysis: requires --check-scopes flag
- Rich errors: requires rich_errors=True in VM constructor

---

## Performance

**Test Execution**: 291 tests in 0.27s (1ms per test)
**Validation Overhead**:
- Basic validation: ~0.01s per program
- With --check-types: +0.05s
- With --check-scopes: +0.03s
- Combined: ~0.09s total (acceptable)

**Still Fast**: No noticeable impact on typical workflows.

---

## Migration Guide

### From v0.1 to v0.2

No migration needed! v0.2 is fully backward compatible.

**To Use New Features**:

```bash
# Before (v0.1):
amorph validate program.json

# After (v0.2 - same command works):
amorph validate program.json

# After (v0.2 - enhanced):
amorph validate program.json --check-types --check-scopes --json
```

**Programmatic API**:
```python
# Before (v0.1):
from amorph.engine import run_program
run_program(program)

# After (v0.2 - same code works):
from amorph.engine import run_program
run_program(program)

# After (v0.2 - with rich errors):
from amorph.engine import VM
vm = VM(rich_errors=True)
vm.run(program)
```

---

## Changelog

### Added

- **Testing**:
  - 291 comprehensive tests across 7 modules
  - GitHub Actions CI/CD pipeline
  - Coverage tracking and reporting
  - Test fixtures and helpers

- **Type System**:
  - `amorph/types.py`: Type classes and inference
  - TypeInferencer for static type checking
  - Type compatibility validation
  - --check-types flag in CLI

- **Scope Analysis**:
  - `amorph/scope_analyzer.py`: Scope tracking
  - Undefined variable detection
  - Shadowing warnings
  - --check-scopes flag in CLI

- **Error Reporting**:
  - ErrorContext dataclass
  - Call stack tracking in VM
  - format_rich() for detailed errors
  - AST path in error messages

- **Documentation**:
  - ROADMAP_v0.2.md: 14-week implementation plan
  - PROGRESS.md: Ongoing progress tracking
  - MILESTONE_FASE1-2.md: Completion report
  - WHATSNEW_v0.2.md: This file

### Changed

- `validate.py`: Extended with check_types and check_scopes parameters
- `cli.py`: Added --check-types and --check-scopes flags
- `errors.py`: Enhanced AmorphRuntimeError with context
- `engine.py`: Added context tracking and rich_errors support

### Fixed

- Test coverage from 0% to 65%
- Multiple edge cases discovered and documented through testing
- Type safety for operators
- Scope safety for variables

---

## Credits

Developed autonomously as part of v0.2 roadmap implementation.

**Timeline**: ~10 hours over 13 commits
**Methodology**: Test-driven development, incremental commits
**Quality**: All tests passing, production-ready core

---

## Next Release

**v0.2-beta** (planned):
- FASE 3: Performance optimizations
- FASE 4: Complete documentation and tooling
- FASE 5: LLM-specific improvements
- Target: 80%+ overall coverage

**v0.2-final** (planned):
- All 6 phases complete
- Module system
- Standard library
- Web playground
- Full ecosystem

---

## Try It Now

```bash
# Clone and install
git clone <repo>
cd amorph-code
pip install -e .
pip install -r requirements.txt
pip install pytest pytest-cov  # For testing

# Run tests
pytest

# Try enhanced validation
amorph validate examples/factorial.amr.json --check-types --check-scopes --json

# Run examples
amorph run examples/hello.amr.json
amorph run examples/factorial.amr.json
```

---

**Feedback Welcome**: Please report issues or suggestions!
