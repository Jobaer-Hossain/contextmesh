"""
ContextMesh Local SQLite & Privacy-Preserving FTS Engine
Stores personal developer activity locally with automated credential & secret redaction.
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from contextmesh.core.models import ContextEvent, EventSource, ContextSearchResult, PrivacyRule


DEFAULT_REDACTION_PATTERNS = [
    (r"(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", "[REDACTED_SECRET]"),
    (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]"),
    (r"ghp_[a-zA-Z0-9]{30,}", "[REDACTED_GITHUB_TOKEN]"),
    (r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", "Bearer [REDACTED_TOKEN]")
]


class LocalContextStore:

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".contextmesh" / "context.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            # Events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    tags_json TEXT,
                    is_sensitive INTEGER DEFAULT 0
                )
            """)
            
            # FTS5 full-text search table
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                    title,
                    content,
                    content='events',
                    content_rowid='rowid'
                )
            """)

            # Privacy rules table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS privacy_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    action TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1
                )
            """)

    def sanitize_content(self, text: str) -> Tuple[str, bool]:
        """Redacts secrets, credentials, and passwords before storing."""
        modified = text
        redacted = False
        for pattern, replacement in DEFAULT_REDACTION_PATTERNS:
            if re.search(pattern, modified, re.IGNORECASE):
                modified = re.sub(pattern, replacement, modified, flags=re.IGNORECASE)
                redacted = True
        return modified, redacted

    def insert_event(self, event: ContextEvent) -> bool:
        clean_content, was_redacted = self.sanitize_content(event.content)
        event.content = clean_content
        if was_redacted:
            event.is_sensitive = True

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO events 
                (id, timestamp, source, title, content, metadata_json, tags_json, is_sensitive)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.timestamp.isoformat(),
                    event.source.value,
                    event.title,
                    event.content,
                    json.dumps(event.metadata),
                    json.dumps(event.tags),
                    1 if event.is_sensitive else 0
                )
            )
            # Update FTS
            conn.execute(
                "INSERT INTO events_fts(rowid, title, content) SELECT rowid, title, content FROM events WHERE id = ?",
                (event.id,)
            )
        return True

    def query_context(self, query: str, source: Optional[EventSource] = None, limit: int = 10, hours: Optional[int] = None) -> List[ContextSearchResult]:
        """Queries local events using FTS5 with fallback substring matching."""
        results: List[ContextSearchResult] = []
        with self._get_connection() as conn:
            # Clean search terms for FTS syntax
            clean_terms = re.sub(r"[^\w\s]", "", query).strip()
            if not clean_terms:
                return self.get_recent(limit=limit, source=source)

            fts_query = " OR ".join([f'"{term}"*' for term in clean_terms.split() if term])

            sql = """
                SELECT e.id, e.timestamp, e.source, e.title, e.content, e.metadata_json, bm25(events_fts) as rank
                FROM events_fts
                JOIN events e ON events_fts.rowid = e.rowid
                WHERE events_fts MATCH ?
            """
            params: List[Any] = [fts_query]

            if source:
                sql += " AND e.source = ?"
                params.append(source.value)

            if hours:
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                sql += " AND e.timestamp >= ?"
                params.append(cutoff)

            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)

            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                # Fallback to standard LIKE query
                sql_fallback = "SELECT id, timestamp, source, title, content, metadata_json, 1.0 as rank FROM events WHERE (title LIKE ? OR content LIKE ?)"
                params_fallback = [f"%{query}%", f"%{query}%"]
                if source:
                    sql_fallback += " AND source = ?"
                    params_fallback.append(source.value)
                sql_fallback += " ORDER BY timestamp DESC LIMIT ?"
                params_fallback.append(limit)
                rows = conn.execute(sql_fallback, params_fallback).fetchall()

            for r in rows:
                content = r["content"]
                snippet = content[:180] + ("..." if len(content) > 180 else "")
                results.append(ContextSearchResult(
                    event_id=r["id"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    source=EventSource(r["source"]),
                    title=r["title"],
                    snippet=snippet,
                    relevance_score=round(abs(float(r["rank"])), 2) if "rank" in r.keys() else 1.0,
                    metadata=json.loads(r["metadata_json"] or "{}")
                ))

        return results

    def get_recent(self, limit: int = 20, source: Optional[EventSource] = None) -> List[ContextSearchResult]:
        results: List[ContextSearchResult] = []
        with self._get_connection() as conn:
            sql = "SELECT id, timestamp, source, title, content, metadata_json FROM events"
            params = []
            if source:
                sql += " WHERE source = ?"
                params.append(source.value)
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            for r in rows:
                content = r["content"]
                snippet = content[:180] + ("..." if len(content) > 180 else "")
                results.append(ContextSearchResult(
                    event_id=r["id"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    source=EventSource(r["source"]),
                    title=r["title"],
                    snippet=snippet,
                    relevance_score=1.0,
                    metadata=json.loads(r["metadata_json"] or "{}")
                ))
        return results

    def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            sources = {}
            for r in conn.execute("SELECT source, COUNT(*) as c FROM events GROUP BY source").fetchall():
                sources[r["source"]] = r["c"]
            redacted_count = conn.execute("SELECT COUNT(*) FROM events WHERE is_sensitive = 1").fetchone()[0]
            return {
                "total_events": total,
                "sources_breakdown": sources,
                "redacted_events_count": redacted_count,
                "db_size_kb": round(self.db_path.stat().st_size / 1024, 1) if self.db_path.exists() else 0
            }
