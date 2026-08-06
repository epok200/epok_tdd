# Philosophy

Epok TDD treats code quality as infrastructure rather than a prompt request.

## Deterministic before probabilistic

An agent may propose a change. Scripts decide whether measurable rules passed. No LLM is allowed to award itself coverage, complexity, mutation, typing, or architecture points.

## Behavior first

Tests protect observable behavior. Metrics help prioritize risk; they do not prove correctness. High coverage cannot rescue an incomprehensible design, and elegant code cannot excuse missing behavior.

Coverage is evidence, not decoration. When a requested report is missing or unusable, Epok TDD fails explicitly instead of treating unknown protection as success.

## Risk before aesthetics

Cyclomatic complexity tells us where understanding and modification become harder. It does not automatically mean a design is wrong. CRAP combines that complexity with test protection, while mutation testing challenges whether the tests can actually notice behavioral damage.

The blocking question is not merely “is this function complicated?” It is “is this function risky, insufficiently protected, or getting worse?”

## Ratchet, not purity theater

Existing repositories contain debt. Epok TDD should prevent new debt and reward improvement instead of making adoption impossible with an absolute wall on day one.

The baseline is enforceable infrastructure. It rejects rising complexity or CRAP, falling coverage, and disappearing evidence even when the absolute thresholds have not yet been crossed.

## Small components, explicit boundaries

A component exists because it owns a real responsibility. Layers, services, repositories, protocols, and factories are not virtues by themselves. Ceremony is debt when it does not isolate volatility or clarify a contract.

## Evidence over aesthetics

Every rejection must identify the file, location, rule, observed value, configured limit, and a practical next action. Vague judgments such as “make this cleaner” are not quality gates.

Contextual smells remain warnings or review signals. Epok TDD should surface judgment, not impersonate it.
