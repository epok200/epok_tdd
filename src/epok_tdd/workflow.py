from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from time import monotonic

from epok_tdd.config import Config
from epok_tdd.models import AnalysisReport, Severity


class GateMode(StrEnum):
    QUICK = "quick"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class PhaseResult:
    name: str
    status: str
    detail: str = ""
    duration_seconds: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status in {"passed", "skipped"}


@dataclass(slots=True)
class GateResult:
    phases: list[PhaseResult] = field(default_factory=list[PhaseResult])

    @property
    def passed(self) -> bool:
        return all(phase.passed for phase in self.phases)


def validate_specification(path: Path | None) -> PhaseResult:
    if path is None:
        return PhaseResult("specification", "failed", "No active specification configured")
    if not path.exists():
        return PhaseResult("specification", "failed", f"Specification not found: {path}")
    text = path.read_text(encoding="utf-8")
    if re.search(r"^Status:\s*Approved\b", text, flags=re.IGNORECASE | re.MULTILINE) is None:
        return PhaseResult(
            "specification",
            "failed",
            "Specification must have explicit human-approved status",
        )
    required = ("## Acceptance criteria", "## Out of scope")
    missing = [heading for heading in required if heading.lower() not in text.lower()]
    if missing:
        return PhaseResult(
            "specification",
            "failed",
            f"Specification is missing: {', '.join(missing)}",
        )
    return PhaseResult("specification", "passed", str(path))


def _run_command(name: str, command: tuple[str, ...]) -> PhaseResult:
    if not command:
        return PhaseResult(name, "skipped", "No command configured")
    started = monotonic()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as error:
        return PhaseResult(name, "failed", str(error), monotonic() - started)
    output = (completed.stdout + completed.stderr).strip()
    status = "passed" if completed.returncode == 0 else "failed"
    return PhaseResult(name, status, output, monotonic() - started)


def run_gate(
    config: Config,
    *,
    mode: GateMode = GateMode.QUICK,
    analyzer: Callable[[], AnalysisReport],
) -> GateResult:
    result = GateResult()
    result.phases.append(validate_specification(config.specification))
    result.phases.append(_run_command("tests", config.commands.tests))

    started = monotonic()
    analysis = analyzer()
    fail_on = Severity(config.fail_on)
    analysis_passed = analysis.passed(fail_on=fail_on)
    result.phases.append(
        PhaseResult(
            "cleaner-and-architect",
            "passed" if analysis_passed else "failed",
            f"{len(analysis.findings)} finding(s)",
            monotonic() - started,
        )
    )
    result.phases.append(_run_command("lint", config.commands.lint))
    result.phases.append(_run_command("types", config.commands.types))
    if mode is GateMode.FULL:
        result.phases.append(_run_command("mutation", config.commands.mutation))
    else:
        result.phases.append(
            PhaseResult("mutation", "skipped", "Quick mode; use --mode full for mutation testing")
        )
    return result
