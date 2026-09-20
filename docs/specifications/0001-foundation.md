# Specification 0001: Foundation quality gate

Status: Approved by product owner on 2026-08-05

## Purpose

Create the smallest useful quality gate that lets Codex implement Python changes while deterministic tools decide whether the result is acceptable.

## Acceptance criteria

### Scenario: analyze Python source deterministically

Given a Python source tree
When Epok TDD checks the tree
Then it reports excessive cyclomatic complexity
And it reports overly deep public type annotations
And it reports anonymous mapping contracts at public boundaries
And it reports generic module names configured as forbidden.

### Scenario: combine complexity and coverage

Given a Coverage.py JSON report
When Epok TDD analyzes a function
Then it calculates function-level coverage from executable lines
And it calculates the CRAP score using the published formula
And it rejects a function above the configured threshold.

### Scenario: protect quality with a ratchet

Given a committed Epok TDD baseline
When a later change introduces a new violation or worsens a metric
Then the check reports the regression
And existing debt that did not worsen does not block unrelated work.

### Scenario: run the Martin-inspired workflow without a swarm

Given commands configured in `pyproject.toml`
When Codex or a human runs the quality gate
Then Epok TDD validates the approved specification
And runs tests
And runs deterministic cleanup and architecture checks
And optionally runs mutation testing
And runs final lint and type checks
And returns one report and process exit code.

## Out of scope for 0.1

Epok TDD will not generate production code, create autonomous agents, replace Ruff or Pytest, infer business requirements, or claim that every design judgment can be automated.
