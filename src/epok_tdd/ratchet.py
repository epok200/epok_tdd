from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from epok_tdd.models import AnalysisReport, Finding


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


def _worsened(current: object, previous: object) -> bool:
    return (
        isinstance(current, (int, float))
        and not isinstance(current, bool)
        and isinstance(previous, (int, float))
        and not isinstance(previous, bool)
        and current > previous
    )


def compare_with_baseline(report: AnalysisReport, baseline: Baseline) -> list[Finding]:
    regressions: list[Finding] = []
    for finding in report.findings:
        if finding.identity not in baseline.findings:
            regressions.append(finding)
            continue
        if _worsened(finding.observed, baseline.findings[finding.identity]):
            regressions.append(finding)
    return regressions
