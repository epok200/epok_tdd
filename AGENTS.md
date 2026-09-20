# Instructions for coding agents

Read the active specification and `docs/philosophy.md` before implementation.

Use TDD for behavior changes: write a failing test, run it, implement the smallest passing change, then refactor while green.

Do not bypass or weaken a quality rule merely to make the gate pass. A threshold change requires an explicit product decision and an explanation in the pull request.

Prefer existing Python tools over reimplementing their mature behavior. Epok TDD owns orchestration, policy, ratcheting, and reporting.

Do not introduce a layer, protocol, repository, factory, service, helper module, or DTO without a concrete boundary or behavior that benefits from it.

Before delivery run:

```bash
uv run pytest --cov=epok_tdd --cov-branch --cov-report=json:coverage.json
uv run epok-tdd check src --coverage coverage.json
uv run ruff check .
uv run pyright
```

For high-risk changes also run `uv run mutmut run`.
