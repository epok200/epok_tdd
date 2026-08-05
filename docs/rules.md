# Rule catalog

Epok TDD rules are intentionally few, deterministic, and evidence-backed. A rule must identify a concrete location and explain the smallest useful response.

| Rule | Default severity | Meaning |
| --- | --- | --- |
| `EPK001` | error | The Python file could not be parsed or read. |
| `EPK101` | warning | A function exceeds the configured parameter limit. |
| `EPK102` | review | A public function exposes an anonymous mapping contract. This is a review signal, not an automatic demand for a DTO. |
| `EPK103` | warning | A public type annotation is nested beyond the configured depth. |
| `EPK104` | warning | A module uses a generic name such as `utils` or `helpers`. |
| `EPK201` | error | Cyclomatic complexity exceeds the configured limit. |
| `EPK202` | error | CRAP exceeds the configured limit after combining complexity and coverage. |
| `EPK301` | error | A configured architecture boundary imports a forbidden dependency. |

## Severity philosophy

An **error** is objective enough to block automatically. A **warning** is a strong design smell with measurable evidence. A **review** asks for human judgment because context can make the pattern legitimate.

## CRAP coverage model

Version 0.1 maps Coverage.py executed and missing lines into each function's source range. This is deterministic and practical, but it is not full basis-path coverage. Branch coverage should still be enabled when producing the input report.
