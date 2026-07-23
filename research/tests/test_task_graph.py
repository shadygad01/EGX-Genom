import pytest

from agx_research.orchestration.task_graph import Task, TaskGraph, TaskStatus


def test_runs_tasks_in_dependency_order():
    graph = TaskGraph()
    order: list[str] = []

    graph.add_task(Task(id="a", name="a"), lambda deps: order.append("a"))
    graph.add_task(Task(id="b", name="b", dependencies=["a"]), lambda deps: order.append("b"))
    graph.add_task(Task(id="c", name="c", dependencies=["b"]), lambda deps: order.append("c"))

    graph.run_all()

    assert order == ["a", "b", "c"]


def test_rejects_unknown_dependency():
    graph = TaskGraph()
    with pytest.raises(ValueError):
        graph.add_task(Task(id="a", name="a", dependencies=["does-not-exist"]), lambda deps: None)


def test_detects_cycle():
    graph = TaskGraph()
    # Build a 2-cycle by hand-editing dependencies after construction
    # (add_task validates against already-added tasks, so a direct cycle
    # can't be added through the public API -- but a task referencing
    # itself can).
    task = Task(id="a", name="a", dependencies=["a"])
    graph._tasks["a"] = task  # noqa: SLF001 -- constructing a cycle deliberately for the test
    graph._runners["a"] = lambda deps: None  # noqa: SLF001
    with pytest.raises(ValueError):
        graph.topological_order()


def test_task_records_status_and_timing():
    graph = TaskGraph()
    task = Task(id="a", name="a")
    graph.add_task(task, lambda deps: 42)

    result_task = graph.run_task("a")

    assert result_task.status == TaskStatus.SUCCEEDED
    assert result_task.started_at is not None
    assert result_task.completed_at is not None
    assert result_task.reproducibility_hash is not None
    assert graph.result("a") == 42


def test_failed_task_records_error_and_reraises():
    graph = TaskGraph()

    def _boom(deps):
        raise RuntimeError("kaboom")

    task = Task(id="a", name="a")
    graph.add_task(task, _boom)

    with pytest.raises(RuntimeError):
        graph.run_task("a")

    assert task.status == TaskStatus.FAILED
    assert task.error == "kaboom"


def test_task_can_be_rerun_independently():
    graph = TaskGraph()
    calls = {"count": 0}

    def _increment(deps):
        calls["count"] += 1
        return calls["count"]

    graph.add_task(Task(id="a", name="a"), _increment)
    graph.run_task("a")
    assert graph.result("a") == 1

    graph.run_task("a")
    assert graph.result("a") == 2


def test_downstream_task_receives_upstream_result():
    graph = TaskGraph()
    graph.add_task(Task(id="a", name="a"), lambda deps: 10)
    graph.add_task(Task(id="b", name="b", dependencies=["a"]), lambda deps: deps["a"] * 2)

    graph.run_all()

    assert graph.result("b") == 20
