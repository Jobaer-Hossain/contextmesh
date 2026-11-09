"""
ContextMesh Unit Tests
"""

import unittest
import tempfile
import uuid
from pathlib import Path
from contextmesh.core.models import ContextEvent, EventSource
from contextmesh.core.store import LocalContextStore
from contextmesh.core.mcp_server import ContextMeshMCPServer


class TestContextMesh(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_context.db"
        self.store = LocalContextStore(self.db_path)
        self.mcp = ContextMeshMCPServer(self.store)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_insert_and_fts_search(self):
        event = ContextEvent(
            id=str(uuid.uuid4()),
            source=EventSource.TERMINAL,
            title="Docker compose up debugging",
            content="Error with postgres database port 5432 conflict",
            tags=["docker", "postgres"]
        )
        self.store.insert_event(event)

        results = self.store.query_context("postgres port conflict")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].event_id, event.id)

    def test_secret_redaction(self):
        event = ContextEvent(
            id=str(uuid.uuid4()),
            source=EventSource.GIT,
            title="Commit with accidental token",
            content="Testing with api_key='sk-1234567890abcdef1234567890abcdef' in header",
            tags=["git"]
        )
        self.store.insert_event(event)

        recent = self.store.get_recent(limit=1)
        self.assertTrue(recent[0].snippet.find("sk-1234567890") == -1)
        self.assertIn("[REDACTED", recent[0].snippet)

    def test_mcp_tool_execution(self):
        event = ContextEvent(
            id=str(uuid.uuid4()),
            source=EventSource.NOTES,
            title="Authentication Architecture Decision",
            content="Decided to use OAuth2 PKCE with Redis token revocations",
            tags=["auth"]
        )
        self.store.insert_event(event)

        resp = self.mcp.execute_tool("query_personal_context", {"query": "OAuth2 PKCE", "limit": 2})
        self.assertEqual(resp["results_count"], 1)
        self.assertIn("OAuth2 PKCE", resp["snippets"][0]["snippet"])


if __name__ == "__main__":
    unittest.main()
