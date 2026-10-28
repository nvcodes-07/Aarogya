import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Doctor, DoctorSlot, Appointment, AmbulanceRequest, SupportTicket, HumanEscalation
from app.services import operations, knowledge, agent
from app.seed_data import seed_database

# Use in-memory SQLite for isolated fast tests
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    seed_database(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_health_and_seed_data(test_db):
    doctors = operations.get_all_doctors(test_db)
    assert len(doctors) >= 4
    names = [d.name for d in doctors]
    assert "Dr. Ananya Sharma" in names
    assert "Dr. Rahul Mehta" in names
    assert "Dr. Priya Nair" in names
    assert "Dr. Vikram Patel" in names

def test_search_doctors(test_db):
    cardio_docs = operations.search_doctors(test_db, query="cardiology")
    assert len(cardio_docs) >= 1
    assert cardio_docs[0].department == "Cardiology"

    name_docs = operations.search_doctors(test_db, query="Mehta")
    assert len(name_docs) >= 1
    assert "Mehta" in name_docs[0].name

def test_check_slots_and_booking_success(test_db):
    doc = test_db.query(Doctor).filter(Doctor.department == "Cardiology").first()
    assert doc is not None

    kolkata_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    tomorrow = (kolkata_now + timedelta(days=2)).strftime("%Y-%m-%d")

    slots = operations.check_slots(test_db, doc.id, tomorrow)
    assert len(slots) > 0
    test_slot = slots[0]
    time_str = test_slot["slot_time"]

    # Book appointment
    apt = operations.create_appointment(
        db=test_db,
        doctor_id=doc.id,
        patient_name="Amit Verma",
        patient_phone="9876543210",
        date=tomorrow,
        time_slot=time_str,
        notes="Heart checkup"
    )

    assert apt.id is not None
    assert apt.reference_code.startswith("APT-")
    assert apt.status == "CONFIRMED"
    assert apt.patient_name == "Amit Verma"

    # Verify slot is now booked
    updated_slots = operations.check_slots(test_db, doc.id, tomorrow)
    target_slot = next(s for s in updated_slots if s["slot_time"] == time_str)
    assert target_slot["is_booked"] is True

def test_duplicate_and_unavailable_slot_prevention(test_db):
    doc = test_db.query(Doctor).filter(Doctor.department == "Orthopedics").first()
    kolkata_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    target_date = (kolkata_now + timedelta(days=3)).strftime("%Y-%m-%d")

    # Book 02:00 PM
    operations.create_appointment(
        db=test_db,
        doctor_id=doc.id,
        patient_name="Sanjay Gupta",
        patient_phone="9811122233",
        date=target_date,
        time_slot="02:00 PM"
    )

    # Attempting to book the EXACT SAME occupied slot must raise ValueError
    with pytest.raises(ValueError) as exc:
        operations.create_appointment(
            db=test_db,
            doctor_id=doc.id,
            patient_name="Second Patient",
            patient_phone="9899988877",
            date=target_date,
            time_slot="02:00 PM"
        )
    assert "already occupied" in str(exc.value) or "already booked" in str(exc.value)

def test_ambulance_request_creation_and_disclaimer(test_db):
    req = operations.create_ambulance_request(
        db=test_db,
        patient_name="Rohit Sharma",
        contact_phone="9876543210",
        pickup_address="Vijay Nagar, Indore",
        emergency_nature="Breathing difficulty",
        is_emergency=False
    )

    assert req.id is not None
    assert req.reference_code.startswith("AMB-")
    assert req.status == "REQUEST_RECORDED_DEMO"
    assert "No real ambulance has been dispatched" in req.disclaimer
    assert "108" in req.disclaimer

def test_support_ticket_creation(test_db):
    tkt = operations.create_support_ticket(
        db=test_db,
        patient_name="Amit Verma",
        contact_phone="9876543210",
        category="BILLING",
        priority="HIGH",
        description="I have been waiting for a billing response for a long time. Please register my complaint."
    )

    assert tkt.id is not None
    assert tkt.reference_code.startswith("TKT-")
    assert tkt.category == "BILLING"
    assert tkt.priority == "HIGH"
    assert tkt.status == "OPEN"

def test_human_escalation_creation(test_db):
    esc = operations.escalate_to_human(
        db=test_db,
        patient_name="Sunita Rao",
        contact_phone="9876543210",
        reason="Patient requests to speak directly with an emergency coordinator",
        priority="HIGH"
    )

    assert esc.id is not None
    assert esc.reference_code.startswith("ESC-")
    assert esc.status == "PENDING"

def test_hospital_knowledge_faq_retrieval():
    faq = knowledge.search_hospital_faq("What are the visiting hours for ICU?")
    assert faq is not None
    assert "Visiting Hours" in faq["category"]
    assert "11:00 AM" in faq["answer"]

    faq2 = knowledge.search_hospital_faq("Does hospital support cashless Star Health or HDFC insurance?")
    assert faq2 is not None
    assert "Billing" in faq2["category"]
    assert "Star Health" in faq2["answer"]

    # Policy not in knowledge base
    unknown = knowledge.search_hospital_faq("Do you provide helicopter parking on the roof?")
    assert unknown is None

def test_agent_multi_turn_and_explicit_confirmation(test_db):
    session_id = "test-session-multi-turn"

    # Turn 1: Patient asks for cardiologist tomorrow
    resp1 = agent.handle_deterministic_turn(
        db=test_db,
        message="I want to see a cardiologist tomorrow.",
        session_id=session_id,
        history=[],
        pending_booking=None
    )
    assert "Dr. Ananya Sharma" in resp1.reply
    assert "Available Slots:" in resp1.reply

    # Turn 2: Patient picks 2 PM with history from Turn 1
    h1 = [{"role": "user", "content": "I want to see a cardiologist tomorrow."}]
    resp2 = agent.handle_deterministic_turn(
        db=test_db,
        message="2 PM",
        session_id=session_id,
        history=h1,
        pending_booking=None
    )
    assert "02:00 PM" in resp2.reply
    assert "Patient Full Name" in resp2.reply
    assert "10-digit Phone Number" in resp2.reply

    # Turn 3: Patient provides name and phone number with accumulated history
    h2 = h1 + [
        {"role": "assistant", "content": resp1.reply},
        {"role": "user", "content": "2 PM"}
    ]
    resp3 = agent.handle_deterministic_turn(
        db=test_db,
        message="Amit Verma, 9876543210",
        session_id=session_id,
        history=h2,
        pending_booking=None
    )
    assert resp3.pending_booking is not None
    assert resp3.pending_booking.patient_name == "Amit Verma"
    assert resp3.pending_booking.patient_phone == "9876543210"
    assert "Please Confirm Your Appointment Details" in resp3.reply
    assert "Shall I go ahead and confirm" in resp3.reply

    # Turn 4: Patient explicitly confirms
    resp4 = agent.handle_deterministic_turn(
        db=test_db,
        message="Yes, confirm it.",
        session_id=session_id,
        history=[],
        pending_booking=resp3.pending_booking
    )
    assert resp4.action_performed == "appointment_booked"
    assert resp4.action_reference.startswith("APT-")
    assert "Appointment Confirmed!" in resp4.reply
    assert resp4.pending_booking is None

    # Verify write in DB
    db_apt = test_db.query(Appointment).filter(Appointment.reference_code == resp4.action_reference).first()
    assert db_apt is not None
    assert db_apt.patient_name == "Amit Verma"
    assert db_apt.appointment_time == "02:00 PM"

def test_agent_emergency_guidance(test_db):
    resp = agent.handle_deterministic_turn(
        db=test_db,
        message="Patient has severe chest pain and is not breathing! Help!",
        session_id="test-session-2",
        history=[],
        pending_booking=None
    )

    assert "CRITICAL MEDICAL EMERGENCY ALERT" in resp.reply
    assert "108 / 112" in resp.reply
    assert "0731-4999999" in resp.reply
    assert resp.action_performed == "emergency_escalated"
