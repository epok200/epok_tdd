# Epok TDD

**Epok TDD is an executable quality constitution for Python code produced with coding agents.**

It does not replace Ruff, Pytest, Coverage.py, Pyright, or Mutmut. It coordinates them, adds deterministic design policies, and turns their evidence into one quality-gate decision that Codex or a human can act on.

## Product direction

Epok TDD adapts the six-stage workflow popularized by Robert C. Martin's Swarm Forge to a practical constraint: most developers do not own a programmable swarm of agents. Codex can implement the change; Epok TDD acts as the deterministic QA system around it.

The stages are:

1. specification approval;
2. TDD implementation;
3. cleanup through complexity, coverage, and CRAP;
4. architecture contracts;
5. mutation testing;
6. final QA.

The stages are roles in a workflow, not mandatory autonomous agents.

## Initial CLI

```bash
uv run epok-tdd check src --coverage coverage.json
uv run epok-tdd gate
uv run epok-tdd baseline create src --coverage coverage.json
```

The first release focuses on trustworthy local analysis, a configurable ratchet, and a unified report. It deliberately avoids AI-based linting: deterministic checks decide whether a rule passed.

## Development

```bash
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run pyright
```

See `docs/philosophy.md`, `docs/workflow.md`, and `AGENTS.md` before changing the architecture.
