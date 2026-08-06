# Epok TDD

**Epok TDD is an executable quality constitution for Python code produced with coding agents.**

It does not replace Ruff, Pytest, Coverage.py, Pyright, or Mutmut. It coordinates deterministic evidence, adds design and architecture policies, applies a quality ratchet, and returns one decision that Codex or a human can act on.

## Why it exists

Prompts are guidance, not enforcement. A coding agent can agree to keep code simple and still produce unnecessary layers, weak tests, deeply nested contracts, rising complexity, or architecture violations.

Epok TDD moves those repeatable judgments into infrastructure:

- tests verify observable behavior;
- branch-aware coverage and complexity produce function-level CRAP;
- architecture contracts protect dependency direction;
- deterministic rules surface concrete design smells;
- the baseline prevents new debt without demanding instant perfection;
- mutation testing challenges whether tests detect behavioral damage.

Complexity alone is a warning. Missing evidence, excessive CRAP, architecture violations, and metric regressions can block the change.

## Workflow

Epok TDD adapts Robert C. Martin's six Swarm Forge responsibilities to a practical setup with one coding agent:

1. a human approves the specification;
2. Codex implements through TDD;
3. the cleaner gate measures complexity, coverage, and CRAP;
4. architecture contracts protect boundaries;
5. mutation testing hardens the tests;
6. final QA combines every deterministic result.

The stages are responsibilities, not mandatory autonomous agents.

## Commands

```bash
uv run epok-tdd check src --coverage coverage.json
uv run epok-tdd baseline create src --coverage coverage.json
uv run epok-tdd gate --mode quick
uv run epok-tdd gate --mode full
```

`check` analyzes code and optionally applies the committed baseline. `baseline create` records reviewed existing debt. The quick gate is intended for normal pull requests; the full gate adds mutation testing for critical changes and releases.

## Configuration

Epok TDD reads `pyproject.toml`:

```toml
[tool.epok-tdd]
paths = ["src"]
specification = "docs/specifications/current.md"
fail_on = "error"
max_complexity = 10
max_crap = 30.0
max_parameters = 6
max_type_depth = 3
forbidden_module_names = ["utils", "helpers", "common", "misc"]
baseline = ".epok-tdd-baseline.json"

[tool.epok-tdd.commands]
tests = ["pytest", "--cov=my_package", "--cov-branch", "--cov-report=json:coverage.json"]
lint = ["ruff", "check", "."]
types = ["pyright"]
mutation = ["mutmut", "run"]

[[tool.epok-tdd.architecture.contracts]]
source = "domain"
forbid = ["fastapi", "sqlalchemy"]
```

A requested coverage report that is missing, malformed, or empty is a blocking evidence failure. Relative Coverage.py file paths are resolved from the report directory, so audits remain portable across workspaces and CI runners.

## Development

```bash
uv sync --all-groups
uv run epok-tdd gate --mode quick
```

See `docs/philosophy.md`, `docs/rules.md`, `docs/workflow.md`, and `AGENTS.md` before changing the quality model.

## Scope

Epok TDD deliberately avoids AI-based grading. It cannot prove that every abstraction is justified or that every dictionary should become a DTO. Contextual judgments remain review signals; measurable claims must be decided by deterministic tools.
