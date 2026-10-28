from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

def generate_timestamp():
    return datetime.utcnow()

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False, index=True)
    specialization = Column(String(150), nullable=False)
    qualification = Column(String(100), nullable=False)
    experience_years = Column(Integer, default=5)
    consultation_fee = Column(Integer, default=800)
    room_no = Column(String(50), nullable=False)
    opd_timings = Column(String(100), default="09:00 AM - 04:00 PM")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=generate_timestamp)

    slots = relationship("DoctorSlot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")

class DoctorSlot(Base):
    __tablename__ = "doctor_slots"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    slot_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    slot_time = Column(String(20), nullable=False)              # e.g. "02:00 PM"
    is_booked = Column(Boolean, default=False)

    doctor = relationship("Doctor", back_populates="slots")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=generate_timestamp)

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    reference_code = Column(String(50), unique=True, nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    doctor_name = Column(String(100), nullable=False)
    doctor_department = Column(String(100), nullable=False)
    patient_name = Column(String(100), nullable=False)
    patient_phone = Column(String(20), nullable=False)
    appointment_date = Column(String(20), nullable=False)       # YYYY-MM-DD
    appointment_time = Column(String(20), nullable=False)       # e.g. "02:00 PM"
    status = Column(String(30), default="CONFIRMED")            # CONFIRMED, CANCELLED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=generate_timestamp)

    doctor = relationship("Doctor", back_populates="appointments")

class AmbulanceRequest(Base):
    __tablename__ = "ambulance_requests"

    id = Column(Integer, primary_key=True, index=True)
    reference_code = Column(String(50), unique=True, nullable=False, index=True)
    patient_name = Column(String(100), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    pickup_address = Column(Text, nullable=False)
    emergency_nature = Column(Text, nullable=True)
    status = Column(String(50), default="REQUEST_RECORDED_DEMO") # Strict requirement
    is_emergency_redirect = Column(Boolean, default=False)
    disclaimer = Column(Text, default="SIMULATED DEMO: This is a hackathon prototype request. No real ambulance has been dispatched. For medical emergencies, dial 108 / 112 immediately.")
    created_at = Column(DateTime, default=generate_timestamp)

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    reference_code = Column(String(50), unique=True, nullable=False, index=True)
    patient_name = Column(String(100), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)  # BILLING, APPOINTMENT, SERVICE, CALLBACK, GENERAL
    priority = Column(String(20), default="MEDIUM") # LOW, MEDIUM, HIGH, URGENT
    description = Column(Text, nullable=False)
    status = Column(String(30), default="OPEN")    # OPEN, RESOLVED
    created_at = Column(DateTime, default=generate_timestamp)

class HumanEscalation(Base):
    __tablename__ = "human_escalations"

    id = Column(Integer, primary_key=True, index=True)
    reference_code = Column(String(50), unique=True, nullable=False, index=True)
    patient_name = Column(String(100), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    priority = Column(String(20), default="HIGH")  # MEDIUM, HIGH, URGENT
    status = Column(String(30), default="PENDING") # PENDING, ATTENDED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=generate_timestamp)

class AgentActionLog(Base):
    __tablename__ = "agent_action_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(50), nullable=False) # TOOL_CALL, ESCALATION, FAULT, INTENT
    tool_name = Column(String(100), nullable=True)
    parameters = Column(Text, nullable=True)
    result_status = Column(String(30), nullable=False) # SUCCESS, FAILED, VALIDATION_ERROR
    result_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=generate_timestamp)
