from enum import Enum
from typing import TypedDict

class Project(TypedDict):
    class Url(TypedDict):
        board: str
        calendar: str
        list: str

    id: str
    name: str
    is_active: str
    token: str
    last_modified: str
    is_public: str
    is_private: str
    default_swimlane: str
    show_default_swimlane: str
    description: str
    identifier: str
    url: Url

class Column(TypedDict):
    id: str
    title: str
    position: str
    project_id: str
    task_limit: str

class Task(TypedDict):
    class Color(TypedDict):
        name: str
        background: str
        border: str

    id: str
    title: str
    description: str
    date_creation: str
    color_id: str
    project_id: str
    column_id: str
    owner_id: str
    position: str
    is_active: str
    date_completed: str | None
    score: str
    date_due: str
    category_id: str
    creator_id: str
    date_modification: str
    reference: str
    date_started: str | None
    time_spent: str
    time_estimated: str
    swimlane_id: str
    date_moved: str
    recurrence_status: str
    recurrence_trigger: str
    recurrence_factor: str
    recurrence_timeframe: str
    recurrence_basedate: str
    recurrence_parent: str | None
    recurrence_child: str | None
    priority: str
    external_provider: str | None
    external_uri: str | None
    url: str
    color: Color

class Subtask(TypedDict):
    class Status(Enum):
        NOT_STARTED = 1
        IN_PROGRESS = 2
        FINISHED = 3

    id: str
    title: str
    status: str
    time_estimated: str
    time_spent: str
    task_id: str
    user_id: str
