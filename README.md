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
- **SQLite FTS5 + sentence-transformers** for hybrid skill search *(Fase 1)*
- **FastAPI + watchdog** for Flux webhook listener *(Fase 2)*
- **Flux** (Docker) as Kanban board with MCP server *(Fase 2)*
- **Anthropic Haiku** for memory evaluation and optimization *(Fase 4)*

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

---

## Quick Start

```bash
# New project
prism init my-project

# Existing project
cd my-existing-project
prism attach

# See active configuration
prism config show
```

---

## Commands

### `prism init [NAME]`

Initialize a new PRISM project. Creates a directory `NAME` (or uses the current directory if omitted), sets up `.prism/` config files, and seeds `~/.prism/memory/` with starter skills.

```bash
prism init my-project          # creates ./my-project/
prism init                     # initializes current directory
prism init my-project --no-speckit     # skip Spec-Kit setup
prism init my-project --no-embeddings  # FTS5 only (Fase 1 option)
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

Detects whether [Spec-Kit](https://github.com/github/spec-kit) is already initialized and skips re-init if so. Always creates `.prism/` and seeds memory.

---

### `prism config show`

Show the active configuration — global (`~/.prism/prism.config.yaml`), per-project (`.prism/project.yaml`), and the merged agent role assignments.

```bash
prism config show
prism config show --project-dir ./other-project
```

**Config files:**

`~/.prism/prism.config.yaml` — global defaults for all projects:
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
```

`.prism/AGENTS.md` — per-project overrides (project wins over global):
```yaml
project: my-project
agents:
  developer:
    tool: claude_code   # override for this project
    model: anthropic.sonnet
```

---

### `prism seed [--force]`

Load seed skills into `~/.prism/memory/skills/`. Called automatically by `init` and `attach`.

```bash
prism seed            # skip if skills already exist
prism seed --force    # overwrite existing seed files
```

**Included seed skills:**

| Skill | Domain |
|-------|--------|
| `nodejs-testing-jest` | Node.js unit testing patterns |
| `python-fastapi-structure` | FastAPI project layout + dependency injection |
| `react-component-patterns` | React hooks + composition patterns |
| `cicd-github-actions-basic` | GitHub Actions CI/CD setup |
| `docker-compose-dev` | Local dev environment with Docker Compose |
| `git-conventional-commits` | Commit message conventions |
| `error-handling-patterns` | Result types, API errors, structured logging |

---

### Fase 1 commands *(coming soon)*

| Command | Description |
|---------|-------------|
| `prism skill add` | Add a skill interactively or from a file |
| `prism skill list` | List skills with optional status filter |
| `prism skill search <query>` | Hybrid FTS5 + semantic search |
| `prism index rebuild` | Rebuild SQLite index from markdown files |
| `prism inject` | Inject relevant skills into `.prism/injected-context.md` |
| `prism memory push/pull/status` | Sync memory with Git remote |

### Fase 2 commands *(coming soon)*

| Command | Description |
|---------|-------------|
| `prism board setup` | Launch Flux via Docker + register MCP |
| `prism board listen [--daemon]` | Start webhook listener (port 8765) |
| `prism board stop/status` | Manage the listener process |
| `prism augment [--file]` | Enrich tasks.md with PRISM context |
| `prism sync` | Push tasks.md to Flux Backlog |
| `prism task show <TASK-ID>` | Generate `current-task.md` for a task |

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
├── prism/
│   ├── cli/                   ← Click commands (one file per command)
│   ├── memory/                ← SQLite FTS5 + embeddings (Fase 1)
│   ├── agents/                ← AGENTS.md parser + launcher (Fase 3)
│   ├── board/                 ← Flux MCP client + webhook (Fase 2)
│   ├── speckit/               ← Spec-Kit bridge (Fase 2)
│   ├── utils/                 ← yaml_utils, git helpers
│   ├── templates/             ← project templates + seed skills
│   ├── config.py              ← Pydantic config schemas + loaders
│   └── project.py             ← init/attach business logic
└── tests/
    ├── test_config.py
    ├── test_init.py
    └── test_attach.py
```

## User Project Structure

```
my-project/
├── .prism/
│   ├── PRISM.md              ← canonical context (edit this — source of truth)
│   ├── AGENTS.md             ← agent team config (tool + model per role)
│   ├── project.yaml          ← metadata (name, stack, flux_project_id)
│   ├── injected-context.md   ← auto-generated by prism inject (Fase 1)
│   └── current-task.md       ← auto-generated by webhook (Fase 2)
├── CLAUDE.md                 ← generated by prism generate-context (Fase 3)
└── src/

~/.prism/
├── prism.config.yaml         ← global tool/model/role defaults
└── memory/
    ├── index.db              ← SQLite FTS5 + embedding cache (Fase 1)
    ├── skills/               ← reusable implementation patterns
    ├── gotchas/              ← documented surprises and pitfalls
    ├── decisions/            ← architecture decisions (ADRs)
    └── episodes/             ← compressed session summaries
```

---

## Development

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=prism --cov-report=term-missing

# Try a command
uv run prism init test-app --no-speckit
```

## Build Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Fase 0 — Foundation** | ✅ Done | CLI, config system, init/attach, seed skills |
| **Fase 1 — Memory Layer** | 🔲 Pending | SQLite FTS5 + embeddings, skill CRUD, inject |
| **Fase 2 — Board Integration** | 🔲 Pending | Flux Docker, webhook listener, augment/sync |
| **Fase 3 — Agent Orchestration** | 🔲 Pending | AGENTS.md parser, context generator, launcher |
| **Fase 4 — Optimizer Agent** | 🔲 Pending | Haiku-powered health checks, compression, dedup |
