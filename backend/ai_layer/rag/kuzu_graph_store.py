from pathlib import Path
from typing import Any


class KuzuGraphStore:
    """Represent kuzu graph store data and behavior."""

    def __init__(self, db_path: str) -> None:
        """Initialize the kuzu graph store."""

        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.available = False
        try:
            import kuzu

            self.kuzu = kuzu
            self.db = kuzu.Database(str(self.db_path))
            self.conn = kuzu.Connection(self.db)
            self.available = True
        except Exception:
            self.kuzu = None
            self.db = None
            self.conn = None

    def init_schema(self) -> None:
        """Initialize the schema."""

        if not self.available:
            return
        statements = [
            "CREATE NODE TABLE IF NOT EXISTS User(id INT64, full_name STRING, role STRING, department_id INT64, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Department(id INT64, name STRING, parent_id INT64, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Task(id INT64, title STRING, status STRING, deadline STRING, department_id INT64, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Evidence(id INT64, file_name STRING, relevance_score DOUBLE, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Criterion(id INT64, name STRING, group_name STRING, max_score DOUBLE, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Chunk(id INT64, evidence_id INT64, content_preview STRING, PRIMARY KEY(id))",
            "CREATE REL TABLE IF NOT EXISTS USER_BELONGS_TO(FROM User TO Department)",
            "CREATE REL TABLE IF NOT EXISTS DEPARTMENT_PARENT_OF(FROM Department TO Department)",
            "CREATE REL TABLE IF NOT EXISTS USER_ASSIGNED_TASK(FROM User TO Task)",
            "CREATE REL TABLE IF NOT EXISTS TASK_HAS_EVIDENCE(FROM Task TO Evidence)",
            "CREATE REL TABLE IF NOT EXISTS EVIDENCE_HAS_CHUNK(FROM Evidence TO Chunk)",
            "CREATE REL TABLE IF NOT EXISTS TASK_MEASURED_BY(FROM Task TO Criterion)",
            "CREATE REL TABLE IF NOT EXISTS CHUNK_SUPPORTS_CRITERION(FROM Chunk TO Criterion)",
        ]
        for statement in statements:
            self._execute(statement)

    def upsert_user(self, user: Any) -> None:
        """Create or update the user."""

        self._merge(
            "User",
            "id",
            user.id,
            {
                "full_name": user.full_name,
                "role": user.role,
                "department_id": user.department_id or 0,
            },
        )

    def upsert_department(self, department: Any) -> None:
        """Create or update the department."""

        self._merge(
            "Department",
            "id",
            department.id,
            {"name": department.name, "parent_id": department.parent_id or 0},
        )

    def upsert_task(self, task: Any) -> None:
        """Create or update the task."""

        deadline = task.deadline.isoformat() if task.deadline else ""
        self._merge(
            "Task",
            "id",
            task.id,
            {
                "title": task.title,
                "status": task.status,
                "deadline": deadline,
                "department_id": task.department_id or 0,
            },
        )

    def upsert_evidence(self, evidence: Any) -> None:
        """Create or update the evidence."""

        self._merge(
            "Evidence",
            "id",
            evidence.id,
            {
                "file_name": evidence.file_name,
                "relevance_score": evidence.ai_relevance_score or 0,
            },
        )

    def upsert_criterion(self, criterion: Any) -> None:
        """Create or update the criterion."""

        self._merge(
            "Criterion",
            "id",
            criterion.id,
            {
                "name": criterion.criterion_name,
                "group_name": criterion.group_name,
                "max_score": criterion.max_score,
            },
        )

    def upsert_chunk(self, chunk: Any) -> None:
        """Create or update the chunk."""

        self._merge(
            "Chunk",
            "id",
            chunk.id,
            {"evidence_id": chunk.evidence_id, "content_preview": chunk.content[:240]},
        )

    def link_user_department(self, user_id: int, department_id: int) -> None:
        """Link the user department."""

        self._link("User", user_id, "Department", department_id, "USER_BELONGS_TO")

    def link_user_task(self, user_id: int, task_id: int) -> None:
        """Link the user task."""

        self._link("User", user_id, "Task", task_id, "USER_ASSIGNED_TASK")

    def link_task_evidence(self, task_id: int, evidence_id: int) -> None:
        """Link the task evidence."""

        self._link("Task", task_id, "Evidence", evidence_id, "TASK_HAS_EVIDENCE")

    def link_evidence_chunk(self, evidence_id: int, chunk_id: int) -> None:
        """Link the evidence chunk."""

        self._link("Evidence", evidence_id, "Chunk", chunk_id, "EVIDENCE_HAS_CHUNK")

    def link_task_criterion(self, task_id: int, criterion_id: int) -> None:
        """Link the task criterion."""

        self._link("Task", task_id, "Criterion", criterion_id, "TASK_MEASURED_BY")

    def find_task_context(self, task_id: int) -> list[dict]:
        """Find the task context."""

        return self._query_dicts(
            "MATCH (t:Task)-[:TASK_HAS_EVIDENCE]->(e:Evidence) WHERE t.id=$id RETURN t.title, t.status, e.file_name, e.relevance_score LIMIT 10",
            {"id": task_id},
        )

    def find_user_context(self, user_id: int) -> list[dict]:
        """Find the user context."""

        return self._query_dicts(
            "MATCH (u:User)-[:USER_ASSIGNED_TASK]->(t:Task) WHERE u.id=$id RETURN u.full_name, t.title, t.status, t.deadline LIMIT 20",
            {"id": user_id},
        )

    def find_department_risks(self, department_id: int | None = None) -> list[dict]:
        """Find the department risks."""

        if department_id:
            return self._query_dicts(
                "MATCH (d:Department)<-[:USER_BELONGS_TO]-(u:User)-[:USER_ASSIGNED_TASK]->(t:Task) WHERE d.id=$id RETURN d.name, u.full_name, t.title, t.status LIMIT 30",
                {"id": department_id},
            )
        return self._query_dicts(
            "MATCH (d:Department)<-[:USER_BELONGS_TO]-(u:User)-[:USER_ASSIGNED_TASK]->(t:Task) RETURN d.name, u.full_name, t.title, t.status LIMIT 30",
            {},
        )

    def _merge(self, label: str, key: str, key_value: Any, props: dict) -> None:
        """Handle the operation."""

        if not self.available:
            return
        set_clause = ", ".join(f"n.{name} = ${name}" for name in props)
        self._execute(
            f"MERGE (n:{label} {{{key}: $key_value}}) SET {set_clause}",
            {"key_value": key_value, **props},
        )

    def _link(
        self, from_label: str, from_id: int, to_label: str, to_id: int, rel: str
    ) -> None:
        """Link the operation."""

        if not self.available:
            return
        self._execute(
            f"MATCH (a:{from_label} {{id: $from_id}}), (b:{to_label} {{id: $to_id}}) MERGE (a)-[:{rel}]->(b)",
            {"from_id": from_id, "to_id": to_id},
        )

    def _execute(self, statement: str, params: dict | None = None) -> None:
        """Execute the operation."""

        if self.available:
            self.conn.execute(statement, params or {})

    def _query_dicts(self, statement: str, params: dict | None = None) -> list[dict]:
        """Handle the dicts."""

        if not self.available:
            return []
        try:
            result = self.conn.execute(statement, params or {})
            rows = []
            while result.has_next():
                row = result.get_next()
                rows.append({f"col_{idx}": value for idx, value in enumerate(row)})
            return rows
        except Exception:
            return []
