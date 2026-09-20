from pathlib import Path

import pytest

from epok_tdd.config import Commands, ConfigError, load_config


def test_load_config_resolves_paths_and_commands_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.epok-tdd]
paths = ["src", "packages/domain"]
specification = "docs/spec.md"
fail_on = "warning"
max_complexity = 8
max_crap = 20.5
max_parameters = 5
max_type_depth = 2
forbidden_module_names = ["utils"]
baseline = ".quality.json"

[tool.epok-tdd.commands]
tests = ["pytest", "-q"]
lint = ["ruff", "check", "."]
types = ["pyright"]
mutation = ["mutmut", "run"]

[[tool.epok-tdd.architecture.contracts]]
source = "domain"
forbid = ["fastapi", "sqlalchemy"]
""".strip(),
        encoding="utf-8",
    )

    config = load_config(pyproject)

    assert config.root == tmp_path
    assert config.paths == (tmp_path / "src", tmp_path / "packages/domain")
    assert config.specification == tmp_path / "docs/spec.md"
    assert config.fail_on == "warning"
    assert config.max_complexity == 8
    assert config.max_crap == 20.5
    assert config.max_parameters == 5
    assert config.max_type_depth == 2
    assert config.forbidden_module_names == ("utils",)
    assert config.baseline == tmp_path / ".quality.json"
    assert config.commands.tests == ("pytest", "-q")
    assert config.commands.lint == ("ruff", "check", ".")
    assert config.commands.types == ("pyright",)
    assert config.commands.mutation == ("mutmut", "run")
    assert len(config.architecture_contracts) == 1
    assert config.architecture_contracts[0].source == "domain"
    assert config.architecture_contracts[0].forbid == ("fastapi", "sqlalchemy")


def test_load_config_rejects_unknown_failure_severity(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.epok-tdd]
fail_on = "sometimes"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="fail_on"):
        load_config(pyproject)


def test_load_config_uses_safe_defaults(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'example'\n", encoding="utf-8")

    config = load_config(pyproject)

    assert config.root == tmp_path
    assert config.paths == (tmp_path / "src",)
    assert config.specification is None
    assert config.fail_on == "error"
    assert config.max_complexity == 10
    assert config.max_crap == 30.0
    assert config.max_parameters == 6
    assert config.max_type_depth == 3
    assert config.forbidden_module_names == ("utils", "helpers", "common", "misc")
    assert config.baseline is None
    assert config.commands == Commands()
    assert config.architecture_contracts == ()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[tool.epok-tdd]\npaths = 'src'\n", "paths"),
        ("[tool.epok-tdd]\ncommands = 'pytest'\n", "commands"),
        ("[tool.epok-tdd]\narchitecture = 'domain'\n", "architecture"),
        (
            "[tool.epok-tdd.architecture]\ncontracts = 'invalid'\n",
            "contracts",
        ),
        (
            "[[tool.epok-tdd.architecture.contracts]]\nforbid = ['fastapi']\n",
            "source",
        ),
        (
            "[[tool.epok-tdd.architecture.contracts]]\nsource = 'domain'\nforbid = 'fastapi'\n",
            "contract.forbid",
        ),
    ],
)
def test_load_config_rejects_malformed_tables(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_config(pyproject)


def test_load_config_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "missing.toml")
