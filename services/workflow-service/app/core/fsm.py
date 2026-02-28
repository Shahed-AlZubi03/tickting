from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.ticket import Ticket, AuditLog
from datetime import datetime

class TicketState:
    CREATED = "CREATED"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED_FURTHER = "ESCALATED_FURTHER"
    REJECTED = "REJECTED"

VALID_TRANSITIONS = {
    TicketState.CREATED: [TicketState.TRIAGED, TicketState.ASSIGNED, TicketState.REJECTED],
    TicketState.TRIAGED: [TicketState.ASSIGNED, TicketState.REJECTED],
    TicketState.ASSIGNED: [TicketState.IN_REVIEW, TicketState.REJECTED, TicketState.CREATED],
    TicketState.IN_REVIEW: [TicketState.RESOLVED, TicketState.REJECTED, TicketState.ASSIGNED, TicketState.ESCALATED_FURTHER],
    TicketState.RESOLVED: [],
    TicketState.ESCALATED_FURTHER: [],
    TicketState.REJECTED: []
}

class TicketStateMachine:
    def __init__(self, db: Session):
        self.db = db

    def validate_transition(self, current_state: str, new_state: str):
        if new_state not in VALID_TRANSITIONS.get(current_state, []):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Invalid state transition",
                    "current_state": current_state,
                    "attempted_state": new_state,
                    "reason": f"Transition from {current_state} to {new_state} is not permitted."
                }
            )

    def transition(self, ticket: Ticket, new_state: str, actor: str, action: str, reason: Optional[str] = None, metadata_info: Optional[Dict[str, Any]] = None) -> Ticket:
        """
        Transition a ticket to a new state and record the history atomically within the session.
        Does NOT commit. The caller must commit the transaction.
        """
        self.validate_transition(ticket.status, new_state)

        previous_state = ticket.status
        ticket.status = new_state
        
        timestamp = datetime.utcnow()
        timestamp_iso = timestamp.isoformat()

        # Build history log entry
        log_entry = {
            "action": action,
            "actor": actor,
            "previous_state": previous_state,
            "new_state": new_state,
            "reason": reason,
            "timestamp": timestamp_iso
        }
        
        # We need to append to the JSON array or assign a new list if it's None/empty
        current_history = list(ticket.history_log) if ticket.history_log is not None else []
        current_history.append(log_entry)
        ticket.history_log = current_history

        # Global audit log insertion
        audit_entry = AuditLog(
            ticket_id=ticket.id,
            actor=actor,
            action=action,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
            metadata_info=metadata_info or {},
            timestamp=timestamp
        )
        self.db.add(audit_entry)
        
        return ticket
