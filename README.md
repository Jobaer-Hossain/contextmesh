# ContextMesh

> **Local-first developer context API and Model Context Protocol (MCP) server.**  
> Indexes your local Git diffs, terminal history, and markdown notes in a private SQLite database with automated secret redaction.

Modern software development often suffers from fragmented context: past terminal commands, switched Git branches, and design notes scattered across markdown scratchpads.

ContextMesh runs as a lightweight, 100% local daemon. It continuously indexes your developer activity into an embedded SQLite database (using FTS5 full-text indexing), intercepts and redacts sensitive credentials (API keys, passwords, bearer tokens), and exposes an MCP server interface so client tooling can query:
> *"What command did I run earlier that fixed the Postgres port conflict?"*  
> *"Which file had the OAuth token revocation logic?"*

---

## Key Features

1. **100% Local-First & Zero Cloud Leakage**: All indexes and metadata reside in a local SQLite database (`~/.contextmesh/context.db`). No raw context ever leaves your device.
2. **Automated Secret & Credential Redaction**: Regular expression filters automatically redact provider API keys, tokens, and passwords before indexing.
3. **Model Context Protocol (MCP) Ready**: Built-in MCP endpoints (`query_personal_context`, `get_recent_developer_activity`) allow seamless connection to IDE extensions, local agents, and developer tooling.
4. **Developer Activity Collectors**: Built-in collectors for Git repositories (active branch, recent commits, dirty working trees), terminal command outputs, and local Markdown documentation.
5. **Interactive Web Console & CLI**: Search through past context, inspect redaction stats, and trigger manual indexers.

---

## Quickstart

### Installation
```bash
git clone https://github.com/Jobaer-Hossain/contextmesh.git
cd contextmesh

pip install -r requirements.txt
```

### CLI Usage
```bash
# Index current Git repository and Markdown docs
python -m contextmesh.cli sync

# Search personal context
python -m contextmesh.cli search "postgres database"

# Inspect database statistics and redacted secrets count
python -m contextmesh.cli stats
```

### Web Console & MCP Server
```bash
python run.py --port 8002
```
Open **`http://localhost:8002`** in your browser to explore the local context timeline and search playground.

---

## MCP Server Configuration

To connect ContextMesh to **Claude Desktop**, add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "contextmesh": {
      "command": "python",
      "args": ["-m", "contextmesh.cli", "mcp"]
    }
  }
}
```

---

## Automated Tests
```bash
python -m unittest tests.test_contextmesh
```

---

## License
MIT License. Free for open-source and commercial use.
