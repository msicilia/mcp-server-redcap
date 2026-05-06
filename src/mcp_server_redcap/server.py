from mcp.server.fastmcp import FastMCP

from .tools import arms_events, files, instruments, metadata, records, surveys


def create_server() -> FastMCP:
    mcp = FastMCP("mcp-server-redcap")
    records.register(mcp)
    metadata.register(mcp)
    instruments.register(mcp)
    files.register(mcp)
    arms_events.register(mcp)
    surveys.register(mcp)
    return mcp


def main() -> None:
    mcp = create_server()
    mcp.run()
