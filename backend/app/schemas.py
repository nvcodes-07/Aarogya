from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

# --- Doctors & Slots ---
class DoctorSlotSchema(BaseModel):
    id: int
    doctor_id: int
    slot_date: str
    slot_time: str
    is_booked: bool

    model_config = ConfigDict(from_attributes=True)

class DoctorSchema(BaseModel):
    id: int
    name: str
    department: str
    specialization: str
    qualification: str
    experience_years: int
    consultation_fee: int
    room_no: str
    opd_timings: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

# --- Appointments ---
class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_name: str = Field(..., min_length=2, max_length=100)
    patient_phone: str = Field(..., min_length=10, max_length=15)
    appointment_date: str = Field(..., description="Format: YYYY-MM-DD")
    appointment_time: str = Field(..., description="Format: e.g. 02:00 PM")
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: int
    reference_code: str
    doctor_id: int
    doctor_name: str
    doctor_department: str
    patient_name: str
    patient_phone: str
    appointment_date: str
    appointment_time: str
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Ambulance Requests ---
class AmbulanceRequestCreate(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=100)
    contact_phone: str = Field(..., min_length=10, max_length=15)
    pickup_address: str = Field(..., min_length=5)
    emergency_nature: Optional[str] = None
    is_emergency: bool = False

class AmbulanceRequestResponse(BaseModel):
    id: int
    reference_code: str
    patient_name: str
    contact_phone: str
    pickup_address: str
    emergency_nature: Optional[str]
    status: str
    is_emergency_redirect: bool
    disclaimer: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Support Tickets ---
class SupportTicketCreate(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=100)
    contact_phone: str = Field(..., min_length=10, max_length=15)
    category: str = Field(..., description="BILLING, APPOINTMENT, SERVICE, CALLBACK, GENERAL")
    priority: str = Field("MEDIUM", description="LOW, MEDIUM, HIGH, URGENT")
    description: str = Field(..., min_length=5)

class SupportTicketResponse(BaseModel):
    id: int
    reference_code: str
    patient_name: str
    contact_phone: str
    category: str
    priority: str
    description: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Human Escalation ---
class HumanEscalationCreate(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=100)
    contact_phone: str = Field(..., min_length=10, max_length=15)
    reason: str = Field(..., min_length=3)
    priority: str = "HIGH"
    notes: Optional[str] = None

class HumanEscalationResponse(BaseModel):
    id: int
    reference_code: str
    patient_name: str
    contact_phone: str
    reason: str
    priority: str
    status: str
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Agent Action Logs ---
class AgentActionLogResponse(BaseModel):
    id: int
    action_type: str
    tool_name: Optional[str]
    parameters: Optional[str]
    result_status: str
    result_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Dashboard Overview Stats ---
class DashboardStatsResponse(BaseModel):
    total_appointments: int
    total_ambulance_requests: int
    total_support_tickets: int
    total_escalations: int
    total_doctors: int
    system_mode: str

# --- Chat Interaction ---
class ChatMessage(BaseModel):
    role: str # "user" | "assistant" | "system"
    content: str

class PendingBookingState(BaseModel):
    doctor_id: int
    doctor_name: str
    doctor_department: str
    consultation_fee: int
    appointment_date: str
    appointment_time: str
    patient_name: str
    patient_phone: str
    notes: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default-session"
    history: Optional[List[ChatMessage]] = []
    pending_booking: Optional[PendingBookingState] = None

class ChatResponse(BaseModel):
    reply: str
    mode: str # "ai" or "deterministic_demo"
    session_id: str
    action_performed: Optional[str] = None
    action_reference: Optional[str] = None
    pending_booking: Optional[PendingBookingState] = None
    structured_data: Optional[Dict[str, Any]] = None
    suggested_prompts: Optional[List[str]] = None

# --- Operator Authentication ---
class OperatorLoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)

class OperatorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    username: str
    role: str = "hospital_operator"
    hospital: str

class OperatorInfoResponse(BaseModel):
    username: str
    role: str
    hospital: str

class StatusUpdateRequest(BaseModel):
    status: str = Field(..., min_length=2)

