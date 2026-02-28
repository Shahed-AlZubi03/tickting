from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from app.core.db import Base

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    source_query = Column(Text, nullable=False)
    agent_decision = Column(String(255), nullable=True)
    confidence_score = Column(Float, nullable=True)
    escalation_reason = Column(Text, nullable=False)
    assigned_to = Column(String(255), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="CREATED", index=True)
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # history_log stored as structured JSON array
    history_log = Column(JSON, nullable=False, default=list)

class AuditLog(Base):
    """
    Immutable structured audit records representing mutations in the system.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    actor = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    previous_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    metadata_info = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
