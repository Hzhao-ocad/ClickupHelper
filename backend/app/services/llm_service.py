import json
import logging
from datetime import datetime
from uuid import uuid4

from openai import OpenAI

from app.models.operations import PRIORITY_MAP
from app.utils.date_utils import resolve_relative_dates

logger = logging.getLogger(__name__)

# ── Tool definitions for OpenAI function-calling format ───────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task in ClickUp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Task name/title"},
                    "description": {"type": "string", "description": "Task description or details"},
                    "list_name": {"type": "string", "description": "Name of the ClickUp list to place the task in"},
                    "priority": {"type": "string", "enum": ["urgent", "high", "normal", "low"], "description": "Task priority"},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "assignee_name": {"type": "string", "description": "Name of person to assign"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to apply"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update an existing task's fields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Task name or ID to identify the task"},
                    "name": {"type": "string", "description": "New task name"},
                    "description": {"type": "string", "description": "New task description"},
                    "priority": {"type": "string", "enum": ["urgent", "high", "normal", "low"]},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "assignee_name": {"type": "string", "description": "New assignee name"},
                    "status": {"type": "string", "description": "New status name"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to apply"},
                },
                "required": ["task_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_due_date",
            "description": "Set or change the due date on a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Task name or ID"},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                },
                "required": ["task_identifier", "due_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_priority",
            "description": "Set or change the priority on a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Task name or ID"},
                    "priority": {"type": "string", "enum": ["urgent", "high", "normal", "low"]},
                },
                "required": ["task_identifier", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_task",
            "description": "Assign a team member to a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Task name or ID"},
                    "assignee_name": {"type": "string", "description": "Name of person to assign"},
                },
                "required": ["task_identifier", "assignee_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_comment",
            "description": "Add a comment to a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Task name or ID"},
                    "comment_text": {"type": "string", "description": "Comment text to add"},
                },
                "required": ["task_identifier", "comment_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a calendar event or meeting as a task with date/time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "date": {"type": "string", "description": "Event date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "Event time in HH:MM format"},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format (alternative to duration)"},
                    "list_name": {"type": "string", "description": "List to place event task in"},
                    "description": {"type": "string", "description": "Event description"},
                    "priority": {"type": "string", "enum": ["urgent", "high", "normal", "low"]},
                    "assignee_name": {"type": "string", "description": "Name of person to assign"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to apply"},
                },
                "required": ["title", "date", "list_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "Update an existing calendar event's fields (title, date, time, duration, description, priority, list, assignee).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Event/task name or ID to identify it"},
                    "title": {"type": "string", "description": "New event title"},
                    "date": {"type": "string", "description": "New event date in YYYY-MM-DD format"},
                    "time": {"type": "string", "description": "New event time in HH:MM format"},
                    "duration_minutes": {"type": "integer", "description": "New duration in minutes"},
                    "end_date": {"type": "string", "description": "New end date in YYYY-MM-DD format"},
                    "description": {"type": "string", "description": "New event description"},
                    "priority": {"type": "string", "enum": ["urgent", "high", "normal", "low"]},
                    "list_name": {"type": "string", "description": "Move event to a different list"},
                    "assignee_name": {"type": "string", "description": "New assignee name"},
                    "status": {"type": "string", "description": "New status name"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to apply"},
                },
                "required": ["task_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_clarification",
            "description": "Request clarification from the user when the request is ambiguous or missing required information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "question": {"type": "string"},
                                "answer_type": {"type": "string", "enum": ["text", "list_selection", "date", "person"]},
                                "options": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["id", "question", "answer_type"],
                        },
                    },
                },
                "required": ["questions"],
            },
        },
    },
]


class LLMService:
    def __init__(self, config):
        self.client = OpenAI(
            api_key=config.deepseek_api_key,
            base_url=config.deepseek_base_url,
        )
        self.model = config.deepseek_model
        self.max_tokens = config.deepseek_max_tokens
        self.temperature = config.deepseek_temperature

    def build_system_prompt(self, workspace_context: dict | None) -> str:
        now = datetime.now()
        dates = resolve_relative_dates(now.date())

        date_examples = "\n".join(f'  "{k}" -> {v}' for k, v in dates.items())

        prompt_parts = [
            "You are a ClickUp Voice Assistant. Your job is to interpret natural language commands and produce structured ClickUp API operations.",
            "The user may speak in English, Chinese (中文), or a mixture of both (code-switching). Understand and process all languages seamlessly.",
            "用户在可能使用英文、中文或中英混合的方式交流。请无缝理解并处理所有语言。",
            f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Current day: {now.strftime('%A')}",
            "",
            "## Available workspace context:",
        ]

        if workspace_context and not workspace_context.get("error"):
            prompt_parts.append(json.dumps(workspace_context, indent=2, ensure_ascii=False))
        else:
            prompt_parts.append("No workspace context available. Ask the user for list and assignee details.")

        prompt_parts.extend([
            "",
            "## Behavior rules:",
            "1. ALWAYS use the provided functions. Never respond with free text.",
            "2. When any reference is ambiguous or a required field is missing, use the request_clarification function. Never guess.",
            "3. Resolve relative dates ('tomorrow', 'next Tuesday', 'next week', '明天', '下周二', '下周') using the current date above and the date reference below.",
            "4. Match user references like 'the backend project' or '后端项目' against workspace context names (list names, space names, member names). If no clear match, ask.",
            "5. A single voice input may require MULTIPLE operations (batch mode). Create one function call per operation.",
            "6. For priorities: urgent=1, high=2, normal=3, low=4. Use the string labels.",
            "7. When creating a task, if the user doesn't specify a list, use the request_clarification function to ask.",
            "8. Task names, descriptions, and comments should preserve the user's original language. Do not translate between Chinese and English unless the user explicitly asks.",
            "",
            "## Date resolution reference (current date is the baseline):",
            date_examples,
        ])

        return "\n".join(prompt_parts)

    def interpret(self, transcript: str, workspace_context: dict | None, conversation_history: list | None = None):
        system_prompt = self.build_system_prompt(workspace_context)

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": transcript})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return self._parse_response(response, workspace_context)

    def _parse_response(self, response, workspace_context: dict | None):
        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            return {
                "requires_clarification": True,
                "clarification_questions": [{"id": "general", "question": "I couldn't understand that request. Could you rephrase it?", "answer_type": "text"}],
            }

        operations = []
        clarification_questions = []

        for tc in msg.tool_calls:
            name = tc.function.name
            args = self._safe_json_parse(tc.function.arguments, name)

            if name == "request_clarification":
                clarification_questions.extend(args.get("questions", []))
                continue

            op = self._build_operation(name, args, workspace_context)
            operations.append(op)

        if clarification_questions:
            return {
                "requires_clarification": True,
                "clarification_questions": clarification_questions,
            }

        return {
            "requires_clarification": False,
            "operations": operations,
        }

    def _safe_json_parse(self, json_str: str, tool_name: str = "unknown") -> dict:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(
                "Malformed JSON from LLM for tool '%s' (len=%d), attempting recovery. Raw: %.300s",
                tool_name, len(json_str), json_str,
            )
            depth = 0
            start = json_str.find("{")
            if start == -1:
                logger.error("No JSON object found in function arguments for '%s'", tool_name)
                return {}
            for i, ch in enumerate(json_str[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        extracted = json_str[start : i + 1]
                        try:
                            return json.loads(extracted)
                        except json.JSONDecodeError:
                            logger.exception("Recovery parse also failed for '%s'", tool_name)
                            return {}
            logger.error("Unbalanced braces in function arguments for '%s'", tool_name)
            return {}

    def _build_operation(self, name: str, args: dict, workspace_context: dict | None) -> dict:
        op_id = str(uuid4())

        # Resolve name-based references to IDs
        params = dict(args)

        # Resolve list_name -> list_id
        if "list_name" in params:
            list_name = params.pop("list_name")
            resolved = self._resolve_list(list_name, workspace_context)
            params["list_id"] = resolved or list_name
            params["list_name"] = list_name

        # Resolve assignee_name -> assignee_id
        if "assignee_name" in params:
            assignee = params.pop("assignee_name")
            resolved = self._resolve_member(assignee, workspace_context)
            params["assignee_id"] = resolved or assignee
            params["assignee_name"] = assignee

        # Map priority
        if "priority" in params:
            p = str(params["priority"]).lower()
            params["priority"] = PRIORITY_MAP.get(p, 3)
            params["priority_label"] = p

        # Build a human-readable summary
        summary = self._build_summary(name, params)

        return {
            "id": op_id,
            "type": name,
            "summary": summary,
            "params": params,
            "confidence": 1.0,
        }

    def _resolve_list(self, list_name: str, ctx: dict | None) -> str | None:
        if not ctx:
            return None
        name_lower = list_name.lower()
        for space in ctx.get("spaces", []):
            for lst in space.get("lists", []):
                if name_lower in lst["name"].lower():
                    return lst["id"]
            for folder in space.get("folders", []):
                for lst in folder.get("lists", []):
                    if name_lower in lst["name"].lower():
                        return lst["id"]
        return None

    def _resolve_member(self, member_name: str, ctx: dict | None) -> str | None:
        if not ctx:
            return None
        name_lower = member_name.lower()
        for m in ctx.get("members", []):
            if name_lower in (m.get("username", "") + m.get("email", "")).lower():
                return str(m["id"])
        return None

    def _build_summary(self, op_type: str, params: dict) -> str:
        name = params.get("name") or params.get("title") or params.get("task_identifier") or ""
        list_name = params.get("list_name") or params.get("list_id") or ""
        priority = params.get("priority_label") or ""
        due = params.get("due_date") or ""
        assignee = params.get("assignee_name") or ""

        if op_type == "create_task":
            parts = [f"Create task '{name}'"]
            if list_name:
                parts.append(f"in {list_name}")
            if priority:
                parts.append(f"at {priority} priority")
            if due:
                parts.append(f"due {due}")
            if assignee:
                parts.append(f"assigned to {assignee}")
            return " ".join(parts)

        if op_type == "update_task":
            return f"Update '{name}'"
        if op_type == "set_due_date":
            return f"Set due date for '{name}' to {due}"
        if op_type == "set_priority":
            return f"Set priority for '{name}' to {priority}"
        if op_type == "assign_task":
            return f"Assign '{name}' to {assignee}"
        if op_type == "add_comment":
            return f"Add comment to '{name}'"
        if op_type == "create_calendar_event":
            return f"Create calendar event '{name}' on {params.get('date', '')}"
        if op_type == "update_calendar_event":
            parts = [f"Update calendar event '{name}'"]
            if params.get("date"):
                parts.append(f"to {params['date']}")
            if params.get("time"):
                parts.append(f"at {params['time']}")
            return " ".join(parts)

        return f"{op_type.replace('_', ' ')}: {name}"
