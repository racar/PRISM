# PRISM — Project Reasoning & Intelligent Skill Memory

Agent-agnostic orchestration system with cross-project skill memory. PRISM sits between you and your AI coding agents — it keeps a persistent knowledge base of skills, gotchas, and decisions, and makes sure the right context reaches the right agent at the right time.

```
┌─────────────────────────────────────────────────────────┐
│                       HUMAN                             │
│  Reviews Flux board → Approves tasks → Moves to Ready   │
└──────────────────────┬──────────────────────────────────┘
                       │ browser localhost:3000
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
    → Flux starts on localhost:3000, MCP registered, webhook configured

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
    → Memory capture queued (Fase 3)

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

Requires Docker running. Starts Flux on `localhost:3000`.

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

### Fase 3 commands *(coming soon)*

| Command | Description |
|---------|-------------|
| `prism start --role <role>` | Generate context file and launch agent |
| `prism resume` | Show project state and suggest next agent |
| `prism generate-context` | Generate CLAUDE.md / .cursorrules / AGENTS.md |

### Fase 4 commands *(coming soon)*

| Command | Description |
|---------|-------------|
| `prism health` | Token budget and skill status report |
| `prism optimize [--dry-run] [--auto]` | Compress, deduplicate, detect conflicts |
| `prism schedule enable/disable` | Weekly automated optimizer cron job |

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
    │   └── compressor.py    ← skill compression (Fase 4)
    ├── board/
    │   ├── flux_client.py   ← FluxClient HTTP REST with retry
    │   ├── task_mapper.py   ← tasks.md parser + current-task.md generator
    │   └── webhook_listener.py  ← FastAPI webhook app
    ├── speckit/
    │   ├── augmenter.py     ← tasks.md → tasks.prism.md with PRISM context
    │   └── watcher.py       ← watchdog observer on .specify/specs/
    ├── agents/              ← AGENTS.md parser + launcher (Fase 3)
    ├── utils/               ← yaml_utils, git helpers
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
├── prism.config.yaml         ← global tool/model/role defaults
├── listener.log              ← webhook listener output (daemon mode)
└── memory/
    ├── index.db              ← SQLite FTS5 + embedding cache
    ├── index.yaml            ← human-readable index summary
    ├── skills/               ← reusable implementation patterns
    ├── gotchas/              ← documented surprises and pitfalls
    ├── decisions/            ← architecture decisions (ADRs)
    └── episodes/             ← compressed session summaries (Fase 4)
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
```

## Build Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Fase 0 — Foundation** | ✅ Done | CLI, config system, init/attach, seed skills |
| **Fase 1 — Memory Layer** | ✅ Done | SQLite FTS5 + embeddings, skill CRUD, inject, Git sync |
| **Fase 2 — Board Integration** | ✅ Done | Flux REST client, webhook listener, augment/sync, current-task.md |
| **Fase 3 — Agent Orchestration** | 🔲 Pending | AGENTS.md parser, context generator, launcher |
| **Fase 4 — Optimizer Agent** | 🔲 Pending | Haiku-powered health checks, compression, dedup |
