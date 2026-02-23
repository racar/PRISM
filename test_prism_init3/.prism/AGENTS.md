project: "test_prism_init3"
version: "1.0"
created: "2026-02-22"

# Agent team configuration for test_prism_init3
# Overrides ~/.prism/prism.config.yaml for this project.
# Run: prism config show  to see resolved configuration.

agents:
  architect:
    tool: claude_code
    model: anthropic.opus
    reason: "Complex planning — needs full context window and strong reasoning"
    fallback:
      tool: claude_code
      model: anthropic.sonnet

  developer:
    tool: opencode
    model: moonshot.kimi
    reason: "Fast implementation — Kimi K2 excels at code generation"
    fallback:
      tool: claude_code
      model: anthropic.sonnet

  reviewer:
    tool: claude_code
    model: anthropic.sonnet

  memory:
    tool: claude_code
    model: anthropic.haiku

  optimizer:
    tool: claude_code
    model: anthropic.haiku
