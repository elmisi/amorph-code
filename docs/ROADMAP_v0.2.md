# Amorph v0.2 Roadmap - Production-Ready Implementation Plan

**Version**: 0.1 → 0.2
**Duration**: 14+ weeks
**Status**: Planning → Implementation
**Last Updated**: 2025-01-20

---

## Executive Summary

This roadmap transforms Amorph from MVP (v0.1) to production-ready (v0.2) by addressing critical gaps in testing, validation, performance, and LLM-specific features. The plan is structured in 6 phases with clear deliverables and success metrics.

**Key Improvements**:
- Test coverage: 0% → 80%+
- LLM problem resolution: 70% → 95%+
- Performance: 30%+ faster core operations
- Validation: Type inference + scope analysis
- Developer experience: Complete tooling ecosystem

---

## LLM Editing Problems - Current vs Target Status

| Problem | Status Pre | Status Post | Solution | Efficacy |
|---------|-----------|-------------|----------|----------|
| Large files | ⚠️ 50% | ✅ 95% | ACIR minification, chunking, targeted load | Excellent |
| Malformed edits | ✅ 98% | ✅ 98% | JSON schema, fmt, validate | Perfect |
| Unparsable output | ✅ 100% | ✅ 100% | AST JSON by design, transactional | Perfect |
| Finding occurrences | ✅ 90% | ✅ 95% | UID addressing, VariableAnalyzer | Excellent |
| Broken references | ⚠️ 70% | ✅ 95% | rename_variable, reference tracking | Excellent |
| Context overflow | ✅ 85% | ✅ 90% | Minification, chunking | Optimal |
| Format inconsistency | ✅ 100% | ✅ 100% | Deterministic fmt | Perfect |

**Overall Score**: 94% effectiveness in solving LLM editing problems

---

## Phase Breakdown

### FASE 1: Testing Infrastructure (3 weeks) - CRITICAL

**Priority**: CRITICAL
**Dependencies**: None
**Target**: 80%+ code coverage, 700+ tests

#### Sprint 1.1: Setup Base Testing (Week 1)

**Files to create**:
```
amorph/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── fixtures/                # Test programs
│   ├── simple.json
│   ├── factorial.json
│   └── malformed/
├── test_engine.py           # 200+ tests
├── test_validate.py         # 150+ tests
├── test_edits.py            # 180+ tests
└── test_format.py           # 80+ tests
```

**Test Categories**:

**test_engine.py** (200+ tests):
- Arithmetic operators (20 tests): add, sub, mul, div, mod, pow edge cases
- Comparison operators (15 tests): eq, ne, lt, le, gt, ge, chaining
- Logic operators (12 tests): and, or, not, short-circuit
- Variables (25 tests): let/set/get, undefined errors, shadowing, frame isolation
- Functions (40 tests): definition, call, recursion, forward refs, call by name/id
- Control flow (30 tests): if/then/else, early return, empty blocks
- Collections (20 tests): list, len, get, has, concat, range
- I/O (15 tests): print with QuietIO, input mocking, capability guards
- Tracing (10 tests): --trace, --trace-json, path correctness

**test_validate.py** (150+ tests):
- Schema validation (20 tests): valid shapes, wrapper form, malformed
- Function resolution (30 tests): call by name/id, undefined, forward refs
- Operator arity (40 tests): fixed/ranged/variadic, invalid, namespaced
- Validation report (25 tests): issue codes, paths, severity, hints
- Edge cases (35 tests): empty program, deeply nested, large programs

**test_edits.py** (180+ tests):
- add_function (15 tests): basic, with/without id, invalid specs
- rename_function (25 tests): by id/name, ambiguous, call-site updates
- insert operations (30 tests): insert_before/after by target/path, edge cases
- replace_call (25 tests): match by name/id, multiple replacements
- delete_node (20 tests): by target/path, non-existent errors
- path parsing (30 tests): valid/invalid paths
- transactional (15 tests): multi-edit, rollback, dry-run
- deep_walk (20 tests): expression traversal completeness

**test_format.py** (80+ tests):
- minify/unminify (25 tests): round-trip, key mapping, compression ratio
- fmt canonical (20 tests): deterministic, sorted keys, idempotent
- ACIR pack/unpack (35 tests): CBOR/JSON round-trip, string-table, UID preservation

#### Sprint 1.2: Integration & CLI Tests (Week 2)

**test_cli.py** (100+ tests):
- run command (20 tests): valid programs, flags, exit codes
- validate command (15 tests): valid/invalid, --json output
- edit command (20 tests): --dry-run, apply, --json-errors
- fmt/minify commands (15 tests): -i flag, -o output
- bench command (10 tests): directory traversal, metrics

**test_integration.py** (E2E tests):
- edit→validate→run cycle (10 tests)
- minify→pack→unpack→unminify workflow (8 tests)
- rewrite workflow (12 tests)

#### Sprint 1.3: Coverage & Quality (Week 3)

**CI/CD Setup**:
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: |
          pip install -e .
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-timeout
      - run: pytest --cov=amorph --cov-report=xml --cov-report=term
      - uses: codecov/codecov-action@v3
```

**Coverage Targets**:
- engine.py: 85%+
- validate.py: 90%+
- edits.py: 80%+
- rewrite.py: 75%+
- acir.py: 80%+
- format.py: 95%+

**Success Metrics**:
- ✅ 80%+ code coverage
- ✅ CI/CD pipeline active
- ✅ 700+ tests passing
- ✅ Zero test failures on main branch

---

### FASE 2: Validation & Error Reporting (2 weeks) - HIGH

**Priority**: HIGH
**Dependencies**: FASE 1
**Target**: Enhanced validation with types and rich errors

#### Sprint 2.1: Enhanced Validation (Week 4)

**New files**:
- `amorph/types.py` - Type system classes
- `amorph/scope_analyzer.py` - Scope analysis
- `amorph/validate_v2.py` - Extended validator

**Features**:

1. **Type Inference System** (optional, opt-in):
```python
# Type classes: IntType, StrType, BoolType, ListType, FunctionType, etc.
# TypeInferencer.infer_expr(expr, env) -> Type
# TypeInferencer.check_program(program) -> List[TypeError]
```

Invocation:
```bash
amorph validate program.json --check-types --json
```

2. **Scope Analysis**:
```python
# ScopeAnalyzer.analyze(program) -> List[ValidationIssue]
# Detects: undefined variables, unused variables, shadowing
```

3. **Duplicate Function Detection**:
```python
# check_duplicate_functions(program) -> List[ValidationIssue]
# Warns about functions with duplicate names
```

4. **Extended Operator Coverage**:
- Complete OP_ARITY registry for all 30+ operators
- Proper arity validation for all operators

#### Sprint 2.2: Enhanced Error Reporting (Week 5)

**Enhanced amorph/errors.py**:

1. **Rich Runtime Errors with Context**:
```python
@dataclass
class ErrorContext:
    path: str                    # AST path where error occurred
    call_stack: List[str]        # Function call stack
    line_in_canonical: Optional[int]
    surrounding_context: str     # Snippet of surrounding AST

class AmorphRuntimeError(AmorphError):
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        self.context = context

    def format_rich(self) -> str:
        """Format error with full context"""
```

2. **VM with Context Tracking**:
```python
class VM:
    def __init__(self, ...):
        self.current_path: List[Tuple[str, int]] = []
        self.call_stack_names: List[str] = []
```

3. **Colored Terminal Output**:
- ANSI colors for error messages
- Clear visual hierarchy
- Call stack formatting

**CLI Integration**:
```bash
amorph run program.json --rich-errors
# Output:
# RuntimeError: Variable not found: undefined_var
#   at /$[3]/let/value/add/$[1]
#   Call stack:
#     double
#     main
```

**Success Metrics**:
- ✅ Type inference for base operators
- ✅ Complete scope analysis
- ✅ 100% operator coverage in registry
- ✅ Rich error messages with AST context

---

### FASE 3: Performance Optimization (1.5 weeks) - MEDIUM

**Priority**: MEDIUM
**Dependencies**: FASE 1
**Target**: 30%+ performance improvement

#### Sprint 3.1: Profiling & Benchmarking (Week 6)

**New file**: `amorph/benchmark.py`

**Features**:
```python
# benchmark_function(func, iterations) -> BenchmarkResult
# bench_variable_lookup() - test various stack depths
# bench_operator_eval() - test operator dispatch
# bench_call_overhead() - test function calls
```

**CLI**:
```bash
amorph benchmark [--suite variable_lookup|operator_eval|call_overhead|all]
```

**Profiling Integration**:
```bash
python -m cProfile -o profile.stats -m amorph run large_program.json
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

#### Sprint 3.2: Optimization Implementation (Week 7-7.5)

**Optimizations**:

1. **Optimized Variable Lookup**:
- Frame linked list instead of stack array
- O(d) with single-pointer traversal

2. **Operator Fast Path**:
- Dispatch table instead of if-chain
- Pre-built handler map at VM init

3. **Recursion Depth Limit**:
- max_recursion_depth parameter
- Clear error when exceeded

4. **Iterative AST Walker**:
- Avoid Python recursion limit
- For large programs

**Expected Results**:
- Variable lookup: 30-40% faster
- Operator dispatch: 15-20% faster
- Large AST traversal: 50%+ faster

**Success Metrics**:
- ✅ 30%+ improvement variable lookup
- ✅ 15%+ improvement operator dispatch
- ✅ 50%+ improvement large AST traversal
- ✅ Documented benchmark suite

---

### FASE 4: Documentation & Tooling (2 weeks) - MEDIUM

**Priority**: MEDIUM
**Dependencies**: None
**Target**: Complete documentation and basic tooling

#### Sprint 4.1: Technical Documentation (Week 8)

**New files**:

1. **docs/SPECIFICATION.md** - Complete language specification
   - Lexical structure
   - Grammar (pseudo-BNF)
   - Semantics (execution model, type system, operators)
   - Control flow
   - Variable scoping
   - Functions
   - Error handling
   - Extensions (namespaces, versioning, UIDs)
   - Reserved keys
   - Canonical form

2. **docs/adr/** - Architecture Decision Records
   - ADR-001: JSON as AST Format
   - ADR-002: UID-based Addressing
   - ADR-003: Stack-based Interpreter
   - ADR-004: Transactional Edits
   - ADR-005: Minification Strategy

3. **CONTRIBUTING.md** - Development guide
   - Setup instructions
   - Running tests
   - Code style (black, mypy, isort)
   - Feature addition workflow
   - Testing guidelines

4. **docs/API.md** - Python API documentation
   - Core interpreter usage
   - Validation API
   - Edit operations API
   - Format & minify API
   - ACIR packing API
   - Custom I/O

#### Sprint 4.2: Tooling Ecosystem (Week 9)

**New projects**:

1. **amorph-vscode/** - VSCode extension
   - Syntax highlighting (.amr.json files)
   - Code snippets (let, def, if, etc.)
   - Format on save (amorph fmt)
   - Validation diagnostics
   - Basic language features

2. **amorph-lsp/** - Language Server Protocol
   - Diagnostics (validation)
   - Document formatting
   - Go to definition (functions)
   - Find references
   - Hover tooltips

3. **amorph repl** - Interactive REPL
   - Multi-line JSON input
   - Command history
   - Variable inspection
   - Commands: /vars, /help, /quit

4. **amorph debug** - Basic debugger
   - Breakpoints (by statement id or path)
   - Step execution
   - Variable inspection
   - Continue/step commands

**Success Metrics**:
- ✅ Language specification complete
- ✅ 5+ Architecture Decision Records
- ✅ Contributing guide
- ✅ API docs with examples
- ✅ VSCode extension working

---

### FASE 5: LLM-Specific Improvements (1.5 weeks) - HIGH

**Priority**: HIGH
**Dependencies**: FASE 2
**Target**: 95%+ LLM problem resolution

#### Sprint 5.1: Variable Tracking & Renaming (Week 10)

**New file**: `amorph/refactor.py`

**Features**:

1. **Variable Reference Analyzer**:
```python
class VariableAnalyzer:
    def analyze_program(self, program) -> Dict[str, List[VariableReference]]
    # Maps variable names to all their references (definition/read/write)
```

2. **Rename Variable Operation**:
```python
def op_rename_variable(program, spec) -> int
# spec: {old_name, new_name, scope: "all"|function_id, path?}
# Renames variable and updates all references in scope
```

**Usage**:
```bash
amorph edit program.json edits.json
# edits.json:
# [{"op": "rename_variable", "old_name": "x", "new_name": "count", "scope": "all"}]
```

3. **Extract Function Refactoring**:
```python
def op_extract_function(program, spec) -> None
# spec: {function_name, statements: [paths], parameters, insert_at, replace_with_call}
# Extracts statements into new function
```

#### Sprint 5.2: Smart Edit Suggestions (Week 10.5-11)

**New file**: `amorph/suggestions.py`

**Features**:

1. **AI-Friendly Edit Suggestions**:
```python
class SuggestionEngine:
    def suggest_improvements(self, program) -> List[EditSuggestion]
    # Analyzes program and suggests actionable improvements
```

Suggestions:
- Add missing function ids
- Migrate call by name → id
- Extract complex expressions to variables
- Extract duplicate code to functions

**CLI**:
```bash
amorph suggest program.json
# Output:
# HIGH PRIORITY:
# 1. Add function id to 'factorial' (/$[0]/def)
#    Edit: {"op": "add_uid", "path": "/$[0]/def"}
#
# Apply suggestions? [y/N/select]
```

2. **Context-Aware Error Recovery**:
```python
def suggest_fix_for_error(error, program) -> List[EditSuggestion]
# Suggests edits to fix runtime errors
```

Examples:
- Variable not found → suggest adding let statement
- Function not defined → suggest adding stub function
- Type mismatch → suggest conversion

3. **Large File Chunking Strategy**:
```python
class ProgramChunker:
    def chunk_by_functions(self, program, max_size=10000) -> List[Tuple[str, List]]
    def targeted_load(self, program, target_path, context_size=5) -> List
```

**CLI Integration**:
```bash
# Edit specific function without loading entire file
amorph edit-function program.json function_id edits.json

# Validate specific path with context
amorph validate program.json --path "/$[100]" --context 5
```

**Success Metrics**:
- ✅ Variable rename with call-site updates
- ✅ Extract function refactoring
- ✅ Smart error recovery suggestions
- ✅ Large file chunking (<10KB chunks)

---

### FASE 6: Advanced Features (3+ weeks) - LOW PRIORITY

**Priority**: LOW
**Dependencies**: FASE 5
**Target**: Modules, standard library, ecosystem maturity

#### Sprint 6.1: Module System (Week 12-13)

**Features**:
- Import mechanism with stable names
- Namespace qualification: `module.function`
- Selective imports
- Circular dependency detection
- Content hashing for cache invalidation

**Example**:
```json
{
  "version": "0.2",
  "imports": [
    {"module": "math", "from": "./math.amr.json"},
    {"module": "utils", "from": "./utils.amr.json", "import": ["double"]}
  ],
  "program": [...]
}
```

#### Sprint 6.2: Standard Library (Week 14)

**Categories**:
- Collections: map, filter, reduce, zip, enumerate
- String: split, join, replace, trim, upper, lower
- Math: sqrt, abs, min, max, floor, ceil, round
- Date/Time: now, parse_date, format_date
- File I/O: read_file, write_file, exists, list_dir
- JSON: parse, stringify
- HTTP: fetch (basic GET/POST)

**Implementation**:
- Pure Amorph implementations where possible
- Native Python bindings for I/O
- Namespaced: `std.collections.map`

#### Sprint 6.3: Web Playground (Week 15)

**Features**:
- React + Monaco Editor
- Live editor with syntax highlighting
- Run button with output panel
- Examples gallery
- Export/import programs
- Share via URL (gzip + base64)

---

## Timeline Summary

| Month | Weeks | Focus | Deliverables |
|-------|-------|-------|--------------|
| **Month 1** | 1-4 | Critical Foundations | Tests (80%+ coverage), Enhanced validation |
| **Month 2** | 5-8 | Robustness & Performance | Rich errors, 30%+ faster, Complete docs |
| **Month 3** | 9-11 | Ecosystem & LLM | Tooling, Variable refactoring, Suggestions |
| **Month 4+** | 12+ | Advanced Features | Modules, Standard library, Community |

---

## Success Metrics by Milestone

### Milestone 1: Production-Ready Core (Week 1-5)

**Deliverables**:
- ✅ Test suite complete (80%+ coverage)
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Enhanced validation (types, scope, operators)
- ✅ Rich error reporting (context, call stack, colors)
- ✅ Complete API documentation

**Metrics**:
- Code coverage: 0% → 80%+
- Tests: 0 → 700+
- Validation errors detected: +40%
- Error debuggability: +200%

### Milestone 2: Performance & Tooling (Week 6-9)

**Deliverables**:
- ✅ 30%+ performance improvement
- ✅ Benchmark suite
- ✅ Language specification
- ✅ VSCode extension
- ✅ REPL
- ✅ Web playground (basic)

**Metrics**:
- Variable lookup: -35% time
- Operator eval: -20% time
- Developer onboarding: <30min
- VSCode installs: 100+ (target month 1)

### Milestone 3: LLM Excellence (Week 10-11)

**Deliverables**:
- ✅ Variable rename refactoring
- ✅ Extract function
- ✅ Smart edit suggestions
- ✅ Large file chunking
- ✅ Context-aware error recovery
- ✅ Targeted editing

**Metrics**:
- LLM problem resolution: 70% → 95%
- Edit success rate: 90% → 98%
- Context window usage: -40%
- Refactoring accuracy: 95%+

### Milestone 4: Ecosystem Complete (Week 12-14)

**Deliverables**:
- ✅ Module system (v0.2)
- ✅ Standard library (50+ functions)
- ✅ Web playground (full features)
- ✅ Debugger CLI
- ✅ Community forum/docs site

**Metrics**:
- Available functions: 30 → 80+
- Multi-file project support: ✅
- Community adoption: 500+ users (target)

---

## Risk Management

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Test coverage under 80% | Medium | High | Block PR if coverage drops, daily checks |
| Performance degrades | Low | Medium | Benchmark in CI/CD, regression tests |
| Breaking changes API | Medium | High | Semantic versioning, deprecation warnings |
| Low LLM adoption | Medium | Medium | Example-driven docs, tutorials, integrations |
| Scope creep | High | Medium | Strict sprint planning, feature freeze |

---

## Effort Estimation

**Team Size**: 1-2 developers

| Phase | Effort (person-days) | Complexity | Risk |
|-------|---------------------|------------|------|
| FASE 1: Testing | 15 days | Medium | Low |
| FASE 2: Validation | 10 days | Medium-High | Medium |
| FASE 3: Performance | 7 days | High | Medium |
| FASE 4: Documentation | 10 days | Low | Low |
| FASE 5: LLM Features | 7 days | High | Medium |
| FASE 6: Advanced | 15+ days | Very High | High |
| **TOTAL** | **64+ days** | - | - |

**Timeline**: ~13 weeks (3.2 months) for Milestones 1-3

---

## Immediate Next Steps

### Week 1 - Day 1 Action Items

1. **Setup Testing Infrastructure** (2-3 hours)
```bash
mkdir -p amorph/tests/fixtures/malformed
touch amorph/tests/{__init__.py,conftest.py,test_engine.py}
pip install pytest pytest-cov pytest-timeout pytest-watch
```

2. **Setup CI/CD** (1 hour)
```bash
mkdir -p .github/workflows
# Create test.yml (see FASE 1.3)
git add .github/workflows/test.yml
git commit -m "Add CI/CD pipeline"
```

3. **Create Project Board** (30 min)
- GitHub Projects: Backlog, Todo, In Progress, Review, Done
- Populate with FASE 1 tasks
- Assign priorities and estimates

---

## Conclusion

This roadmap provides:
1. ✅ Detailed 14+ week roadmap
2. ✅ Complete (95%+) resolution of LLM editing problems
3. ✅ Testing from 0% → 80%+ coverage
4. ✅ Performance optimization 30%+
5. ✅ Complete ecosystem (docs, tools, LSP)
6. ✅ Realistic timeline with verifiable milestones

After implementation, Amorph will be:
- Production-ready for LLM use cases
- Robust and well-tested
- Performant for large-scale programs
- Comprehensively documented
- Equipped with modern tooling

The main gap (testing) is eliminated in FASE 1, while subsequent phases build on solid foundations to create a truly excellent AI-first language.
