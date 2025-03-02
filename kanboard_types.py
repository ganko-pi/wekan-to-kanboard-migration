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
