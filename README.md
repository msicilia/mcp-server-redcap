# mcp-server-redcap

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for interacting with [REDCap](https://projectredcap.org/) (Research Electronic Data Capture) instances.

## Features

| Tool | Description |
|------|-------------|
| `export_records` | Export records with optional filters by field, record ID, or event |
| `import_records` | Import records from a JSON payload |
| `delete_records` | Delete records by ID |
| `export_report` | Export a saved REDCap report by its ID |
| `get_project_info` | Retrieve project-level information and settings |
| `get_metadata` | Export the data dictionary, optionally filtered by field or form |
| `get_instruments` | List all instruments (forms/surveys) |
| `get_instrument_event_mappings` | List arm/event/instrument mappings (longitudinal projects) |

## Installation

```bash
pip install mcp-server-redcap
```

Or with `uv`:

```bash
uvx mcp-server-redcap
```

## Configuration

The server reads connection details from environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `REDCAP_URL` | Yes | Full REDCap API endpoint URL (e.g. `https://redcap.example.org/api/`) |
| `REDCAP_TOKEN` | Yes | Project-level API token from REDCap → API → Generate Token |
| `REDCAP_VERIFY_SSL` | No | Set to `false` to skip SSL verification (default: `true`) |

Create a `.env` file in your working directory and the server will load it automatically:

```env
REDCAP_URL=https://redcap.example.org/api/
REDCAP_TOKEN=your_project_token_here
```

## Usage with Claude Code

Add the server to your Claude Code MCP configuration:

```bash
claude mcp add redcap -e REDCAP_URL=https://redcap.example.org/api/ \
                      -e REDCAP_TOKEN=your_token -- uvx mcp-server-redcap
```

Or edit `.claude/settings.json` manually:

```json
{
  "mcpServers": {
    "redcap": {
      "command": "uvx",
      "args": ["mcp-server-redcap"],
      "env": {
        "REDCAP_URL": "https://redcap.example.org/api/",
        "REDCAP_TOKEN": "your_project_token_here"
      }
    }
  }
}
```

## Development

```bash
git clone https://github.com/msicilia/mcp-server-redcap
cd mcp-server-redcap
uv sync --extra dev
```

Run the MCP inspector for interactive local testing:

```bash
uv run mcp dev src/mcp_server_redcap/server.py
```

Run the server directly (stdio transport, for use with MCP clients):

```bash
uv run mcp-server-redcap
```

## Project structure

```
src/mcp_server_redcap/
├── __init__.py
├── __main__.py          # python -m mcp_server_redcap
├── server.py            # FastMCP server factory and entry point
├── connection.py        # REDCap project connection (lazy, singleton)
└── tools/
    ├── __init__.py
    ├── records.py       # export / import / delete / report tools
    ├── metadata.py      # project info and data dictionary tools
    └── instruments.py   # instruments and event mapping tools
```

## License

MIT
