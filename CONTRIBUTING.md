# Contributing

Epok TDD must be held to the standard it asks from other projects.

Start with an approved specification for behavior changes. Follow red, green, refactor. Tests should exercise public behavior and include failure paths, not merely increase a percentage.

Before opening a pull request, run:

```bash
uv sync --all-groups
uv run epok-tdd gate --mode quick
```

For changes to coverage mapping, CRAP, command execution, architecture rules, or the ratchet, also run:

```bash
uv run epok-tdd gate --mode full
```

A rule addition must include its rationale, severity, false-positive analysis, examples that should fail, and examples that must remain valid. Threshold changes are product decisions, not convenient fixes for CI.
