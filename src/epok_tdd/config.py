from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast


class ConfigError(ValueError):
    """Raised when Epok TDD configuration is invalid."""


@dataclass(frozen=True, slots=True)
class Commands:
    tests: tuple[str, ...] = ()
    lint: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    mutation: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ArchitectureContract:
    source: str
    forbid: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Config:
    root: Path = Path(".")
    paths: tuple[Path, ...] = (Path("src"),)
    specification: Path | None = None
    fail_on: str = "error"
    max_complexity: int = 10
    max_crap: float = 30.0
    max_parameters: int = 6
    max_type_depth: int = 3
    forbidden_module_names: tuple[str, ...] = ("utils", "helpers", "common", "misc")
    baseline: Path | None = None
    commands: Commands = field(default_factory=Commands)
    architecture_contracts: tuple[ArchitectureContract, ...] = ()


def _tuple_of_strings(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ConfigError(f"{field_name} must be an array of strings")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise ConfigError(f"{field_name} must be an array of strings")
    return tuple(item for item in items if isinstance(item, str))


def _table(parent: dict[str, object], key: str, *, field_name: str) -> dict[str, object]:
    value = parent.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{field_name} must be a TOML table")
    return cast(dict[str, object], value)


def _integer(value: object, *, field_name: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{field_name} must be an integer")
    return value


def _number(value: object, *, field_name: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{field_name} must be a number")
    return float(value)


def _load_commands(raw: dict[str, object]) -> Commands:
    commands = _table(raw, "commands", field_name="[tool.epok-tdd.commands]")
    return Commands(
        tests=_tuple_of_strings(commands.get("tests"), field_name="commands.tests"),
        lint=_tuple_of_strings(commands.get("lint"), field_name="commands.lint"),
        types=_tuple_of_strings(commands.get("types"), field_name="commands.types"),
        mutation=_tuple_of_strings(commands.get("mutation"), field_name="commands.mutation"),
    )


def _load_contracts(raw: dict[str, object]) -> tuple[ArchitectureContract, ...]:
    architecture = _table(raw, "architecture", field_name="[tool.epok-tdd.architecture]")
    contracts_value = architecture.get("contracts", [])
    if not isinstance(contracts_value, list):
        raise ConfigError("architecture.contracts must be an array of tables")

    parsed: list[ArchitectureContract] = []
    for raw_contract in cast(list[object], contracts_value):
        if not isinstance(raw_contract, dict):
            raise ConfigError("each architecture contract needs a string source")
        contract = cast(dict[str, object], raw_contract)
        source = contract.get("source")
        if not isinstance(source, str):
            raise ConfigError("each architecture contract needs a string source")
        parsed.append(
            ArchitectureContract(
                source=source,
                forbid=_tuple_of_strings(contract.get("forbid"), field_name="contract.forbid"),
            )
        )
    return tuple(parsed)


def _resolve_optional_path(root: Path, value: object) -> Path | None:
    return root / value if isinstance(value, str) else None


def load_config(pyproject: Path = Path("pyproject.toml")) -> Config:
    if not pyproject.exists():
        raise ConfigError(f"Configuration file not found: {pyproject}")

    root = pyproject.resolve().parent
    with pyproject.open("rb") as stream:
        document = cast(dict[str, object], tomllib.load(stream))
    tool = _table(document, "tool", field_name="[tool]")
    raw = _table(tool, "epok-tdd", field_name="[tool.epok-tdd]")

    fail_on = raw.get("fail_on", "error")
    if not isinstance(fail_on, str) or fail_on not in {"review", "warning", "error"}:
        raise ConfigError("fail_on must be one of: review, warning, error")

    raw_paths = _tuple_of_strings(raw.get("paths", ["src"]), field_name="paths")
    return Config(
        root=root,
        paths=tuple(root / item for item in raw_paths),
        specification=_resolve_optional_path(root, raw.get("specification")),
        fail_on=fail_on,
        max_complexity=_integer(
            raw.get("max_complexity"), field_name="max_complexity", default=10
        ),
        max_crap=_number(raw.get("max_crap"), field_name="max_crap", default=30.0),
        max_parameters=_integer(
            raw.get("max_parameters"), field_name="max_parameters", default=6
        ),
        max_type_depth=_integer(
            raw.get("max_type_depth"), field_name="max_type_depth", default=3
        ),
        forbidden_module_names=_tuple_of_strings(
            raw.get("forbidden_module_names", ["utils", "helpers", "common", "misc"]),
            field_name="forbidden_module_names",
        ),
        baseline=_resolve_optional_path(root, raw.get("baseline")),
        commands=_load_commands(raw),
        architecture_contracts=_load_contracts(raw),
    )
