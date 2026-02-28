# JNPI Core Ticketing & State Machine Subsystem
## Integration Guide

This guide outlines the API contracts for the Core Ticketing Subsystem (`workflow-service`) intended for Teams 2, 3, 4, and 5.

### 1. For Team 2 (Agent Service)
When the AI agent system cannot resolve a query with sufficient confidence, standard policy requires escalating it to a human reviewer.

**Endpoint**: `POST /tickets`
**Action**: Create a new escalation ticket.
**Contract Request**:
```json
{
  "query": "Is installing a temporary server rack permitted in Sector 7?",
  "agent_decision": "Permitted with caveats",
  "confidence_score": 0.35,
  "escalation_reason": "Confidence below 0.85 threshold.",
  "assigned_reviewer": "human_reviewer_992" // Optional
}
```
**Response**: `201 Created` returning the full ticket state including its assigned `id`.

### 2. For Team 3 (Governance Service)
Team 3 needs to monitor ticket state metrics for compliance and benchmarking.

**Endpoint**: `GET /tickets`
**Action**: Retrieve all tickets along with their statuses.
**Endpoint**: `GET /tickets/{id}`
**Action**: Retrieve a specific ticket and its full `TicketHistory` audit log. The `history` array contains immutable log entries with timestamps, actors, prev/new states, and reasons.

### 3. For Team 4 (Notifications & Operations)
Team 4 currently subscribes to final resolution events to dispatch alerts.

Currently, the `POST /resolve` endpoint validates the human decision. Integration with Team 4's message broker is architected to trigger immediately after the database commit in `app/api/resolve.py:resolve_ticket`.
Depending on your AMQP/Kafka setup, you will subscribe to the `ticket_resolved` topic emitted by our service.

### 4. For Team 5 (Frontend)
The frontend uses the core endpoints to power the human review console.

- **Load Dashboard**: `GET /tickets` (paginated via `skip` and `limit`)
- **Review Ticket**: `GET /tickets/{id}`
- **Assign/Triage**: `POST /escalate`
  **Example Request**:
  ```json
  {
      "ticket_id": 1,
      "actor": "reviewer_992",
      "action": "assign",
      "new_state": "ASSIGNED",
      "reason": "Acknowledging assignment and beginning review"
  }
  ```
- **Finalize Review**: `POST /resolve`
  **Example Request**:
  ```json
  {
      "ticket_id": 1,
      "actor": "reviewer_992",
      "final_decision": "Installation permitted pending safety review.",
      "resolution_status": "RESOLVED",
      "reason": "Verified Sector 7 building codes in manual."
  }
  ```

### General Error Handling
All errors (such as invalid state transitions) return HTTP 400 or HTTP 404 with structured JSON describing the issue:
```json
{
  "detail": "Invalid transition from CREATED to RESOLVED"
}
```
All valid interactions are guaranteed atomic. The REST server runs on standard port 8000 when booted via `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Full interactive documentation is available at `/docs`.
