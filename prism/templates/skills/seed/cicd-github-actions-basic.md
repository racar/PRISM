---
skill_id: cicd-github-actions-basic
type: skill
domain_tags: [cicd, github-actions, devops, automation]
scope: global
stack_context: [github, docker, nodejs, python]
created: 2026-02-20
last_used: 2026-02-20
reuse_count: 0
project_origin: prism-seed
status: active
verified_by: human
---

# GitHub Actions CI/CD Basics

## Key Insight
Use `on: [push, pull_request]` for CI. Cache dependencies with `actions/cache` to cut build times by 60–80%. Separate CI (test on PR) from CD (deploy on merge to main).

## Trigger
When setting up automated tests or deployment for a project on GitHub.

## Solution

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm

      - run: npm ci
      - run: npm test -- --coverage
      - run: npm run lint
```

```yaml
# For Python projects
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - run: pip install -e ".[dev]"
      - run: pytest --cov
```

## Notes
- Use `actions/cache@v4` explicitly if your build tool isn't auto-cached
- Secrets go in repo Settings → Secrets — reference as `${{ secrets.MY_SECRET }}`
- Use `needs: [test]` in deploy job to enforce test-before-deploy
- `concurrency:` group prevents redundant runs on rapid pushes
