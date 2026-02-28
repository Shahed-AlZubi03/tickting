# JNPI Workflow Service (Core Ticketing & State Machine)

This service manages the strict, stateful lifecycle of human-in-the-loop (HITL) escalations from the agent service within the JNPI platform.

## Architecture
- **Framework**: FastAPI
- **Database**: PostgreSQL (Strict requirement)
- **Migrations**: Alembic
- **Patterns**: Layered Architecture, Strict FSM, Immutable Audit Logging

## API Interfaces

- **`POST /tickets`**: Create a ticket. (Expected by Team 2 - Agent Service payload). Idempotent.
- **`GET /tickets`**: Pagination & filterable list. List available for Team 5.
- **`PATCH /tickets/{id}`**: Assign users.
- **`POST /escalate`**: Step through strict internal states.
- **`POST /resolve`**: Resolve a ticket (triggers stubbed Team 4 webhook/event).
- **`GET /audit`**: Query raw audit representations for Team 3 (Governance).

## State Machine
The FSM supports specific strict states:
`CREATED` -> `TRIAGED` -> `ASSIGNED` -> `IN_REVIEW` -> `RESOLVED` / `REJECTED` / `ESCALATED_FURTHER`. Invalid transitions throw `409` conflict responses.
