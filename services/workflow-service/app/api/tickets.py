from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.ticket import Ticket, AuditLog
from app.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate, TicketStateEnum
from app.core.fsm import TicketStateMachine, TicketState

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket_in: TicketCreate, db: Session = Depends(get_db)):
    """
    Create a new escalation ticket from the Agent Service.
    Captures query data, AI decision, and atomitcally creates the initial history log.
    Includes idempotency check based on source_query.
    """
    # Idempotency check: Reject duplicate source queries that are CREATED
    existing_ticket = db.query(Ticket).filter(
        Ticket.source_query == ticket_in.source_query,
        Ticket.status == TicketState.CREATED
    ).first()
    
    if existing_ticket:
        return existing_ticket

    try:
        db_ticket = Ticket(
            source_query=ticket_in.source_query,
            agent_decision=ticket_in.agent_decision,
            confidence_score=ticket_in.confidence_score,
            escalation_reason=ticket_in.escalation_reason,
            assigned_to=ticket_in.assigned_to,
            status=TicketState.CREATED
        )
        db.add(db_ticket)
        db.flush()

        # Generate initial history logic inline to comply with JSON array requirements
        fsm = TicketStateMachine(db)
        # Using the transition method just for the initial log is a bit hacky, 
        # so we'll just insert the first TicketHistory/AuditLog manually as this is creation, not transition.
        timestamp = datetime.utcnow()
        timestamp_iso = timestamp.isoformat()
        
        log_entry = {
            "action": "CREATE",
            "actor": "system",
            "previous_state": None,
            "new_state": TicketState.CREATED,
            "reason": "Initial escalation creation",
            "timestamp": timestamp_iso
        }
        db_ticket.history_log = [log_entry]

        audit_entry = AuditLog(
            ticket_id=db_ticket.id,
            actor="system",
            action="CREATE",
            previous_state=None,
            new_state=TicketState.CREATED,
            reason="Initial escalation creation",
            timestamp=timestamp
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(db_ticket)
        return db_ticket
    except Exception as e:
        db.rollback()
        raise e


@router.get("", response_model=List[TicketResponse])
def get_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TicketStateEnum] = None,
    assigned_to: Optional[str] = None,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of tickets with optional filtering.
    """
    query = db.query(Ticket)
    
    if status is not None:
        query = query.filter(Ticket.status == status.value)
    if assigned_to is not None:
        query = query.filter(Ticket.assigned_to == assigned_to)
    if date_start is not None:
        query = query.filter(Ticket.created_at >= date_start)
    if date_end is not None:
        query = query.filter(Ticket.created_at <= date_end)
        
    return query.offset(skip).limit(limit).all()


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific ticket by ID, including its history.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, update_data: TicketUpdate, db: Session = Depends(get_db)):
    """
    Partially update mutable fields on a ticket.
    Currently allows updating assigned_to. Status updates MUST go through /escalate or /resolve.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    
    if update_data.status is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status cannot be updated directly. Use /escalate or /resolve.")

    try:
        if update_data.assigned_to is not None:
            # Audit log this assignment mutation
            audit_entry = AuditLog(
                ticket_id=ticket.id,
                actor="system",
                action="UPDATE_ASSIGNMENT",
                previous_state=ticket.status,
                new_state=ticket.status,
                reason=f"Assigned to {update_data.assigned_to}"
            )
            db.add(audit_entry)
            
            # Record directly on the ticket log
            log_entry = {
                "action": "UPDATE_ASSIGNMENT",
                "actor": "system",
                "previous_state": ticket.status,
                "new_state": ticket.status,
                "reason": f"Assigned to {update_data.assigned_to}",
                "timestamp": datetime.utcnow().isoformat()
            }
            current_history = list(ticket.history_log)
            current_history.append(log_entry)
            ticket.history_log = current_history
            
            ticket.assigned_to = update_data.assigned_to
            
        db.commit()
        db.refresh(ticket)
        return ticket
    except Exception as e:
        db.rollback()
        raise e
