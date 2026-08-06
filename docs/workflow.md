# Workflow for Codex

Epok TDD maps the six Swarm Forge responsibilities onto one coding agent plus deterministic gates.

## 1. Specification

The human approves intent, acceptance criteria, and explicit exclusions. Codex may clarify wording, but it must not silently redefine product behavior.

## 2. Coder

Codex follows red, green, refactor. Tests exercise public behavior rather than private implementation details and generate branch-aware Coverage.py JSON evidence.

## 3. Cleaner

Epok TDD measures cyclomatic complexity, function coverage, CRAP, type depth, meaningful parameter count, and configured design policies. Complexity guides attention; CRAP identifies unprotected risk.

Codex receives concrete findings and makes the smallest refactor that resolves the evidence. It must not introduce abstractions merely to reduce a metric.

## 4. Architect

Architecture contracts protect dependency direction and module boundaries. Architecture is not permission to introduce layers speculatively.

## 5. Hardener

Mutation testing challenges the test suite. Surviving mutants are evidence that a behavior is not effectively protected. Full mutation is reserved for deliberate hardening runs rather than every small edit.

## 6. QA

The quick gate validates the approved specification, tests, coverage evidence, calibrated design checks, the committed quality ratchet, Ruff, and the type checker.

The full gate adds mutation testing. One failed deterministic phase rejects the result; an agent explanation cannot override it.

## Adoption in existing repositories

Create a baseline only after reviewing its contents. Existing debt may remain, but future changes cannot increase complexity or CRAP, reduce coverage, or make measured evidence disappear.

For routine work, use the quick gate. Security-sensitive, domain-critical, or release changes use the full gate.
