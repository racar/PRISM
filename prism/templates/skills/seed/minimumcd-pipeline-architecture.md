---
skill_id: minimumcd-pipeline-architecture
type: skill
domain_tags: [cicd, pipeline, devops, quality-gates, deployment, continuous-delivery]
scope: global
stack_context: [github-actions, gitlab-ci, docker, python, nodejs]
created: 2026-02-22
last_used: 2026-02-22
reuse_count: 0
project_origin: prism
status: active
verified_by: human
---

# MinimumCD Pipeline Reference Architecture

## Key Insight
Fail fast, fail cheap: order quality gates so the cheapest and most common failure detectors run first. Six sequential stages with strict time budgets enforce this.

## Trigger
When designing or implementing a full CI/CD pipeline with quality gates, progressive deployment, or contract testing.

## Solution

### Gate Sequence

1. **Pre-Commit** — lint, types, secrets, SAST (developer machine)
2. **Stage 1 (<5 min)** — build, unit tests, vuln scan, license, complexity
3. **Stage 2 (<10 min)** — contract tests, schema migration, IaC drift
4. **Stage 3 (<15 min)** — mutation tests, perf, security, SBOM, compliance
5. **Acceptance (<20 min)** — functional, load, chaos, feature interaction
6. **Production** — canary 10%→50%→100%, health checks, SLO verification

### Pre-Feature Baseline (9 non-negotiable gates)

Every trunk commit must pass before feature work begins:
lint, types, secrets, SAST, build, unit tests, vuln scan, contract tests, schema migration.

### Pipeline Patterns

| Topology | Pattern |
|----------|---------|
| 1 team, monolith | Linear pipeline (all stages sequential) |
| N teams, shared deploy | Sub-pipelines per module → shared integration stage |
| Independent services | Contract verification replaces integration testing |

## Notes
- Enforce baseline gates as required status checks on trunk
- Use path-based triggers for Pattern 2 to avoid redundant builds
- Contract broker (Pact/Specmatic) enables independent deploy in Pattern 3
- Progressive deploy: auto-rollback on health check failure at any canary step
