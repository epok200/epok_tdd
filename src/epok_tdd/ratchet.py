from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from epok_tdd.models import AnalysisReport, Finding, FunctionMetric, Severity


@dataclass(frozen=True, slots=True)
class Baseline:
    findings: dict[str, float | int | str | None]
    metrics: dict[str, dict[str, float | int | None]]

    @classmethod
    def from_report(cls, report: AnalysisReport) -> Baseline:
        return cls(
            findings={finding.identity: finding.observed for finding in report.findings},
            metrics={
                metric.identity: {
                    "complexity": metric.complexity,
                    "coverage": metric.coverage,
                    "crap": metric.crap,
                }
                for metric in report.metrics
            },
        )

    @classmethod
    def load(cls, path: Path) -> Baseline:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return cls(findings=dict(raw.get("findings", {})), metrics=dict(raw.get("metrics", {})))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"version": 1, "findings": self.findings, "metrics": self.metrics},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _worsened(current: object, previous: object) -> bool:
    current_number = _number(current)
    previous_number = _number(previous)
    return (
        current_number is not None
        and previous_number is not None
        and current_number > previous_number
    )


def _metric_regressions(
    metric: FunctionMetric,
    previous: dict[str, float | int | None],
) -> list[str]:
    regressions: list[str] = []
    previous_complexity = _number(previous.get("complexity"))
    current_complexity = _number(metric.complexity)
    if (
        previous_complexity is not None
        and current_complexity is not None
        and current_complexity > previous_complexity
    ):
        regressions.append(
            f"complexity {previous_complexity:g}→{current_complexity:g}"
        )

    previous_coverage = _number(previous.get("coverage"))
    current_coverage = _number(metric.coverage)
    if previous_coverage is not None and current_coverage is None:
        regressions.append("coverage became unavailable")
    elif (
        previous_coverage is not None
        and current_coverage is not None
        and current_coverage < previous_coverage
    ):
        regressions.append(f"coverage {previous_coverage:.3f}→{current_coverage:.3f}")

    previous_crap = _number(previous.get("crap"))
    current_crap = _number(metric.crap)
    if previous_crap is not None and current_crap is None:
        regressions.append("CRAP became unavailable")
    elif (
        previous_crap is not None
        and current_crap is not None
        and current_crap > previous_crap
    ):
        regressions.append(f"CRAP {previous_crap:.3f}→{current_crap:.3f}")
    return regressions


def _metric_finding(metric: FunctionMetric, regressions: list[str]) -> Finding:
    return Finding(
        rule_id="EPK401",
        message=f"{metric.symbol} worsened from the committed quality baseline",
        path=metric.path,
        line=metric.line,
        severity=Severity.ERROR,
        symbol=metric.symbol,
        observed="; ".join(regressions),
        limit="no metric regression",
        suggestion="Restore the previous risk level or intentionally replace the baseline.",
    )


def compare_with_baseline(report: AnalysisReport, baseline: Baseline) -> list[Finding]:
    regressions: list[Finding] = []
    for finding in report.findings:
        if finding.identity not in baseline.findings:
            regressions.append(finding)
            continue
        if _worsened(finding.observed, baseline.findings[finding.identity]):
            regressions.append(finding)

    for metric in report.metrics:
        previous = baseline.metrics.get(metric.identity)
        if previous is None:
            continue
        metric_regressions = _metric_regressions(metric, previous)
        if metric_regressions:
            regressions.append(_metric_finding(metric, metric_regressions))
    return sorted(regressions, key=lambda item: (item.path.as_posix(), item.line, item.rule_id))
