from __future__ import annotations

from pathlib import Path

from epok_tdd.models import AnalysisReport, Finding, Severity


def test_report_failure_threshold_is_explicit() -> None:
    report = AnalysisReport(
        findings=[
            Finding(
                rule_id="EPK001",
                message="Review this boundary",
                path=Path("src/example.py"),
                line=3,
                severity=Severity.WARNING,
            )
        ]
    )

    assert report.passed(fail_on=Severity.ERROR)
    assert not report.passed(fail_on=Severity.WARNING)


def test_finding_identity_is_stable_for_baselines() -> None:
    finding = Finding(
        rule_id="EPK201",
        message="Complexity exceeds limit",
        path=Path("src/example.py"),
        line=4,
        severity=Severity.ERROR,
        symbol="calculate",
        observed=12,
        limit=10,
    )

    assert finding.identity == "EPK201:src/example.py:calculate"
    assert finding.to_dict()["observed"] == 12


def test_report_serialization_contains_metrics_and_identity() -> None:
    from epok_tdd.models import FunctionMetric

    metric = FunctionMetric(
        path=Path("src/example.py"),
        symbol="calculate",
        line=1,
        end_line=3,
        complexity=2,
        coverage=0.5,
        crap=2.5,
    )
    report = AnalysisReport(metrics=[metric])

    payload = report.to_dict()

    assert payload["passed"] is True
    assert payload["metrics"][0]["identity"] == "src/example.py:calculate"
    assert payload["metrics"][0]["path"] == "src/example.py"
