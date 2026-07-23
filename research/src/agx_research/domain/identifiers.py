"""Consistent ID minting for every versioned entity in the system."""

from __future__ import annotations

import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
