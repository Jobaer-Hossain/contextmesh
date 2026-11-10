"""
ContextMesh Model Context Protocol (MCP) Interface
Exposes local developer context tools via Model Context Protocol (MCP) for IDE extensions and tooling.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from contextmesh.core.store import LocalContextStore
from contextmesh.core.collector import ContextCollector
from contextmesh.core.models import EventSource


class ContextMeshMCPServer:

    def __init__(self, store: LocalContextStore):
        self.store = store
        self.collector = ContextCollector(store)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns standard Model Context Protocol (MCP) tool schema definitions."""
        return [
            {
                "name": "query_personal_context",
                "description": "Searches the developer's local private context history (Git diffs, terminal commands, notes, and activity) for past actions, bugs, commands, and decisions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language question or search query (e.g. 'What was the error with postgres migration?')"
                        },
                        "source": {
                            "type": "string",
                            "enum": ["terminal", "git", "notes", "browser", "ide"],
                            "description": "Optional filter by source type"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 5,
                            "description": "Maximum number of context snippets to return"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_recent_developer_activity",
                "description": "Retrieves chronological recent activity to understand what the user was recently working on.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "description": "Number of recent events"
                        }
                    }
                }
            }
        ]

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the requested MCP tool."""
        if tool_name == "query_personal_context":
            query = arguments.get("query", "")
            source_str = arguments.get("source")
            source = EventSource(source_str) if source_str else None
            limit = int(arguments.get("limit", 5))

            results = self.store.query_context(query=query, source=source, limit=limit)
            return {
                "results_count": len(results),
                "snippets": [
                    {
                        "source": r.source.value,
                        "title": r.title,
                        "timestamp": r.timestamp.isoformat(),
                        "snippet": r.snippet,
                        "metadata": r.metadata
                    }
                    for r in results
                ]
            }

        elif tool_name == "get_recent_developer_activity":
            limit = int(arguments.get("limit", 10))
            recent = self.store.get_recent(limit=limit)
            return {
                "events_count": len(recent),
                "timeline": [
                    {
                        "source": r.source.value,
                        "title": r.title,
                        "timestamp": r.timestamp.isoformat(),
                        "snippet": r.snippet
                    }
                    for r in recent
                ]
            }

        return {"error": f"Unknown tool: {tool_name}"}
