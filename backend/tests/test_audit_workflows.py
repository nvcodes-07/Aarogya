import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Doctor, DoctorSlot, Appointment, AmbulanceRequest, SupportTicket, HumanEscalation
from app.services import operations, knowledge, agent
from app.seed_data import seed_database

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

def test_workflow_a_appointment_complete_sequence(test_db):
    """
    Workflow A:
    1. Patient asks for a cardiologist appointment tomorrow afternoon.
    2. The agent checks available slots using the backend.
    3. The agent asks for missing patient details.
    4. It presents a booking summary and requests confirmation.
    5. The patient confirms.
    6. The backend validates the slot and creates the appointment.
    7. The agent displays the actual booking reference returned by the backend.
    8. The operations dashboard shows the new appointment.
    Verify that an appointment is not created before confirmation and that unavailable or duplicate slots are rejected.
    """
    session_id = "wf-a-session"
    initial_apt_count = test_db.query(Appointment).count()

    # Step 1: Patient asks for cardiologist appointment tomorrow afternoon
    resp1 = agent.handle_deterministic_turn(
        db=test_db,
        message="I want to book an appointment with a cardiologist tomorrow afternoon",
        session_id=session_id,
        history=[],
        pending_booking=None
    )

    # Step 2 & 3: Agent checks available slots and asks for missing details
    assert "Dr. Ananya Sharma" in resp1.reply
    assert "02:00 PM" in resp1.reply
    assert "Patient Full Name" in resp1.reply
    assert "Phone Number" in resp1.reply
    assert resp1.pending_booking is None
    # Crucial check: Appointment must NOT be created yet
    assert test_db.query(Appointment).count() == initial_apt_count

    # Step 4: Patient provides name & phone (testing non-'am' name)
    history_turn1 = [
        {"role": "user", "content": "I want to book an appointment with a cardiologist tomorrow afternoon"},
        {"role": "assistant", "content": resp1.reply}
    ]
    resp2 = agent.handle_deterministic_turn(
        db=test_db,
        message="Suresh Gupta, 9876543210",
        session_id=session_id,
        history=history_turn1,
        pending_booking=None
    )

    # Agent presents booking summary and requests confirmation
    assert resp2.pending_booking is not None
    assert resp2.pending_booking.doctor_name == "Dr. Ananya Sharma"
    assert resp2.pending_booking.patient_name == "Suresh Gupta"
    assert resp2.pending_booking.patient_phone == "9876543210"
    assert "Please Confirm Your Appointment Details" in resp2.reply
    assert "Dr. Ananya Sharma" in resp2.reply
    assert "02:00 PM" in resp2.reply
    # Still NOT created before confirmation!
    assert test_db.query(Appointment).count() == initial_apt_count

    # Step 5: Patient confirms
    resp3 = agent.handle_deterministic_turn(
        db=test_db,
        message="Yes, confirm it.",
        session_id=session_id,
        history=history_turn1 + [{"role": "user", "content": "Suresh Gupta, 9876543210"}, {"role": "assistant", "content": resp2.reply}],
        pending_booking=resp2.pending_booking
    )

    # Step 6 & 7: Backend creates appointment and agent displays actual booking reference
    assert resp3.action_performed == "appointment_booked"
    assert resp3.action_reference is not None
    assert resp3.action_reference.startswith("APT-")
    assert resp3.action_reference in resp3.reply
    assert "Appointment Confirmed!" in resp3.reply
    assert resp3.pending_booking is None

    # Step 8: Database shows new appointment
    assert test_db.query(Appointment).count() == initial_apt_count + 1
    new_apt = test_db.query(Appointment).filter(Appointment.reference_code == resp3.action_reference).first()
    assert new_apt is not None
    assert new_apt.patient_name == "Suresh Gupta"
    assert new_apt.doctor_name == "Dr. Ananya Sharma"
    assert new_apt.appointment_time == "02:00 PM"

    # Verify duplicate / unavailable slot rejection
    with pytest.raises(ValueError) as exc:
        operations.create_appointment(
            db=test_db,
            doctor_id=new_apt.doctor_id,
            patient_name="Second Patient",
            patient_phone="9123456780",
            date=new_apt.appointment_date,
            time_slot="02:00 PM"
        )
    assert "already occupied" in str(exc.value) or "already booked" in str(exc.value)

def test_workflow_b_hospital_faq(test_db):
    """
    Workflow B:
    Ask about OPD timings and documents required for an appointment.
    Verify answers come from configured hospital knowledge base.
    Verify that ungrounded queries acknowledge limitation rather than invent policies.
    """
    # 1. OPD timings
    resp_opd = agent.handle_deterministic_turn(
        db=test_db,
        message="What are the OPD timings?",
        session_id="wf-b",
        history=[],
        pending_booking=None
    )
    assert "09:00 AM to 01:00 PM" in resp_opd.reply
    assert "OPD Timings" in resp_opd.reply

    # 2. Documents required
    resp_docs = agent.handle_deterministic_turn(
        db=test_db,
        message="What documents are required for an appointment?",
        session_id="wf-b",
        history=[],
        pending_booking=None
    )
    assert "prescriptions" in resp_docs.reply or "photo ID" in resp_docs.reply or "Aadhaar" in resp_docs.reply

    # 3. Ungrounded question acknowledging limitation
    resp_unknown = agent.handle_deterministic_turn(
        db=test_db,
        message="What is the hospital policy on bringing exotic pets?",
        session_id="wf-b",
        history=[],
        pending_booking=None
    )
    assert "not found in our verified" in resp_unknown.reply or "not available" in resp_unknown.reply
    assert "do not speculate or invent hospital policies" in resp_unknown.reply

def test_workflow_c_simulated_ambulance(test_db):
    """
    Workflow C:
    Submit simulated ambulance request.
    Verify validated, persisted, unique reference generated, disclaimer that no real ambulance dispatched.
    """
    initial_count = test_db.query(AmbulanceRequest).count()
    msg = "I need an ambulance for my father near Vijay Nagar, Indore. Contact 9876543210."
    resp = agent.handle_deterministic_turn(
        db=test_db,
        message=msg,
        session_id="wf-c",
        history=[],
        pending_booking=None
    )

    assert resp.action_performed == "ambulance_recorded"
    assert resp.action_reference.startswith("AMB-")
    assert "No real ambulance has been dispatched" in resp.reply
    assert "108 / 112" in resp.reply

    # Check persistence
    assert test_db.query(AmbulanceRequest).count() == initial_count + 1
    amb = test_db.query(AmbulanceRequest).filter(AmbulanceRequest.reference_code == resp.action_reference).first()
    assert amb is not None
    assert amb.status == "REQUEST_RECORDED_DEMO"
    assert "Vijay Nagar" in amb.pickup_address

def test_workflow_d_complaint_and_escalation(test_db):
    """
    Workflow D:
    Submit a billing complaint and separately request a human representative.
    Verify ticket and escalation records written to DB.
    """
    init_tickets = test_db.query(SupportTicket).count()
    init_escs = test_db.query(HumanEscalation).count()

    # Complaint
    resp_tkt = agent.handle_deterministic_turn(
        db=test_db,
        message="I have been waiting for a billing response for a long time. Please register my complaint.",
        session_id="wf-d",
        history=[],
        pending_booking=None
    )
    assert resp_tkt.action_performed == "ticket_created"
    assert resp_tkt.action_reference.startswith("TKT-")
    assert test_db.query(SupportTicket).count() == init_tickets + 1
    tkt = test_db.query(SupportTicket).filter(SupportTicket.reference_code == resp_tkt.action_reference).first()
    assert tkt is not None
    assert tkt.category == "BILLING"
    assert tkt.status == "OPEN"

    # Human escalation
    resp_esc = agent.handle_deterministic_turn(
        db=test_db,
        message="I want to speak with a human representative.",
        session_id="wf-d",
        history=[],
        pending_booking=None
    )
    assert resp_esc.action_performed == "escalation_recorded"
    assert resp_esc.action_reference.startswith("ESC-")
    assert test_db.query(HumanEscalation).count() == init_escs + 1
    esc = test_db.query(HumanEscalation).filter(HumanEscalation.reference_code == resp_esc.action_reference).first()
    assert esc is not None
    assert esc.status == "PENDING"

