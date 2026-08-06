from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any, cast

from epok_tdd.models import AnalysisReport, Finding, FunctionMetric, Severity

_ALWAYS_ENFORCED_RULES = frozenset({"EPK001", "EPK002", "EPK301", "EPK401", "EPK402"})


class BaselineError(ValueError):
    """Raised when a quality baseline cannot be trusted."""


@dataclass(frozen=True, slots=True)
class Baseline:
    findings: dict[str, float | int | str | None]
    metrics: dict[str, dict[str, float | int | None]]

    @classmethod
    def from_report(cls, report: AnalysisReport) -> Baseline:
        return cls(
            findings={
                finding.identity: finding.observed
                for finding in report.findings
                if finding.rule_id not in _ALWAYS_ENFORCED_RULES
            },
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
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, JSONDecodeError) as error:
            raise BaselineError(f"Unable to read quality baseline {path}: {error}") from error
        if not isinstance(raw_value, dict):
            raise BaselineError(f"Quality baseline must be a JSON object: {path}")
        raw = cast(dict[str, object], raw_value)
        if raw.get("version") != 1:
            raise BaselineError(f"Unsupported quality baseline version: {path}")
        return cls(
            findings=_parse_findings(raw.get("findings"), path),
            metrics=_parse_metrics(raw.get("metrics"), path),
        )

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


def _baseline_scalar(value: object) -> float | int | str | None:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BaselineError("Baseline values must be numbers, strings, or null")
    return value


def _metric_scalar(value: object) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BaselineError("Baseline metrics must be numbers or null")
    return value


def _parse_findings(value: object, path: Path) -> dict[str, float | int | str | None]:
    if not isinstance(value, dict):
        raise BaselineError(f"Quality baseline has no valid findings table: {path}")
    findings: dict[str, float | int | str | None] = {}
    for identity, observed in cast(dict[object, object], value).items():
        if not isinstance(identity, str):
            raise BaselineError(f"Quality baseline finding identities must be strings: {path}")
        findings[identity] = _baseline_scalar(observed)
    return findings


def _parse_metrics(
    value: object,
    path: Path,
) -> dict[str, dict[str, float | int | None]]:
    if not isinstance(value, dict):
        raise BaselineError(f"Quality baseline has no valid metrics table: {path}")
    metrics: dict[str, dict[str, float | int | None]] = {}
    for identity, raw_metric in cast(dict[object, object], value).items():
        if not isinstance(identity, str) or not isinstance(raw_metric, dict):
            raise BaselineError(f"Quality baseline metrics are malformed: {path}")
        metric = cast(dict[str, object], raw_metric)
        metrics[identity] = {
            "complexity": _metric_scalar(metric.get("complexity")),
            "coverage": _metric_scalar(metric.get("coverage")),
            "crap": _metric_scalar(metric.get("crap")),
        }
    return metrics


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


def _complexity_regression(
    metric: FunctionMetric,
    previous: dict[str, float | int | None],
) -> str | None:
    old = _number(previous.get("complexity"))
    current = _number(metric.complexity)
    if old is None or current is None or current <= old:
        return None
    return f"complexity {old:g}→{current:g}"


def _coverage_regression(
    metric: FunctionMetric,
    previous: dict[str, float | int | None],
) -> str | None:
    old = _number(previous.get("coverage"))
    current = _number(metric.coverage)
    if old is None:
        return None
    if current is None:
        return "coverage became unavailable"
    if current < old:
        return f"coverage {old:.3f}→{current:.3f}"
    return None


def _crap_regression(
    metric: FunctionMetric,
    previous: dict[str, float | int | None],
) -> str | None:
    old = _number(previous.get("crap"))
    current = _number(metric.crap)
    if old is None:
        return None
    if current is None:
        return "CRAP became unavailable"
    if current > old:
        return f"CRAP {old:.3f}→{current:.3f}"
    return None


def _metric_regressions(
    metric: FunctionMetric,
    previous: dict[str, float | int | None],
) -> list[str]:
    candidates = (
        _complexity_regression(metric, previous),
        _coverage_regression(metric, previous),
        _crap_regression(metric, previous),
    )
    return [candidate for candidate in candidates if candidate is not None]


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


def _baseline_error_finding(path: Path, error: BaselineError) -> Finding:
    return Finding(
        rule_id="EPK402",
        message=str(error),
        path=path,
        line=1,
        severity=Severity.ERROR,
        suggestion="Recreate the baseline from reviewed, valid quality evidence.",
    )


def compare_with_baseline(report: AnalysisReport, baseline: Baseline) -> list[Finding]:
    regressions: list[Finding] = []
    for finding in report.findings:
        if finding.rule_id in _ALWAYS_ENFORCED_RULES:
            regressions.append(finding)
            continue
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


def apply_baseline(report: AnalysisReport, path: Path) -> list[Finding]:
    try:
        baseline = Baseline.load(path)
    except BaselineError as error:
        return sorted(
            [*report.findings, _baseline_error_finding(path, error)],
            key=lambda item: (item.path.as_posix(), item.line, item.rule_id),
        )
    return compare_with_baseline(report, baseline)
