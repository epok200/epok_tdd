import json
import sys
from pathlib import Path

import pytest

from epok_tdd.cli import main


def _write_project(
    tmp_path: Path,
    *,
    max_complexity: int = 10,
    fail_on: str = "error",
    include_baseline: bool = False,
) -> Path:
    source = tmp_path / "src"
    source.mkdir()
    (source / "example.py").write_text(
        "def identity(value: int) -> int:\n    return value\n",
        encoding="utf-8",
    )
    specification = tmp_path / "spec.md"
    specification.write_text(
        (
            "# Feature\n\nStatus: Approved\n\n"
            "## Acceptance criteria\nWorks\n\n## Out of scope\nNothing\n"
        ),
        encoding="utf-8",
    )
    coverage_writer = tmp_path / "write_coverage.py"
    coverage_writer.write_text(
        "from pathlib import Path\n"
        "Path('coverage.json').write_text("
        "'{\"files\": {\"src/example.py\": {\"executed_lines\": [1, 2], "
        "\"missing_lines\": [], \"executed_branches\": [], "
        "\"missing_branches\": []}}}')\n",
        encoding="utf-8",
    )
    pyproject = tmp_path / "pyproject.toml"
    baseline = 'baseline = ".baseline.json"' if include_baseline else ""
    pyproject.write_text(
        f"""
[tool.epok-tdd]
paths = ["src"]
specification = "spec.md"
max_complexity = {max_complexity}
fail_on = "{fail_on}"
{baseline}

[tool.epok-tdd.commands]
tests = ["{sys.executable}", "write_coverage.py"]
""".strip(),
        encoding="utf-8",
    )
    return pyproject


def test_cli_check_supports_text_and_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pyproject = _write_project(tmp_path)

    assert main(["--config", str(pyproject), "check"]) == 0
    assert "quality gate passed" in capsys.readouterr().out.lower()

    assert main(["--config", str(pyproject), "check", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["metrics"][0]["symbol"] == "identity"


def test_cli_resolves_explicit_paths_from_configured_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pyproject = _write_project(tmp_path)
    runner = tmp_path / "runner"
    runner.mkdir()
    monkeypatch.chdir(runner)

    assert main(["--config", str(pyproject), "check", "src", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["metrics"][0]["path"] == "src/example.py"
    assert payload["metrics"][0]["symbol"] == "identity"


def test_cli_creates_and_uses_baseline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = _write_project(
        tmp_path,
        max_complexity=0,
        fail_on="warning",
        include_baseline=True,
    )
    baseline = tmp_path / ".baseline.json"

    assert main(["--config", str(pyproject), "baseline", "create"]) == 0
    assert baseline.exists()
    capsys.readouterr()

    assert main(["--config", str(pyproject), "check"]) == 0
    assert "quality gate passed" in capsys.readouterr().out.lower()
    assert main(["--config", str(pyproject), "check", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is True
    assert payload["findings"]
    assert payload["effective_findings"] == []
    assert main(
        ["--config", str(pyproject), "check", "--format", "json", "--no-baseline"]
    ) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert main(["--config", str(pyproject), "check", "--no-baseline"]) == 1


def test_cli_gate_and_configuration_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pyproject = _write_project(tmp_path)

    assert main(["--config", str(pyproject), "gate", "--mode", "quick"]) == 0
    output = capsys.readouterr().out
    assert "SPECIFICATION" not in output
    assert "PASSED" in output
    assert "SKIPPED mutation" in output
    assert (tmp_path / "coverage.json").exists()

    with pytest.raises(SystemExit) as error:
        main(["--config", str(tmp_path / "missing.toml"), "check"])
    assert error.value.code == 2
