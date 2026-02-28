from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TicketStateEnum(str, Enum):
    CREATED = "CREATED"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED_FURTHER = "ESCALATED_FURTHER"
    REJECTED = "REJECTED"

class AuditLogResponse(BaseModel):
    id: int
    ticket_id: int
    actor: str = Field(..., description="The actor performing the action.")
    action: str = Field(..., description="The action being performed.")
    previous_state: Optional[TicketStateEnum] = Field(None, description="The state of the ticket before the action.")
    new_state: TicketStateEnum = Field(..., description="The state of the ticket after the action.")
    reason: Optional[str] = Field(None, description="The rationale or reason for the state change.")
    metadata_info: Optional[Dict[str, Any]] = Field(None, description="Extra metadata.")
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketBase(BaseModel):
    source_query: str = Field(..., description="The original user query.")
    agent_decision: Optional[str] = Field(None, description="The preliminary decision made by the AI agent.")
    confidence_score: Optional[float] = Field(None, description="The confidence score of the AI agent.")
    escalation_reason: str = Field(..., description="The reason this query was escalated to human review.")
    assigned_to: Optional[str] = Field(None, description="The ID of the human reviewer assigned to this ticket.")
    status: TicketStateEnum = Field(TicketStateEnum.CREATED, description="The current status of the ticket.")
    resolution: Optional[str] = Field(None, description="The resolution text/decision.")
    resolved_by: Optional[str] = Field(None, description="The user who resolved the ticket.")
    resolved_at: Optional[datetime] = Field(None, description="When the ticket was resolved.")

class TicketCreate(BaseModel):
    source_query: str = Field(..., description="The original user query.")
    agent_decision: Optional[str] = Field(None, description="The preliminary decision made by the AI agent.")
    confidence_score: Optional[float] = Field(None, description="The confidence score of the AI agent.")
    escalation_reason: str = Field(..., description="The reason this query was escalated to human review.")
    assigned_to: Optional[str] = Field(None, description="The ID of the human reviewer assigned to this ticket.")

class TicketUpdate(BaseModel):
    assigned_to: Optional[str] = None
    status: Optional[TicketStateEnum] = None

class TicketResponse(TicketBase):
    id: int
    created_at: datetime
    updated_at: datetime
    history_log: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class EscalationRequest(BaseModel):
    ticket_id: int = Field(..., description="The ID of the ticket to escalate.")
    actor: str = Field(..., description="The user or service ID triggering the escalation/state transition.")
    action: str = Field(..., description="The action triggering the escalation transition (e.g., 'approve', 'assign').")
    new_state: TicketStateEnum = Field(..., description="The target state for the ticket.")
    reason: str = Field(..., description="The reason for transitioning the state.")
    metadata_info: Optional[Dict[str, Any]] = Field(None, description="Extra transition metadata.")

class ResolutionRequest(BaseModel):
    ticket_id: int = Field(..., description="The ID of the ticket to resolve.")
    actor: str = Field(..., description="The human reviewer resolving the ticket.")
    final_decision: str = Field(..., description="The final decision or answer provided by the human reviewer.")
    resolution_status: TicketStateEnum = Field(..., description="The resolution state, either RESOLVED or REJECTED.")
    reason: str = Field(..., description="Rationale for the final decision.")
