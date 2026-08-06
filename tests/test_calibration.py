from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from epok_tdd.analysis import analyze_paths
from epok_tdd.config import Commands, Config
from epok_tdd.models import AnalysisReport, Finding, FunctionMetric, Severity
from epok_tdd.ratchet import Baseline, apply_baseline, compare_with_baseline
from epok_tdd.workflow import run_gate


def test_coverage_paths_are_resolved_from_report_and_include_branches(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source = project / "src" / "feature.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def choose(value: int) -> int:\n"
        "    if value:\n"
        "        return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    coverage = project / "coverage.json"
    coverage.write_text(
        json.dumps(
            {
                "files": {
                    "src/feature.py": {
                        "executed_lines": [1, 2, 3],
                        "missing_lines": [4],
                        "executed_branches": [[2, 3]],
                        "missing_branches": [[2, 4]],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    config = Config(paths=(project / "src",))

    report = analyze_paths(config.paths, config=config, coverage_path=coverage)

    assert report.metrics[0].coverage == pytest.approx(4 / 6)
    assert report.metrics[0].crap is not None
    assert not any(finding.rule_id == "EPK002" for finding in report.findings)


def test_explicit_missing_or_empty_coverage_is_an_error(tmp_path: Path) -> None:
    source = tmp_path / "feature.py"
    source.write_text("def feature():\n    return True\n", encoding="utf-8")
    config = Config(paths=(tmp_path,))

    missing = analyze_paths(config.paths, config=config, coverage_path=tmp_path / "missing.json")
    assert [finding.rule_id for finding in missing.findings] == ["EPK002"]
    assert missing.findings[0].severity is Severity.ERROR

    empty_path = tmp_path / "coverage.json"
    empty_path.write_text('{"files": {}}', encoding="utf-8")
    empty = analyze_paths(config.paths, config=config, coverage_path=empty_path)
    assert any(finding.rule_id == "EPK002" for finding in empty.findings)


def test_method_receiver_does_not_count_as_business_parameter(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "class Service:\n"
        "    def run(self, one, two, three):\n"
        "        return one + two + three\n"
        "\n"
        "    @classmethod\n"
        "    def build(cls, one, two, three):\n"
        "        return cls()\n",
        encoding="utf-8",
    )
    config = Config(paths=(tmp_path,), max_parameters=3)

    report = analyze_paths(config.paths, config=config)

    assert not any(finding.rule_id == "EPK101" for finding in report.findings)


def test_complexity_is_a_warning_while_crap_remains_blocking(tmp_path: Path) -> None:
    source = tmp_path / "feature.py"
    source.write_text(
        "def choose(one, two):\n"
        "    if one:\n"
        "        return 1\n"
        "    if two:\n"
        "        return 2\n"
        "    return 0\n",
        encoding="utf-8",
    )
    config = Config(paths=(tmp_path,), max_complexity=2)

    report = analyze_paths(config.paths, config=config)

    finding = next(item for item in report.findings if item.rule_id == "EPK201")
    assert finding.severity is Severity.WARNING


def test_ratchet_rejects_metric_regression_below_absolute_thresholds() -> None:
    baseline_metric = FunctionMetric(
        path=Path("src/a.py"),
        symbol="work",
        line=1,
        end_line=5,
        complexity=4,
        coverage=0.9,
        crap=4.04,
    )
    current_metric = FunctionMetric(
        path=Path("src/a.py"),
        symbol="work",
        line=1,
        end_line=6,
        complexity=5,
        coverage=0.8,
        crap=5.2,
    )
    baseline = Baseline.from_report(AnalysisReport(metrics=[baseline_metric]))

    regressions = compare_with_baseline(
        AnalysisReport(metrics=[current_metric]),
        baseline,
    )

    assert len(regressions) == 1
    assert regressions[0].rule_id == "EPK401"
    assert regressions[0].severity is Severity.ERROR
    assert "complexity" in str(regressions[0].observed)
    assert "coverage" in str(regressions[0].observed)
    assert "CRAP" in str(regressions[0].observed)


def test_gate_applies_baseline_instead_of_blocking_unchanged_debt(tmp_path: Path) -> None:
    specification = tmp_path / "spec.md"
    specification.write_text(
        "# Feature\n\nStatus: Approved\n\n## Acceptance criteria\nYes\n\n## Out of scope\nNo\n",
        encoding="utf-8",
    )
    finding = Finding(
        rule_id="EPK202",
        message="legacy risk",
        path=Path("src/a.py"),
        line=1,
        severity=Severity.ERROR,
        symbol="legacy",
        observed=40.0,
        limit=30.0,
    )
    baseline_path = tmp_path / "baseline.json"
    Baseline.from_report(AnalysisReport(findings=[finding])).save(baseline_path)
    passing = (sys.executable, "-c", "raise SystemExit(0)")
    config = Config(
        paths=(tmp_path,),
        specification=specification,
        baseline=baseline_path,
        commands=Commands(tests=passing, lint=passing, types=passing),
    )

    result = run_gate(config, analyzer=lambda: AnalysisReport(findings=[finding]))

    assert result.passed
    assert "0 effective" in result.phases[2].detail
    assert "1 total" in result.phases[2].detail


def test_baseline_never_suppresses_integrity_failures(tmp_path: Path) -> None:
    finding = Finding(
        rule_id="EPK002",
        message="coverage missing",
        path=Path("coverage.json"),
        line=1,
        severity=Severity.ERROR,
    )
    baseline_path = tmp_path / "baseline.json"
    Baseline(findings={finding.identity: None}, metrics={}).save(baseline_path)

    effective = apply_baseline(AnalysisReport(findings=[finding]), baseline_path)

    assert [item.rule_id for item in effective] == ["EPK002"]


def test_malformed_baseline_becomes_a_blocking_finding(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        '{"version": 9, "findings": {}, "metrics": {}}',
        encoding="utf-8",
    )

    effective = apply_baseline(AnalysisReport(), baseline_path)

    assert [item.rule_id for item in effective] == ["EPK402"]
    assert effective[0].severity is Severity.ERROR
