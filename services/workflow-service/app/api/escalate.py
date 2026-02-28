from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import EscalationRequest, TicketResponse
from app.core.fsm import TicketStateMachine

router = APIRouter(prefix="/escalate", tags=["Escalation"])

@router.post("", response_model=TicketResponse, status_code=status.HTTP_200_OK)
def escalate_ticket(request: EscalationRequest, db: Session = Depends(get_db)):
    """
    Trigger a state transition for a ticket according to strict FSM rules.
    """
    ticket = db.query(Ticket).filter(Ticket.id == request.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    fsm = TicketStateMachine(db)
    
    try:
        updated_ticket = fsm.transition(
            ticket=ticket,
            new_state=request.new_state.value,
            actor=request.actor,
            action=request.action,
            reason=request.reason,
            metadata_info=request.metadata_info
        )
        
        db.commit()
        db.refresh(updated_ticket)
        return updated_ticket
        
    except HTTPException:
        db.rollback()
        raise # Reraise the 409 conflict exactly as produced by fsm
    except Exception as e:
        db.rollback()
        raise e
