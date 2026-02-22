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

## Auto-Write Configuration (Create & Edit Files)

All PRISM agents have **AUTOMATIC PERMISSION** to create and edit files in this project. You do NOT need to ask for permission to:

- Create new source code files
- Edit existing source code files
- Update configuration files
- Modify documentation files
- Create and update test files
- Write to PRISM configuration files

## Protected Files (Require Explicit Permission for Writing)

The following files/directories ALWAYS require explicit user permission before creating or editing:

- Environment files (.env*, *.key, *.pem, *.p12)
- Secrets and credentials (secrets/**, credentials/**, *.password, *.secret)
- SSH keys (.ssh/**)
- AWS credentials (.aws/**)
- Large directories (node_modules/**, .git/**)
- Binary files and build outputs

## How to Create and Edit Files

Simply use the available tools to write files when needed:

```
Write("path/to/new_file.py", content="...")
Edit("path/to/existing_file.py", oldString="...", newString="...")
Edit("path/to/file.py", oldString="...", newString="...", replaceAll=True)
```

No need to ask for confirmation - proceed with creating and editing to implement changes, add features, fix bugs, and update documentation.

**Important Guidelines:**
- Create files in appropriate locations following project structure
- Use existing code patterns and conventions
- Add final newlines to all new files
- Keep methods under 10 lines when possible
- Follow the project's domain vocabulary for naming
