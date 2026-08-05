# Philosophy

Epok TDD treats code quality as infrastructure rather than a prompt request.

## Deterministic before probabilistic

An agent may propose a change. Scripts decide whether measurable rules passed. No LLM is allowed to award itself coverage, complexity, mutation, typing, or architecture points.

## Behavior first

Tests protect observable behavior. Metrics help prioritize risk; they do not prove correctness. High coverage cannot rescue an incomprehensible design, and elegant code cannot excuse missing behavior.

## Ratchet, not purity theater

Existing repositories contain debt. Epok TDD should prevent new debt and reward improvement instead of making adoption impossible with an absolute wall on day one.

## Small components, explicit boundaries

A component exists because it owns a real responsibility. Layers, services, repositories, protocols, and factories are not virtues by themselves. Ceremony is debt when it does not isolate volatility or clarify a contract.

## Evidence over aesthetics

Every rejection must identify the file, location, rule, observed value, configured limit, and a practical next action. Vague judgments such as “make this cleaner” are not quality gates.
