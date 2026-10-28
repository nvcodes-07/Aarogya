# AarogyaConnect AI — 6-Minute Live Demonstration Script

**Hospital Branding:** Aarogya Multispeciality Hospital (Indore, MP)  
**Tagline:** *"From patient conversations to completed hospital workflows."*  
**Application URL:** `http://localhost:5173` (Frontend) | `http://localhost:8000` (Backend API & SQLite)

---

## Pre-Demo Checklist (1 Minute Before Presentation)

1. Ensure the backend is active on port 8000:
   ```bash
   PYTHONPATH=backend ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Ensure the frontend is active on port 5173:
   ```bash
   cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
   ```
3. *(Optional)* To reset the demonstration database to a clean baseline before beginning:
   ```bash
   ./venv/bin/python3 reset_demo_db.py
   ```
4. Open `http://localhost:5173` in your browser. Confirm the landing view is the **Patient Assistant**.

---

## Scene 1 — Real Appointment Booking Workflow
*Demonstrates multi-turn intent resolution, real-time doctor slot availability, missing detail collection, explicit patient confirmation, and backend transaction execution.*

1. **User Action:** In the chat input, type or click:
   ```text
   I am Amit Verma. I want to book a cardiology appointment tomorrow afternoon.
   ```
2. **What the Agent Does:**
   - Detects patient name: `Amit Verma`.
   - Queries SQLite for available Cardiology specialists (`Dr. Ananya Sharma`).
   - Checks available afternoon slots for tomorrow (e.g., `02:00 PM`).
   - Identifies that contact phone is missing.
   - Presents doctor profile, consultation fee (₹1000), selectable slot cards, and requests the 10-digit phone number.
3. **User Action:** Type patient phone:
   ```text
   9876543210
   ```
4. **What the Agent Does:**
   - Displays a dedicated **Proposed Appointment (Pending Confirmation)** card with doctor details, date, slot time, and patient info.
   - **Crucial Rule Verification:** An appointment is **NOT** created before confirmation.
5. **User Action:** Click the **Confirm Booking** button or type:
   ```text
   Yes, confirm it.
   ```
6. **What the Agent Does:**
   - Validates slot availability on the backend.
   - Commits the record to SQLite and marks the slot as booked.
   - Returns a real, permanent booking reference: `APT-XXXXXX`.
   - Displays the green **Confirmed Appointment (Live in SQLite)** card.

---

## Scene 2 — Grounded Hospital Information & Policy FAQ
*Demonstrates reliable, non-hallucinatory retrieval from the verified hospital knowledge base.*

1. **User Action:** In the chat input, type or click:
   ```text
   What documents should I bring to my appointment?
   ```
2. **What the Agent Does:**
   - Searches the hospital knowledge base.
   - Returns verified requirements: Previous prescriptions, medical history, lab reports, photo ID (such as Aadhaar), and overnight fasting instructions (if blood work/ultrasound is scheduled).
   - Never hallucinates or invents arbitrary hospital policies.

---

## Scene 3 — Simulated Ambulance Demo Request
*Demonstrates conversational dispatch intake, unique reference generation, emergency escalation, and strict disclaimer safety.*

1. **User Action:** In the chat input, type or click:
   ```text
   I want to register an ambulance request for a patient.
   ```
2. **What the Agent Does:**
   - Explains that the prototype registers demo assistance into the hospital database.
   - Requests patient contact name, phone number, and pickup location.
3. **User Action:** Provide pickup details:
   ```text
   Pickup address is near Vijay Nagar, Indore. Contact phone 9876543210 for patient Rahul.
   ```
4. **What the Agent Does:**
   - Validates address and 10-digit phone.
   - Records the request in SQLite and generates a reference: `AMB-XXXXXX`.
   - Displays the **Simulated Ambulance Request** card.
   - Prominently displays the red emergency advisory:
     > *"⚠️ PROTOTYPE DEMONSTRATION ONLY: No real ambulance has been dispatched. For an actual medical emergency, immediately dial 108 / 112."*

---

## Scene 4 — Support Grievance Filing
*Demonstrates customer operations grievance filing, automatic priority/category assignment, and operational ticket generation.*

1. **User Action:** In the chat input, type or click:
   ```text
   I have a billing issue. Please register my complaint.
   ```
2. **What the Agent Does:**
   - Categorizes grievance under `BILLING` with priority `MEDIUM`/`HIGH`.
   - Generates a permanent ticket in SQLite: `TKT-XXXXXX`.
   - Displays the **Support Ticket Registered** card with a direct shortcut to speak with a human coordinator.

---

## Scene 5 — Operations Dashboard Verification (Staff Access)
*Demonstrates role-based access control, operator authentication, and live SQLite database synchronization.*

1. **User Action:** Click the **Operator Login** button in the top navigation bar (or the Staff Gateway in the left sidebar).
2. **What Happens:**
   - The **Hospital Operator Gate** modal appears.
   - Click **"Autofill Demo Credentials from Backend"** (populates `operator@aarogya.org` via backend environment variables with zero hardcoded client passwords).
   - Click **Authenticate Operator**.
3. **Demonstrating Live Database Records:**
   - The view transitions seamlessly to the **AarogyaConnect AI Operations Dashboard**.
   - **Metrics Overview:** Point out updated real-time counts for appointments, ambulance demos, and tickets.
   - **Confirmed Appointments Table:** Show the booking created in Scene 1 (`APT-XXXXXX` for `Amit Verma`) highlighted with a `NEW` badge.
   - **Ambulance Requests Table:** Show `AMB-XXXXXX` marked with `REQUEST_RECORDED_DEMO` and persistent simulation notice.
   - **Support Tickets Table:** Show `TKT-XXXXXX` in `OPEN` status.
   - **Interactive Status Update:** Click the **Resolve** button on `TKT-XXXXXX` — the ticket instantly updates to `RESOLVED` via backend API (`PATCH /api/tickets/{id}/status`).
   - **Audit Trail Table:** Show the timestamped logs of agent tool executions.

---

## Scene 6 — Human Escalation & Callback Queue
*Demonstrates seamless escalation from automated patient assistance to live operator queue.*

1. **User Action:** Click the **Patient Assistant** link in the dashboard header to return to the chat.
2. **User Action:** In the chat input, type:
   ```text
   I want to speak with a human representative.
   ```
3. **What the Agent Does:**
   - Registers an internal escalation in SQLite: `ESC-XXXXXX`.
   - Displays the **Human Operator Escalation** card.
4. **User Action:** Switch back to the **Operations Dashboard** tab (available in the navbar for authenticated operators).
5. **Dashboard Demonstration:**
   - Point to the **Human Escalations** table.
   - Show `ESC-XXXXXX` live in the operator queue under `PENDING ATTENTION`.
   - Click **Resolve** to mark the escalation resolved by the operator.
6. **User Action:** Click **Logout** in the navigation bar to demonstrate session termination and return to the secure patient view.

---

## Live Demo Summary Takeaway
- **100% Functional:** Every action writes real records to SQLite.
- **Zero Hallucination:** Deterministic fallback mode works fully offline.
- **Role-Separated:** Unauthenticated patients cannot see or query hospital-wide rosters; authorized operators access real audit controls.
- **Strict Safety:** Never claims false dispatch and advises 108/112 for real emergencies.

