from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.ticket import AuditLog
from app.schemas.ticket import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: Optional[int] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of immutable audit logs with optional filtering.
    """
    query = db.query(AuditLog)
    
    if ticket_id is not None:
        query = query.filter(AuditLog.ticket_id == ticket_id)
    if actor is not None:
        query = query.filter(AuditLog.actor == actor)
    if action is not None:
        query = query.filter(AuditLog.action == action)
        
    return query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
