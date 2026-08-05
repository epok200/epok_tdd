from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


def _tuple_of_strings(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{field_name} must be an array of strings")
    return tuple(value)


def _table(parent: dict[str, Any], key: str, *, field_name: str) -> dict[str, Any]:
    value = parent.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{field_name} must be a TOML table")
    return value


def _load_commands(raw: dict[str, Any]) -> Commands:
    commands = _table(raw, "commands", field_name="[tool.epok-tdd.commands]")
    return Commands(
        tests=_tuple_of_strings(commands.get("tests"), field_name="commands.tests"),
        lint=_tuple_of_strings(commands.get("lint"), field_name="commands.lint"),
        types=_tuple_of_strings(commands.get("types"), field_name="commands.types"),
        mutation=_tuple_of_strings(commands.get("mutation"), field_name="commands.mutation"),
    )


def _load_contracts(raw: dict[str, Any]) -> tuple[ArchitectureContract, ...]:
    architecture = _table(raw, "architecture", field_name="[tool.epok-tdd.architecture]")
    contracts = architecture.get("contracts", [])
    if not isinstance(contracts, list):
        raise ConfigError("architecture.contracts must be an array of tables")

    parsed: list[ArchitectureContract] = []
    for contract in contracts:
        if not isinstance(contract, dict) or not isinstance(contract.get("source"), str):
            raise ConfigError("each architecture contract needs a string source")
        parsed.append(
            ArchitectureContract(
                source=contract["source"],
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
        document = tomllib.load(stream)
    tool = _table(document, "tool", field_name="[tool]")
    raw = _table(tool, "epok-tdd", field_name="[tool.epok-tdd]")

    fail_on = raw.get("fail_on", "error")
    if fail_on not in {"review", "warning", "error"}:
        raise ConfigError("fail_on must be one of: review, warning, error")

    raw_paths = _tuple_of_strings(raw.get("paths", ["src"]), field_name="paths")
    return Config(
        paths=tuple(root / item for item in raw_paths),
        specification=_resolve_optional_path(root, raw.get("specification")),
        fail_on=fail_on,
        max_complexity=int(raw.get("max_complexity", 10)),
        max_crap=float(raw.get("max_crap", 30.0)),
        max_parameters=int(raw.get("max_parameters", 6)),
        max_type_depth=int(raw.get("max_type_depth", 3)),
        forbidden_module_names=_tuple_of_strings(
            raw.get("forbidden_module_names", ["utils", "helpers", "common", "misc"]),
            field_name="forbidden_module_names",
        ),
        baseline=_resolve_optional_path(root, raw.get("baseline")),
        commands=_load_commands(raw),
        architecture_contracts=_load_contracts(raw),
    )
