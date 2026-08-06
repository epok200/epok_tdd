from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from epok_tdd.analysis import analyze_paths, annotation_depth, crap_score, cyclomatic_complexity
from epok_tdd.config import Config


def test_crap_score_rewards_coverage_without_hiding_complexity() -> None:
    assert crap_score(complexity=10, coverage=0.0) == 110.0
    assert crap_score(complexity=10, coverage=0.8) == pytest.approx(10.8)
    assert crap_score(complexity=31, coverage=1.0) == 31.0


def test_cyclomatic_complexity_counts_independent_decisions() -> None:
    function = ast.parse(
        """
def classify(values):
    if not values:
        return "empty"
    for value in values:
        if value > 10 and value % 2 == 0:
            return "large-even"
    return "other"
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert cyclomatic_complexity(function) == 5


def test_annotation_depth_exposes_anonymous_nested_contracts() -> None:
    annotation = ast.parse(
        "def load() -> dict[str, list[tuple[int, str]]]: ..."
    ).body[0]

    assert isinstance(annotation, ast.FunctionDef)
    assert annotation_depth(annotation.returns) == 3


def test_analysis_reports_only_evidence_backed_policy_violations(tmp_path: Path) -> None:
    package = tmp_path / "sample"
    package.mkdir()
    source = package / "utils.py"
    source.write_text(
        """
def route(
    first: int,
    second: int,
    third: int,
    fourth: int,
) -> dict[str, list[tuple[int, str]]]:
    if first:
        return {"result": [(first, "first")]}
    if second:
        return {"result": [(second, "second")]}
    return {"result": []}
""".lstrip(),
        encoding="utf-8",
    )
    config = Config(
        paths=(package,),
        max_complexity=2,
        max_parameters=3,
        max_type_depth=2,
        forbidden_module_names=("utils",),
    )

    report = analyze_paths(config.paths, config=config)

    rules = {finding.rule_id for finding in report.findings}
    assert rules == {"EPK101", "EPK102", "EPK103", "EPK104", "EPK201"}
    assert all(finding.path == source for finding in report.findings)
    assert all(finding.line > 0 for finding in report.findings)


def test_analysis_calculates_function_level_crap_from_coverage_json(tmp_path: Path) -> None:
    source = tmp_path / "calculator.py"
    source.write_text(
        """
def choose(value: int) -> int:
    if value > 10:
        return 10
    if value > 0:
        return 1
    return 0
""".lstrip(),
        encoding="utf-8",
    )
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    str(source): {
                        "executed_lines": [1, 2, 3],
                        "missing_lines": [4, 5, 6],
                        "excluded_lines": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    config = Config(paths=(tmp_path,), max_crap=4.0)

    report = analyze_paths(config.paths, config=config, coverage_path=coverage_path)

    metric = report.metrics[0]
    assert metric.symbol == "choose"
    assert metric.complexity == 3
    assert metric.coverage == pytest.approx(0.5)
    assert metric.crap == pytest.approx(4.125)
    assert [finding.rule_id for finding in report.findings] == ["EPK202"]


def test_analysis_reports_forbidden_architecture_imports(tmp_path: Path) -> None:
    domain = tmp_path / "domain"
    domain.mkdir()
    source = domain / "service.py"
    source.write_text(
        "import fastapi\nfrom sqlalchemy.orm import Session\n",
        encoding="utf-8",
    )
    from epok_tdd.config import ArchitectureContract

    config = Config(
        paths=(tmp_path,),
        architecture_contracts=(
            ArchitectureContract(source="domain", forbid=("fastapi", "sqlalchemy")),
        ),
    )

    report = analyze_paths(config.paths, config=config)

    violations = [finding for finding in report.findings if finding.rule_id == "EPK301"]
    assert [finding.line for finding in violations] == [1, 2]
    assert all("forbidden dependency" in finding.message for finding in violations)


def test_analysis_reports_syntax_errors_instead_of_crashing(tmp_path: Path) -> None:
    source = tmp_path / "broken.py"
    source.write_text("def broken(:\n", encoding="utf-8")
    config = Config(paths=(tmp_path,))

    report = analyze_paths(config.paths, config=config)

    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "EPK001"
    assert report.findings[0].line == 1


def test_analysis_keeps_qualified_symbols_and_ignores_private_mapping_contracts(
    tmp_path: Path,
) -> None:
    source = tmp_path / "model.py"
    source.write_text(
        """
class Parser:
    async def parse(self, value: int) -> int:
        return value

    def _serialize(self) -> dict[str, int]:
        return {"value": 1}
""".lstrip(),
        encoding="utf-8",
    )
    config = Config(paths=(tmp_path,))

    report = analyze_paths(config.paths, config=config)

    assert [metric.symbol for metric in report.metrics] == ["Parser.parse", "Parser._serialize"]
    assert not any(finding.rule_id == "EPK102" for finding in report.findings)


def test_complexity_supports_python_control_flow_constructs() -> None:
    function = ast.parse(
        """
def evaluate(items, flag):
    assert items
    while flag:
        try:
            values = [item for item in items if item > 0]
        except ValueError:
            return 0
        match values:
            case [first, *_]:
                return first if flag else 0
            case _:
                return 0
    return 0
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert cyclomatic_complexity(function) == 8


def test_annotation_depth_handles_unions_and_missing_annotations() -> None:
    function = ast.parse("def parse(value: list[int] | None): ...").body[0]

    assert isinstance(function, ast.FunctionDef)
    assert annotation_depth(function.args.args[0].annotation) == 1
    assert annotation_depth(None) == 0


def test_coverage_without_executable_lines_remains_unknown(tmp_path: Path) -> None:
    source = tmp_path / "empty.py"
    source.write_text("def marker():\n    pass\n", encoding="utf-8")
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps({"files": {str(source): {"executed_lines": [], "missing_lines": []}}}),
        encoding="utf-8",
    )
    config = Config(paths=(source,))

    report = analyze_paths(config.paths, config=config, coverage_path=coverage_path)

    assert report.metrics[0].coverage is None
    assert report.metrics[0].crap is None


def test_analysis_uses_repository_relative_paths_for_portable_baselines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("def feature():\n    return True\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config = Config(paths=(tmp_path / "src",))

    report = analyze_paths(config.paths, config=config)

    assert report.metrics[0].path == Path("src/feature.py")
