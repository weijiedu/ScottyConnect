from __future__ import annotations

from abc import ABC, abstractmethod

from app.tasks.model.Task import Task

# Interface
class TaskComponent(ABC):
    # Uniform API for both leaf and composite tasks.

    @abstractmethod
    def get_progress(self) -> float:
        """Return completion percentage 0–100"""

    @abstractmethod
    def count_tasks(self) -> int:
        """Return total number of tasks in this subtree including itself"""

    @abstractmethod
    def collect_ids(self) -> list[str]:
        """Return every task ID in this subtree including itself"""

    @abstractmethod
    def find_by_status(self, status: str) -> list[Task]:
        """Return all tasks in this subtree that match status"""

    @abstractmethod
    def to_dict(self) -> dict:
        """Serialise the node and its subtree to a plain dict"""

    @abstractmethod
    def is_composite(self) -> bool:
        """True when the node holds children."""


class LeafTask(TaskComponent):
    # Leaf task with no sub-tasks.

    def __init__(self, task: Task) -> None:
        self.task = task

    def get_progress(self) -> float:
        if self.task.status == "completed":
            return 100.0

        return 0.0

    def count_tasks(self) -> int:
        return 1

    def collect_ids(self) -> list[str]:
        if self.task.id:
            return [self.task.id]

        return []

    def find_by_status(self, status: str) -> list[Task]:
        if self.task.status == status:
            return [self.task]

        return []

    def to_dict(self) -> dict:
        d = self.task.model_dump(mode="json")
        # add children and progress
        d["children"] = []
        d["progress"] = self.get_progress()

        return d

    def is_composite(self) -> bool:
        return False


class CompositeTask(TaskComponent):
    # Composite task contains child TaskComponents.

    def __init__(self, task: Task, children: list[TaskComponent] | None = None) -> None:
        self.task = task
        self.children: list[TaskComponent] = children or []

    def add(self, child: TaskComponent) -> None:
        self.children.append(child)

    def remove(self, child: TaskComponent) -> None:
        self.children.remove(child)

    def get_progress(self) -> float:
        if not self.children:
            if self.task.status == "completed":
                return 100.0

            return 0.0

        return sum(c.get_progress() for c in self.children) / len(self.children)

    def count_tasks(self) -> int:
        return 1 + sum(c.count_tasks() for c in self.children)

    def collect_ids(self) -> list[str]:
        if self.task.id:
            ids = [self.task.id]
        else:            
            ids = []   
        
        for c in self.children:
            ids.extend(c.collect_ids())

        return ids

    def find_by_status(self, status: str) -> list[Task]:
        if self.task.status == status: 
            result = [self.task]
        else:
            result = []
     
        for c in self.children:
            result.extend(c.find_by_status(status))

        return result

    def to_dict(self) -> dict:
        d = self.task.model_dump(mode="json")
        # add children and progress
        d["children"] = [c.to_dict() for c in self.children]
        d["progress"] = self.get_progress()

        return d

    def is_composite(self) -> bool:
        return True


def build_task_tree(tasks: list[Task]) -> list[TaskComponent]:
    # Build a list of root-level TaskComponent trees from a flat task list.
    # Groups tasks by parent_id, then recursively constructs CompositeTask / LeafTask nodes from the roots downward.
    children_map: dict[str | None, list[Task]] = {}

    for t in tasks:
        if t.parent_id not in children_map:
            children_map[t.parent_id] = []

        children_map[t.parent_id].append(t)

    def _build(task: Task) -> TaskComponent:
        child_tasks = children_map.get(task.id, [])

        if child_tasks:
            built_children = []

            for ct in child_tasks:
                built_child = _build(ct)
                built_children.append(built_child)

            return CompositeTask(task, built_children)

        return LeafTask(task)

    root_tasks = children_map.get(None, [])
    result = []

    for t in root_tasks:
        built_root = _build(t)
        result.append(built_root)

    return result
