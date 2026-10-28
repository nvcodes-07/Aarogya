# AarogyaConnect AI — Hospital Operations Platform

**AarogyaConnect AI** is an action-oriented customer operations platform built for **Aarogya Multispeciality Hospital** (Indore, MP) for **Code-E-Fiesta 2026**.

Tagline: *"From patient conversations to completed hospital workflows."*

Unlike generic conversational chatbots, AarogyaConnect AI executes real hospital backend operations:
1. **Doctor Appointment Booking:** Searches specialists (Cardiology, Orthopedics, Dermatology, General Medicine), checks real-time slot availability, collects patient details, enforces explicit confirmation, and records bookings with unique references (`APT-XXXXXX`) in SQLite.
2. **Simulated Ambulance Requests:** Collects pickup details with a prominent emergency safety disclaimer, creates unique references (`AMB-XXXXXX`), and routes critical life-threatening emergencies (acute chest pain, stroke, trauma) to National Emergency Services (108 / 112).
3. **Grounded Hospital Knowledge Base:** Delivers non-hallucinatory policy answers for OPD schedules, visiting hours, cashless TPA insurance, and appointment preparation.
4. **Complaint Management & Human Escalation:** Files customer support grievances (`TKT-XXXXXX`) and escalates urgent issues to human duty coordinators (`ESC-XXXXXX`).
5. **Real-time Operations Dashboard:** Role-separated dashboard providing hospital operators with live roster monitoring, interactive ticket resolution, and an agent tool execution audit trail.

---

## Architecture & Patient/Operator Separation

```text
                  ┌─────────────────────────────────────────────────────────────┐
                  │                 Public Internet / Patient                   │
                  └──────────────────────────────┬──────────────────────────────┘
                                                 │
                                 Default Landing View: Patient Portal
                                                 │
                                                 ▼
                  ┌─────────────────────────────────────────────────────────────┐
                  │                     Patient Assistant                       │
                  │  • Book Appointment (Confirmation required)                 │
                  │  • Hospital Policies & FAQ retrieval                        │
                  │  • Simulated Ambulance demo registration                    │
                  │  • Support grievance filing / human callback                │
                  └──────────────────────────────┬──────────────────────────────┘
                                                 │
                                                 ▼
             Public Endpoints: /api/chat, /api/doctors, /api/appointments (POST)
       ──────────────────────────────────────────────────────────────────────────────
             Protected Endpoints: /api/dashboard/stats, /api/appointments (GET),
                                  /api/ambulance-requests (GET), /api/tickets (GET),
                                  /api/escalations (GET), /api/actions (GET)
                                                 ▲
                                                 │ (Bearer <HMAC-SHA256 Token>)
                                                 │
                  ┌─────────────────────────────────────────────────────────────┐
                  │                 Hospital Operator Portal Gate               │
                  │  • Dedicated "Operator Login" button in Navbar & Sidebar    │
                  │  • Authenticates against backend OPERATOR_* env variables   │
                  │  • ZERO hardcoded passwords in frontend code                │
                  │  • Autofills demo credentials directly from backend         │
                  └──────────────────────────────┬──────────────────────────────┘
                                                 │
                                                 ▼
                  ┌─────────────────────────────────────────────────────────────┐
                  │                Operations Dashboard (Locked)                │
                  │  • Confirmed Appointments Roster                            │
                  │  • Simulated Ambulance Request Queue                        │
                  │  • Grievances & Support Tickets (Interactive Resolution)    │
                  │  • Human Escalation Desk                                    │
                  │  • Agent Audit Trails & System Metrics                      │
                  └─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

- **Frontend:** React 19, TypeScript, Vite 6, Tailwind CSS 3, Lucide React icons
- **Backend API:** FastAPI, Pydantic v2, Starlette, Uvicorn (ASGI)
- **Database & ORM:** SQLite 3, SQLAlchemy 2.0 (Relational schema with ACID transactions)
- **AI Orchestration:** Dual-engine architecture:
  - **LLM Function Calling Engine:** OpenAI-compatible API (Groq, OpenAI, Ollama, etc.)
  - **Deterministic Fallback Engine:** 100% offline rule-based parser with state machines and regex extraction (guarantees zero hallucination even with zero API keys or no internet)
- **Security & Authorization:** HMAC-SHA256 signed bearer session tokens, FastAPI dependencies (`Depends(require_operator)`), constant-time signature comparison (`hmac.compare_digest`)
- **Testing:** Pytest, HTTPX, FastAPI TestClient (41 automated tests)

---

## Project Structure

```text
Aarogya AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat.py             # Public chat orchestrator endpoint
│   │   │   └── endpoints.py        # Public & protected hospital REST APIs
│   │   ├── auth.py                 # HMAC-SHA256 token generation & verification
│   │   ├── config.py               # Pydantic settings loading from .env
│   │   ├── database.py             # SQLAlchemy engine & session factory
│   │   ├── main.py                 # FastAPI application factory & CORS setup
│   │   ├── models.py               # ORM models (Doctors, Slots, Appointments, etc.)
│   │   ├── schemas.py              # Pydantic validation schemas
│   │   ├── seed_data.py            # Dynamic seeding for upcoming dates & slots
│   │   └── services/
│   │       ├── agent.py            # Dual-mode AI agent & intent parser
│   │       ├── knowledge.py        # Seeded hospital policy knowledge base
│   │       └── operations.py       # Database transactional operations & audit logging
│   ├── requirements.txt            # Python dependencies
│   └── tests/
│       ├── test_ai_agent.py        # Agent tool and prompt tests
│       ├── test_api.py             # Public vs protected auth boundary tests
│       ├── test_audit_workflows.py # Core 4 workflow integration tests
│       ├── test_operations.py      # Database CRUD & constraint tests
│       └── test_phase6_scenarios.py # 10 end-to-end audit scenario tests
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatCards.tsx       # Rich interactive cards (Slots, Proposed, Confirmed)
│   │   │   ├── FormattedMessage.tsx# Markdown renderer with safe line formatting
│   │   │   ├── Navbar.tsx          # Top navigation with role-separated auth entry
│   │   │   └── OperatorLoginModal.tsx # Demo authentication gate with zero hardcoded secret
│   │   ├── services/
│   │   │   └── api.ts              # Typed API client with automatic token injection
│   │   ├── types/
│   │   │   └── index.ts            # TypeScript interfaces
│   │   ├── App.tsx                 # Core UI with Patient Portal & Operations Dashboard
│   │   └── main.tsx                # React entry point
│   ├── package.json
│   └── vite.config.ts
├── .env.example                    # Template environment variables
├── reset_demo_db.py                # Single-command database reset script
├── DEMO_SCRIPT.md                  # 6-minute live presentation guide
└── README.md                       # Comprehensive documentation
```

---

## Quick Start & Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+ and npm

### 1. Environment Setup
```bash
# Clone or navigate to the project directory
cd "/Users/neev/Aarogya AI"

# Copy environment template
cp .env.example .env
```

### 2. Backend Setup
```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Start backend server (Port 8000)
PYTHONPATH=backend ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be accessible at: `http://localhost:8000/docs`

### 3. Frontend Setup
```bash
# In a separate terminal tab:
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
The patient portal will be live at: `http://localhost:5173`

---

## Environment Variables Configuration

All backend configurations are managed via `.env` (loaded automatically by `backend/app/config.py`):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Deployment environment |
| `HOST` | `0.0.0.0` | API bind address |
| `PORT` | `8000` | API bind port |
| `DATABASE_URL` | `sqlite:///./aarogya_hospital.db` | SQLite database path |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins |
| `OPERATOR_USERNAME` | `operator@aarogya.org` | Demo operator username |
| `OPERATOR_PASSWORD` | `AarogyaOp@2026` | Demo operator password |
| `OPERATOR_SECRET_KEY` | *(HMAC secret)* | Secret for HMAC-SHA256 session tokens |
| `OPERATOR_TOKEN_EXPIRE_HOURS` | `12` | Session duration |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | *(blank)* | **Optional** LLM API key |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | LLM model name |

### Configuring an LLM Provider Safely
The application works 100% offline using its local Deterministic Fallback Engine. To enable real LLM function calling without hardcoding secrets:
1. Open `.env`
2. Add your provider's API key:
   ```env
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_API_KEY=gsk_your_actual_key_here
   LLM_MODEL=llama-3.3-70b-versatile
   ```
3. Restart the backend. The UI status pill will switch from `Deterministic Fallback Demo` to `AI Mode (llama-3.3-70b-versatile)`.
4. **Never commit `.env` to version control.**

---

## Database Reset Instructions

To reset the demonstration database to a pristine baseline (clearing test data and generating fresh doctor slots for the upcoming 5 days):

```bash
# Run from repository root:
./venv/bin/python3 reset_demo_db.py
```

This cleans and re-seeds:
- 4 Specialist Doctors (Cardiology, Orthopedics, Dermatology, General Medicine)
- 25 dynamic future consultation slots (10:00 AM, 11:30 AM, 02:00 PM, 03:30 PM, 04:30 PM across upcoming days)
- 1 baseline sample appointment for initial dashboard rendering

---

## Running Automated Tests

Run the complete 41-test backend test suite:

```bash
PYTHONPATH=backend ./venv/bin/pytest -v
```

Run frontend production build verification:

```bash
cd frontend && npm run build
```

---

## Role-Based Access Credentials

- **Patient Portal:** Open access at `http://localhost:5173`
- **Hospital Operator Portal:**
  - Click **Operator Login** in the header
  - **Username:** `operator@aarogya.org`
  - **Password:** `AarogyaOp@2026` *(or click "Autofill Demo Credentials from Backend" in the login gate)*

---

## Safety, Privacy & Demo Disclaimers

1. **Simulated Ambulance Requests:** All ambulance dispatches registered in this portal are simulations for hackathon demonstration. No actual vehicle is dispatched. For actual medical emergencies in India, dial **108 / 112**.
2. **Emergency Triage:** Inputs containing acute life-threatening triggers (chest pain, stroke, unconsciousness) immediately bypass intake and advise calling 108 / 112.
3. **Medical Advice Disclaimer:** AarogyaConnect AI does not diagnose medical conditions or prescribe medications. It is strictly an operational intake assistant.
4. **Patient Privacy Guard:** Hospital-wide rosters and patient records are protected server-side with HMAC-SHA256 authorization. Unauthenticated patients cannot dump or list database records.
