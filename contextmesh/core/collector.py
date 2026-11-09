"""
ContextMesh Context Collectors
Gathers developer activity from Git repositories, terminal logs, and local markdown documentation.
"""

import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from contextmesh.core.models import ContextEvent, EventSource
from contextmesh.core.store import LocalContextStore


class ContextCollector:

    def __init__(self, store: LocalContextStore):
        self.store = store

    def collect_git_activity(self, repo_path: Path) -> List[ContextEvent]:
        """Inspects git status, active branch, and recent commit history."""
        events: List[ContextEvent] = []
        if not (repo_path / ".git").exists():
            return events

        try:
            # Active branch
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(repo_path),
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()

            # Recent commits
            log_output = subprocess.check_output(
                ["git", "log", "-n", "3", "--pretty=format:%h - %s (%cr)"],
                cwd=str(repo_path),
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()

            # Status / dirty diffs
            status_output = subprocess.check_output(
                ["git", "status", "--short"],
                cwd=str(repo_path),
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()

            content = f"Branch: {branch}\nRecent Commits:\n{log_output}\n\nWorking Directory Changes:\n{status_output or 'Clean'}"

            event = ContextEvent(
                id=f"git-{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(),
                source=EventSource.GIT,
                title=f"Git Repo Status ({repo_path.name} on {branch})",
                content=content,
                metadata={"repo_name": repo_path.name, "branch": branch},
                tags=["git", "vcs", repo_path.name]
            )
            self.store.insert_event(event)
            events.append(event)
        except Exception as e:
            pass

        return events

    def record_terminal_command(self, command: str, output: str = "", exit_code: int = 0) -> ContextEvent:
        """Records a terminal execution snippet."""
        event = ContextEvent(
            id=f"term-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            source=EventSource.TERMINAL,
            title=f"Terminal Command: {command[:40]}",
            content=f"$ {command}\nExit Code: {exit_code}\nOutput:\n{output[:500]}",
            metadata={"command": command, "exit_code": exit_code},
            tags=["terminal", "cli"]
        )
        self.store.insert_event(event)
        return event

    def index_markdown_notes(self, docs_dir: Path) -> int:
        """Indexes local markdown documentation and developer notes."""
        indexed = 0
        if not docs_dir.exists():
            return 0

        for md in docs_dir.rglob("*.md"):
            try:
                content = md.read_text(encoding="utf-8", errors="replace")
                if len(content.strip()) < 10:
                    continue
                event = ContextEvent(
                    id=f"doc-{uuid.uuid4().hex[:8]}",
                    timestamp=datetime.fromtimestamp(md.stat().st_mtime),
                    source=EventSource.NOTES,
                    title=f"Note: {md.name}",
                    content=content[:2000],  # index first 2KB of note
                    metadata={"file_path": str(md), "size_bytes": md.stat().st_size},
                    tags=["notes", "docs", md.stem]
                )
                self.store.insert_event(event)
                indexed += 1
            except Exception:
                pass
        return indexed
