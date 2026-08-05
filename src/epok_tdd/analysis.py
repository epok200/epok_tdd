from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from epok_tdd.config import ArchitectureContract, Config
from epok_tdd.models import AnalysisReport, Finding, FunctionMetric, Severity

_MAPPING_NAMES = {"dict", "Dict", "Mapping", "MutableMapping"}


def crap_score(complexity: int, coverage: float) -> float:
    """Calculate Change Risk Anti-Patterns for one function."""

    bounded_coverage = min(1.0, max(0.0, coverage))
    return complexity**2 * (1.0 - bounded_coverage) ** 3 + complexity


class _ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.score = 1

    def visit_If(self, node: ast.If) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.score += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.score += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        non_default_cases = sum(
            not (isinstance(case.pattern, ast.MatchAs) and case.pattern.name is None)
            for case in node.cases
        )
        self.score += non_default_cases
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    visitor = _ComplexityVisitor()
    for statement in node.body:
        visitor.visit(statement)
    return visitor.score


def annotation_depth(node: ast.expr | None) -> int:
    if node is None:
        return 0
    if isinstance(node, ast.Subscript):
        return 1 + annotation_depth(node.slice)
    if isinstance(node, (ast.Tuple, ast.List)):
        return max((annotation_depth(item) for item in node.elts), default=0)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return max(annotation_depth(node.left), annotation_depth(node.right))
    return 0


def _annotation_root(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Subscript):
        return _annotation_root(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


@dataclass(frozen=True, slots=True)
class _Function:
    node: ast.FunctionDef | ast.AsyncFunctionDef
    symbol: str

    @property
    def line(self) -> int:
        return self.node.lineno

    @property
    def end_line(self) -> int:
        return self.node.end_lineno or self.node.lineno


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[_Function] = []
        self._scope: list[str] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        symbol = ".".join((*self._scope, node.name))
        self.functions.append(_Function(node=node, symbol=symbol))
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()


@dataclass(frozen=True, slots=True)
class _CoverageFile:
    executed: frozenset[int]
    missing: frozenset[int]

    def ratio(self, start: int, end: int) -> float | None:
        relevant_executed = {line for line in self.executed if start <= line <= end}
        relevant_missing = {line for line in self.missing if start <= line <= end}
        total = len(relevant_executed) + len(relevant_missing)
        if total == 0:
            return None
        return len(relevant_executed) / total


class _CoverageIndex:
    def __init__(self, files: dict[Path, _CoverageFile]) -> None:
        self._files = files

    @classmethod
    def load(cls, path: Path | None) -> _CoverageIndex:
        if path is None or not path.exists():
            return cls({})
        raw = json.loads(path.read_text(encoding="utf-8"))
        files: dict[Path, _CoverageFile] = {}
        for name, data in raw.get("files", {}).items():
            if not isinstance(data, dict):
                continue
            files[Path(name).resolve()] = _CoverageFile(
                executed=frozenset(int(line) for line in data.get("executed_lines", [])),
                missing=frozenset(int(line) for line in data.get("missing_lines", [])),
            )
        return cls(files)

    def for_path(self, path: Path) -> _CoverageFile | None:
        return self._files.get(path.resolve())


def _display_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        return path


def _iter_python_files(paths: Iterable[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.add(path)
        elif path.is_dir():
            files.update(
                candidate
                for candidate in path.rglob("*.py")
                if not any(part.startswith(".") for part in candidate.parts)
            )
    return sorted(files)


def _parameter_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    arguments = node.args
    return (
        len(arguments.posonlyargs)
        + len(arguments.args)
        + len(arguments.kwonlyargs)
        + int(arguments.vararg is not None)
        + int(arguments.kwarg is not None)
    )


def _all_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.expr]:
    annotations: list[ast.expr] = []
    for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
        if argument.annotation is not None:
            annotations.append(argument.annotation)
    if node.args.vararg and node.args.vararg.annotation:
        annotations.append(node.args.vararg.annotation)
    if node.args.kwarg and node.args.kwarg.annotation:
        annotations.append(node.args.kwarg.annotation)
    if node.returns is not None:
        annotations.append(node.returns)
    return annotations


def _module_name(path: Path, roots: tuple[Path, ...]) -> str:
    for root in roots:
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if relative == Path("."):
            return path.stem
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
    return path.stem


def _import_targets(tree: ast.AST) -> list[tuple[str, int]]:
    targets: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append((node.module, node.lineno))
    return targets


def _architecture_findings(
    path: Path,
    tree: ast.AST,
    module: str,
    contracts: tuple[ArchitectureContract, ...],
) -> list[Finding]:
    findings: list[Finding] = []
    for contract in contracts:
        if module != contract.source and not module.startswith(f"{contract.source}."):
            continue
        for target, line in _import_targets(tree):
            forbidden = next(
                (
                    prefix
                    for prefix in contract.forbid
                    if target == prefix or target.startswith(f"{prefix}.")
                ),
                None,
            )
            if forbidden is not None:
                findings.append(
                    Finding(
                        rule_id="EPK301",
                        message=f"Module {module!r} imports forbidden dependency {target!r}",
                        path=path,
                        line=line,
                        severity=Severity.ERROR,
                        observed=target,
                        limit=f"not {forbidden}",
                        suggestion="Move the dependency behind an allowed boundary.",
                    )
                )
    return findings


def _generic_module_finding(path: Path, config: Config) -> Finding | None:
    if path.stem not in config.forbidden_module_names:
        return None
    return Finding(
        rule_id="EPK104",
        message=f"Generic module name {path.stem!r} hides responsibility",
        path=path,
        line=1,
        severity=Severity.WARNING,
        observed=path.stem,
        suggestion="Rename the module after the capability it owns.",
    )


def _syntax_finding(path: Path, error: OSError | SyntaxError) -> Finding:
    line = error.lineno if isinstance(error, SyntaxError) and error.lineno else 1
    return Finding(
        rule_id="EPK001",
        message=f"Unable to analyze Python source: {error}",
        path=path,
        line=line,
        severity=Severity.ERROR,
    )


def _signature_findings(path: Path, function: _Function, config: Config) -> list[Finding]:
    node = function.node
    findings: list[Finding] = []
    parameters = _parameter_count(node)
    if parameters > config.max_parameters:
        findings.append(
            Finding(
                rule_id="EPK101",
                message=f"{function.symbol} has too many parameters",
                path=path,
                line=function.line,
                severity=Severity.WARNING,
                symbol=function.symbol,
                observed=parameters,
                limit=config.max_parameters,
                suggestion="Group a real data concept or split responsibilities.",
            )
        )
    if node.name.startswith("_"):
        return findings

    annotations = _all_annotations(node)
    if any(_annotation_root(annotation) in _MAPPING_NAMES for annotation in annotations):
        findings.append(
            Finding(
                rule_id="EPK102",
                message=f"{function.symbol} exposes an anonymous mapping contract",
                path=path,
                line=function.line,
                severity=Severity.REVIEW,
                symbol=function.symbol,
                suggestion="Use a named DTO when this function crosses a data boundary.",
            )
        )
    deepest = max((annotation_depth(item) for item in annotations), default=0)
    if deepest > config.max_type_depth:
        findings.append(
            Finding(
                rule_id="EPK103",
                message=f"{function.symbol} has an overly nested type annotation",
                path=path,
                line=function.line,
                severity=Severity.WARNING,
                symbol=function.symbol,
                observed=deepest,
                limit=config.max_type_depth,
                suggestion="Name the contract with a type alias or data class.",
            )
        )
    return findings


def _risk_findings(
    path: Path,
    function: _Function,
    metric: FunctionMetric,
    config: Config,
) -> list[Finding]:
    findings: list[Finding] = []
    if metric.complexity > config.max_complexity:
        findings.append(
            Finding(
                rule_id="EPK201",
                message=f"{function.symbol} exceeds cyclomatic complexity",
                path=path,
                line=function.line,
                severity=Severity.ERROR,
                symbol=function.symbol,
                observed=metric.complexity,
                limit=config.max_complexity,
                suggestion="Separate decisions by responsibility or simplify the control flow.",
            )
        )
    if metric.crap is not None and metric.crap > config.max_crap:
        findings.append(
            Finding(
                rule_id="EPK202",
                message=f"{function.symbol} exceeds the CRAP threshold",
                path=path,
                line=function.line,
                severity=Severity.ERROR,
                symbol=function.symbol,
                observed=round(metric.crap, 3),
                limit=config.max_crap,
                suggestion="Add meaningful tests, simplify the function, or both.",
            )
        )
    return findings


def _function_metric(
    path: Path,
    function: _Function,
    coverage_file: _CoverageFile | None,
) -> FunctionMetric:
    complexity = cyclomatic_complexity(function.node)
    function_coverage = (
        coverage_file.ratio(function.line, function.end_line) if coverage_file else None
    )
    function_crap = (
        crap_score(complexity, function_coverage) if function_coverage is not None else None
    )
    return FunctionMetric(
        path=path,
        symbol=function.symbol,
        line=function.line,
        end_line=function.end_line,
        complexity=complexity,
        coverage=function_coverage,
        crap=function_crap,
    )


def _analyze_file(
    path: Path,
    roots: tuple[Path, ...],
    config: Config,
    coverage: _CoverageIndex,
) -> AnalysisReport:
    report = AnalysisReport()
    output_path = _display_path(path)
    generic_finding = _generic_module_finding(output_path, config)
    if generic_finding:
        report.findings.append(generic_finding)

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as error:
        report.findings.append(_syntax_finding(output_path, error))
        return report

    module = _module_name(path, roots)
    report.findings.extend(
        _architecture_findings(output_path, tree, module, config.architecture_contracts)
    )
    collector = _FunctionCollector()
    collector.visit(tree)
    coverage_file = coverage.for_path(path)
    for function in collector.functions:
        metric = _function_metric(output_path, function, coverage_file)
        report.metrics.append(metric)
        report.findings.extend(_signature_findings(output_path, function, config))
        report.findings.extend(_risk_findings(output_path, function, metric, config))
    return report


def analyze_paths(
    paths: Iterable[Path],
    *,
    config: Config,
    coverage_path: Path | None = None,
) -> AnalysisReport:
    roots = tuple(Path(path) for path in paths)
    coverage = _CoverageIndex.load(coverage_path)
    report = AnalysisReport()
    for path in _iter_python_files(roots):
        file_report = _analyze_file(path, roots, config, coverage)
        report.findings.extend(file_report.findings)
        report.metrics.extend(file_report.metrics)

    report.findings.sort(key=lambda item: (item.path.as_posix(), item.line, item.rule_id))
    report.metrics.sort(key=lambda item: (item.path.as_posix(), item.line, item.symbol))
    return report
