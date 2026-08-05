from __future__ import annotations

import sys
from pathlib import Path

from epok_tdd.config import Commands, Config
from epok_tdd.models import AnalysisReport
from epok_tdd.workflow import GateMode, run_gate, validate_specification


def test_specification_requires_explicit_human_approval(tmp_path: Path) -> None:
    specification = tmp_path / "spec.md"
    specification.write_text(
        """
# Feature

Status: Draft

## Acceptance criteria

Something works.

## Out of scope

Nothing else.
""".strip(),
        encoding="utf-8",
    )

    result = validate_specification(specification)

    assert not result.passed
    assert "approved" in result.detail.lower()


def test_quick_gate_runs_tests_analysis_and_qa_but_skips_mutation(tmp_path: Path) -> None:
    specification = tmp_path / "spec.md"
    specification.write_text(
        """
# Feature

Status: Approved

## Acceptance criteria

Something works.

## Out of scope

Nothing else.
""".strip(),
        encoding="utf-8",
    )
    passing = (sys.executable, "-c", "raise SystemExit(0)")
    forbidden_mutation = (sys.executable, "-c", "raise SystemExit(99)")
    config = Config(
        paths=(tmp_path,),
        specification=specification,
        commands=Commands(
            tests=passing,
            lint=passing,
            types=passing,
            mutation=forbidden_mutation,
        ),
    )

    result = run_gate(
        config,
        mode=GateMode.QUICK,
        analyzer=lambda: AnalysisReport(),
    )

    assert result.passed
    assert [phase.name for phase in result.phases] == [
        "specification",
        "tests",
        "cleaner-and-architect",
        "lint",
        "types",
        "mutation",
    ]
    assert result.phases[-1].status == "skipped"


def test_specification_reports_missing_file_and_sections(tmp_path: Path) -> None:
    missing = validate_specification(tmp_path / "missing.md")
    assert not missing.passed
    assert "not found" in missing.detail.lower()

    incomplete = tmp_path / "incomplete.md"
    incomplete.write_text("# Feature\n\nStatus: Approved\n", encoding="utf-8")
    result = validate_specification(incomplete)
    assert not result.passed
    assert "missing" in result.detail.lower()


def test_full_gate_runs_mutation_and_reports_command_failures(tmp_path: Path) -> None:
    specification = tmp_path / "spec.md"
    specification.write_text(
        "# Feature\n\nStatus: Approved\n\n## Acceptance criteria\nYes\n\n## Out of scope\nNo\n",
        encoding="utf-8",
    )
    passing = (sys.executable, "-c", "print('ok')")
    failing = (sys.executable, "-c", "print('mutant survived'); raise SystemExit(1)")
    config = Config(
        paths=(tmp_path,),
        specification=specification,
        commands=Commands(tests=passing, mutation=failing),
    )

    result = run_gate(config, mode=GateMode.FULL, analyzer=AnalysisReport)

    assert not result.passed
    assert result.phases[-1].name == "mutation"
    assert result.phases[-1].status == "failed"
    assert "mutant survived" in result.phases[-1].detail
    assert result.phases[3].status == "skipped"


def test_gate_reports_missing_executable(tmp_path: Path) -> None:
    specification = tmp_path / "spec.md"
    specification.write_text(
        "# Feature\n\nStatus: Approved\n\n## Acceptance criteria\nYes\n\n## Out of scope\nNo\n",
        encoding="utf-8",
    )
    config = Config(
        paths=(tmp_path,),
        specification=specification,
        commands=Commands(tests=("definitely-not-a-real-command",)),
    )

    result = run_gate(config, analyzer=AnalysisReport)

    assert result.phases[1].status == "failed"
    assert "No such file" in result.phases[1].detail
