import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Self, cast

type Branch = tuple[int, int]


@dataclass(frozen=True, slots=True)
class CoverageFile:
    executed_lines: frozenset[int]
    missing_lines: frozenset[int]
    executed_branches: frozenset[Branch]
    missing_branches: frozenset[Branch]

    def ratio(self, start: int, end: int) -> float | None:
        executed_lines = {line for line in self.executed_lines if start <= line <= end}
        missing_lines = {line for line in self.missing_lines if start <= line <= end}
        executed_branches = {
            branch for branch in self.executed_branches if start <= branch[0] <= end
        }
        missing_branches = {
            branch for branch in self.missing_branches if start <= branch[0] <= end
        }
        executed = len(executed_lines) + len(executed_branches)
        total = executed + len(missing_lines) + len(missing_branches)
        return executed / total if total else None


def _integer_lines(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    return [item for item in cast(list[object], value) if isinstance(item, int)]


def _branches(value: object) -> list[Branch]:
    if not isinstance(value, list):
        return []
    branches: list[Branch] = []
    for raw_branch in cast(list[object], value):
        if not isinstance(raw_branch, list):
            continue
        branch = cast(list[object], raw_branch)
        if len(branch) != 2:
            continue
        start, end = branch
        if isinstance(start, int) and isinstance(end, int):
            branches.append((start, end))
    return branches


def _coverage_source(root: Path, name: str) -> Path:
    source = Path(name)
    return source.resolve() if source.is_absolute() else (root / source).resolve()


def _coverage_file(value: object) -> CoverageFile | None:
    if not isinstance(value, dict):
        return None
    data = cast(dict[str, object], value)
    return CoverageFile(
        executed_lines=frozenset(_integer_lines(data.get("executed_lines"))),
        missing_lines=frozenset(_integer_lines(data.get("missing_lines"))),
        executed_branches=frozenset(_branches(data.get("executed_branches"))),
        missing_branches=frozenset(_branches(data.get("missing_branches"))),
    )


class CoverageIndex:
    def __init__(
        self,
        files: dict[Path, CoverageFile],
        error: str | None = None,
        *,
        requested: bool = True,
    ) -> None:
        self._files = files
        self.error = error
        self.requested = requested

    @classmethod
    def load(cls, path: Path | None) -> Self:
        if path is None:
            return cls({}, requested=False)
        if not path.exists():
            return cls({}, f"Coverage report not found: {path}")
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, JSONDecodeError, TypeError) as error:
            return cls({}, f"Unable to read coverage report {path}: {error}")
        if not isinstance(raw_value, dict):
            return cls({}, f"Coverage report must be a JSON object: {path}")
        raw = cast(dict[str, object], raw_value)

        raw_files = raw.get("files")
        if not isinstance(raw_files, dict):
            return cls({}, f"Coverage report has no valid files table: {path}")

        root = path.resolve().parent
        files: dict[Path, CoverageFile] = {}
        for name, raw_data in cast(dict[object, object], raw_files).items():
            if not isinstance(name, str):
                continue
            coverage_file = _coverage_file(raw_data)
            if coverage_file is not None:
                files[_coverage_source(root, name)] = coverage_file
        if not files:
            return cls({}, f"Coverage report contains no measured Python files: {path}")
        return cls(files)

    def for_path(self, path: Path) -> CoverageFile | None:
        return self._files.get(path.resolve())
