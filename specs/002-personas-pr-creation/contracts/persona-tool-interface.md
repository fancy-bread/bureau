# Contract: Persona Tool Interface

**Feature**: Bureau Personas and PR Creation | **Date**: 2026-04-18

Defines the tools available to the Builder (and optionally Planner) personas via Anthropic tool use.
All tools are implemented in `bureau/tools/` and serialised to Anthropic tool schema at call time.

---

## Tools

### `read_file`

Read the contents of a file in the target repo.

```json
{
  "name": "read_file",
  "description": "Read the full contents of a file. Path is relative to the repo root.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "File path relative to repo root (e.g. src/main.py)"
      }
    },
    "required": ["path"]
  }
}
```

**Returns**: File contents as a string, or an error message if the file does not exist.

---

### `write_file`

Write (overwrite) a file in the target repo. Full file content must be provided — no partial writes.

```json
{
  "name": "write_file",
  "description": "Write full content to a file. Creates the file if it does not exist. Always provide the complete file content.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "File path relative to repo root"
      },
      "content": {
        "type": "string",
        "description": "Complete file content to write"
      }
    },
    "required": ["path", "content"]
  }
}
```

**Returns**: `"ok"` on success, or an error message.
**Constraint**: Path must be within the repo root. Writes outside repo root are rejected.

---

### `list_directory`

List files and directories at a path within the target repo.

```json
{
  "name": "list_directory",
  "description": "List files and subdirectories at the given path.",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Directory path relative to repo root. Use '.' for root."
      }
    },
    "required": ["path"]
  }
}
```

**Returns**: Newline-separated list of entries with type prefix: `[file]` or `[dir]`.

---

### `run_command`

Execute a shell command in the target repo. Used by the Builder to run tests, builds, and other verification steps.

```json
{
  "name": "run_command",
  "description": "Run a shell command in the repo root. Returns stdout, stderr, and exit code. Use for install, build, and test commands only.",
  "input_schema": {
    "type": "object",
    "properties": {
      "command": {
        "type": "string",
        "description": "Shell command to execute (e.g. 'pytest tests/', 'npm test')"
      }
    },
    "required": ["command"]
  }
}
```

**Returns**: JSON object: `{"stdout": "...", "stderr": "...", "exit_code": 0}`
**Constraints**:
- `cwd` is always the repo root
- Timeout: `command_timeout` seconds (default 300)
- Stdout/stderr truncated to 4000 characters each (most recent output retained)
- The Builder MUST use this tool to run `test_cmd`; the exit code determines pass/fail

---

## Tool Availability by Persona

| Tool | Planner | Builder | Critic |
|------|---------|---------|--------|
| `read_file` | ✅ | ✅ | ✅ |
| `write_file` | — | ✅ | — |
| `list_directory` | ✅ | ✅ | — |
| `run_command` | — | ✅ | — |

The Critic receives the Builder's summary from run memory rather than reading files directly. The Planner reads relevant source files to understand the codebase structure.

---

## Tool Execution Contract

- All tools execute synchronously within the node's event loop
- Tool errors (file not found, command timeout) are returned as error strings, not exceptions — the persona decides how to handle them
- `write_file` calls are committed to the filesystem immediately; there is no transaction or rollback
- `run_command` inherits the shell environment of the bureau process (PATH, credentials, etc.)
