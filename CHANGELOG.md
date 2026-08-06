# Changelog

## 0.1.0 - Unreleased

### Added

- deterministic Python source analysis;
- cyclomatic complexity and branch-aware function-level CRAP calculation;
- public boundary checks for anonymous mappings and nested types;
- configurable architecture import contracts;
- portable quality baselines with enforceable metric regression ratcheting;
- explicit coverage-evidence validation;
- versioned baseline schema validation and non-suppressible integrity rules;
- quick and full Martin-inspired quality gates;
- GitHub Actions workflows for normal QA and mutation testing;
- reproducible audits against Epok Auth and Cortex Agent SDK;
- Codex-focused workflow and agent instructions.

### Calibrated

- Coverage.py relative paths resolve from the report directory;
- external project commands and relative artifacts resolve from the configured project root;
- executed and missing branch arcs participate in function coverage;
- missing, malformed, or empty requested coverage reports fail explicitly;
- `self` and `cls` are excluded from business-parameter counts;
- cyclomatic complexity is a warning while CRAP remains blocking;
- the gate applies the committed baseline and rejects worsening metrics;
- baselines cannot suppress syntax, evidence, architecture, ratchet, or baseline-integrity failures.
