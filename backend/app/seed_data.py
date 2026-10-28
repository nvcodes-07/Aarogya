import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import Doctor, DoctorSlot, Appointment, AmbulanceRequest, SupportTicket, HumanEscalation, AgentActionLog

# Asia/Kolkata offset is UTC+5:30
KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))

def get_kolkata_now():
    return datetime.now(KOLKATA_TZ)

SEED_DOCTORS = [
    {
        "name": "Dr. Ananya Sharma",
        "department": "Cardiology",
        "specialization": "Interventional Cardiology & Heart Health",
        "qualification": "MBBS, MD (Medicine), DM (Cardiology)",
        "experience_years": 14,
        "consultation_fee": 1000,
        "room_no": "OPD 204 (2nd Floor)",
        "opd_timings": "09:00 AM - 04:00 PM"
    },
    {
        "name": "Dr. Rahul Mehta",
        "department": "Orthopedics",
        "specialization": "Joint Replacement & Arthroscopic Surgery",
        "qualification": "MBBS, MS (Orthopedics), M.Ch (Ortho)",
        "experience_years": 16,
        "consultation_fee": 900,
        "room_no": "OPD 108 (1st Floor)",
        "opd_timings": "10:00 AM - 05:00 PM"
    },
    {
        "name": "Dr. Priya Nair",
        "department": "Dermatology",
        "specialization": "Clinical Dermatology & Trichology",
        "qualification": "MBBS, MD (Dermatology, Venereology & Leprosy)",
        "experience_years": 9,
        "consultation_fee": 750,
        "room_no": "OPD 312 (3rd Floor)",
        "opd_timings": "11:00 AM - 03:00 PM"
    },
    {
        "name": "Dr. Vikram Patel",
        "department": "General Medicine",
        "specialization": "Internal Medicine, Diabetes & Preventive Health",
        "qualification": "MBBS, MD (Internal Medicine), FICP",
        "experience_years": 19,
        "consultation_fee": 600,
        "room_no": "OPD 102 (1st Floor)",
        "opd_timings": "09:00 AM - 06:00 PM"
    }
]

SLOT_TIMES = [
    "10:00 AM",
    "11:30 AM",
    "02:00 PM",  # Afternoon
    "03:30 PM",  # Afternoon
    "04:30 PM"   # Afternoon
]

def seed_database(db: Session):
    """Seed initial doctors and dynamic future slots relative to Asia/Kolkata."""
    # 1. Seed Doctors
    existing_doctors = {d.name: d for d in db.query(Doctor).all()}
    created_doctors = []

    for doc_data in SEED_DOCTORS:
        if doc_data["name"] not in existing_doctors:
            doc = Doctor(**doc_data)
            db.add(doc)
            db.flush()
            created_doctors.append(doc)
        else:
            created_doctors.append(existing_doctors[doc_data["name"]])
    db.commit()

    # 2. Seed future slots for next 5 days
    now_kolkata = get_kolkata_now()
    all_doctors = db.query(Doctor).all()

    for doc in all_doctors:
        for day_offset in range(1, 6): # tomorrow to +5 days
            slot_date = (now_kolkata + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            for time_str in SLOT_TIMES:
                # Check if slot already exists
                existing_slot = db.query(DoctorSlot).filter(
                    DoctorSlot.doctor_id == doc.id,
                    DoctorSlot.slot_date == slot_date,
                    DoctorSlot.slot_time == time_str
                ).first()
                if not existing_slot:
                    new_slot = DoctorSlot(
                        doctor_id=doc.id,
                        slot_date=slot_date,
                        slot_time=time_str,
                        is_booked=False
                    )
                    db.add(new_slot)
    db.commit()

    # 3. Seed demonstration baseline records if tables are empty
    if db.query(Appointment).count() == 0:
        cardio_doc = db.query(Doctor).filter(Doctor.name == "Dr. Ananya Sharma").first()
        if cardio_doc:
            # Let's create one confirmed sample appointment
            tomorrow_date = (now_kolkata + timedelta(days=1)).strftime("%Y-%m-%d")
            # Mark slot booked
            slot = db.query(DoctorSlot).filter(
                DoctorSlot.doctor_id == cardio_doc.id,
                DoctorSlot.slot_date == tomorrow_date,
                DoctorSlot.slot_time == "10:00 AM"
            ).first()
            if slot:
                slot.is_booked = True
            
            sample_apt = Appointment(
                reference_code="APT-DEMO-1001",
                doctor_id=cardio_doc.id,
                doctor_name=cardio_doc.name,
                doctor_department=cardio_doc.department,
                patient_name="Rajesh Sharma",
                patient_phone="9826012345",
                appointment_date=tomorrow_date,
                appointment_time="10:00 AM",
                status="CONFIRMED",
                notes="Follow-up on ECG report"
            )
            db.add(sample_apt)

    if db.query(AmbulanceRequest).count() == 0:
        sample_amb = AmbulanceRequest(
            reference_code="AMB-DEMO-2001",
            patient_name="Suman Joshi",
            contact_phone="9876543210",
            pickup_address="Flat 402, Shanti Heights, AB Road, Indore",
            emergency_nature="Patient experiencing severe shortness of breath",
            status="REQUEST_RECORDED_DEMO",
            is_emergency_redirect=True,
            disclaimer="SIMULATED DEMO: This is a hackathon prototype request. No real ambulance has been dispatched. For medical emergencies, dial 108 / 112 immediately."
        )
        db.add(sample_amb)

    if db.query(SupportTicket).count() == 0:
        sample_ticket = SupportTicket(
            reference_code="TKT-DEMO-3001",
            patient_name="Kavita Sen",
            contact_phone="9425098765",
            category="BILLING",
            priority="HIGH",
            description="Pending cashless TPA claim reimbursement pre-auth status from Star Health.",
            status="OPEN"
        )
        db.add(sample_ticket)

    if db.query(HumanEscalation).count() == 0:
        sample_esc = HumanEscalation(
            reference_code="ESC-DEMO-4001",
            patient_name="Sunil Verma",
            contact_phone="9876543210",
            reason="Patient requested immediate callback from OPD duty coordinator regarding admission formalities.",
            priority="HIGH",
            status="OPEN",
            notes="Initial demonstration escalation record."
        )
        db.add(sample_esc)

    if db.query(AgentActionLog).count() == 0:
        sample_log = AgentActionLog(
            action_type="SYSTEM_INIT",
            tool_name="seed_database",
            parameters="{}",
            result_status="SUCCESS",
            result_summary="System initialized with Aarogya Multispeciality Hospital specialists & live slots."
        )
        db.add(sample_log)

    db.commit()
