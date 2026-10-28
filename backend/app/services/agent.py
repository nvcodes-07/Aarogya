import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Doctor
from app.schemas import ChatResponse, PendingBookingState
from app.services import operations, knowledge

KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))

def get_kolkata_now():
    return datetime.now(KOLKATA_TZ)

SYSTEM_PROMPT = """You are AarogyaConnect AI, the action-oriented digital customer operations agent for Aarogya Multispeciality Hospital (Indore, India).
Hospital Tagline: "From patient conversations to completed hospital workflows."

Role & Tone:
- You are an empathetic, courteous, professional, and efficient healthcare operations assistant.
- You respond in the same language the patient used (fluent English or natural, clear Hindi / Hinglish).
- Keep answers patient-friendly, helpful, and concise.

STRICT GROUNDING & HOSPITAL DATABASE PROTOCOL:
- You are directly connected to the hospital's live SQLite database and verified policy knowledge base through tools.
- NEVER invent doctors, fees, room numbers, open slots, appointment IDs, or policies.
- Every specific fact about doctors, slots, policies, or actions MUST come from calling the approved tools.
- If a user asks about a policy not present in the verified hospital FAQ, clearly acknowledge that this information is not found in hospital verified records and offer to connect them with a human coordinator.

AVAILABLE TOOLS & WORKFLOW RULES:
1. search_doctors(query, department):
   Call to search hospital specialists (Cardiology, Orthopedics, Dermatology, General Medicine).
2. check_slots(doctor_id, date):
   Call to check real-time available appointment slots for a doctor on a specific date (YYYY-MM-DD).
3. prepare_appointment_confirmation(doctor_id, date, time_slot, patient_name, patient_phone, notes):
   When the patient provides their preferred doctor, date, slot time, patient name, and phone number, call this tool to validate availability and stage the booking summary.
   DO NOT confirm the booking yet! Present the summary clearly and ask the patient: "Would you like me to confirm this appointment?"
4. confirm_appointment(doctor_id, date, time_slot, patient_name, patient_phone, notes):
   Call ONLY when the patient has explicitly confirmed (e.g. "Yes", "Confirm", "Proceed", "हाँ, कन्फर्म करें").
5. search_hospital_faq(query):
   Call for questions regarding hospital OPD hours, visiting policies, cashless TPA insurance, required documents, or diagnostic fasting.
6. create_ambulance_request(patient_name, contact_phone, pickup_address, emergency_nature, is_emergency):
   Call to register a simulated prototype ambulance demo request. Always remind the patient that this is a simulated demo and for real emergencies dial 108 / 112 immediately.
7. create_support_ticket(patient_name, contact_phone, category, priority, description):
   Call to register a formal support grievance (Billing, Appointment, Service, Callback).
8. escalate_to_human(patient_name, contact_phone, reason, priority):
   Call when the user asks to speak with a human or when a grievance needs manual coordinator followup.

EMERGENCY PROTOCOL:
For life-threatening emergencies (chest pain, collapsed, unconscious, severe breathing difficulty), immediately tell the patient to call National Emergency Services (108 / 112) without delay.

PRIVACY & ACCESS RESTRICTIONS:
You are serving on the public patient portal. NEVER disclose other patients' records, hospital-wide appointment lists, all support tickets, or internal escalations. If requested, explain that hospital-wide operational records are restricted to authenticated hospital operators."""

# --- Tool Definitions for OpenAI-compatible LLMs ---
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_doctors",
            "description": "Search hospital doctors by name, specialization, or department.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Doctor name or specialty keyword (e.g. cardiologist, Sharma)"},
                    "department": {"type": "string", "description": "Department name (e.g. Cardiology, Orthopedics)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_slots",
            "description": "Check real-time slot availability for a doctor on a specific date (YYYY-MM-DD) when a patient is inquiring about available times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "integer", "description": "Doctor ID"},
                    "date": {"type": "string", "description": "Date formatted as YYYY-MM-DD"}
                },
                "required": ["doctor_id", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_appointment_confirmation",
            "description": "Call this tool whenever a patient provides or agrees on a doctor, date, time slot, patient name, and phone number. This validates slot availability and stages the booking summary for explicit confirmation. Never confirm without calling this first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "integer"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_slot": {"type": "string", "description": "e.g. 02:00 PM"},
                    "patient_name": {"type": "string"},
                    "patient_phone": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["doctor_id", "date", "time_slot", "patient_name", "patient_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_appointment",
            "description": "Create verified appointment in SQLite database AFTER explicit patient confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "integer"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_slot": {"type": "string", "description": "e.g. 02:00 PM"},
                    "patient_name": {"type": "string"},
                    "patient_phone": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["doctor_id", "date", "time_slot", "patient_name", "patient_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hospital_faq",
            "description": "Retrieve hospital policies, OPD timings, visiting hours, cashless insurance, and test prep instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The policy or hospital question"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_ambulance_request",
            "description": "Record a simulated demo ambulance request in the hospital database. Call this tool whenever a patient asks to request or dispatch an ambulance and provides pickup address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "contact_phone": {"type": "string"},
                    "pickup_address": {"type": "string"},
                    "emergency_nature": {"type": "string"},
                    "is_emergency": {"type": "boolean"}
                },
                "required": ["patient_name", "contact_phone", "pickup_address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Register a formal hospital grievance or support ticket in SQLite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "contact_phone": {"type": "string"},
                    "category": {"type": "string", "enum": ["BILLING", "APPOINTMENT", "SERVICE", "CALLBACK", "GENERAL"]},
                    "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"]},
                    "description": {"type": "string"}
                },
                "required": ["patient_name", "contact_phone", "category", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate conversation to a human hospital duty manager or operator.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string"},
                    "contact_phone": {"type": "string"},
                    "reason": {"type": "string"},
                    "priority": {"type": "string", "enum": ["MEDIUM", "HIGH", "URGENT"]}
                },
                "required": ["patient_name", "contact_phone", "reason"]
            }
        }
    }
]

# --- Helper Intent Parsers for Deterministic Mode ---

def parse_date_intent(text: str) -> str:
    """Parse relative date expressions (tomorrow, day after tomorrow, today) to YYYY-MM-DD."""
    now = get_kolkata_now()
    lower = text.lower()
    
    # Explicit YYYY-MM-DD
    date_match = re.search(r"\b(202\d-[0-1]\d-[0-3]\d)\b", text)
    if date_match:
        return date_match.group(1)

    if "day after tomorrow" in lower:
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")
    elif "tomorrow" in lower:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "today" in lower:
        return now.strftime("%Y-%m-%d")
    
    # Default to tomorrow for bookings if unspecified
    return (now + timedelta(days=1)).strftime("%Y-%m-%d")

def parse_time_slot(text: str) -> Optional[str]:
    """Parse time slot from text (e.g. '2 PM', '2:00 PM', '10 AM', '11:30 AM', 'afternoon')."""
    lower = text.lower()
    if re.search(r"\b10(?::00)?\s*am\b", lower):
        return "10:00 AM"
    if re.search(r"\b11(?::30)?\s*am\b", lower):
        return "11:30 AM"
    if re.search(r"\b(?:0?2(?::00)?\s*pm|afternoon)\b", lower):
        return "02:00 PM"
    if re.search(r"\b(?:0?3(?::30)?\s*pm)\b", lower):
        return "03:30 PM"
    if re.search(r"\b(?:0?4(?::30)?\s*pm)\b", lower):
        return "04:30 PM"
    return None

def extract_phone(text: str) -> Optional[str]:
    """Extract a 10-digit Indian phone number."""
    match = re.search(r"\b([6-9]\d{9})\b", text)
    if match:
        return match.group(1)
    match2 = re.search(r"(?:\+91[\-\s]?)?([6-9]\d{4}[\-\s]?\d{5})", text)
    if match2:
        return re.sub(r"\D", "", match2.group(1))[-10:]
    return None

def extract_name(text: str) -> Optional[str]:
    """Extract patient name from patterns like 'I am Amit Verma', 'My name is Amit Verma', or 'Amit Verma, 9876543210'."""
    cleaned = text.strip()
    
    # 1. Explicit intro patterns: "I am X", "My name is X", "Patient name is X", "Name: X"
    m1 = re.search(r"(?:i am|my name is|patient(?:'s)?(?:\s+name)?(?:\s*is)?(?:\s*:)?|name(?:\s*is)?(?:\s*:)?)\s+([A-Za-z][A-Za-z\s\']{1,35})", cleaned, re.IGNORECASE)
    if m1:
        raw_name = re.split(r"[\.,;\n\?!]|phone|mobile|contact|\d|\band\b|\bi\s+want\b|\bi\s+need\b|\blooking\b", m1.group(1), flags=re.I)[0].strip()
        words = [w for w in raw_name.split() if w.lower() not in {"a", "an", "the", "patient", "mr", "mrs", "dr", "ms"}]
        if 1 <= len(words) <= 4:
            candidate = " ".join(words)
            if len(candidate) >= 2 and candidate.lower() not in {"here", "there", "interested", "writing", "calling", "asking"}:
                return candidate.title()

    # 2. Name followed by phone: "Amit Verma, 9876543210" or "Suresh Gupta 9876543210"
    phone_match = re.search(r"(?:\+91[\-\s]?)?[6-9]\d{9}", cleaned)
    if phone_match:
        prefix = cleaned[:phone_match.start()].strip(" ,-:\t")
        if prefix:
            prefix = re.sub(r"^(?:patient|name|contact|for)\s*[:\-]?\s*", "", prefix, flags=re.I).strip(" ,-:")
            prefix = re.split(r"[\.\n;!]", prefix)[-1].strip()
            if re.match(r"^[A-Za-z][A-Za-z\s\.\']{1,40}$", prefix) and len(prefix) >= 2:
                words = prefix.split()
                if 1 <= len(words) <= 4 and prefix.lower() not in {"yes", "confirm", "please", "hi", "hello", "ok", "okay", "sure"}:
                    return prefix.title()

    return None

def extract_address(text: str) -> Optional[str]:
    """Extract pickup address for ambulance requests."""
    phone_match = re.search(r"(?:\+91[\-\s]?)?[6-9]\d{9}", text)
    text_no_phone = (text[:phone_match.start()] + text[phone_match.end():]) if phone_match else text

    m = re.search(r"(?:pickup address(?:\s+is)?|address(?:\s+is)?|location(?:\s+is)?|pickup(?:\s+at|\s+from)?|near|at)\s+([A-Za-z0-9\s,\-\/\.\#]{4,100})", text_no_phone, re.IGNORECASE)
    if m:
        addr = m.group(1).strip()
        addr = re.split(r"[\.\n;]|contact|phone|patient|mobile", addr, flags=re.I)[0].strip(" ,-:")
        if len(addr) >= 4:
            return addr

    m2 = re.search(r"\b([A-Za-z0-9\s,\-\/]{4,50}(?:indore|nagar|colony|road|bypass|square|chowk|street|hospital|bhavan|enclave))\b", text_no_phone, re.I)
    if m2:
        return m2.group(1).strip(" ,-:")

    if "indore" in text.lower():
        return "Vijay Nagar, Indore"
    return None

def is_confirmation(text: str) -> bool:
    lower = text.lower().strip()
    confirm_phrases = ["yes", "confirm", "confirm it", "proceed", "book it", "please confirm", "sure", "yep", "yeah", "ok", "okay", "go ahead"]
    return any(p in lower for p in confirm_phrases)

def is_cancellation(text: str) -> bool:
    lower = text.lower().strip()
    cancel_phrases = ["no", "cancel", "cancel it", "don't", "stop", "change", "abort", "not now"]
    return any(p in lower for p in cancel_phrases)

def is_emergency_query(text: str) -> bool:
    lower = text.lower()
    emergency_keywords = [
        "heart attack", "chest pain", "unconscious", "not breathing", "cannot breathe",
        "heavy bleeding", "severe bleeding", "stroke", "paralysis", "collapsed", "cardiac arrest",
        "unresponsive", "choking", "seizure", "dying", "severe head injury"
    ]
    return any(kw in lower for kw in emergency_keywords)


# --- Deterministic Orchestrator (Robust Demo Mode) ---

def handle_deterministic_turn(
    db: Session,
    message: str,
    session_id: str,
    history: List[Any],
    pending_booking: Optional[PendingBookingState]
) -> ChatResponse:
    text = message.strip()
    lower = text.lower()

    # 1. PENDING CONFIRMATION RESOLUTION
    if pending_booking:
        if is_confirmation(text):
            # Attempt real database write
            try:
                appointment = operations.create_appointment(
                    db=db,
                    doctor_id=pending_booking.doctor_id,
                    patient_name=pending_booking.patient_name,
                    patient_phone=pending_booking.patient_phone,
                    date=pending_booking.appointment_date,
                    time_slot=pending_booking.appointment_time,
                    notes=pending_booking.notes
                )
                reply = (
                    f"✅ **Appointment Confirmed!**\n\n"
                    f"• **Reference ID:** `{appointment.reference_code}`\n"
                    f"• **Doctor:** {appointment.doctor_name} ({appointment.doctor_department})\n"
                    f"• **Date & Time:** {appointment.appointment_date} at {appointment.appointment_time}\n"
                    f"• **Patient:** {appointment.patient_name} ({appointment.patient_phone})\n"
                    f"• **Location:** OPD Desk, Aarogya Multispeciality Hospital\n\n"
                    f"A confirmation SMS has been simulated. This booking is now live on the hospital operations dashboard."
                )
                return ChatResponse(
                    reply=reply,
                    mode="deterministic_demo",
                    session_id=session_id,
                    action_performed="appointment_booked",
                    action_reference=appointment.reference_code,
                    pending_booking=None,
                    structured_data={
                        "type": "appointment",
                        "reference_code": appointment.reference_code,
                        "doctor_name": appointment.doctor_name,
                        "date": appointment.appointment_date,
                        "time": appointment.appointment_time,
                        "patient_name": appointment.patient_name
                    },
                    suggested_prompts=["Check appointment prep instructions", "Register an ambulance request", "Ask about visiting hours"]
                )
            except ValueError as e:
                # Slot became unavailable
                return ChatResponse(
                    reply=f"⚠️ **Could not complete booking:** {str(e)}\n\nWould you like to select an alternative slot?",
                    mode="deterministic_demo",
                    session_id=session_id,
                    pending_booking=None,
                    suggested_prompts=["Search cardiologists", "View tomorrow's afternoon slots"]
                )
        elif is_cancellation(text):
            return ChatResponse(
                reply="❌ The pending appointment booking has been cancelled as requested. No records were created in the system. How else may I assist you?",
                mode="deterministic_demo",
                session_id=session_id,
                pending_booking=None,
                suggested_prompts=["Find another doctor", "Hospital OPD timings", "Ambulance request"]
            )

    # 2. PRIVACY & ACCESS CONTROL: Deny patient access to hospital-wide records or other patients' data
    if any(phrase in lower for phrase in [
        "all appointments", "other patients", "other patient", "all patient", "show all tickets",
        "all escalations", "hospital records", "database dump", "view all bookings",
        "who else is booked", "list all appointments", "see all appointments", "all bookings"
    ]):
        return ChatResponse(
            reply=(
                "🔒 **Access Restricted**: Hospital-wide appointment listings, support tickets, and patient records are confidential and restricted to authorized hospital operators only.\n\n"
                "Patients can book individual consultations, register complaints, or check public OPD timings using this assistant. For patient privacy, viewing hospital-wide operational records requires authorized operator login."
            ),
            mode="deterministic_demo",
            session_id=session_id,
            suggested_prompts=["Book an appointment", "Check OPD timings", "File a complaint"]
        )

    # 3. CRITICAL EMERGENCY DETECTION
    if is_emergency_query(text):
        phone = extract_phone(text) or "9876543210"
        name = extract_name(text) or "Emergency Patient"
        
        # Log emergency escalation in DB
        esc = operations.escalate_to_human(
            db=db,
            patient_name=name,
            contact_phone=phone,
            reason=f"CRITICAL EMERGENCY TRIGGER: {text}",
            priority="URGENT",
            notes="Automatic critical emergency alert recorded from chat."
        )

        reply = (
            f"🚨 **CRITICAL MEDICAL EMERGENCY ALERT**\n\n"
            f"**Please call National Emergency Services (108 / 112) IMMEDIATELY.**\n\n"
            f"Do NOT rely on online chat or wait for a text response for acute chest pain, unconsciousness, severe breathing trouble, or trauma.\n\n"
            f"*(Notice: An urgent escalation `{esc.reference_code}` has been flagged on the hospital emergency monitor. All hospital telephone numbers (e.g. 0731-4999999) in this prototype are unverified fictional demo contacts; always call 108 / 112 for real emergencies).* "
        )
        return ChatResponse(
            reply=reply,
            mode="deterministic_demo",
            session_id=session_id,
            action_performed="emergency_escalated",
            action_reference=esc.reference_code,
            structured_data={"type": "emergency_alert", "escalation_ref": esc.reference_code},
            suggested_prompts=["Hospital Emergency Location", "Register simulated ambulance demo", "Speak to a Human Coordinator"]
        )

    # 3. AMBULANCE REQUEST INTENT
    in_ambulance_flow = any(k in lower for k in ["ambulance", "pickup father", "pickup patient", "urgent van", "transport to hospital"])
    if not in_ambulance_flow and history:
        last_assistant = next(
            (h for h in reversed(history) if ((h.role if hasattr(h, "role") else h.get("role")) == "assistant")),
            None
        )
        if last_assistant:
            last_content = (last_assistant.content if hasattr(last_assistant, "content") else last_assistant.get("content", "")).lower()
            if "ambulance request service" in last_content or "pickup address" in last_content:
                in_ambulance_flow = True

    if in_ambulance_flow:
        phone = extract_phone(text)
        if not phone and history:
            for h in reversed(history):
                p = extract_phone(h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else ""))
                if p:
                    phone = p
                    break

        name = extract_name(text)
        if not name and history:
            for h in reversed(history):
                n = extract_name(h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else ""))
                if n:
                    name = n
                    break
        name = name or "Patient Relatives"

        address = extract_address(text)

        if not address or not phone:
            return ChatResponse(
                reply=(
                    "🚑 **Aarogya Ambulance Request Service**\n\n"
                    "To register an ambulance request in our hospital system, please provide:\n"
                    "1. **Patient / Contact Name**\n"
                    "2. **10-digit Phone Number**\n"
                    "3. **Pickup Address** (e.g., near Vijay Nagar, Indore)\n\n"
                    "⚠️ *Please note: This prototype registers the request into our demo database. For life-threatening emergencies, dial 108 / 112 immediately.*"
                ),
                mode="deterministic_demo",
                session_id=session_id,
                suggested_prompts=["Ambulance near Vijay Nagar, Indore, Contact 9876543210"]
            )

        # Create the ambulance request record in DB
        amb = operations.create_ambulance_request(
            db=db,
            patient_name=name,
            contact_phone=phone,
            pickup_address=address,
            emergency_nature="Ambulance pickup requested via patient operations portal",
            is_emergency=False
        )

        reply = (
            f"🚑 **Ambulance Request Recorded**\n\n"
            f"• **Request Reference:** `{amb.reference_code}`\n"
            f"• **Patient / Contact:** {amb.patient_name} ({amb.contact_phone})\n"
            f"• **Pickup Address:** {amb.pickup_address}\n"
            f"• **System Status:** `{amb.status}`\n\n"
            f"⚠️ **IMPORTANT NOTICE:** This is a **simulated prototype request** recorded in the AarogyaConnect demo database. "
            f"**No real ambulance has been dispatched.** For an actual emergency, dial 108 / 112 directly."
        )

        return ChatResponse(
            reply=reply,
            mode="deterministic_demo",
            session_id=session_id,
            action_performed="ambulance_recorded",
            action_reference=amb.reference_code,
            structured_data={
                "type": "ambulance_request",
                "reference_code": amb.reference_code,
                "patient_name": amb.patient_name,
                "contact_phone": amb.contact_phone,
                "status": amb.status,
                "pickup_address": amb.pickup_address,
                "disclaimer": amb.disclaimer
            },
            suggested_prompts=["Check OPD Timings", "Book an appointment", "Hospital Emergency Hotline"]
        )

    # 4. COMPLAINT / SUPPORT TICKET INTENT
    if any(k in lower for k in ["complaint", "billing response", "billing issue", "refund", "ticket", "overcharge", "waiting for a long time", "grievance"]):
        phone = extract_phone(text)
        if not phone and history:
            for h in reversed(history):
                p = extract_phone(h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else ""))
                if p:
                    phone = p
                    break
        phone = phone or "9876543210"

        name = extract_name(text)
        if not name and history:
            for h in reversed(history):
                n = extract_name(h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else ""))
                if n:
                    name = n
                    break
        name = name or "Patient"
        
        category = "BILLING" if any(b in lower for b in ["bill", "billing", "charge", "refund", "cost"]) else "SERVICE"
        priority = "HIGH" if any(u in lower for u in ["long time", "urgent", "frustrated", "delay"]) else "MEDIUM"

        ticket = operations.create_support_ticket(
            db=db,
            patient_name=name,
            contact_phone=phone,
            category=category,
            priority=priority,
            description=text
        )

        reply = (
            f"📋 **Support Ticket Registered**\n\n"
            f"• **Ticket ID:** `{ticket.reference_code}`\n"
            f"• **Category:** {ticket.category}\n"
            f"• **Priority:** {ticket.priority}\n"
            f"• **Status:** `{ticket.status}`\n"
            f"• **Patient:** {ticket.patient_name}\n\n"
            f"Your issue has been logged into the hospital customer operations desk. A patient coordinator will review ticket `{ticket.reference_code}` shortly."
        )

        return ChatResponse(
            reply=reply,
            mode="deterministic_demo",
            session_id=session_id,
            action_performed="ticket_created",
            action_reference=ticket.reference_code,
            structured_data={
                "type": "support_ticket",
                "reference_code": ticket.reference_code,
                "patient_name": ticket.patient_name,
                "contact_phone": ticket.contact_phone,
                "category": ticket.category,
                "priority": ticket.priority,
                "description": ticket.description,
                "status": ticket.status
            },
            suggested_prompts=["Check cashless TPA insurance", "Speak to a human coordinator", "Hospital OPD hours"]
        )

    # 5. HUMAN ESCALATION INTENT
    if any(k in lower for k in ["speak with a human", "talk to a human", "human agent", "talk to human", "operator", "duty manager", "representative"]):
        phone = extract_phone(text)
        if not phone and history:
            for h in reversed(history):
                p = extract_phone(h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else ""))
                if p:
                    phone = p
                    break
        phone = phone or "9876543210"

        name = extract_name(text)
        if not name and history:
            for h in reversed(history):
                n = extract_name(h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else ""))
                if n:
                    name = n
                    break
        name = name or "Patient"

        esc = operations.escalate_to_human(
            db=db,
            patient_name=name,
            contact_phone=phone,
            reason=text,
            priority="HIGH"
        )

        reply = (
            f"👨‍⚕️ **Human Escalation Registered**\n\n"
            f"• **Escalation Reference:** `{esc.reference_code}`\n"
            f"• **Status:** `PENDING ATTENTION`\n"
            f"• **Reason:** {esc.reason}\n\n"
            f"An operations coordinator has been notified on the hospital dashboard. (Hospital Demo Helpline: 0731-4999000 — Fictional Prototype Desk)."
        )

        return ChatResponse(
            reply=reply,
            mode="deterministic_demo",
            session_id=session_id,
            action_performed="escalation_recorded",
            action_reference=esc.reference_code,
            structured_data={
                "type": "human_escalation",
                "reference_code": esc.reference_code,
                "patient_name": esc.patient_name,
                "contact_phone": esc.contact_phone,
                "priority": esc.priority,
                "reason": esc.reason,
                "status": esc.status
            },
            suggested_prompts=["Book cardiologist appointment", "Hospital visiting hours", "OPD Timings"]
        )

    # 6. HOSPITAL FAQ RETRIEVAL (Run before booking so questions like 'documents required for an appointment' get FAQ answers)
    faq_match = knowledge.search_hospital_faq(text)
    if faq_match and not any(b in lower for b in ["book with", "book dr", "book at", "book for", "confirm"]):
        operations.log_action(
            db, "TOOL_CALL", "search_hospital_faq", json.dumps({"query": text}), "SUCCESS", f"FAQ match: {faq_match['category']}"
        )
        reply = (
            f"ℹ️ **Aarogya Hospital Information — {faq_match['category']}**\n\n"
            f"{faq_match['answer']}"
        )
        return ChatResponse(
            reply=reply,
            mode="deterministic_demo",
            session_id=session_id,
            structured_data={"type": "faq_answer", "category": faq_match["category"]},
            suggested_prompts=["Book an appointment", "OPD Timings", "Cashless TPA Insurance"]
        )

    # 7. APPOINTMENT BOOKING / DOCTOR SEARCH INTENT
    is_appointment_request = any(k in lower for k in [
        "book an appointment", "book appointment", "see a cardiologist", "want to see a doctor",
        "cardiologist", "orthopedic", "dermatologist", "general medicine", "ananya sharma",
        "rahul mehta", "priya nair", "vikram patel", "doctor", "consultation", "appointment"
    ])

    in_appointment_flow = is_appointment_request or bool(
        re.search(r"\b(?:0?[1-9]|1[0-2])(?::[0-5]\d)?\s*(?:am|pm)\b|\b(?:afternoon|morning|evening)\b", lower)
    )

    # Check conversation history to continue multi-turn booking flows
    if not in_appointment_flow and history:
        last_assistant = next(
            (h for h in reversed(history) if ((h.role if hasattr(h, "role") else h.get("role")) == "assistant")),
            None
        )
        if last_assistant:
            last_content = (last_assistant.content if hasattr(last_assistant, "content") else last_assistant.get("content", "")).lower()
            if any(phrase in last_content for phrase in [
                "patient full name", "phone number", "selected slot", "which slot time do you prefer",
                "available slots", "open slots", "alternative open slots", "confirm your appointment",
                "cardiologist", "consultation fee", "doctor", "dr.", "appointment", "booking"
            ]):
                in_appointment_flow = True

    if in_appointment_flow:
        # Combine current text with history text to resolve multi-turn conversation context
        combined_text = text.lower()
        for h in (history or []):
            if hasattr(h, "content"):
                combined_text += " " + h.content.lower()
            elif isinstance(h, dict) and "content" in h:
                combined_text += " " + str(h["content"]).lower()

        # Detect department or doctor
        matched_doctor = None
        if "cardio" in combined_text or "heart" in combined_text or "sharma" in combined_text:
            matched_doctor = db.query(Doctor).filter(Doctor.department == "Cardiology").first()
        elif "ortho" in combined_text or "bone" in combined_text or "joint" in combined_text or "mehta" in combined_text:
            matched_doctor = db.query(Doctor).filter(Doctor.department == "Orthopedics").first()
        elif "derma" in combined_text or "skin" in combined_text or "nair" in combined_text:
            matched_doctor = db.query(Doctor).filter(Doctor.department == "Dermatology").first()
        elif "medicine" in combined_text or "general" in combined_text or "patel" in combined_text or "fever" in combined_text or "diabetes" in combined_text:
            matched_doctor = db.query(Doctor).filter(Doctor.department == "General Medicine").first()

        # If user explicitly asked about appointments but doctor not matched yet
        if not matched_doctor:
            doctors = operations.get_all_doctors(db)
            doc_list_md = "\n".join([f"• **{d.name}** — {d.department} ({d.specialization}) | Fee: ₹{d.consultation_fee}" for d in doctors])
            return ChatResponse(
                reply=(
                    f"🏥 **Available Specialists at Aarogya Hospital:**\n\n{doc_list_md}\n\n"
                    f"Which specialist or department would you like to consult with?"
                ),
                mode="deterministic_demo",
                session_id=session_id,
                suggested_prompts=["Book with Dr. Ananya Sharma (Cardiology)", "Book with Dr. Rahul Mehta (Orthopedics)", "Book with Dr. Priya Nair (Dermatology)"]
            )

        # Parse date, slot, phone, and name from current message or fallback to user history (most recent first)
        target_date = parse_date_intent(text)
        if "tomorrow" not in lower and "today" not in lower and "day after tomorrow" not in lower:
            for h in reversed(history or []):
                h_text = (h.content if hasattr(h, "content") else h.get("content", "")).lower()
                if "tomorrow" in h_text or "today" in h_text or re.search(r"\b(202\d-[0-1]\d-[0-3]\d)\b", h_text):
                    target_date = parse_date_intent(h_text)
                    break

        time_slot = parse_time_slot(text)
        if not time_slot:
            # Check if previous assistant message specified a selected slot
            for h in reversed(history or []):
                h_text = h.content if hasattr(h, "content") else h.get("content", "")
                m_slot = re.search(r"(?:selected slot:?\s*|slot:?\s*|\bat\s+)(\d{1,2}:\d{2}\s*(?:AM|PM))", h_text, re.I)
                if m_slot:
                    time_slot = m_slot.group(1).upper()
                    break

            if not time_slot:
                for h in reversed(history or []):
                    role = h.role if hasattr(h, "role") else h.get("role", "")
                    if role == "user":
                        h_text = h.content if hasattr(h, "content") else h.get("content", "")
                        ts = parse_time_slot(h_text)
                        if ts:
                            time_slot = ts
                            break

        phone = extract_phone(text)
        if not phone:
            for h in reversed(history or []):
                role = h.role if hasattr(h, "role") else h.get("role", "")
                if role == "user":
                    h_text = h.content if hasattr(h, "content") else h.get("content", "")
                    p = extract_phone(h_text)
                    if p:
                        phone = p
                        break

        name = extract_name(text)
        if not name:
            for h in reversed(history or []):
                role = h.role if hasattr(h, "role") else h.get("role", "")
                if role == "user":
                    h_text = h.content if hasattr(h, "content") else h.get("content", "")
                    n = extract_name(h_text)
                    if n:
                        name = n
                        break

        # Check existing slots for doctor on this date
        slots = operations.check_slots(db, matched_doctor.id, target_date)
        available_slots = [s["slot_time"] for s in slots if not s["is_booked"]]

        # If user asked for afternoon / morning in general, pick the first available matching slot
        if "afternoon" in combined_text and (not time_slot or time_slot not in available_slots):
            open_afternoons = [s for s in available_slots if "PM" in s and s != "12:00 PM"]
            if open_afternoons:
                time_slot = open_afternoons[0]
        elif "morning" in combined_text and (not time_slot or time_slot not in available_slots):
            open_mornings = [s for s in available_slots if "AM" in s]
            if open_mornings:
                time_slot = open_mornings[0]

        # If user hasn't specified a valid time slot yet:
        if not time_slot or time_slot not in [s["slot_time"] for s in slots]:
            slot_options = ", ".join([f"`{s}`" for s in available_slots]) if available_slots else "No available slots"
            reply = (
                f"🩺 Found **{matched_doctor.name}** ({matched_doctor.department}, {matched_doctor.specialization}).\n\n"
                f"• **Date:** {target_date}\n"
                f"• **Consultation Fee:** ₹{matched_doctor.consultation_fee}\n"
                f"• **Available Slots:** {slot_options}\n\n"
                f"Which slot time do you prefer (e.g. 2 PM, 10 AM, 11:30 AM)?"
            )
            return ChatResponse(
                reply=reply,
                mode="deterministic_demo",
                session_id=session_id,
                structured_data={
                    "type": "slots_list",
                    "doctor_id": matched_doctor.id,
                    "doctor_name": matched_doctor.name,
                    "doctor_department": matched_doctor.department,
                    "specialization": matched_doctor.specialization,
                    "consultation_fee": matched_doctor.consultation_fee,
                    "room_no": matched_doctor.room_no,
                    "date": target_date,
                    "available_slots": available_slots
                },
                suggested_prompts=["2 PM", "10:00 AM", "11:30 AM", "03:30 PM"]
            )

        # If slot is occupied
        slot_obj = next((s for s in slots if s["slot_time"] == time_slot), None)
        if slot_obj and slot_obj["is_booked"]:
            alternative_str = ", ".join([f"`{s}`" for s in available_slots])
            return ChatResponse(
                reply=(
                    f"⚠️ The slot **{time_slot}** on {target_date} for {matched_doctor.name} is already booked.\n\n"
                    f"**Alternative open slots:** {alternative_str}\n\n"
                    f"Please choose an open slot."
                ),
                mode="deterministic_demo",
                session_id=session_id,
                structured_data={
                    "type": "slots_list",
                    "doctor_id": matched_doctor.id,
                    "doctor_name": matched_doctor.name,
                    "doctor_department": matched_doctor.department,
                    "specialization": matched_doctor.specialization,
                    "consultation_fee": matched_doctor.consultation_fee,
                    "room_no": matched_doctor.room_no,
                    "date": target_date,
                    "available_slots": available_slots
                },
                suggested_prompts=[s for s in available_slots[:3]]
            )

        # If name or phone is missing, prompt for missing details
        if not name or not phone:
            if name and not phone:
                missing_text = f"To prepare your booking for **{name}**, please provide your **10-digit Phone Number** (e.g., 9876543210)."
                chips = ["9876543210", "Cancel booking", "View other slots"]
            elif phone and not name:
                missing_text = f"To prepare your booking for phone `{phone}`, please provide the **Patient Full Name** (e.g., Amit Verma)."
                chips = ["Amit Verma", "Cancel booking", "View other slots"]
            else:
                missing_text = "To prepare your booking, please share:\n• **Patient Full Name**\n• **10-digit Phone Number**\n\n*(e.g., Amit Verma, 9876543210)*"
                chips = ["Amit Verma, 9876543210", "Cancel booking", "View other slots"]

            return ChatResponse(
                reply=(
                    f"🩺 I have checked available slots for **{matched_doctor.name}** ({matched_doctor.department}) on **{target_date}**.\n\n"
                    f"• **Selected Slot:** {time_slot}\n"
                    f"• **Consultation Fee:** ₹{matched_doctor.consultation_fee}\n\n"
                    f"{missing_text}"
                ),
                mode="deterministic_demo",
                session_id=session_id,
                structured_data={
                    "type": "slots_list",
                    "doctor_id": matched_doctor.id,
                    "doctor_name": matched_doctor.name,
                    "doctor_department": matched_doctor.department,
                    "specialization": matched_doctor.specialization,
                    "consultation_fee": matched_doctor.consultation_fee,
                    "room_no": matched_doctor.room_no,
                    "date": target_date,
                    "selected_slot": time_slot,
                    "available_slots": available_slots
                },
                suggested_prompts=chips
            )

        # All details present: Stage for EXPLICIT CONFIRMATION (Rule: Never book without explicit confirmation)
        pending = PendingBookingState(
            doctor_id=matched_doctor.id,
            doctor_name=matched_doctor.name,
            doctor_department=matched_doctor.department,
            consultation_fee=matched_doctor.consultation_fee,
            appointment_date=target_date,
            appointment_time=time_slot,
            patient_name=name,
            patient_phone=phone,
            notes="Booked via AarogyaConnect AI assistant"
        )

        reply = (
            f"📋 **Please Confirm Your Appointment Details:**\n\n"
            f"• **Doctor:** {matched_doctor.name} ({matched_doctor.department})\n"
            f"• **OPD Room:** {matched_doctor.room_no}\n"
            f"• **Date:** {target_date}\n"
            f"• **Time:** {time_slot}\n"
            f"• **Patient Name:** {name}\n"
            f"• **Contact Phone:** {phone}\n"
            f"• **Consultation Fee:** ₹{matched_doctor.consultation_fee}\n\n"
            f"Shall I go ahead and confirm this appointment for you? Please reply with **'Yes, confirm it'** or **'No, cancel'**."
        )

        return ChatResponse(
            reply=reply,
            mode="deterministic_demo",
            session_id=session_id,
            pending_booking=pending,
            structured_data={
                "type": "booking_summary_pending_confirmation",
                "doctor_name": matched_doctor.name,
                "date": target_date,
                "time": time_slot,
                "patient_name": name,
                "fee": matched_doctor.consultation_fee
            },
            suggested_prompts=["Yes, confirm it.", "No, cancel."]
        )

    # Check if user asked a hospital question/policy that wasn't found in knowledge base
    is_question = any(lower.startswith(w) for w in ["what", "how", "can", "do", "is", "are", "where", "why", "tell", "does"]) or any(
        q in lower for q in ["policy", "rule", "timings", "hours", "charges", "documents", "cost", "allowed", "service"]
    )
    if is_question:
        operations.log_action(
            db, "TOOL_CALL", "search_hospital_faq", json.dumps({"query": text}), "FAILED", "Policy not found in hospital knowledge base."
        )
        return ChatResponse(
            reply=(
                f"I apologize, but that specific hospital policy or question is not found in our verified {settings.HOSPITAL_NAME} knowledge base.\n\n"
                f"To ensure patient safety and avoid misinformation, I do not speculate or invent hospital policies. For verified assistance on this topic, our patient care coordinator or front desk can assist you directly.\n\n"
                f"Would you like me to connect you with a hospital representative or help you book a specialist appointment?"
            ),
            mode="deterministic_demo",
            session_id=session_id,
            suggested_prompts=["Speak with a human coordinator", "Check OPD timings", "Book an appointment"]
        )

    # 8. FALLBACK / GRACEFUL EXPLANATION
    return ChatResponse(
        reply=(
            f"Hello! I am AarogyaConnect AI, the operations assistant for {settings.HOSPITAL_NAME}.\n\n"
            f"I can directly assist you with:\n"
            f"1. **Booking Doctor Appointments** (Cardiology, Orthopedics, Dermatology, General Medicine)\n"
            f"2. **Ambulance Assistance** (Simulated emergency pickup registration)\n"
            f"3. **Hospital Policies & FAQs** (OPD timings, visiting hours, cashless TPA insurance, test prep)\n"
            f"4. **Registering Complaints & Grievances** (Billing issues, delay tickets, human operator escalation)\n\n"
            f"How may I help you today?"
        ),
        mode="deterministic_demo",
        session_id=session_id,
        suggested_prompts=[
            "I want to book an appointment with a cardiologist tomorrow afternoon",
            "What are the OPD timings and visiting hours?",
            "I need an ambulance for my father near Vijay Nagar, Indore",
            "I have been waiting for a billing response for a long time. Register a complaint."
        ]
    )


# --- Sarvam AI & OpenAI-compatible LLM Orchestration ---

async def handle_ai_turn(
    db: Session,
    message: str,
    session_id: str,
    history: List[Any],
    pending_booking: Optional[PendingBookingState]
) -> ChatResponse:
    """Execute AI tool calling with official Sarvam Chat Completion API.
    If the API call fails or times out, seamlessly falls back to deterministic engine."""
    api_key = settings.active_llm_api_key
    base_url = settings.active_llm_base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        url = f"{base_url}/v1/chat/completions"
    else:
        url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Dynamic temporal calendar context
    now_kolkata = get_kolkata_now()
    today_str = now_kolkata.strftime("%Y-%m-%d")
    tomorrow_str = (now_kolkata + timedelta(days=1)).strftime("%Y-%m-%d")

    messages.append({
        "role": "system",
        "content": (
            f"[CALENDAR CONTEXT: Today is {today_str} ({now_kolkata.strftime('%A')}). "
            f"Tomorrow is {tomorrow_str}. "
            f"Always use YYYY-MM-DD for tool calls. "
            f"Hospital OPD Timings: 09:00 AM - 06:00 PM. "
            f"Standard slot times: 10:00 AM, 11:30 AM, 02:00 PM, 03:30 PM, 04:30 PM.]"
        )
    })

    # If an appointment booking is staged awaiting user confirmation
    if pending_booking:
        messages.append({
            "role": "system",
            "content": (
                f"[PENDING APPOINTMENT IN PROGRESS: "
                f"Doctor ID: {pending_booking.doctor_id}, Doctor Name: {pending_booking.doctor_name}, "
                f"Department: {pending_booking.doctor_department}, Date: {pending_booking.appointment_date}, "
                f"Time Slot: {pending_booking.appointment_time}, Patient: {pending_booking.patient_name}, "
                f"Phone: {pending_booking.patient_phone}, Fee: ₹{pending_booking.consultation_fee}. "
                f"If the patient confirms (e.g. 'yes', 'confirm', 'proceed', 'haan', 'कन्फर्म'), "
                f"you MUST call `confirm_appointment` with doctor_id={pending_booking.doctor_id}, "
                f"date='{pending_booking.appointment_date}', time_slot='{pending_booking.appointment_time}', "
                f"patient_name='{pending_booking.patient_name}', patient_phone='{pending_booking.patient_phone}'. "
                f"If the patient cancels, politely acknowledge cancellation without calling confirm_appointment.]"
            )
        })

    # Add recent history
    for h in (history or [])[-6:]:
        if hasattr(h, "role") and hasattr(h, "content"):
            messages.append({"role": h.role, "content": h.content})
        elif isinstance(h, dict):
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    messages.append({"role": "user", "content": message})

    action_performed = None
    action_ref = None
    structured_data = None
    new_pending = pending_booking
    final_content = ""

    async with httpx.AsyncClient(timeout=35.0) as client:
        for iteration in range(3):
            payload = {
                "model": settings.active_llm_model,
                "messages": messages,
                "tools": AGENT_TOOLS,
                "tool_choice": "auto",
                "temperature": 0.1
            }

            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            message_obj = choice.get("message", {})
            tool_calls = message_obj.get("tool_calls", [])

            if not tool_calls:
                final_content = message_obj.get("content") or ""
                break

            # Append the assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message_obj.get("content") or "",
                "tool_calls": tool_calls
            })

            # Execute tool calls
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                raw_args = tc["function"].get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except Exception:
                    args = {}

                if fn_name == "search_doctors":
                    docs = operations.search_doctors(db, query=args.get("query"), department=args.get("department"))
                    res = [
                        {
                            "id": d.id,
                            "name": d.name,
                            "department": d.department,
                            "specialization": d.specialization,
                            "qualification": d.qualification,
                            "experience_years": d.experience_years,
                            "fee": d.consultation_fee,
                            "room": d.room_no,
                            "timings": d.opd_timings
                        }
                        for d in docs
                    ]
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "name": fn_name, "content": json.dumps(res)})
                    if not structured_data:
                        structured_data = {"type": "doctors_list", "doctors": res}

                elif fn_name == "check_slots":
                    doc_id = args.get("doctor_id")
                    date_str = args.get("date")
                    slots = operations.check_slots(db, doctor_id=doc_id, date=date_str)
                    doc = operations.get_doctor_by_id(db, doc_id) if doc_id else None
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "name": fn_name, "content": json.dumps(slots)})
                    structured_data = {
                        "type": "slots_list",
                        "doctor_id": doc.id if doc else doc_id,
                        "doctor_name": doc.name if doc else "Doctor",
                        "department": doc.department if doc else "",
                        "consultation_fee": doc.consultation_fee if doc else 800,
                        "room_no": doc.room_no if doc else "OPD",
                        "slots": slots
                    }

                elif fn_name == "search_hospital_faq":
                    faq = knowledge.search_hospital_faq(args.get("query", ""))
                    if faq:
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "name": fn_name, "content": json.dumps(faq)})
                        structured_data = {
                            "type": "faq",
                            "category": faq.get("category", "Hospital Policy"),
                            "question": faq.get("question", ""),
                            "answer": faq.get("answer", "")
                        }
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": fn_name,
                            "content": json.dumps({
                                "status": "not_found",
                                "message": "Policy not found in hospital verified knowledge base. Explain that this specific information is not in the hospital's verified records, do not speculate or invent policies, and offer escalation to a human representative."
                            })
                        })

                elif fn_name == "prepare_appointment_confirmation":
                    doc_id = args.get("doctor_id")
                    doc = operations.get_doctor_by_id(db, doc_id) if doc_id else None
                    if not doc:
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "name": fn_name, "content": json.dumps({"error": "Doctor not found"})})
                    else:
                        date_val = args.get("date")
                        slot_val = args.get("time_slot")
                        slots = operations.check_slots(db, doc_id, date_val)
                        slot_obj = next((s for s in slots if s["slot_time"] == slot_val), None)
                        if not slot_obj or slot_obj["is_booked"]:
                            open_slots = [s["slot_time"] for s in slots if not s["is_booked"]]
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "name": fn_name,
                                "content": json.dumps({
                                    "status": "unavailable",
                                    "error": f"Slot {slot_val} on {date_val} is already booked or unavailable.",
                                    "available_slots": open_slots
                                })
                            })
                        else:
                            new_pending = PendingBookingState(
                                doctor_id=doc.id,
                                doctor_name=doc.name,
                                doctor_department=doc.department,
                                consultation_fee=doc.consultation_fee,
                                appointment_date=date_val,
                                appointment_time=slot_val,
                                patient_name=args.get("patient_name") or "Patient",
                                patient_phone=args.get("patient_phone") or "9876543210",
                                notes=args.get("notes")
                            )
                            action_performed = "booking_proposed"
                            structured_data = {
                                "type": "proposed_booking",
                                "doctor_name": doc.name,
                                "department": doc.department,
                                "consultation_fee": doc.consultation_fee,
                                "appointment_date": date_val,
                                "appointment_time": slot_val,
                                "patient_name": args.get("patient_name") or "Patient",
                                "patient_phone": args.get("patient_phone") or "9876543210",
                                "room_no": doc.room_no
                            }
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "name": fn_name,
                                "content": json.dumps({
                                    "status": "pending_confirmation",
                                    "summary": {
                                        "doctor": doc.name,
                                        "department": doc.department,
                                        "date": date_val,
                                        "time": slot_val,
                                        "patient": args.get("patient_name"),
                                        "phone": args.get("patient_phone"),
                                        "fee": doc.consultation_fee,
                                        "room": doc.room_no
                                    },
                                    "instruction": "Present this booking summary clearly and ask the patient: 'Would you like me to confirm this appointment?' Do NOT confirm until the patient replies with explicit confirmation."
                                })
                            })

                elif fn_name == "confirm_appointment":
                    try:
                        apt = operations.create_appointment(
                            db=db,
                            doctor_id=args.get("doctor_id"),
                            patient_name=args.get("patient_name"),
                            patient_phone=args.get("patient_phone"),
                            date=args.get("date"),
                            time_slot=args.get("time_slot"),
                            notes=args.get("notes")
                        )
                        action_performed = "appointment_booked"
                        action_ref = apt.reference_code
                        new_pending = None
                        structured_data = {
                            "type": "appointment",
                            "reference_code": apt.reference_code,
                            "doctor": apt.doctor_name,
                            "department": apt.doctor_department,
                            "date": apt.appointment_date,
                            "time": apt.appointment_time,
                            "patient": apt.patient_name
                        }
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": fn_name,
                            "content": json.dumps({
                                "status": "confirmed",
                                "reference_code": apt.reference_code,
                                "doctor": apt.doctor_name,
                                "date": apt.appointment_date,
                                "time": apt.appointment_time,
                                "patient": apt.patient_name
                            })
                        })
                    except ValueError as e:
                        messages.append({
                            "tool_call_id": tc["id"],
                            "role": "tool",
                            "name": fn_name,
                            "content": json.dumps({"status": "failed", "error": str(e)})
                        })

                elif fn_name == "create_ambulance_request":
                    amb = operations.create_ambulance_request(
                        db=db,
                        patient_name=args.get("patient_name"),
                        contact_phone=args.get("contact_phone"),
                        pickup_address=args.get("pickup_address"),
                        emergency_nature=args.get("emergency_nature"),
                        is_emergency=args.get("is_emergency", False)
                    )
                    action_performed = "ambulance_recorded"
                    action_ref = amb.reference_code
                    structured_data = {
                        "type": "ambulance_request",
                        "reference_code": amb.reference_code,
                        "patient_name": amb.patient_name,
                        "contact_phone": amb.contact_phone,
                        "pickup_address": amb.pickup_address,
                        "emergency_nature": amb.emergency_nature,
                        "status": amb.status,
                        "is_emergency_redirect": amb.is_emergency_redirect,
                        "disclaimer": amb.disclaimer
                    }
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": fn_name,
                        "content": json.dumps({
                            "reference": amb.reference_code,
                            "status": amb.status,
                            "disclaimer": amb.disclaimer
                        })
                    })

                elif fn_name == "create_support_ticket":
                    tkt = operations.create_support_ticket(
                        db=db,
                        patient_name=args.get("patient_name"),
                        contact_phone=args.get("contact_phone"),
                        category=args.get("category", "GENERAL"),
                        priority=args.get("priority", "MEDIUM"),
                        description=args.get("description", "")
                    )
                    action_performed = "ticket_created"
                    action_ref = tkt.reference_code
                    structured_data = {
                        "type": "support_ticket",
                        "reference_code": tkt.reference_code,
                        "patient_name": tkt.patient_name,
                        "category": tkt.category,
                        "priority": tkt.priority,
                        "description": tkt.description,
                        "status": tkt.status
                    }
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": fn_name,
                        "content": json.dumps({
                            "reference": tkt.reference_code,
                            "status": tkt.status
                        })
                    })

                elif fn_name == "escalate_to_human":
                    esc = operations.escalate_to_human(
                        db=db,
                        patient_name=args.get("patient_name"),
                        contact_phone=args.get("contact_phone"),
                        reason=args.get("reason", "Patient requested operator"),
                        priority=args.get("priority", "HIGH")
                    )
                    action_performed = "escalation_recorded"
                    action_ref = esc.reference_code
                    structured_data = {
                        "type": "human_escalation",
                        "reference_code": esc.reference_code,
                        "patient_name": esc.patient_name,
                        "reason": esc.reason,
                        "priority": esc.priority,
                        "status": esc.status
                    }
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": fn_name,
                        "content": json.dumps({
                            "reference": esc.reference_code,
                            "status": esc.status
                        })
                    })

    if not final_content and message_obj:
        final_content = message_obj.get("content") or ""

    # Ensure pending booking staging if slot, doctor, name, and phone were present
    if new_pending is None and action_performed != "appointment_booked":
        p_name = extract_name(message)
        p_phone = extract_phone(message)
        p_slot = parse_time_slot(message)
        if p_name and p_phone and p_slot and structured_data:
            doc_id = structured_data.get("doctor_id")
            if not doc_id and structured_data.get("doctors"):
                doc_id = structured_data["doctors"][0].get("id")
            doc = operations.get_doctor_by_id(db, doc_id) if doc_id else None
            if doc:
                slot_date = parse_date_intent(message)
                new_pending = PendingBookingState(
                    doctor_id=doc.id,
                    doctor_name=doc.name,
                    doctor_department=doc.department,
                    consultation_fee=doc.consultation_fee,
                    appointment_date=slot_date,
                    appointment_time=p_slot,
                    patient_name=p_name,
                    patient_phone=p_phone,
                    notes=None
                )
                action_performed = "booking_proposed"
                structured_data = {
                    "type": "proposed_booking",
                    "doctor_name": doc.name,
                    "department": doc.department,
                    "consultation_fee": doc.consultation_fee,
                    "appointment_date": slot_date,
                    "appointment_time": p_slot,
                    "patient_name": p_name,
                    "patient_phone": p_phone,
                    "room_no": doc.room_no
                }

    # Ensure explicit confirmation creates appointment if pending_booking is active
    if pending_booking and is_confirmation(message) and action_performed != "appointment_booked":
        try:
            apt = operations.create_appointment(
                db=db,
                doctor_id=pending_booking.doctor_id,
                patient_name=pending_booking.patient_name,
                patient_phone=pending_booking.patient_phone,
                date=pending_booking.appointment_date,
                time_slot=pending_booking.appointment_time,
                notes=pending_booking.notes
            )
            action_performed = "appointment_booked"
            action_ref = apt.reference_code
            new_pending = None
            structured_data = {
                "type": "appointment",
                "reference_code": apt.reference_code,
                "doctor": apt.doctor_name,
                "department": apt.doctor_department,
                "date": apt.appointment_date,
                "time": apt.appointment_time,
                "patient": apt.patient_name
            }
            if not final_content or "confirmed" not in final_content.lower():
                final_content = (
                    f"✅ **Appointment Confirmed!**\n\n"
                    f"• **Booking Reference:** `{apt.reference_code}`\n"
                    f"• **Doctor:** {apt.doctor_name} ({apt.doctor_department})\n"
                    f"• **Date & Slot:** {apt.appointment_date} at {apt.appointment_time}\n"
                    f"• **Patient:** {apt.patient_name} ({apt.patient_phone})\n"
                    f"• **Consultation Fee:** ₹{pending_booking.consultation_fee}\n\n"
                    f"Your appointment is registered in the hospital operations system. Please arrive 15 minutes before your consultation."
                )
        except ValueError as e:
            final_content = f"⚠️ Could not confirm appointment: {str(e)}"

    return ChatResponse(
        reply=final_content,
        mode="ai",
        session_id=session_id,
        action_performed=action_performed,
        action_reference=action_ref,
        pending_booking=new_pending,
        structured_data=structured_data,
        suggested_prompts=["Book an appointment", "Hospital OPD hours", "Ambulance request"]
    )


# --- Main Entry Point for Chat Orchestrator ---

async def process_chat_message(
    db: Session,
    message: str,
    session_id: str,
    history: List[Any],
    pending_booking: Optional[PendingBookingState]
) -> ChatResponse:
    """Main orchestrator: Uses Sarvam AI if configured, otherwise falls back gracefully to deterministic demo engine."""
    # 1. IMMEDIATE CRITICAL EMERGENCY CHECK
    # Real-life patient safety: If acute chest pain, unconsciousness, severe trauma is detected,
    # immediately present the 108/112 emergency alert and log an urgent escalation without network delay.
    if is_emergency_query(message):
        phone = extract_phone(message) or "9876543210"
        name = extract_name(message) or "Emergency Patient"
        esc = operations.escalate_to_human(
            db=db,
            patient_name=name,
            contact_phone=phone,
            reason=f"CRITICAL EMERGENCY TRIGGER: {message.strip()}",
            priority="URGENT",
            notes="Automatic critical emergency alert recorded from chat."
        )
        return ChatResponse(
            reply=(
                "🚨 **CRITICAL MEDICAL EMERGENCY ALERT**\n\n"
                "**Please call National Emergency Services (108 / 112) IMMEDIATELY.**\n\n"
                "Do NOT rely on online chat or wait for a text response for acute chest pain, unconsciousness, severe breathing trouble, or trauma.\n\n"
                f"*(Notice: An urgent escalation `{esc.reference_code}` has been flagged on the hospital emergency monitor. All hospital telephone numbers (e.g. 0731-4999999) in this prototype are unverified fictional demo contacts; always call 108 / 112 for real emergencies).* "
            ),
            mode="ai" if settings.is_ai_configured else "deterministic_demo",
            session_id=session_id,
            action_performed="emergency_escalated",
            action_reference=esc.reference_code,
            structured_data={
                "type": "emergency_alert",
                "reference_code": esc.reference_code,
                "helpline": "108 / 112"
            },
            suggested_prompts=["Call 108 / 112 Emergency", "Hospital Casualty Desk"]
        )

    # 2. PRIVACY & ACCESS CONTROL GUARD
    # Deny public patient attempts to dump hospital-wide appointment lists, tickets, or records
    lower = message.lower().strip()
    if any(phrase in lower for phrase in [
        "all appointments", "other patients", "other patient", "all patient", "show all tickets",
        "all escalations", "hospital records", "database dump", "view all bookings",
        "who else is booked", "list all appointments", "see all appointments", "all bookings"
    ]):
        return ChatResponse(
            reply=(
                "🔒 **Access Restricted**: Hospital-wide appointment listings, support tickets, and patient records are confidential and restricted to authorized hospital operators only.\n\n"
                "Patients can book individual consultations, register complaints, or check public OPD timings using this assistant. For patient privacy, viewing hospital-wide operational records requires authorized operator login."
            ),
            mode="ai" if settings.is_ai_configured else "deterministic_demo",
            session_id=session_id,
            suggested_prompts=["Book an appointment", "Check OPD timings", "File a complaint"]
        )

    # 3. SARVAM AI ORCHESTRATION WITH DETERMINISTIC FALLBACK
    if settings.is_ai_configured:
        try:
            return await handle_ai_turn(
                db=db,
                message=message,
                session_id=session_id,
                history=history,
                pending_booking=pending_booking
            )
        except Exception as e:
            # Safe fallback if Sarvam API errors, times out, or quota exhausted
            operations.log_action(
                db=db,
                action_type="FAULT",
                tool_name="sarvam_ai_orchestrator",
                parameters=None,
                result_status="FAILED",
                result_summary=f"Sarvam AI API failed ({str(e)}). Falling back to deterministic demo engine."
            )
            return handle_deterministic_turn(
                db=db,
                message=message,
                session_id=session_id,
                history=history,
                pending_booking=pending_booking
            )
    else:
        return handle_deterministic_turn(
            db=db,
            message=message,
            session_id=session_id,
            history=history,
            pending_booking=pending_booking
        )
