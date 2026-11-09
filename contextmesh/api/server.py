"""
ContextMesh FastAPI Server
Exposes REST endpoints, MCP JSON-RPC protocol, and serves the local privacy-first dashboard.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from contextmesh.core.store import LocalContextStore
from contextmesh.core.collector import ContextCollector
from contextmesh.core.mcp_server import ContextMeshMCPServer
from contextmesh.core.models import ContextEvent, SearchQuery, EventSource

app = FastAPI(
    title="ContextMesh API",
    description="Local-First Personal Context API for AI Assistants",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = LocalContextStore()
collector = ContextCollector(store)
mcp = ContextMeshMCPServer(store)


@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "service": "ContextMesh Local Daemon",
        "db_location": str(store.db_path)
    }


@app.get("/api/stats")
def get_stats():
    return store.get_stats()


@app.get("/api/events")
def list_events(limit: int = 30, source: Optional[str] = None):
    src = EventSource(source) if source else None
    return store.get_recent(limit=limit, source=src)


@app.post("/api/events")
def create_event(event: ContextEvent):
    store.insert_event(event)
    return {"status": "saved", "id": event.id, "was_sanitized": event.is_sensitive}


@app.post("/api/query")
def search_context(query_req: SearchQuery):
    results = store.query_context(
        query=query_req.query,
        source=query_req.source,
        limit=query_req.limit,
        hours=query_req.time_window_hours
    )
    return results


@app.get("/api/mcp/tools")
def list_mcp_tools():
    return mcp.get_tool_definitions()


@app.post("/api/mcp/call")
def call_mcp_tool(payload: Dict[str, Any]):
    tool_name = payload.get("name")
    args = payload.get("arguments", {})
    return mcp.execute_tool(tool_name, args)


@app.post("/api/collect/git")
def collect_git(payload: Dict[str, str]):
    path_str = payload.get("path", ".")
    repo_path = Path(path_str).resolve()
    events = collector.collect_git_activity(repo_path)
    return {"status": "success", "collected_events": len(events), "repo": repo_path.name}


@app.post("/api/collect/notes")
def collect_notes(payload: Dict[str, str]):
    path_str = payload.get("path", ".")
    docs_dir = Path(path_str).resolve()
    count = collector.index_markdown_notes(docs_dir)
    return {"status": "success", "indexed_notes": count}


# Mount Web Dashboard
static_path = Path(__file__).resolve().parent.parent / "web" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_index():
    index_file = static_path / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ContextMesh Local Dashboard</h1>")
