# Workflow for Codex

Epok TDD maps the six Swarm Forge responsibilities onto one coding agent plus deterministic gates.

## 1. Specification

The human approves intent and acceptance criteria. Codex may clarify or improve wording, but it must not silently redefine the product behavior.

## 2. Coder

Codex follows red, green, refactor. Tests exercise public behavior rather than private implementation details.

## 3. Cleaner

Epok TDD measures complexity, function coverage, CRAP, type depth, parameter count, and configured design policies. Codex receives concrete findings and makes the smallest refactor that resolves them.

## 4. Architect

Architecture contracts protect dependency direction and module boundaries. Architecture is not permission to introduce layers speculatively.

## 5. Hardener

Mutation testing challenges the test suite. Surviving mutants are evidence that a behavior is not effectively protected.

## 6. QA

Lint, type checking, tests, the quality ratchet, and optional mutation checks produce the final decision.

For routine work, use the quick gate and mutate changed code in CI or before release. Security-sensitive or domain-critical changes use the full gate.
