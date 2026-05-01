from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4


@dataclass
class Session:
    session_id: str
    created_at: datetime
    workspace_context: dict | None = None
    pending_operations: dict = field(default_factory=dict)
    conversation_history: list = field(default_factory=list)


class SessionService:
    def __init__(self, ttl_minutes: int = 60):
        self.sessions: dict[str, Session] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def create_session(self) -> Session:
        self._cleanup()
        sid = str(uuid4())
        session = Session(session_id=sid, created_at=datetime.now())
        self.sessions[sid] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session and datetime.now() - session.created_at > self.ttl:
            del self.sessions[session_id]
            return None
        return session

    def store_operations(self, session_id: str, ops: list):
        session = self.get_session(session_id)
        if session:
            for op in ops:
                session.pending_operations[op["id"]] = op

    def get_operations(self, session_id: str, op_ids: list[str]) -> list:
        session = self.get_session(session_id)
        if not session:
            return []
        return [session.pending_operations[oid] for oid in op_ids if oid in session.pending_operations]

    def update_operation(self, session_id: str, op_id: str, edits: dict):
        session = self.get_session(session_id)
        if session and op_id in session.pending_operations:
            session.pending_operations[op_id]["params"].update(edits)

    def append_history(self, session_id: str, entry: dict):
        session = self.get_session(session_id)
        if session:
            session.conversation_history.append(entry)

    def _cleanup(self):
        now = datetime.now()
        expired = [sid for sid, s in self.sessions.items() if now - s.created_at > self.ttl]
        for sid in expired:
            del self.sessions[sid]
