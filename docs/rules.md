# Rule catalog

Epok TDD rules are intentionally few, deterministic, and evidence-backed. A rule must identify a concrete location and explain the smallest useful response.

| Rule | Default severity | Meaning |
| --- | --- | --- |
| `EPK001` | error | A Python file could not be parsed or read. |
| `EPK002` | error | Explicit coverage evidence is missing, malformed, or contains no measured files. CRAP was not evaluated. |
| `EPK101` | warning | A function exceeds the configured business-parameter limit. Method receivers `self` and `cls` are excluded. |
| `EPK102` | review | A public function exposes an anonymous mapping contract. This is a contextual review signal, not an automatic demand for a DTO. |
| `EPK103` | warning | A public type annotation is nested beyond the configured depth. |
| `EPK104` | warning | A module uses a generic name such as `utils` or `helpers`. |
| `EPK201` | warning | Cyclomatic complexity exceeds the configured navigation threshold. Complexity alone does not prove unsafe code. |
| `EPK202` | error | CRAP exceeds the configured limit after combining complexity with measured test coverage. |
| `EPK301` | error | A configured architecture boundary imports a forbidden dependency. |
| `EPK401` | error | Complexity or CRAP increased, coverage decreased, or previously available evidence disappeared relative to the committed baseline. |

## Severity philosophy

An **error** is objective enough to block automatically. A **warning** is a measurable design smell that deserves attention but may be justified by the domain. A **review** asks for human judgment because context can make the pattern legitimate.

Complexity is a map, not a conviction. A complex function with strong tests can remain maintainable; CRAP and the quality ratchet determine whether its risk is unprotected or worsening.

## CRAP coverage model

Epok TDD resolves relative Coverage.py file names against the directory containing the JSON report. Function coverage combines executed and missing lines with executed and missing branch arcs whose source line belongs to the function.

This is deterministic and portable, but it is still an approximation rather than full basis-path coverage. Projects should generate the report with branch coverage enabled. When an explicit report cannot be trusted, Epok TDD emits `EPK002` instead of silently producing unknown CRAP values.
