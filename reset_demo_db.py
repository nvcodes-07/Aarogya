#!/usr/bin/env python3
"""
AarogyaConnect AI - Safe Demo Database Reset Script
Resets the SQLite database and seeds realistic fictional doctors and upcoming slots.
"""
import os
import sys

# Ensure backend directory is resolved relative to this script's directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
VENV_PYTHON = os.path.join(PROJECT_ROOT, "venv", "bin", "python3")

# Auto-re-execute using the project virtual environment if dependencies are missing
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    try:
        import sqlalchemy  # Check if current interpreter has required dependencies
    except ImportError:
        os.execv(VENV_PYTHON, [VENV_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.database import engine, Base, SessionLocal
from app import models  # Explicitly load all schema models onto Base.metadata
from app.seed_data import seed_database
from app.config import settings

def reset_database():
    print("🏥 Resetting AarogyaConnect AI Demonstration Database...")
    
    # Dispose active connection pools
    engine.dispose()

    # Drop all existing tables
    Base.metadata.drop_all(bind=engine)
    print("✓ Cleared existing records and tables.")

    # Re-create fresh schema
    Base.metadata.create_all(bind=engine)
    print("✓ Created fresh database schema.")

    # Re-seed realistic doctors and upcoming slots
    db = SessionLocal()
    try:
        seed_database(db)
        
        # Count seeded records for verification summary
        doc_count = db.query(models.Doctor).count()
        slot_count = db.query(models.DoctorSlot).count()
        apt_count = db.query(models.Appointment).count()
        amb_count = db.query(models.AmbulanceRequest).count()
        tkt_count = db.query(models.SupportTicket).count()
        esc_count = db.query(models.HumanEscalation).count()

        print("✓ Seeded realistic hospital data:")
        print(f"  • {doc_count} Doctors across Cardiology, Orthopedics, Dermatology, and General Medicine")
        print(f"  • {slot_count} Available OPD appointment slots for the next 5 days")
        print(f"  • {apt_count} Baseline confirmed appointment (Dr. Ananya Sharma)")
        print(f"  • {amb_count} Baseline simulated ambulance request")
        print(f"  • {tkt_count} Baseline support ticket (Cashless insurance query)")
        print(f"  • {esc_count} Baseline human escalation record")
    finally:
        db.close()
        engine.dispose()

    print("\n✅ Database reset successfully completed!")
    print(f"Database location: {settings.DATABASE_URL}")
    print("The system is now primed for a clean hackathon presentation.")

if __name__ == "__main__":
    reset_database()
