from __future__ import annotations

from pathlib import Path

from epok_tdd.models import AnalysisReport, Finding, FunctionMetric, Severity
from epok_tdd.ratchet import Baseline, compare_with_baseline


def test_ratchet_allows_unchanged_debt_and_rejects_regression() -> None:
    baseline = Baseline.from_report(
        AnalysisReport(
            findings=[
                Finding(
                    rule_id="EPK201",
                    message="old debt",
                    path=Path("src/a.py"),
                    line=1,
                    severity=Severity.ERROR,
                    symbol="legacy",
                    observed=12,
                    limit=10,
                )
            ],
            metrics=[
                FunctionMetric(
                    path=Path("src/a.py"),
                    symbol="legacy",
                    line=1,
                    end_line=5,
                    complexity=12,
                    coverage=1.0,
                    crap=12.0,
                )
            ],
        )
    )
    current = AnalysisReport(
        findings=[
            Finding(
                rule_id="EPK201",
                message="old debt",
                path=Path("src/a.py"),
                line=1,
                severity=Severity.ERROR,
                symbol="legacy",
                observed=12,
                limit=10,
            ),
            Finding(
                rule_id="EPK202",
                message="new risk",
                path=Path("src/b.py"),
                line=10,
                severity=Severity.ERROR,
                symbol="new_feature",
                observed=40.0,
                limit=30.0,
            ),
        ],
        metrics=[
            FunctionMetric(
                path=Path("src/a.py"),
                symbol="legacy",
                line=1,
                end_line=5,
                complexity=12,
                coverage=1.0,
                crap=12.0,
            ),
            FunctionMetric(
                path=Path("src/b.py"),
                symbol="new_feature",
                line=10,
                end_line=30,
                complexity=8,
                coverage=0.0,
                crap=72.0,
            ),
        ],
    )

    regressions = compare_with_baseline(current, baseline)

    assert [finding.identity for finding in regressions] == [
        "EPK202:src/b.py:new_feature"
    ]


def test_baseline_round_trip_and_numeric_regression(tmp_path: Path) -> None:
    finding = Finding(
        rule_id="EPK201",
        message="complexity",
        path=Path("src/a.py"),
        line=1,
        severity=Severity.ERROR,
        symbol="work",
        observed=11,
        limit=10,
    )
    baseline = Baseline.from_report(AnalysisReport(findings=[finding]))
    path = tmp_path / "baseline.json"

    baseline.save(path)
    loaded = Baseline.load(path)
    worse = Finding(
        rule_id="EPK201",
        message="complexity",
        path=Path("src/a.py"),
        line=1,
        severity=Severity.ERROR,
        symbol="work",
        observed=12,
        limit=10,
    )

    assert loaded.findings == baseline.findings
    assert compare_with_baseline(AnalysisReport(findings=[worse]), loaded) == [worse]
