from db.models.kpi import AuditLog
from sqlalchemy.orm import Session


def record_audit_event(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
) -> AuditLog:
    """Append one immutable event for a business action that can affect KPI."""

    event = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before or {},
        after_json=after or {},
        reason=reason,
    )
    db.add(event)
    return event
