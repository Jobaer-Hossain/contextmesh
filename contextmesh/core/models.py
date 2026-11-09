"""
ContextMesh Data Models
Schema definitions for personal context events, local storage, privacy rules, and MCP interfaces.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


class EventSource(str, Enum):
    TERMINAL = "terminal"
    GIT = "git"
    NOTES = "notes"
    BROWSER = "browser"
    IDE = "ide"
    SYSTEM = "system"


class ContextEvent(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source: EventSource
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_sensitive: bool = False


class SearchQuery(BaseModel):
    query: str
    source: Optional[EventSource] = None
    limit: int = 10
    time_window_hours: Optional[int] = None


class ContextSearchResult(BaseModel):
    event_id: str
    timestamp: datetime
    source: EventSource
    title: str
    snippet: str
    relevance_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PrivacyRule(BaseModel):
    id: str
    name: str
    pattern: str = Field(..., description="Regex pattern to redact or block")
    action: str = Field(..., description="'redact' or 'block'")
    enabled: bool = True
