---
skill_id: git-conventional-commits
type: pattern
domain_tags: [git, commits, conventions, versioning]
scope: global
stack_context: []
created: 2026-02-20
last_used: 2026-02-20
reuse_count: 0
project_origin: prism-seed
status: active
verified_by: human
---

# Git Conventional Commits

## Key Insight
Conventional Commits give structured commit history that tools (semantic-release, changelogs, PRISM memory) can parse automatically. The type prefix communicates intent at a glance.

## Trigger
Every time you write a git commit message.

## Solution

```
<type>(<scope>): <short summary>

[optional body — what and why, not how]

[optional footer — BREAKING CHANGE: ..., Closes #123]
```

**Types:**
| Type | When to use |
|------|-------------|
| `feat` | New feature for the user |
| `fix` | Bug fix for the user |
| `refactor` | Code change without feature or fix |
| `test` | Adding or changing tests |
| `docs` | Documentation only |
| `chore` | Build, tooling, dependencies |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration |

**Examples:**
```
feat(auth): add OAuth2 login with GitHub
fix(api): return 404 when user not found instead of 500
refactor(db): extract connection pooling to separate module
chore(deps): upgrade pydantic to 2.7
```

## Notes
- Scope is optional but recommended for multi-module projects
- `BREAKING CHANGE:` in footer triggers major version bump in semantic-release
- Keep summary under 72 characters for clean `git log --oneline`
