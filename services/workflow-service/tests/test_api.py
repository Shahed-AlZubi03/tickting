import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.db import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_ticket():
    response = client.post(
        "/tickets",
        json={
            "source_query": "Is this a policy violation?",
            "agent_decision": "unclear",
            "confidence_score": 0.45,
            "escalation_reason": "Low confidence score",
            "assigned_to": "human-1"
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_query"] == "Is this a policy violation?"
    assert data["status"] == "CREATED"
    assert "id" in data
    assert len(data["history_log"]) == 1
    assert data["history_log"][0]["action"] == "CREATE"

    # Idempotency check
    response2 = client.post(
        "/tickets",
        json={
            "source_query": "Is this a policy violation?",
            "escalation_reason": "Checking idempotency"
        }
    )
    assert response2.status_code == 201
    assert response2.json()["id"] == data["id"] # Should return exact same ticket

def test_escalate_ticket():
    create_response = client.post(
        "/tickets",
        json={
            "source_query": "Escalate me",
            "escalation_reason": "Testing escalation",
        },
    )
    ticket_id = create_response.json()["id"]

    # Assign properly: CREATED -> ASSIGNED
    response = client.post(
        "/escalate",
        json={
            "ticket_id": ticket_id,
            "actor": "reviewer-1",
            "action": "assign",
            "new_state": "ASSIGNED",
            "reason": "Taking ownership of ticket"
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ASSIGNED"

    # Try invalid escalation (ASSIGNED -> RESOLVED is invalid)
    response_invalid = client.post(
        "/escalate",
        json={
            "ticket_id": ticket_id,
            "actor": "reviewer-1",
            "action": "resolve",
            "new_state": "RESOLVED",
            "reason": "Resolving directly from assigned"
        },
    )
    assert response_invalid.status_code == 409

def test_resolve_ticket():
    create_response = client.post(
        "/tickets",
        json={
            "source_query": "Resolve me",
            "escalation_reason": "Testing resolution"
        },
    )
    ticket_id = create_response.json()["id"]

    # FSM Path: CREATED -> ASSIGNED -> IN_REVIEW
    client.post("/escalate", json={"ticket_id": ticket_id, "actor": "r1", "action": "assign", "new_state": "ASSIGNED", "reason": "Claim"})
    client.post("/escalate", json={"ticket_id": ticket_id, "actor": "r1", "action": "review", "new_state": "IN_REVIEW", "reason": "Reviewing"})

    resolve_response = client.post(
        "/resolve",
        json={
            "ticket_id": ticket_id,
            "actor": "r1",
            "final_decision": "No policy violation.",
            "resolution_status": "RESOLVED",
            "reason": "Checked manuals."
        }
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "RESOLVED"
    
    get_response = client.get(f"/tickets/{ticket_id}")
    history = get_response.json()["history_log"]
    assert len(history) == 4 # CREATE -> ASSIGN -> IN_REVIEW -> RESOLVE
    assert history[-1]["action"] == "resolve"
    assert "No policy violation" in history[-1]["reason"]

def test_audit_logs():
    create_response = client.post("/tickets", json={"source_query": "Audit me", "escalation_reason": "Testing audit"})
    ticket_id = create_response.json()["id"]
    client.post("/escalate", json={"ticket_id": ticket_id, "actor": "auditor", "action": "triage", "new_state": "TRIAGED", "reason": "Quick look"})
    
    audit_res = client.get(f"/audit?ticket_id={ticket_id}")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    assert len(audits) == 2
    assert audits[0]["action"] == "triage" # Orders descending
    assert audits[1]["action"] == "CREATE"
