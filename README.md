# PRISM — Project Reasoning & Intelligent Skill Memory

Agent-agnostic orchestration system with cross-project skill memory. PRISM sits between you and your AI coding agents — it keeps a persistent knowledge base of skills, gotchas, and decisions, and makes sure the right context reaches the right agent at the right time.

```
┌─────────────────────────────────────────────────────────┐
│                       HUMAN                             │
│  Reviews Flux board → Approves tasks → Moves to Ready   │
└──────────────────────┬──────────────────────────────────┘
                       │ browser localhost:9000
┌──────────────────────▼──────────────────────────────────┐
│                  FLUX BOARD (Docker)                    │
│  Backlog → Ready → In Progress → Review → Done          │
└──────┬───────────────────────────────────┬──────────────┘
       │ MCP                               │ Webhook
┌──────▼──────────┐               ┌────────▼─────────────┐
│ ARCHITECT AGENT │               │  DEVELOPER AGENT     │
│ tool + model    │               │  tool + model        │
│ (configurable)  │               │  (configurable)      │
└──────┬──────────┘               └────────┬─────────────┘
       └──────────────┬────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────┐
│                 PRISM MEMORY LAYER                      │
│  ~/.prism/memory/ ← private Git repo                   │
│  skills/ · gotchas/ · decisions/ · episodes/            │
│  index.db (SQLite FTS5 + embeddings)                   │
└────────────────────────────────────────────────────────┘
       │
       │ Task Done (Webhook)
       ▼
┌─────────────────────────────────────────────────────────┐
│            DOCKER TEST PIPELINE (Fase 5)                │
│  Isolated containers → Quality Gates → QA Review        │
│  • Lint, Type Check, Tests, Coverage ≥80%               │
│  • Web Terminal for QA access                           │
│  • Auto-PR creation → Human merge                      │
└────────────────────────────────────────────────────────┘
```

## Stack

- **Python 3.11+** with [uv](https://docs.astral.sh/uv/) for package management
- **SQLite FTS5 + sentence-transformers** for hybrid skill search
- **FastAPI + watchdog** for Flux webhook listener and file watcher
- **Flux** (Docker) as Kanban board with MCP server
- **Anthropic Haiku** for memory evaluation *(Fase 4: optimization)*

## Installation

```bash
git clone <repo>
cd prism
uv sync
```

After sync, use `uv run prism` or install globally:

```bash
uv tool install .
prism --version
```

To enable semantic search (optional, ~80 MB model download):

```bash
uv sync --extra embeddings
# then set in ~/.prism/prism.config.yaml:
# memory:
#   embeddings_enabled: true
```

---

## Quick Start

```bash
# 1. Initialize a new project
prism init my-project

# 2. Rebuild the skill index (after init or any manual skill edits)
prism index rebuild

# 3. Inject relevant skills into .prism/injected-context.md
prism inject

# 4. Start the Flux board (requires Docker)
prism board setup
prism board listen --daemon

# 5. After planning, augment tasks and sync to Flux
prism augment
prism sync --project-id <flux-project-id>
```

For a complete walkthrough of setting up a new project, see **[Getting Started](docs/getting-started.md)**.

---

## End-to-End Workflow

```
prism init / prism attach
    → .prism/ created, 7 seed skills loaded

prism index rebuild
    → SQLite FTS5 index built from ~/.prism/memory/

prism inject
    → .prism/injected-context.md generated with relevant skills

prism board setup
    → Flux starts on localhost:9000, MCP registered, webhook configured

prism board listen --daemon
    → Webhook listener on :8765, file watcher on .specify/specs/

[Architect agent runs /speckit.tasks in their tool]

prism augment              ← or auto-triggered by file watcher
    → tasks.prism.md enriched with per-task PRISM Context blocks

prism sync --project-id <id>
    → All tasks created in Flux Backlog (no duplicates)

[Human approves tasks in browser → moves to Ready]

[Webhook fires: todo → doing]
    → .prism/current-task.md auto-generated with skills + gotchas

[Developer agent implements and moves task to Done]

[Webhook fires: done]
    → Docker Test Pipeline triggered (Fase 5)

[Pipeline executes in isolated container]
    → Quality Gates (lint, typecheck, tests, coverage ≥80%)
    → If pass: PR created, ready for QA review

[QA Agent reviews in container via web terminal]
    → prism review --task TASK-42
    → prism approve --pr 123  → Human notified for merge

prism memory push
    → Skills committed and pushed to Git remote
```

---

## Commands

### `prism init [NAME]`

Initialize a new PRISM project. Creates `.prism/` config files and seeds `~/.prism/memory/` with starter skills.

```bash
prism init my-project          # creates ./my-project/
prism init                     # initializes current directory
prism init my-project --no-speckit     # skip Spec-Kit setup
prism init my-project --no-embeddings  # FTS5 only (no model download)
```

Creates:
```
my-project/
└── .prism/
    ├── PRISM.md       ← canonical agent context (edit this)
    ├── AGENTS.md      ← agent team config (tool + model per role)
    └── project.yaml   ← project metadata

~/.prism/
├── prism.config.yaml  ← global config (created on first init)
└── memory/
    └── skills/        ← 7 seed skills loaded here
```

---

### `prism attach [DIRECTORY]`

Attach PRISM to an existing project. Runs in the current directory by default.

```bash
prism attach           # current directory
prism attach ./my-app  # specific path
```

Detects whether [Spec-Kit](https://github.com/github/spec-kit) is already initialized and skips re-init if so.

---

### `prism config show`

Show the active configuration — global, per-project, and merged agent roles.

```bash
prism config show
prism config show --project-dir ./other-project
```

`~/.prism/prism.config.yaml` — global defaults:
```yaml
tools:
  claude_code:
    command: claude
    context_file: CLAUDE.md
    mcp_support: true

models:
  anthropic:
    opus: claude-opus-4-6
    sonnet: claude-sonnet-4-6
    haiku: claude-haiku-4-5-20251001

agent_roles:
  architect:
    default:
      tool: claude_code
      model: anthropic.opus
  developer:
    default:
      tool: opencode
      model: moonshot.kimi

memory:
  embeddings_enabled: false   # set true after: uv sync --extra embeddings
```

`.prism/AGENTS.md` — per-project overrides (project wins over global):
```yaml
project: my-project
agents:
  developer:
    tool: claude_code
    model: anthropic.sonnet
```

---

### `prism seed [--force]`

Load seed skills into `~/.prism/memory/skills/`. Called automatically by `init` and `attach`.

```bash
prism seed            # skip if skills already exist
prism seed --force    # overwrite existing seed files
```

| Skill | Domain |
|-------|--------|
| `nodejs-testing-jest` | Node.js unit testing with Jest |
| `python-fastapi-structure` | FastAPI project layout + dependency injection |
| `react-component-patterns` | React hooks + composition patterns |
| `cicd-github-actions-basic` | GitHub Actions CI/CD |
| `docker-compose-dev` | Local dev with Docker Compose |
| `git-conventional-commits` | Commit message conventions |
| `error-handling-patterns` | Result types, API errors, structured logging |

---

### `prism index rebuild [--verbose]`

Rebuild the SQLite FTS5 index by scanning all `.md` files in `~/.prism/memory/`. Also writes a human-readable `index.yaml`.

```bash
prism index rebuild
prism index rebuild --verbose   # list each file as it's indexed
```

Run this after manually adding or editing skill files.

---

### `prism skill add [--file PATH] [--evaluate]`

Add a skill to memory. Interactive mode prompts for all fields; file mode reads a `.md` with YAML frontmatter.

```bash
prism skill add                        # interactive
prism skill add --file my-skill.md     # from file
prism skill add --file my-skill.md --evaluate  # run Haiku evaluator first
```

**Skill frontmatter schema:**
```yaml
---
skill_id: jwt-rs256-gotcha          # kebab-case, required
type: gotcha                        # skill | pattern | gotcha | decision
domain_tags: [auth, jwt, security]  # at least one required
scope: global                       # global | project
stack_context: [python, fastapi]
created: 2026-02-21
project_origin: my-project
status: active                      # active | deprecated | conflicted | needs_review
verified_by: human                  # human | memory_agent
---
# JWT RS256 Gotcha

## Key Insight
...
```

Saved to `~/.prism/memory/[skills|gotchas|decisions]/[skill_id].md` and indexed automatically.

---

### `prism skill list [--status STATUS]`

List skills with a Rich table.

```bash
prism skill list                     # active skills
prism skill list --status deprecated
prism skill list --status all
```

---

### `prism skill search QUERY`

Search skills using FTS5 (+ semantic reranking if embeddings enabled).

```bash
prism skill search "python fastapi"
prism skill search "JWT authentication gotcha"
```

---

### `prism inject [--budget N] [--query TEXT]`

Search memory and inject relevant skills into `.prism/injected-context.md`. Respects a token budget (default 4000).

```bash
prism inject                          # uses project description from project.yaml
prism inject --query "react auth"     # custom focus query
prism inject --budget 2000            # smaller budget
```

Ranking formula: `(reuse_count × 2) + (recency × 1.5) + (tag_match × 3)`

---

### `prism memory push/pull/status`

Git sync for `~/.prism/memory/`. Requires `git_remote` set in `prism.config.yaml`.

```bash
prism memory push                    # commit all changes + push
prism memory push -m "add jwt skill" # custom message
prism memory pull                    # pull from remote
prism memory status                  # show modified/untracked files
```

Configure remote:
```yaml
# ~/.prism/prism.config.yaml
memory:
  git_remote: "git@github.com:you/prism-memory.git"
  auto_commit: true
```

---

### `prism board setup`

Launch Flux via Docker, register the MCP server with Claude Code, and configure the webhook.

```bash
prism board setup
prism board setup --project-id <existing-flux-id>
```

Requires Docker running. Starts Flux on `localhost:9000`.

---

### `prism board listen [--daemon] [--port N]`

Start the webhook listener (FastAPI on port 8765) and file watcher (`.specify/specs/`).

```bash
prism board listen                   # foreground with live logs
prism board listen --daemon          # background, logs → ~/.prism/listener.log
prism board listen --port 9000       # custom port
```

**Webhook events handled:**

| Transition | Action |
|------------|--------|
| `todo → doing` | Generates `.prism/current-task.md` with skills + gotchas |
| `done` | Triggers memory capture (Fase 3) |
| `tasks.md` file created/modified | Auto-runs `prism augment` (2s debounce) |

---

### `prism board stop / prism board status`

```bash
prism board status    # show PID, running state, log path
prism board stop      # send SIGTERM to listener process
```

---

### `prism augment [--file PATH] [--force]`

Read `tasks.md` from Spec-Kit, search FTS5 per task, and inject a `## PRISM Context` block (500-token budget per task). Writes `tasks.prism.md` — never overwrites the original.

```bash
prism augment                              # latest tasks.md in .specify/specs/
prism augment --file path/to/tasks.md
prism augment --force                      # re-augment even if already done
```

Output format:
```markdown
### Task 1: Implement login endpoint
...

### PRISM Context

**Relevant Skills:**
- **jwt-auth** (skill): JWT Authentication Pattern
- **error-handling-patterns** (pattern): Error Handling Patterns
```

---

### `prism sync [--project-id ID] [--dry-run]`

Push all tasks from `tasks.prism.md` (or `tasks.md`) to Flux Backlog. Skips tasks already synced. Saves the task mapping in `.prism/project.yaml`.

```bash
prism sync --project-id flux-proj-123
prism sync --dry-run                   # preview without creating tasks
```

---

### `prism task show TASK-ID`

Fetch a task from Flux and generate `.prism/current-task.md` with the full DT-4 format.

```bash
prism task show TASK-42
```

Generated file includes:

| Section | Content |
|---------|---------|
| **What to Build** | Full task description from Flux |
| **Acceptance Criteria** | Checkboxes parsed from task body |
| **PRISM Context** | Relevant skills, gotchas, decisions from memory |
| **Definition of Done** | Standard checklist |
| **Output** | YAML block for the agent to fill when complete |

---

### `prism start --role <role> [--no-launch]`

Generate context file and launch an agent by role (architect, developer, reviewer, memory, optimizer).

```bash
prism start --role architect          # Launch architect agent
prism start --role developer            # Launch developer agent
prism start --role architect --no-launch  # Generate context only
```

Workflow:
1. Reads `.prism/AGENTS.md` for tool + model assignment
2. Validates compatibility (capabilities check)
3. Runs `prism inject` to update context
4. Generates appropriate context file (CLAUDE.md, .cursorrules, etc.)
5. Launches the tool (or prints command with `--no-launch`)

---

### `prism resume`

Show project state, board status, memory stats, and suggest the next agent to run.

```bash
prism resume
```

Displays:
- Project overview and active task
- Memory stats (skill count, index status)
- Flux board task counts by status
- Suggested next step (e.g., `prism start --role developer`)
- Warning if memory has uncommitted changes

---

### `prism generate-context --role <role>`

Generate context file for a specific role without launching.

```bash
prism generate-context --role architect
```

Generates tool-specific files:
- `claude_code` → `CLAUDE.md`
- `opencode` → `AGENTS.md`
- `cursor` → `.cursorrules`
- `gemini` → `GEMINI.md`
- `windsurf` → `.windsurfrules`
- `copilot` → `.github/copilot-instructions.md`

---

### `prism health`

Check token budgets and skill health across the project.

```bash
prism health                          # Full health report
prism health --project-dir ./other    # Check different project
```

Reports:
- Token usage per file vs limits
- Skill status counts (ACTIVE, NEEDS_REVIEW, CONFLICTED)
- Total budget utilization
- Exit codes: 0 (healthy), 1 (warnings), 2 (critical)

---

### `prism optimize [--dry-run] [--auto] [--confirm]`

Run memory optimizer: health check, compression, deduplication, conflict detection, staleness check, pattern promotion, constitution audit.

```bash
prism optimize --dry-run             # Report only, no changes
prism optimize --auto                 # Apply safe changes (compression, staleness)
prism optimize --confirm              # Apply all changes (including merges)
```

Optimization steps:
1. **Health Check** — always runs
2. **Staleness Check** — marks skills unused >90 days as NEEDS_REVIEW (auto-applied)
3. **Compression** — compresses skills >2000 tokens with Haiku (auto-applied)
4. **Deduplication** — TF-IDF similarity detection (requires confirmation)
5. **Conflict Detection** — Haiku-based contradiction detection (creates Flux tasks)
6. **Pattern Promotion** — suggests gotchas → patterns (requires confirmation)
7. **Constitution Audit** — checks for contradictory principles (requires confirmation)

---

### `prism schedule enable/disable/status`

Manage weekly automated optimizer cron job.

```bash
prism schedule enable                 # Install weekly cron job
prism schedule disable                # Remove cron job
prism schedule status                 # Check if enabled
```

Runs `prism optimize --auto` every Sunday at 9:00 AM. Logs to `~/.prism/optimizer.log`.

Supports:
- **Unix/Linux/macOS**: cron job
- **Windows**: Task Scheduler

---

### `prism submit-for-qa --task TASK-42`

Submit a completed task for QA review. Creates PR, launches Docker test container, runs quality gates.

```bash
prism submit-for-qa --task TASK-42
```

Workflow:
1. Creates GitHub PR from current changes
2. Launches isolated Docker container with the PR branch
3. Runs quality gates: linting → type check → unit tests → coverage (≥80%) → integration tests
4. If all gates pass: container ready for QA review with web terminal
5. Updates Flux task with container URL and PR link

---

### `prism review --task TASK-42 [--command "..."]`

QA reviews a test container. Access web terminal or execute commands in the container.

```bash
prism review --task TASK-42                    # Show container info and web terminal URL
prism review --task TASK-42 --command "pytest tests/ -v"  # Run tests in container
```

Useful review commands:
```bash
prism review --task TASK-42 --command "cat src/main.py"
prism review --task TASK-42 --command "git diff main...HEAD"
prism review --task TASK-42 --command "coverage report"
```

---

### `prism approve --pr 123 [--message "..."]`

QA approves a PR after review. Notifies human for manual merge.

```bash
prism approve --pr 123 --message "Code clean, tests pass, LGTM"
```

Creates approving review on GitHub and notifies human that PR is ready for merge.

---

### `prism reject --pr 123 --reason "..."`

QA rejects a PR with feedback. Returns task to developer.

```bash
prism reject --pr 123 --reason "Coverage only 60%, needs ≥80%"
```

Creates "changes requested" review on GitHub. Container kept alive for 30 min for debugging.

---

### `prism shell --container prism-test-TASK-42`

Open interactive shell in a test container.

```bash
prism shell --task TASK-42          # Using task ID
prism shell --container prism-test-TASK-42  # Using container name
```

---

## Project Structure

```
prism/
├── pyproject.toml
└── prism/
    ├── cli/                 ← Click commands (one file per command group)
    ├── memory/
    │   ├── schemas.py       ← SkillFrontmatter Pydantic model + dataclasses
    │   ├── store.py         ← SkillStore: SQLite FTS5 + embedding cache
    │   ├── injector.py      ← token-budget ranking → injected-context.md
    │   ├── evaluator.py     ← Haiku ADD/UPDATE/NOOP/DELETE evaluation
    │   ├── compressor.py    ← skill compression (Fase 4)
    │   ├── dedup.py         ← TF-IDF duplicate detection (Fase 4)
    │   ├── conflict.py      ← LLM-based contradiction detection (Fase 4)
    │   ├── stale.py         ← staleness checker (Fase 4)
    │   ├── promoter.py      ← gotcha → pattern promotion (Fase 4)
    │   └── auditor.py       ← constitution.md audit (Fase 4)
    ├── board/
    │   ├── flux_client.py   ← FluxClient HTTP REST with retry
    │   ├── task_mapper.py   ← tasks.md parser + current-task.md generator
    │   └── webhook_listener.py  ← FastAPI webhook app
    ├── speckit/
    │   ├── augmenter.py     ← tasks.md → tasks.prism.md with PRISM context
    │   └── watcher.py       ← watchdog observer on .specify/specs/
    ├── agents/              
    │   ├── config.py        ← AGENTS.md parser (Fase 3)
    │   ├── compatibility.py ← tool capability validation (Fase 3)
    │   ├── context_generator.py  ← CLAUDE.md / .cursorrules generator (Fase 3)
    │   └── launcher.py      ← agent launcher with fallback (Fase 3)
    ├── utils/               ← yaml_utils, git helpers, tfidf
    ├── templates/           ← project templates + 7 seed skills
    ├── config.py            ← Pydantic config schemas + loaders
    └── project.py           ← init/attach business logic
```

## User Project Structure

```
my-project/
├── .prism/
│   ├── PRISM.md              ← canonical context (edit this — source of truth)
│   ├── AGENTS.md             ← agent team config (tool + model per role)
│   ├── project.yaml          ← metadata + flux_task_map
│   ├── injected-context.md   ← auto-generated by prism inject
│   └── current-task.md       ← auto-generated when task moves to In Progress
├── .specify/
│   └── specs/
│       └── feature/
│           ├── tasks.md          ← Spec-Kit output
│           └── tasks.prism.md    ← augmented by prism augment
├── CLAUDE.md                 ← generated by prism generate-context (Fase 3)
└── src/

~/.prism/
├── prism.config.yaml         ← global tool/model/role defaults + context limits
├── listener.log              ← webhook listener output (daemon mode)
└── memory/
    ├── index.db              ← SQLite FTS5 + embedding cache
    ├── index.yaml            ← human-readable index summary
    ├── skills/               ← reusable implementation patterns
    ├── gotchas/              ← documented surprises and pitfalls
    ├── decisions/            ← architecture decisions (ADRs)
    └── episodes/
        └── compressed/       ← skill backups before compression (Fase 4)
```

---

## Development

```bash
# Install with dev dependencies
uv sync --dev

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=prism --cov-report=term-missing

# Run only one phase's tests
uv run pytest tests/test_memory.py
uv run pytest tests/test_board.py
uv run pytest tests/test_agents.py
uv run pytest tests/test_optimizer.py
```

## Build Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Fase 0 — Foundation** | ✅ Done | CLI, config system, init/attach, seed skills |
| **Fase 1 — Memory Layer** | ✅ Done | SQLite FTS5 + embeddings, skill CRUD, inject, Git sync |
| **Fase 2 — Board Integration** | ✅ Done | Flux REST client, webhook listener, augment/sync, current-task.md |
| **Fase 3 — Agent Orchestration** | ✅ Done | AGENTS.md parser, context generator, launcher, resume |
| **Fase 4 — Optimizer Agent** | ✅ Done | Health checks, compression, TF-IDF dedup, conflict detection, staleness checker, scheduler |
| **Fase 5 — Docker Test Pipeline** | ✅ Done | Isolated test containers, quality gates, QA workflow, automated PR validation |
