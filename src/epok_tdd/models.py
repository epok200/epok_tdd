from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

type JsonObject = dict[str, Any]


class Severity(StrEnum):
    """Severity used by deterministic quality findings."""

    REVIEW = "review"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        return {
            Severity.REVIEW: 0,
            Severity.WARNING: 1,
            Severity.ERROR: 2,
        }[self]


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    message: str
    path: Path
    line: int
    severity: Severity
    symbol: str | None = None
    observed: float | int | str | None = None
    limit: float | int | str | None = None
    suggestion: str | None = None

    @property
    def identity(self) -> str:
        location = self.symbol or str(self.line)
        return f"{self.rule_id}:{self.path.as_posix()}:{location}"

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        data["path"] = self.path.as_posix()
        data["severity"] = self.severity.value
        data["identity"] = self.identity
        return data


@dataclass(frozen=True, slots=True)
class FunctionMetric:
    path: Path
    symbol: str
    line: int
    end_line: int
    complexity: int
    coverage: float | None
    crap: float | None

    @property
    def identity(self) -> str:
        return f"{self.path.as_posix()}:{self.symbol}"

    def to_dict(self) -> JsonObject:
        data = asdict(self)
        data["path"] = self.path.as_posix()
        data["identity"] = self.identity
        return data


@dataclass(slots=True)
class AnalysisReport:
    findings: list[Finding] = field(default_factory=list[Finding])
    metrics: list[FunctionMetric] = field(default_factory=list[FunctionMetric])

    def passed(self, fail_on: Severity = Severity.ERROR) -> bool:
        return not any(finding.severity.rank >= fail_on.rank for finding in self.findings)

    def to_dict(self) -> JsonObject:
        return {
            "passed": self.passed(),
            "findings": [finding.to_dict() for finding in self.findings],
            "metrics": [metric.to_dict() for metric in self.metrics],
        }
