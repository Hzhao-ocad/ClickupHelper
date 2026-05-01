import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

PRIORITY_MAP = {
    "urgent": 1,
    "high": 2,
    "normal": 3,
    "low": 4,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
}


class ClickUpService:
    def __init__(self, api_token: str, rate_limit_delay_ms: int = 200):
        self.client = httpx.AsyncClient(
            base_url="https://api.clickup.com/api/v2",
            headers={"Authorization": api_token},
            timeout=30.0,
        )
        self.delay = rate_limit_delay_ms / 1000.0

    async def close(self):
        await self.client.aclose()

    async def _get(self, path, **kwargs):
        r = await self.client.get(path, **kwargs)
        r.raise_for_status()
        return r.json()

    async def _post(self, path, json_data, **kwargs):
        r = await self.client.post(path, json=json_data, **kwargs)
        r.raise_for_status()
        return r.json()

    async def _put(self, path, json_data, **kwargs):
        r = await self.client.put(path, json=json_data, **kwargs)
        r.raise_for_status()
        return r.json()

    # ── Workspace context ──────────────────────────────────────

    async def fetch_workspace_context(self):
        teams_data = await self._get("/team")
        teams = teams_data.get("teams", [])
        if not teams:
            return {"team": None, "spaces": [], "members": [], "statuses": [], "tags": []}

        team = teams[0]
        team_id = team["id"]
        team_name = team["name"]

        spaces_data = await self._get(f"/team/{team_id}/space")
        spaces = []
        for sp in spaces_data.get("spaces", []):
            space = {
                "id": sp["id"],
                "name": sp["name"],
                "folders": [],
                "lists": [],
            }

            folders_data = await self._get(f"/space/{sp['id']}/folder")
            for fld in folders_data.get("folders", []):
                folder = {"id": fld["id"], "name": fld["name"], "lists": []}
                lists_data = await self._get(f"/folder/{fld['id']}/list")
                for lst in lists_data.get("lists", []):
                    folder["lists"].append({"id": lst["id"], "name": lst["name"]})
                space["folders"].append(folder)

            folderless = await self._get(f"/space/{sp['id']}/list")
            for lst in folderless.get("lists", []):
                space["lists"].append({"id": lst["id"], "name": lst["name"]})

            spaces.append(space)

        # Fetch team members
        members = []
        try:
            guests_data = await self._get(f"/team/{team_id}/guest")
            for m in guests_data.get("members", []):
                user = m.get("user", {})
                members.append({"id": user.get("id"), "username": user.get("username", ""), "email": user.get("email", "")})
        except Exception:
            pass
        try:
            team_members = await self._get("/user")
            for m in team_members.get("members", []):
                user = m.get("user", {})
                members.append({"id": user.get("id"), "username": user.get("username", ""), "email": user.get("email", "")})
        except Exception:
            pass

        return {
            "team": {"id": team_id, "name": team_name},
            "spaces": spaces,
            "members": members,
        }

    # ── Operations ─────────────────────────────────────────────

    async def create_task(self, list_id: str, data: dict) -> dict:
        payload = {"name": data["name"]}
        if data.get("description"):
            payload["description"] = data["description"]
        if data.get("priority") is not None:
            payload["priority"] = data["priority"]
        if data.get("due_date"):
            payload["due_date"] = str(self._to_epoch(data["due_date"]))
        if data.get("start_date"):
            payload["start_date"] = str(self._to_epoch(data["start_date"]))
        if data.get("assignees"):
            payload["assignees"] = data["assignees"]
        if data.get("tags"):
            payload["tags"] = data["tags"]

        result = await self._post(f"/list/{list_id}/task", payload)
        return {"id": result.get("id"), "url": result.get("url")}

    async def update_task(self, task_id: str, data: dict) -> dict:
        payload = {}
        if "name" in data:
            payload["name"] = data["name"]
        if "description" in data:
            payload["description"] = data["description"]
        if "priority" in data:
            payload["priority"] = data["priority"]
        if "due_date" in data:
            payload["due_date"] = str(self._to_epoch(data["due_date"]))
        if "start_date" in data:
            payload["start_date"] = str(self._to_epoch(data["start_date"]))
        if "status" in data:
            payload["status"] = data["status"]
        if "assignees" in data:
            payload["assignees"] = data["assignees"]
        if "tags" in data:
            payload["tags"] = data["tags"]

        result = await self._put(f"/task/{task_id}", payload)
        return {"id": result.get("id"), "url": result.get("url")}

    async def add_comment(self, task_id: str, text: str) -> dict:
        result = await self._post(f"/task/{task_id}/comment", {"comment_text": text})
        return {"id": result.get("id")}

    def _to_epoch(self, date_str):
        import datetime as dt
        try:
            d = dt.datetime.fromisoformat(date_str)
            return int(d.timestamp() * 1000)
        except Exception:
            return date_str

    # ── Batch execution ────────────────────────────────────────

    async def execute_operation(self, op: dict) -> dict:
        op_type = op["type"]
        params = op["params"]

        try:
            if op_type == "create_task":
                list_id = params.get("list_id") or params.get("list_name", "")
                if not list_id:
                    return {"operation_id": op["id"], "status": "failed", "error": "No list specified. Please specify which list to create the task in."}
                if params.get("assignee_id"):
                    params["assignees"] = [params["assignee_id"]]
                result = await self.create_task(list_id, params)
                return {
                    "operation_id": op["id"],
                    "status": "success",
                    "clickup_url": result.get("url", ""),
                    "clickup_id": result.get("id", ""),
                    "summary": f"Created task '{params.get('name', '')}'",
                }
            elif op_type == "update_task":
                task_ref = params.get("task_id") or params.get("task_identifier", "")
                if params.get("assignee_id"):
                    params["assignees"] = [params["assignee_id"]]
                result = await self.update_task(task_ref, params)
                return {
                    "operation_id": op["id"],
                    "status": "success",
                    "clickup_url": result.get("url", ""),
                    "clickup_id": result.get("id", ""),
                    "summary": f"Updated task '{params.get('name', task_ref)}'",
                }
            elif op_type == "add_comment":
                task_ref = params.get("task_id") or params.get("task_identifier", "")
                await self.add_comment(task_ref, params.get("comment_text", ""))
                return {
                    "operation_id": op["id"],
                    "status": "success",
                    "clickup_url": "",
                    "clickup_id": "",
                    "summary": f"Added comment to task",
                }
            elif op_type in ("set_due_date", "set_priority", "assign_task"):
                task_ref = params.get("task_id") or params.get("task_identifier", "")
                update_data = {}
                if op_type == "set_due_date":
                    update_data["due_date"] = params.get("due_date")
                elif op_type == "set_priority":
                    priority_text = params.get("priority", "normal")
                    update_data["priority"] = PRIORITY_MAP.get(str(priority_text).lower(), 3)
                elif op_type == "assign_task":
                    update_data["assignees"] = [params.get("assignee_id") or params.get("assignee_name")]
                result = await self.update_task(task_ref, update_data)
                return {
                    "operation_id": op["id"],
                    "status": "success",
                    "clickup_url": result.get("url", ""),
                    "clickup_id": result.get("id", ""),
                    "summary": f"Applied {op_type.replace('_', ' ')}",
                }
            elif op_type == "create_calendar_event":
                # Calendar events are created as tasks with date/time metadata
                title = params.get("title") or params.get("name", "")
                list_id = params.get("list_id") or params.get("list_name", "")
                if not list_id:
                    return {"operation_id": op["id"], "status": "failed", "error": "No list specified. Please specify which list to create the event in."}
                task_data = {"name": title}
                if params.get("description"):
                    task_data["description"] = params.get("description")
                if params.get("priority") is not None:
                    task_data["priority"] = params["priority"]
                if params.get("date"):
                    date_str = params["date"]
                    if params.get("time"):
                        date_str = f"{date_str}T{params['time']}"
                    task_data["start_date"] = date_str
                    if params.get("duration_minutes"):
                        import datetime as dt
                        try:
                            start_dt = dt.datetime.fromisoformat(date_str)
                            end_dt = start_dt + dt.timedelta(minutes=int(params["duration_minutes"]))
                            task_data["due_date"] = end_dt.isoformat()
                        except Exception:
                            task_data["due_date"] = date_str
                    elif params.get("end_date"):
                        task_data["due_date"] = params["end_date"]
                    else:
                        task_data["due_date"] = date_str
                if params.get("assignee_id"):
                    task_data["assignees"] = [params["assignee_id"]]
                if params.get("tags"):
                    task_data["tags"] = params["tags"]
                result = await self.create_task(list_id, task_data)
                return {
                    "operation_id": op["id"],
                    "status": "success",
                    "clickup_url": result.get("url", ""),
                    "clickup_id": result.get("id", ""),
                    "summary": f"Created calendar event '{title}'",
                }
            elif op_type == "update_calendar_event":
                task_ref = params.get("task_id") or params.get("task_identifier", "")
                update_data = {}
                if "title" in params:
                    update_data["name"] = params["title"]
                if "name" in params:
                    update_data["name"] = params["name"]
                if "description" in params:
                    update_data["description"] = params["description"]
                if "priority" in params:
                    priority_text = params.get("priority", "normal")
                    update_data["priority"] = PRIORITY_MAP.get(str(priority_text).lower(), 3)
                if params.get("date"):
                    date_str = params["date"]
                    if params.get("time"):
                        date_str = f"{date_str}T{params['time']}"
                    update_data["start_date"] = date_str
                    if params.get("duration_minutes"):
                        import datetime as dt
                        try:
                            start_dt = dt.datetime.fromisoformat(date_str)
                            end_dt = start_dt + dt.timedelta(minutes=int(params["duration_minutes"]))
                            update_data["due_date"] = end_dt.isoformat()
                        except Exception:
                            pass
                    elif params.get("end_date"):
                        update_data["due_date"] = params["end_date"]
                if params.get("assignee_id"):
                    update_data["assignees"] = [params["assignee_id"]]
                if params.get("status"):
                    update_data["status"] = params["status"]
                if params.get("tags"):
                    update_data["tags"] = params["tags"]
                result = await self.update_task(task_ref, update_data)
                return {
                    "operation_id": op["id"],
                    "status": "success",
                    "clickup_url": result.get("url", ""),
                    "clickup_id": result.get("id", ""),
                    "summary": f"Updated calendar event '{params.get('title', task_ref)}'",
                }
            else:
                return {
                    "operation_id": op["id"],
                    "status": "failed",
                    "error": f"Unknown operation type: {op_type}",
                }
        except Exception as e:
            logger.exception(f"Operation {op['id']} failed")
            return {
                "operation_id": op["id"],
                "status": "failed",
                "error": str(e),
                "summary": f"Failed to execute {op_type}",
            }

    async def execute_batch(self, ops: list[dict]) -> list[dict]:
        results = []
        for op in ops:
            result = await self.execute_operation(op)
            results.append(result)
            if len(ops) > 1:
                await asyncio.sleep(self.delay)
        return results
