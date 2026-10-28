from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.auth import create_operator_token, require_operator, revoke_operator_token
from app.schemas import (
    DoctorSchema,
    DoctorSlotSchema,
    AppointmentCreate,
    AppointmentResponse,
    AmbulanceRequestCreate,
    AmbulanceRequestResponse,
    SupportTicketCreate,
    SupportTicketResponse,
    HumanEscalationCreate,
    HumanEscalationResponse,
    AgentActionLogResponse,
    DashboardStatsResponse,
    OperatorLoginRequest,
    OperatorLoginResponse,
    OperatorInfoResponse,
    StatusUpdateRequest
)
from app.services import operations

router = APIRouter()

# --- Health ---
@router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "hospital": settings.HOSPITAL_NAME,
        "ai_enabled": settings.is_ai_configured,
        "model": settings.active_llm_model if settings.is_ai_configured else "Deterministic Fallback Demo"
    }

# --- Operator Authentication Gate ---
@router.post("/auth/operator/login", response_model=OperatorLoginResponse, tags=["Operator Auth"])
def operator_login(payload: OperatorLoginRequest):
    """Authenticate hospital operator using backend environment variables."""
    # Compare with backend-configured demo operator credentials
    if payload.username.strip() != settings.OPERATOR_USERNAME or payload.password != settings.OPERATOR_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator credentials. Please check your username and password."
        )

    token_data = create_operator_token(payload.username.strip())
    return {
        "access_token": token_data["access_token"],
        "token_type": "bearer",
        "expires_at": token_data["expires_at"],
        "username": token_data["username"],
        "role": token_data["role"],
        "hospital": settings.HOSPITAL_NAME
    }

@router.get("/auth/operator/demo-credentials", tags=["Operator Auth"])
def get_demo_operator_credentials():
    """Demo helper: Exposes environment-configured demo operator credentials for hackathon evaluation."""
    return {
        "username": settings.OPERATOR_USERNAME,
        "password": settings.OPERATOR_PASSWORD,
        "note": "Configured in backend environment variables (OPERATOR_USERNAME and OPERATOR_PASSWORD)."
    }

@router.get("/auth/operator/me", response_model=OperatorInfoResponse, tags=["Operator Auth"])
def get_current_operator(operator_data: Dict[str, Any] = Depends(require_operator)):
    """Validate current operator token and return profile."""
    return {
        "username": operator_data.get("sub", settings.OPERATOR_USERNAME),
        "role": operator_data.get("role", "hospital_operator"),
        "hospital": operator_data.get("hospital", settings.HOSPITAL_NAME)
    }

@router.post("/auth/operator/logout", tags=["Operator Auth"])
def operator_logout(
    operator_data: Dict[str, Any] = Depends(require_operator),
    authorization: Optional[str] = Header(None)
):
    """Logout current operator session and invalidate token on the server."""
    token = operator_data.get("token")
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    if token:
        revoke_operator_token(token)
    return {
        "status": "ok",
        "message": "Operator session logged out and invalidated successfully."
    }

# --- Doctors & Slots (Public Patient Access) ---
@router.get("/doctors", response_model=List[DoctorSchema], tags=["Doctors"])
def list_doctors(db: Session = Depends(get_db)):
    return operations.get_all_doctors(db)

@router.get("/doctors/search", response_model=List[DoctorSchema], tags=["Doctors"])
def search_doctors_endpoint(
    q: Optional[str] = Query(None, description="Doctor name, department, or specialization"),
    department: Optional[str] = Query(None, description="Department filter"),
    db: Session = Depends(get_db)
):
    return operations.search_doctors(db, query=q, department=department)

@router.get("/appointments/slots", response_model=List[DoctorSlotSchema], tags=["Appointments"])
def get_appointment_slots(
    doctor_id: int = Query(..., description="Doctor ID"),
    date: str = Query(..., description="Date formatted as YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    doctor = operations.get_doctor_by_id(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return operations.check_slots(db, doctor_id=doctor_id, date=date)

# --- Appointments ---
@router.post("/appointments", response_model=AppointmentResponse, status_code=201, tags=["Appointments"])
def book_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    """Public Patient Workflow: Create verified appointment after patient confirmation."""
    try:
        return operations.create_appointment(
            db=db,
            doctor_id=payload.doctor_id,
            patient_name=payload.patient_name,
            patient_phone=payload.patient_phone,
            date=payload.appointment_date,
            time_slot=payload.appointment_time,
            notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/appointments", response_model=List[AppointmentResponse], tags=["Appointments"])
def list_appointments(
    limit: int = 50,
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Hospital-wide appointments restricted to authenticated operators."""
    return operations.get_recent_appointments(db, limit=limit)

# --- Ambulance Requests ---
@router.post("/ambulance-requests", response_model=AmbulanceRequestResponse, status_code=201, tags=["Ambulance"])
def request_ambulance(payload: AmbulanceRequestCreate, db: Session = Depends(get_db)):
    """Public Patient Workflow: Submit simulated ambulance request."""
    try:
        return operations.create_ambulance_request(
            db=db,
            patient_name=payload.patient_name,
            contact_phone=payload.contact_phone,
            pickup_address=payload.pickup_address,
            emergency_nature=payload.emergency_nature,
            is_emergency=payload.is_emergency
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ambulance-requests", response_model=List[AmbulanceRequestResponse], tags=["Ambulance"])
def list_ambulance_requests(
    limit: int = 50,
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Hospital-wide ambulance request list restricted to authenticated operators."""
    return operations.get_recent_ambulance_requests(db, limit=limit)

# --- Support Tickets ---
@router.post("/tickets", response_model=SupportTicketResponse, status_code=201, tags=["Support"])
def create_ticket(payload: SupportTicketCreate, db: Session = Depends(get_db)):
    """Public Patient Workflow: Submit hospital grievance or support ticket."""
    try:
        return operations.create_support_ticket(
            db=db,
            patient_name=payload.patient_name,
            contact_phone=payload.contact_phone,
            category=payload.category,
            priority=payload.priority,
            description=payload.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tickets", response_model=List[SupportTicketResponse], tags=["Support"])
def list_tickets(
    limit: int = 50,
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Hospital-wide grievances list restricted to authenticated operators."""
    return operations.get_recent_tickets(db, limit=limit)

@router.patch("/tickets/{ticket_id}/status", response_model=SupportTicketResponse, tags=["Support"])
def update_ticket_status_endpoint(
    ticket_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Update support ticket status by authenticated operator."""
    tkt = operations.update_ticket_status(db, ticket_id=ticket_id, new_status=payload.status)
    if not tkt:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return tkt

# --- Human Escalations ---
@router.post("/escalations", response_model=HumanEscalationResponse, status_code=201, tags=["Escalations"])
def create_escalation(payload: HumanEscalationCreate, db: Session = Depends(get_db)):
    """Public Patient Workflow: Register human assistance escalation."""
    try:
        return operations.escalate_to_human(
            db=db,
            patient_name=payload.patient_name,
            contact_phone=payload.contact_phone,
            reason=payload.reason,
            priority=payload.priority,
            notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/escalations", response_model=List[HumanEscalationResponse], tags=["Escalations"])
def list_escalations(
    limit: int = 50,
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Internal operator escalations list restricted to authenticated operators."""
    return operations.get_recent_escalations(db, limit=limit)

@router.patch("/escalations/{escalation_id}/status", response_model=HumanEscalationResponse, tags=["Escalations"])
def update_escalation_status_endpoint(
    escalation_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Update escalation status by authenticated operator."""
    esc = operations.update_escalation_status(db, escalation_id=escalation_id, new_status=payload.status)
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return esc

# --- Agent Action Logs ---
@router.get("/actions", response_model=List[AgentActionLogResponse], tags=["Actions"])
def list_actions(
    limit: int = 50,
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Internal system audit logs restricted to authenticated operators."""
    return operations.get_recent_action_logs(db, limit=limit)

# --- Dashboard Stats ---
@router.get("/dashboard/stats", response_model=DashboardStatsResponse, tags=["Dashboard"])
def get_dashboard_statistics(
    db: Session = Depends(get_db),
    operator: Dict[str, Any] = Depends(require_operator)
):
    """PROTECTED: Operational aggregated statistics restricted to authenticated operators."""
    return operations.get_dashboard_stats(db)
