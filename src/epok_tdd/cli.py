from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from epok_tdd.analysis import analyze_paths
from epok_tdd.config import Config, ConfigError, load_config
from epok_tdd.models import AnalysisReport, Finding, Severity
from epok_tdd.ratchet import Baseline, compare_with_baseline
from epok_tdd.workflow import GateMode, run_gate


def _print_findings(findings: list[Finding]) -> None:
    if not findings:
        print("Epok TDD: quality gate passed.")
        return
    for finding in findings:
        symbol = f" [{finding.symbol}]" if finding.symbol else ""
        evidence = ""
        if finding.observed is not None:
            evidence = f" observed={finding.observed}"
        if finding.limit is not None:
            evidence += f" limit={finding.limit}"
        print(
            f"{finding.severity.value.upper():7} {finding.rule_id} "
            f"{finding.path}:{finding.line}{symbol} {finding.message}{evidence}"
        )
        if finding.suggestion:
            print(f"         ↳ {finding.suggestion}")


def _effective_findings(report: AnalysisReport, config: Config, *, use_baseline: bool) -> list[Finding]:
    if use_baseline and config.baseline and config.baseline.exists():
        return compare_with_baseline(report, Baseline.load(config.baseline))
    return report.findings


def _run_check(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    paths = tuple(Path(path) for path in args.paths) if args.paths else config.paths
    report = analyze_paths(paths, config=config, coverage_path=args.coverage)
    findings = _effective_findings(report, config, use_baseline=not args.no_baseline)
    if args.format == "json":
        payload = report.to_dict()
        payload["effective_findings"] = [finding.to_dict() for finding in findings]
        print(json.dumps(payload, indent=2))
    else:
        _print_findings(findings)
    threshold = Severity(config.fail_on)
    return int(any(finding.severity.rank >= threshold.rank for finding in findings))


def _run_baseline(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    paths = tuple(Path(path) for path in args.paths) if args.paths else config.paths
    report = analyze_paths(paths, config=config, coverage_path=args.coverage)
    destination = args.output or config.baseline
    if destination is None:
        raise ConfigError("No baseline path configured; use --output")
    Baseline.from_report(report).save(destination)
    print(f"Epok TDD baseline written to {destination}")
    return 0


def _run_gate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    result = run_gate(
        config,
        mode=GateMode(args.mode),
        analyzer=lambda: analyze_paths(
            config.paths,
            config=config,
            coverage_path=args.coverage,
        ),
    )
    for phase in result.phases:
        print(f"{phase.status.upper():7} {phase.name}: {phase.detail}")
    return int(not result.passed)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="epok-tdd",
        description="Executable quality gates for Python coding agents.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Analyze code and apply the quality ratchet.")
    check.add_argument("paths", nargs="*", help="Files or directories; defaults to configuration.")
    check.add_argument("--coverage", type=Path, help="Coverage.py JSON report.")
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument("--no-baseline", action="store_true")
    check.set_defaults(handler=_run_check)

    baseline = subparsers.add_parser("baseline", help="Create a quality baseline.")
    baseline.add_argument("action", choices=("create",))
    baseline.add_argument("paths", nargs="*")
    baseline.add_argument("--coverage", type=Path)
    baseline.add_argument("--output", type=Path)
    baseline.set_defaults(handler=_run_baseline)

    gate = subparsers.add_parser("gate", help="Run the Martin-inspired quality workflow.")
    gate.add_argument("--mode", choices=("quick", "full"), default="quick")
    gate.add_argument("--coverage", type=Path, default=Path("coverage.json"))
    gate.set_defaults(handler=_run_gate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except ConfigError as error:
        parser.error(str(error))
        return 2
