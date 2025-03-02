from typing import TypedDict

class WekanBoard(TypedDict):
    class Member(TypedDict):
        userId: str
        isAdmin: bool
        isActive: bool
        isNoComments: bool
        isCommentOnly: bool
        isWorker: bool

    class Card(TypedDict):
        class Vote(TypedDict):
            question: str
            positive: list
            negative: list
            end: str | None
            public: bool
            allowNonBoardMembers: bool

        class Poker(TypedDict):
            question: bool
            one: list
            two: list
            three: list
            five: list
            eight: list
            thirteen: list
            twenty: list
            forty: list
            oneHundred: list
            unsure: list
            end: str | None
            allowNonBoardMembers: bool

        _id: str
        title: str
        members: list
        labelIds: list
        customFields: list
        listId: str
        sort: int
        swimlaneId: str
        type: str
        cardNumber: int
        archived: bool
        parentId: str
        coverId: str
        createdAt: str
        modifiedAt: str
        dateLastActivity: str
        description: str
        requestedBy: str
        assignedBy: str
        assignees: list
        spentTime: int
        isOvertime: bool
        userId: str
        subtaskSort: int
        linkedId: str
        vote: Vote
        poker: Poker
        targetId_gantt: list
        linkType_gantt: list
        linkId_gantt: list

    class List(TypedDict):
        class WipLimit(TypedDict):
            value: int
            enabled: bool
            soft: bool

        _id: str
        title: str
        sort: int
        type: str
        starred: bool
        archived: bool
        swimlaneId: str
        createdAt: str
        width: str
        updatedAt: str
        modifiedAt: str
        wipLimit: WipLimit

    class Swimlane(TypedDict):
        _id: str
        title: str
        archived: bool
        createdAt: str
        updatedAt: str
        modifiedAt: str
        type: str
        sort: int

    class Activity(TypedDict):
        _id: str
        userId: str
        oldListId: str
        activityType: str
        listName: str
        listId: str
        cardId: str
        cardTitle: str
        swimlaneName: str
        swimlaneId: str
        oldSwimlaneId: str
        createdAt: str
        modifiedAt: str

    class Checklist(TypedDict):
        _id: str
        cardId: str
        title: str
        sort: int
        createdAt: str
        modifiedAt: str
        userId: str

    class ChecklistItem(TypedDict):
        _id: str
        title: str
        checklistId: str
        cardId: str
        sort: int
        isFinished: bool
        createdAt: str
        modifiedAt: str
        userId: str

    class User(TypedDict):
        _id: str
        username: str
        profile: any

    _format: str
    _id: str
    title: str
    permission: str
    slug: str
    archived: bool
    createdAt: str
    modifiedAt: str
    members: list[Member]
    color: str
    allowsCardCounterList: bool
    allowsBoardMemberList: bool
    subtasksDefaultBoardId: str | None
    subtasksDefaultListId: str | None
    dateSettingsDefaultBoardId: str | None
    dateSettingsDefaultListId: str | None
    allowsSubtasks: bool
    allowsAttachments: bool
    allowsChecklists: bool
    allowsComments: bool
    allowsDescriptionTitle: bool
    allowsDescriptionText: bool
    allowsDescriptionTextOnMinicard: bool
    allowsCardNumber: bool
    allowsActivities: bool
    allowsLabels: bool
    allowsCreator: bool
    allowsAssignee: bool
    allowsMembers: bool
    allowsRequestedBy: bool
    allowsCardSortingByNumber: bool
    allowsShowLists: bool
    allowsAssignedBy: bool
    allowsReceivedDate: bool
    allowsStartDate: bool
    allowsEndDate: bool
    allowsDueDate: bool
    presentParentTask: str
    isOvertime: bool
    type: str
    sort: int
    archivedAt: str
    cards: list[Card]
    lists: list[List]
    swimlanes: list[Swimlane]
    activities: list[Activity]
    customFields: list
    attachments: list
    comments: list
    rules: list
    checklists: list[Checklist]
    checklistItems: list[ChecklistItem]
    subtaskItems: list
    triggers: list
    actions: list
    users: list[User]
