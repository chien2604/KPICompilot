from core.deps import require_admin
from db.database import get_db
from db.models.kpi import AuditLog
from db.models.users import User
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 100,
    database_session: Session = Depends(get_db),
    _administrator: User = Depends(require_admin),
) -> list[dict]:
    """Return immutable KPI-impacting events for technical audit purposes."""

    query = database_session.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    rows = query.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "before": row.before_json,
            "after": row.after_json,
            "reason": row.reason,
            "created_at": row.created_at,
        }
        for row in rows
    ]
