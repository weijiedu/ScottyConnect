from __future__ import annotations

from pydantic import BaseModel


class CreateTaskRequest(BaseModel):
    title: str  # task name
    description: str = ""  # optional details about the task
    parent_id: str | None = None  # if set, creates a sub-task under this parent


class UpdateTaskRequest(BaseModel):
    title: str | None = None  # new title
    description: str | None = None  # new description


class ContributeRequest(BaseModel):
    contribution: str  # description of the work done for a claimed task


class TaskNode(BaseModel):
    id: str | None  # MongoDB document ID
    event_id: str  # the event this task belongs to
    parent_id: str | None  # parent task ID (None for root-level tasks)
    title: str  # task name
    description: str  # task details
    status: str  # open / claimed / completed / closed / unavailable
    assigned_to: str | None  # user ID of the person who claimed the task
    assigned_to_username: str | None = None  # name of the claimant
    contribution: str | None  # text submitted when the task was completed
    created_by: str  # user ID of the task creator
    progress: float  # completion percentage, computed by Composite Pattern
    children: list[TaskNode]  # nested sub-tasks
    created_at: str  # timestamp
    updated_at: str

class TaskTreeResponse(BaseModel):
    message: str  # result description
    tasks: list[TaskNode]  # root-level task nodes with nested children
    total_tasks: int = 0 
    code: int  # HTTP status code


class TaskResponse(BaseModel):
    message: str
    task: TaskNode | None = None
    code: int



