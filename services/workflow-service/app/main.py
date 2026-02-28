import uuid
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.tickets import router as tickets_router
from app.api.escalate import router as escalate_router
from app.api.resolve import router as resolve_router
from app.api.audit import router as audit_router
from app.core.db import SessionLocal, get_db

app = FastAPI(
    title="JNPI Core Ticketing API",
    description="Sync, stateful, transactional backbone of the JNPI HITL lifecycle.",
    version="1.0.0",
)

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Service Unavailable: Database connection or operational failure", "request_id": getattr(request.state, "request_id", None)},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": getattr(request.state, "request_id", None)},
    )

@app.get("/health", tags=["system"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "database": db_status}

app.include_router(tickets_router)
app.include_router(escalate_router)
app.include_router(resolve_router)
app.include_router(audit_router)

