"""Knowledge Graph node types.

The brief names Company, Sector, Market, Event, Hypothesis, Experiment,
Feature, Gene, Research Paper, Prediction, and Recommendation as node
types ("include", not an exhaustive list). Knowledge, DatasetSnapshot, and
ResearchFinding are added since they're central, persisted entities that
constantly appear as `Provenance` inputs throughout this codebase — a
knowledge graph that couldn't represent a `KnowledgeObject` would have an
obvious hole in it.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MARKET = "market"
    EVENT = "event"
    HYPOTHESIS = "hypothesis"
    EXPERIMENT = "experiment"
    FEATURE = "feature"
    GENE = "gene"
    RESEARCH_PAPER = "research_paper"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"
    KNOWLEDGE = "knowledge"
    DATASET_SNAPSHOT = "dataset_snapshot"
    RESEARCH_FINDING = "research_finding"


class GraphNode(BaseModel):
    id: str
    version: int = 1
    node_type: NodeType
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)
