project: prism
version: "1.0"
agents:
  architect:
    tool: opencode
    model: moonshot.kimi
    reason: "Using opencode with Kimi K2.5 for architecture and planning"
  developer:
    tool: opencode
    model: moonshot.kimi
    reason: "Using opencode with Kimi K2.5 for fast implementation"
  reviewer:
    tool: opencode
    model: moonshot.kimi
    reason: "Using opencode with Kimi K2.5 for code review"
  memory:
    tool: opencode
    model: moonshot.kimi
    reason: "Using opencode with Kimi K2.5 for memory management"
  optimizer:
    tool: opencode
    model: moonshot.kimi
    reason: "Using opencode with Kimi K2.5 for memory optimization"

# File Access Permissions

## Auto-Read Configuration

All PRISM agents have **AUTOMATIC PERMISSION** to read files in this project. You do NOT need to ask for permission to read:

- Source code files (*.py, *.js, *.ts, *.tsx, *.jsx, etc.)
- Configuration files (*.json, *.yaml, *.yml, *.toml)
- Documentation files (*.md, *.txt)
- Style files (*.css, *.scss)
- HTML files
- PRISM configuration files (.prism/**/*)
- Test files (tests/**/*, specs/**/*)

## Protected Files (Require Explicit Permission)

The following files/directories ALWAYS require explicit user permission before reading:

- Environment files (.env*, *.key, *.pem, *.p12)
- Secrets and credentials (secrets/**, credentials/**, *.password, *.secret)
- SSH keys (.ssh/**)
- AWS credentials (.aws/**)
- Large directories (node_modules/**, .git/**, dist/**, build/**)
- Binary files and build outputs

## How to Read Files

Simply use the available tools to read files when needed:

```
Read("path/to/file.py")
Glob("src/**/*.ts")
Grep("pattern", path="src/")
```

No need to ask for confirmation - proceed with reading to understand the codebase.
