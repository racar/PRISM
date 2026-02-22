# Getting Started with PRISM

Walk through using PRISM for a new development project end-to-end.

## Prerequisites

- **Python 3.11+** with `uv`
- **Docker** running + `flux-mcp` image built/pulled
- **Claude Code** installed (for agent launching)

## Quick Start

```bash
# 1. Initialize project
prism init my-project
cd my-project

# 2. Build the skill index
prism index rebuild

# 3. Inject relevant skills into project context
prism inject

# 4. Set up Flux board (requires Docker + flux-mcp image)
prism board setup

# 5. Start webhook listener (background)
prism board listen --daemon

# 6. Create tasks — either via Spec-Kit or manually write tasks.md
#    Format:
#      ## Epic: Feature Name
#      ### Task 1: Do something
#      - [ ] Criterion A
#      - [ ] Criterion B

# 7. Augment tasks with PRISM memory context
prism augment

# 8. Sync tasks to Flux backlog
prism sync

# 9. Open Flux board at http://localhost:9000 — review & approve tasks

# 10. Launch an agent
prism start --role architect     # for planning/design
prism start --role developer     # for implementation
```

## What each step does

| Step | Command | Effect |
|------|---------|--------|
| Init | `prism init <name>` | Creates `.prism/` with `PRISM.md`, `AGENTS.md`, `project.yaml`; seeds `~/.prism/memory/` with 7 starter skills |
| Attach | `prism attach` | Same as init but for existing projects |
| Index | `prism index rebuild` | Builds SQLite FTS5 index from `~/.prism/memory/` skills/gotchas/decisions |
| Inject | `prism inject` | Ranks relevant skills and writes `.prism/injected-context.md` |
| Board setup | `prism board setup` | Starts Flux Docker container, registers MCP, creates project, configures webhook |
| Listen | `prism board listen --daemon` | Runs webhook server on :8765; auto-generates `current-task.md` when tasks move to "doing" |
| Augment | `prism augment` | Adds PRISM Context blocks to tasks.md -> `tasks.prism.md` |
| Sync | `prism sync` | Pushes parsed epics/tasks into Flux backlog (idempotent, detects changes) |
| Start | `prism start --role <role>` | Generates context file + launches agent tool (Claude Code, Cursor, etc.) |

## Day-to-day workflow

1. Move a task to **"doing"** in Flux -> webhook generates `.prism/current-task.md`
2. Agent reads `current-task.md` for full context (task + skills + gotchas)
3. Agent implements, then moves task to **"done"**
4. Add new skills/gotchas learned: `prism skill add`
5. Rebuild index: `prism index rebuild`
6. Sync memory to git: `prism memory push`

## Useful commands

```bash
prism board status          # Check listener state
prism board stop            # Stop listener
prism resume                # Show project overview + suggested next action
prism skill search "auth"   # Find relevant skills
prism health                # Check project health
prism sync --dry-run        # Preview sync without API calls
```
