from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agx_research.graph.nodes import NodeType


class GraphEdge(BaseModel):
    id: str
    version: int = 1
    source_id: str
    source_type: NodeType
    target_id: str
    target_type: NodeType
    relationship: str
    metadata: dict[str, Any] = Field(default_factory=dict)
