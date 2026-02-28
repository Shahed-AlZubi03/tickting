import pytest
from fastapi import HTTPException
from app.core.fsm import TicketStateMachine, TicketState
from app.models.ticket import Ticket, AuditLog

def test_fsm_valid_transition(db_session):
    ticket = Ticket(
        source_query="Test query",
        escalation_reason="Test reason",
        status=TicketState.CREATED
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    fsm = TicketStateMachine(db_session)
    updated_ticket = fsm.transition(
        ticket=ticket,
        new_state=TicketState.ASSIGNED,
        actor="reviewer-1",
        action="assign",
        reason="Taking ownership"
    )
    db_session.commit()
    
    assert updated_ticket.status == TicketState.ASSIGNED
    assert len(updated_ticket.history_log) == 1
    
    # Check universal audit table
    audit = db_session.query(AuditLog).filter_by(ticket_id=ticket.id).first()
    assert audit is not None
    assert audit.previous_state == TicketState.CREATED
    assert audit.new_state == TicketState.ASSIGNED
    assert audit.actor == "reviewer-1"

def test_fsm_invalid_transition(db_session):
    ticket = Ticket(
        source_query="Test query",
        escalation_reason="Test reason",
        status=TicketState.CREATED
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    fsm = TicketStateMachine(db_session)
    
    with pytest.raises(HTTPException) as exc:
        fsm.transition(
            ticket=ticket,
            new_state=TicketState.RESOLVED, # CREATED -> RESOLVED is invalid
            actor="reviewer-1",
            action="resolve",
            reason="Trying to resolve early"
        )
    
    assert exc.value.status_code == 409
    assert "Invalid state transition" in exc.value.detail["error"]
