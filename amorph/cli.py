from __future__ import annotations

import argparse
import json
import sys

from .engine import run_file
from .uid import main_add_uid
from .edits import main_edit
from .format import fmt_dump, minify_keys, unminify_keys
from .uid import read_json, write_json
from .rewrite import main_rewrite
from .migrate import main_migrate_calls
from .acir import pack as acir_pack, unpack as acir_unpack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="amorph", description="Amorph interpreter (MVP)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a program file (.json)")
    p_run.add_argument("path", help="Path to program JSON file")
    p_run.add_argument("--trace", action="store_true", help="Enable execution trace (text)")
    p_run.add_argument("--trace-json", action="store_true", help="Enable execution trace as JSON events (stderr)")
    p_run.add_argument("--quiet", action="store_true", help="Silence program prints (useful for tests)")
    p_run.add_argument("--deny-input", action="store_true", help="Deny input effect (capability guard)")
    p_run.add_argument("--deny-print", action="store_true", help="Deny print effect (capability guard)")

    p_val = sub.add_parser("validate", help="Validate a program (schema/semantics)")
    p_val.add_argument("path")
    p_val.add_argument("--json", action="store_true", help="Emit JSON report with errors")
    p_val.add_argument("--check-types", action="store_true", help="Enable type checking (experimental)")
    p_val.add_argument("--check-scopes", action="store_true", help="Enable scope analysis")

    p_uid = sub.add_parser("add-uid", help="Add missing UID to statements/defs")
    p_uid.add_argument("path")
    p_uid.add_argument("-i", "--in-place", action="store_true")
    p_uid.add_argument("--deep", action="store_true", help="Add IDs recursively in function bodies/blocks")

    p_edit = sub.add_parser("edit", help="Apply declarative edits to a program")
    p_edit.add_argument("program")
    p_edit.add_argument("edits")
    p_edit.add_argument("--dry-run", action="store_true")
    p_edit.add_argument("--json-errors", action="store_true")

    p_fmt = sub.add_parser("fmt", help="Format program canonically")
    p_fmt.add_argument("path")
    p_fmt.add_argument("-i", "--in-place", action="store_true")

    p_min = sub.add_parser("minify", help="Minify keys for compact form")
    p_min.add_argument("input")
    p_min.add_argument("-o", "--output", required=True)

    p_unmin = sub.add_parser("unminify", help="Restore canonical keys from minified")
    p_unmin.add_argument("input")
    p_unmin.add_argument("-o", "--output", required=True)

    p_bench = sub.add_parser("bench", help="Benchmark/metrics for programs")
    p_bench.add_argument("paths", nargs="*", help="Files or directories (default: examples)")
    p_bench.add_argument("--json", action="store_true", help="Output JSON only")

    p_suggest = sub.add_parser("suggest", help="Suggest improvements and refactorings")
    p_suggest.add_argument("path")
    p_suggest.add_argument("--json", action="store_true", help="Output suggestions as JSON")
    p_suggest.add_argument("--apply", action="store_true", help="Interactively apply suggestions")

    p_rew = sub.add_parser("rewrite", help="Apply pattern-based rewrites to program")
    p_rew.add_argument("program")
    p_rew.add_argument("rules")
    p_rew.add_argument("--dry-run", action="store_true")
    p_rew.add_argument("--limit", type=int, default=None)

    p_mig = sub.add_parser("migrate-calls", help="Migrate function calls between name and id where possible")
    p_mig.add_argument("program")
    p_mig.add_argument("--dry-run", action="store_true")
    p_mig.add_argument("--to", choices=["id", "name"], default="id")

    p_pack = sub.add_parser("pack", help="Pack program to ACIR (CBOR if available)")
    p_pack.add_argument("input")
    p_pack.add_argument("-o", "--output", required=True)
    p_pack.add_argument("--format", choices=["cbor", "json"], default=None)

    p_unpack = sub.add_parser("unpack", help="Unpack ACIR to canonical JSON program")
    p_unpack.add_argument("input")
    p_unpack.add_argument("-o", "--output", required=True)
    p_unpack.add_argument("--format", choices=["cbor", "json"], default=None)

    args = parser.parse_args(argv)
    if args.cmd == "run":
        try:
            res = run_file(args.path, trace=args.trace, trace_json=args.trace_json, quiet=args.quiet, allow_print=not args.deny_print, allow_input=not args.deny_input)
            if res is not None:
                # Print the program result only if non-None
                print(res)
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    if args.cmd == "validate":
        from .validate import validate_program
        data = read_json(args.path)
        if args.json:
            from .validate import validate_program_report
            issues = validate_program_report(
                data,
                prefer_id=True,
                check_types=getattr(args, 'check_types', False),
                check_scopes=getattr(args, 'check_scopes', False)
            )
            ok = len([i for i in issues if i.severity == "error"]) == 0
            print(json.dumps({"ok": ok, "issues": [issue.__dict__ for issue in issues]}, ensure_ascii=False, indent=2))
            return 0 if ok else 1
        else:
            try:
                validate_program(data)
                print("OK")
                return 0
            except Exception as e:
                print(f"Invalid: {e}", file=sys.stderr)
                return 1
    if args.cmd == "add-uid":
        flags: list[str] = []
        if args.in_place:
            flags.append("-i")
        if args.deep:
            flags.append("--deep")
        return main_add_uid([args.path] + flags)
    if args.cmd == "edit":
        flags: list[str] = []
        if args.dry_run:
            flags.append("--dry-run")
        if args.json_errors:
            flags.append("--json-errors")
        return main_edit([args.program, args.edits] + flags)
    if args.cmd == "fmt":
        data = read_json(args.path)
        if args.in_place:
            write_json(args.path, data)
            return 0
        print(fmt_dump(data))
        return 0
    if args.cmd == "minify":
        data = read_json(args.input)
        out = minify_keys(data)
        write_json(args.output, out, indent=None or 0, sort_keys=True)
        return 0
    if args.cmd == "unminify":
        data = read_json(args.input)
        out = unminify_keys(data)
        write_json(args.output, out)
        return 0
    if args.cmd == "suggest":
        from .suggestions import SuggestionEngine
        data = read_json(args.path)
        engine = SuggestionEngine()
        suggestions = engine.suggest_improvements(data)

        if args.json:
            output = {
                "total": len(suggestions),
                "suggestions": [s.to_dict() for s in suggestions]
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            if not suggestions:
                print("No suggestions found. Program looks good!")
                return 0

            print(f"Found {len(suggestions)} suggestions:\n")
            for i, sug in enumerate(suggestions, 1):
                print(f"{i}. [{sug.priority.upper()}] {sug.operation}")
                print(f"   Reason: {sug.reason}")
                print(f"   Impact: {sug.estimated_impact}")
                print()

        return 0
    if args.cmd == "bench":
        from .bench import bench
        report = bench(args.paths)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            agg = report["aggregate"]
            print(f"files={agg['files']} avg_ratio={agg['avg_ratio']} avg_validate_ms={agg['avg_validate_ms']} avg_run_ms={agg.get('avg_run_ms')}")
            for r in report["results"]:
                print(f"- {r['path']}: canon={r['size_bytes_canonical']}B min={r['size_bytes_minified']}B ratio={r['ratio_min_over_canon']} validate_ms={r['validate_ms']} run_ms={r.get('run_ms')} input={r['has_input']}")
        return 0
    if args.cmd == "rewrite":
        flags: list[str] = []
        if args.dry_run:
            flags.append("--dry-run")
        if args.limit is not None:
            flags += ["--limit", str(args.limit)]
        return main_rewrite([args.program, args.rules] + flags)
    if args.cmd == "migrate-calls":
        flags: list[str] = []
        if args.dry_run:
            flags.append("--dry-run")
        if args.to:
            flags += ["--to", args.to]
        return main_migrate_calls([args.program] + flags)
    if args.cmd == "pack":
        data = read_json(args.input)
        prefer_cbor = args.format != "json"
        buf, fmt = acir_pack(data, prefer_cbor=prefer_cbor)
        mode = "wb"
        with open(args.output, mode) as f:
            f.write(buf)
        print(f"wrote {args.output} ({fmt}, {len(buf)} bytes)")
        return 0
    if args.cmd == "unpack":
        fmt = args.format
        with open(args.input, "rb") as f:
            buf = f.read()
        program = acir_unpack(buf, fmt=fmt)
        write_json(args.output, program)
        print(f"wrote {args.output}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
