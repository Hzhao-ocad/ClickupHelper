from enum import Enum


class OperationType(str, Enum):
    CREATE_TASK = "create_task"
    UPDATE_TASK = "update_task"
    SET_DUE_DATE = "set_due_date"
    SET_PRIORITY = "set_priority"
    ASSIGN_TASK = "assign_task"
    ADD_COMMENT = "add_comment"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    UPDATE_CALENDAR_EVENT = "update_calendar_event"


PRIORITY_MAP = {
    "urgent": 1,
    "high": 2,
    "normal": 3,
    "low": 4,
}
