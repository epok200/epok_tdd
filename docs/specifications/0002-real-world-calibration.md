# Specification 0002: Real-world calibration

Status: Approved by product owner on 2026-08-06

## Purpose

Make Epok TDD trustworthy outside its own repository by correcting the defects exposed while auditing Epok Auth and Cortex Agent SDK.

## Acceptance criteria

### Scenario: consume portable coverage reports

Given a Coverage.py JSON report stored at a project root
When its file names are relative to that report
Then Epok TDD resolves them against the report directory
And combines executed and missing lines with executed and missing branches per function.

### Scenario: reject missing evidence

Given an explicit coverage path
When the report is missing, malformed, or contains no measured files
Then Epok TDD emits a blocking deterministic finding
And does not pretend that CRAP was evaluated.

### Scenario: anchor external projects correctly

Given a `pyproject.toml` outside the current working directory
When Epok TDD runs tests, lint, typing, mutation, or resolves a relative coverage path
Then every relative operation is anchored to the directory containing that configuration.

### Scenario: count meaningful parameters

Given an instance or class method
When Epok TDD counts its parameters
Then the implicit `self` or `cls` receiver does not count as a business parameter.

### Scenario: distinguish complexity from unprotected risk

Given a complex function with adequate tests
When complexity exceeds the configured threshold but CRAP remains acceptable
Then complexity is reported as a warning
And CRAP remains the blocking risk signal.

### Scenario: enforce the quality ratchet

Given a committed baseline
When complexity or CRAP increases, coverage decreases, or measured coverage disappears
Then Epok TDD emits a blocking metric-regression finding
And the full gate evaluates effective findings after applying that baseline.

### Scenario: preserve integrity across baselines

Given a baseline containing existing design debt
When the current analysis reports missing evidence, unreadable Python, forbidden architecture, metric regression, or an invalid baseline
Then the baseline cannot suppress that integrity failure
And an invalid baseline becomes a deterministic blocking finding instead of crashing the command.

### Scenario: harden the tests

Given the calibrated implementation
When mutation testing changes the quality engine
Then the test suite detects the behavioral mutations required by this specification.

## Out of scope

This iteration does not add probabilistic AI review, infer whether every dictionary should be a DTO, automatically refactor target repositories, or require mutation testing on every pull request.
