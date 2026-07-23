"""The execution DAG a Research Session runs.

Every `Task` records what it depends on, what it consumed and produced,
its status and timing, and a reproducibility hash of the inputs it actually
ran against — so any single task can be rerun independently later and its
result compared against what was recorded, without rerunning the whole
graph.

Deliberately in-process and synchronous: no distributed execution, no
retries. Scheduling real parallel/distributed execution is a real future
need, but it extends this object rather than requiring a rewrite — the
dependency/status/artifact bookkeeping already matches what a scheduler
would need.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task(BaseModel):
    """A node in the execution graph. `inputs`/`outputs` name artifact ids
    (or, before execution, a human-readable description of what's expected).
    """

    id: str
    version: int = 1
    name: str
    dependencies: list[str] = Field(default_factory=list)
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    reproducibility_hash: str | None = None
    error: str | None = None


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def hash_inputs(inputs: dict[str, Any]) -> str:
    """A deterministic hash of whatever a task actually consumed, for
    reproducibility metadata. Falls back to `str()` for anything that isn't
    JSON-serializable directly or via pydantic's `model_dump`.
    """
    canonical = json.dumps(_to_jsonable(inputs), sort_keys=True, default=str)
    return "inputs_" + hashlib.sha256(canonical.encode()).hexdigest()[:16]


class TaskGraph:
    """Runs `Task`s in dependency order, and lets any single one be rerun."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._runners: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._results: dict[str, Any] = {}

    def add_task(self, task: Task, runner: Callable[[dict[str, Any]], Any]) -> None:
        for dependency_id in task.dependencies:
            if dependency_id not in self._tasks:
                raise ValueError(f"Task {task.id} depends on unknown task {dependency_id}")
        self._tasks[task.id] = task
        self._runners[task.id] = runner

    def topological_order(self) -> list[str]:
        remaining_deps = {tid: set(t.dependencies) for tid, t in self._tasks.items()}
        order: list[str] = []
        ready = sorted(tid for tid, deps in remaining_deps.items() if not deps)

        while ready:
            task_id = ready.pop(0)
            order.append(task_id)
            for other_id, deps in remaining_deps.items():
                if task_id in deps:
                    deps.discard(task_id)
                    if not deps and other_id not in order and other_id not in ready:
                        ready.append(other_id)
            ready.sort()

        if len(order) != len(self._tasks):
            raise ValueError("Task graph has a cycle")
        return order

    def run_task(self, task_id: str) -> Task:
        """(Re)run a single task using whatever results its dependencies currently hold.

        Independently rerunnable: as long as `task_id`'s dependencies have
        already produced results (from an earlier `run_task`/`run_all`),
        this can be called again on its own — e.g. to reproduce or refresh
        just that one step.
        """
        task = self._tasks[task_id]
        dependency_results = {dep: self._results[dep] for dep in task.dependencies}

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        try:
            result = self._runners[task_id](dependency_results)
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = datetime.now()
            raise
        self._results[task_id] = result
        task.status = TaskStatus.SUCCEEDED
        task.reproducibility_hash = hash_inputs(dependency_results)
        task.completed_at = datetime.now()
        return task

    def run_all(self) -> dict[str, Task]:
        for task_id in self.topological_order():
            self.run_task(task_id)
        return dict(self._tasks)

    def result(self, task_id: str) -> Any:
        return self._results[task_id]

    def tasks(self) -> list[Task]:
        return list(self._tasks.values())
