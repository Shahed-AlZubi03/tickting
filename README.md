# JNPI Workflow Service (Core Ticketing & State Machine)

This service manages the strict, stateful lifecycle of human-in-the-loop (HITL) escalations from the agent service within the JNPI platform.

## Architecture
- **Framework**: FastAPI
- **Database**: PostgreSQL (Strict requirement)
- **Migrations**: Alembic
- **Patterns**: Layered Architecture, Strict FSM, Immutable Audit Logging

## Setup & Local Development

1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:
Copy `.env.example` to `.env` and set your specific values.

3. Run migrations and start:
```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Testing
Run the test suite using pytest (uses an isolated SQLite db by default for tests):
```bash
pytest tests/
```

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
