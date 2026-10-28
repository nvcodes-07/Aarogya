import json
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models import Doctor, DoctorSlot, Appointment, AmbulanceRequest, SupportTicket, HumanEscalation, AgentActionLog, Patient
from app.config import settings

def generate_reference(prefix: str) -> str:
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{unique_suffix}"

# --- Doctors & Slots ---

def get_all_doctors(db: Session) -> List[Doctor]:
    return db.query(Doctor).filter(Doctor.is_active == True).all()

def get_doctor_by_id(db: Session, doctor_id: int) -> Optional[Doctor]:
    return db.query(Doctor).filter(Doctor.id == doctor_id, Doctor.is_active == True).first()

SPECIALTY_SYNONYM_MAP = {
    "cardiologist": "Cardiology",
    "cardiology": "Cardiology",
    "cardio": "Cardiology",
    "heart": "Cardiology",
    "orthopedic": "Orthopedics",
    "orthopedics": "Orthopedics",
    "orthopaedics": "Orthopedics",
    "orthopedist": "Orthopedics",
    "bone": "Orthopedics",
    "joint": "Orthopedics",
    "dermatologist": "Dermatology",
    "dermatology": "Dermatology",
    "skin": "Dermatology",
    "hair": "Dermatology",
    "derma": "Dermatology",
    "physician": "General Medicine",
    "general physician": "General Medicine",
    "internal medicine": "General Medicine",
    "general medicine": "General Medicine",
    "diabetes": "General Medicine",
    "fever": "General Medicine",
    "दिल": "Cardiology",
    "हड्डी": "Orthopedics",
    "त्वचा": "Dermatology"
}

def search_doctors(db: Session, query: Optional[str] = None, department: Optional[str] = None) -> List[Doctor]:
    q = db.query(Doctor).filter(Doctor.is_active == True)
    
    if department:
        dept_term = department.strip()
        for term, target_dept in SPECIALTY_SYNONYM_MAP.items():
            if term.lower() == dept_term.lower() or term.lower() in dept_term.lower():
                dept_term = target_dept
                break
        q = q.filter(Doctor.department.ilike(f"%{dept_term}%"))
        
    if query:
        cleaned_query = query.strip()
        conditions = [
            Doctor.name.ilike(f"%{cleaned_query}%"),
            Doctor.department.ilike(f"%{cleaned_query}%"),
            Doctor.specialization.ilike(f"%{cleaned_query}%"),
            Doctor.qualification.ilike(f"%{cleaned_query}%")
        ]
        # Also expand clinical and multilingual synonyms
        for term, target_dept in SPECIALTY_SYNONYM_MAP.items():
            if term.lower() in cleaned_query.lower():
                conditions.append(Doctor.department.ilike(f"%{target_dept}%"))
                conditions.append(Doctor.specialization.ilike(f"%{target_dept}%"))
                
        q = q.filter(or_(*conditions))

    return q.all()

def check_slots(db: Session, doctor_id: int, date: str) -> List[Dict[str, Any]]:
    """Return slots for a given doctor on a specific date (YYYY-MM-DD)."""
    slots = db.query(DoctorSlot).filter(
        DoctorSlot.doctor_id == doctor_id,
        DoctorSlot.slot_date == date.strip()
    ).order_by(DoctorSlot.id).all()
    
    return [
        {
            "id": s.id,
            "doctor_id": s.doctor_id,
            "slot_date": s.slot_date,
            "slot_time": s.slot_time,
            "is_booked": s.is_booked
        }
        for s in slots
    ]

# --- Appointments ---

def create_appointment(
    db: Session,
    doctor_id: int,
    patient_name: str,
    patient_phone: str,
    date: str,
    time_slot: str,
    notes: Optional[str] = None
) -> Appointment:
    # 1. Validate doctor
    doctor = get_doctor_by_id(db, doctor_id)
    if not doctor:
        log_action(db, "TOOL_CALL", "create_appointment", json.dumps({"doctor_id": doctor_id}), "FAILED", f"Doctor ID {doctor_id} not found.")
        raise ValueError(f"Doctor with ID {doctor_id} does not exist.")

    # 2. Check slot existence and availability
    slot = db.query(DoctorSlot).filter(
        DoctorSlot.doctor_id == doctor_id,
        DoctorSlot.slot_date == date.strip(),
        DoctorSlot.slot_time == time_slot.strip()
    ).first()

    if not slot:
        # Check if the doctor even works that day
        log_action(db, "TOOL_CALL", "create_appointment", json.dumps({"doctor_id": doctor_id, "date": date, "time": time_slot}), "FAILED", "Slot does not exist.")
        raise ValueError(f"No consultation slot found for {doctor.name} on {date} at {time_slot}.")

    if slot.is_booked:
        log_action(db, "TOOL_CALL", "create_appointment", json.dumps({"doctor_id": doctor_id, "date": date, "time": time_slot}), "FAILED", "Slot already booked.")
        raise ValueError(f"The slot {time_slot} on {date} for {doctor.name} is already occupied. Please select an available slot.")

    # 3. Check duplicate active booking for the same slot
    existing_apt = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == date.strip(),
        Appointment.appointment_time == time_slot.strip(),
        Appointment.status == "CONFIRMED"
    ).first()

    if existing_apt:
        slot.is_booked = True
        db.commit()
        raise ValueError(f"Slot {time_slot} on {date} is already confirmed under reference {existing_apt.reference_code}.")

    # 4. Mark slot as booked
    slot.is_booked = True

    # 5. Create appointment
    ref = generate_reference("APT")
    appointment = Appointment(
        reference_code=ref,
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        doctor_department=doctor.department,
        patient_name=patient_name.strip(),
        patient_phone=patient_phone.strip(),
        appointment_date=date.strip(),
        appointment_time=time_slot.strip(),
        status="CONFIRMED",
        notes=notes.strip() if notes else None
    )
    db.add(appointment)

    # 6. Upsert patient record
    patient = db.query(Patient).filter(Patient.phone_number == patient_phone.strip()).first()
    if not patient:
        patient = Patient(full_name=patient_name.strip(), phone_number=patient_phone.strip())
        db.add(patient)

    # 7. Log action
    log_action(
        db,
        "TOOL_CALL",
        "create_appointment",
        json.dumps({"doctor": doctor.name, "patient": patient_name, "date": date, "time": time_slot}),
        "SUCCESS",
        f"Appointment confirmed with {doctor.name} ({ref})."
    )

    db.commit()
    db.refresh(appointment)
    return appointment

# --- Ambulance Requests ---

def create_ambulance_request(
    db: Session,
    patient_name: str,
    contact_phone: str,
    pickup_address: str,
    emergency_nature: Optional[str] = None,
    is_emergency: bool = False
) -> AmbulanceRequest:
    ref = generate_reference("AMB")
    disclaimer = (
        "SIMULATED DEMO: This is a hackathon prototype request. "
        "No real ambulance has been dispatched. For medical emergencies, dial 108 / 112 immediately."
    )
    
    ambulance_req = AmbulanceRequest(
        reference_code=ref,
        patient_name=patient_name.strip(),
        contact_phone=contact_phone.strip(),
        pickup_address=pickup_address.strip(),
        emergency_nature=emergency_nature.strip() if emergency_nature else "Ambulance pickup requested",
        status="REQUEST_RECORDED_DEMO", # Strictly required
        is_emergency_redirect=is_emergency,
        disclaimer=disclaimer
    )
    db.add(ambulance_req)

    # If life-threatening emergency, record an immediate priority escalation
    if is_emergency:
        esc_ref = generate_reference("ESC-EMERG")
        escalation = HumanEscalation(
            reference_code=esc_ref,
            patient_name=patient_name.strip(),
            contact_phone=contact_phone.strip(),
            reason=f"CRITICAL EMERGENCY ALERT: Ambulance requested at {pickup_address}. Details: {emergency_nature or 'Urgent medical distress'}",
            priority="URGENT",
            status="PENDING",
            notes="Automatic escalation triggered by emergency detection. Patient instructed to call 108/112."
        )
        db.add(escalation)

    log_action(
        db,
        "TOOL_CALL",
        "create_ambulance_request",
        json.dumps({"patient": patient_name, "phone": contact_phone, "address": pickup_address}),
        "SUCCESS",
        f"Simulated ambulance request recorded ({ref}). Disclaimer shown."
    )

    db.commit()
    db.refresh(ambulance_req)
    return ambulance_req

# --- Support Tickets ---

def create_support_ticket(
    db: Session,
    patient_name: str,
    contact_phone: str,
    category: str,
    priority: str,
    description: str
) -> SupportTicket:
    ref = generate_reference("TKT")
    valid_categories = ["BILLING", "APPOINTMENT", "SERVICE", "CALLBACK", "GENERAL"]
    norm_category = category.upper().strip() if category.upper().strip() in valid_categories else "GENERAL"
    
    valid_priorities = ["LOW", "MEDIUM", "HIGH", "URGENT"]
    norm_priority = priority.upper().strip() if priority.upper().strip() in valid_priorities else "MEDIUM"

    ticket = SupportTicket(
        reference_code=ref,
        patient_name=patient_name.strip(),
        contact_phone=contact_phone.strip(),
        category=norm_category,
        priority=norm_priority,
        description=description.strip(),
        status="OPEN"
    )
    db.add(ticket)

    log_action(
        db,
        "TOOL_CALL",
        "create_support_ticket",
        json.dumps({"patient": patient_name, "category": norm_category, "priority": norm_priority}),
        "SUCCESS",
        f"Support ticket registered ({ref}) for category {norm_category}."
    )

    db.commit()
    db.refresh(ticket)
    return ticket

# --- Human Escalation ---

def escalate_to_human(
    db: Session,
    patient_name: str,
    contact_phone: str,
    reason: str,
    priority: str = "HIGH",
    notes: Optional[str] = None
) -> HumanEscalation:
    ref = generate_reference("ESC")
    valid_priorities = ["MEDIUM", "HIGH", "URGENT"]
    norm_priority = priority.upper().strip() if priority.upper().strip() in valid_priorities else "HIGH"

    escalation = HumanEscalation(
        reference_code=ref,
        patient_name=patient_name.strip(),
        contact_phone=contact_phone.strip(),
        reason=reason.strip(),
        priority=norm_priority,
        status="PENDING",
        notes=notes.strip() if notes else "Patient requested human coordinator intervention."
    )
    db.add(escalation)

    log_action(
        db,
        "ESCALATION",
        "escalate_to_human",
        json.dumps({"patient": patient_name, "reason": reason}),
        "SUCCESS",
        f"Human escalation filed ({ref}) with priority {norm_priority}."
    )

    db.commit()
    db.refresh(escalation)
    return escalation

# --- Action Logging ---

def log_action(
    db: Session,
    action_type: str,
    tool_name: Optional[str],
    parameters: Optional[str],
    result_status: str,
    result_summary: str
) -> AgentActionLog:
    log_entry = AgentActionLog(
        action_type=action_type,
        tool_name=tool_name,
        parameters=parameters,
        result_status=result_status,
        result_summary=result_summary
    )
    db.add(log_entry)
    db.flush()
    return log_entry

# --- Dashboard Queries ---

def get_recent_appointments(db: Session, limit: int = 50) -> List[Appointment]:
    return db.query(Appointment).order_by(Appointment.created_at.desc()).limit(limit).all()

def get_recent_ambulance_requests(db: Session, limit: int = 50) -> List[AmbulanceRequest]:
    return db.query(AmbulanceRequest).order_by(AmbulanceRequest.created_at.desc()).limit(limit).all()

def get_recent_tickets(db: Session, limit: int = 50) -> List[SupportTicket]:
    return db.query(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit).all()

def get_recent_escalations(db: Session, limit: int = 50) -> List[HumanEscalation]:
    return db.query(HumanEscalation).order_by(HumanEscalation.created_at.desc()).limit(limit).all()

def get_recent_action_logs(db: Session, limit: int = 50) -> List[AgentActionLog]:
    return db.query(AgentActionLog).order_by(AgentActionLog.created_at.desc()).limit(limit).all()

def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    return {
        "total_appointments": db.query(Appointment).count(),
        "total_ambulance_requests": db.query(AmbulanceRequest).count(),
        "total_support_tickets": db.query(SupportTicket).count(),
        "total_escalations": db.query(HumanEscalation).count(),
        "total_doctors": db.query(Doctor).filter(Doctor.is_active == True).count(),
        "system_mode": "AI-Powered (Groq/OpenAI)" if settings.is_ai_configured else "Deterministic Fallback Demo"
    }

def update_ticket_status(db: Session, ticket_id: int, new_status: str) -> Optional[SupportTicket]:
    tkt = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not tkt:
        return None
    tkt.status = new_status
    db.commit()
    db.refresh(tkt)
    log_action(
        db,
        action_type="ticket_status_updated",
        tool_name="update_ticket_status",
        parameters=f"ticket_id={ticket_id}, status={new_status}",
        result_status="SUCCESS",
        result_summary=f"Ticket #{tkt.reference_code} status updated to {new_status} by operator."
    )
    return tkt

def update_escalation_status(db: Session, escalation_id: int, new_status: str) -> Optional[HumanEscalation]:
    esc = db.query(HumanEscalation).filter(HumanEscalation.id == escalation_id).first()
    if not esc:
        return None
    esc.status = new_status
    db.commit()
    db.refresh(esc)
    log_action(
        db,
        action_type="escalation_status_updated",
        tool_name="update_escalation_status",
        parameters=f"escalation_id={escalation_id}, status={new_status}",
        result_status="SUCCESS",
        result_summary=f"Escalation #{esc.reference_code} status updated to {new_status} by operator."
    )
    return esc

