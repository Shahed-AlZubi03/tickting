from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import ResolutionRequest, TicketResponse
from app.core.fsm import TicketStateMachine, TicketState

router = APIRouter(prefix="/resolve", tags=["Resolution"])

@router.post("", response_model=TicketResponse, status_code=status.HTTP_200_OK)
def resolve_ticket(request: ResolutionRequest, db: Session = Depends(get_db)):
    """
    Capture a human reviewer's final decision on a ticket.
    Validates that the ticket is in a resolvable state and logs the resolution.
    """
    ticket = db.query(Ticket).filter(Ticket.id == request.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        
    if request.resolution_status.value not in [TicketState.RESOLVED, TicketState.REJECTED]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resolution status. Must be RESOLVED or REJECTED.")

    fsm = TicketStateMachine(db)
    
    try:
        updated_ticket = fsm.transition(
            ticket=ticket,
            new_state=request.resolution_status.value,
            actor=request.actor,
            action="resolve",
            reason=f"Final Decision: {request.final_decision}. Rationale: {request.reason}"
        )
        
        # Enforce Section 3: Persist the resolution with reviewer identity, decision, timestamp
        updated_ticket.resolution = request.final_decision
        updated_ticket.resolved_by = request.actor
        updated_ticket.resolved_at = datetime.utcnow()
        
        db.commit()
        db.refresh(updated_ticket)
        return updated_ticket
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise e
