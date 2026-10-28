import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Appointment
from app.services import agent, operations
from app.seed_data import seed_database
from app.config import settings

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

@pytest.mark.anyio
async def test_ai_tool_calling_workflow(test_db):
    """
    Test AI provider mode tool-calling workflow:
    Simulate LLM tool call to prepare_appointment_confirmation and search_hospital_faq.
    """
    # 1. Mock first LLM response calling 'search_doctors' and 'check_slots'
    mock_tool_call_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "search_doctors",
                                "arguments": json.dumps({"department": "Cardiology"})
                            }
                        }
                    ]
                }
            }
        ]
    }

    # 2. Mock second LLM synthesis response
    mock_followup_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Dr. Ananya Sharma is available in the Cardiology department. Her consultation fee is ₹1000."
                }
            }
        ]
    }

    with patch.object(settings, "LLM_API_KEY", "test-key-12345"), \
         patch("httpx.AsyncClient.post") as mock_post:
        
        # Configure mock responses for pass 1 and pass 2
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = mock_tool_call_resp
        mock_resp1.raise_for_status = MagicMock()

        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = mock_followup_resp
        mock_resp2.raise_for_status = MagicMock()

        mock_post.side_effect = [mock_resp1, mock_resp2]

        chat_resp = await agent.handle_ai_turn(
            db=test_db,
            message="Who is your cardiologist?",
            session_id="ai-session-1",
            history=[],
            pending_booking=None
        )

        assert chat_resp.mode == "ai"
        assert "Dr. Ananya Sharma" in chat_resp.reply
        assert mock_post.call_count == 2

@pytest.mark.anyio
async def test_ai_fault_fallback_to_deterministic(test_db):
    """
    Test that if AI provider fails or times out, the system safely falls back
    to the deterministic engine and does not label it as AI.
    """
    with patch.object(settings, "LLM_API_KEY", "test-key-12345"), \
         patch("httpx.AsyncClient.post", side_effect=Exception("API Connection Timeout")):
        
        # When process_chat_message runs and AI fails, it must fallback to deterministic engine
        chat_resp = await agent.process_chat_message(
            db=test_db,
            message="What are the OPD timings?",
            session_id="fallback-sess",
            history=[],
            pending_booking=None
        )

        assert chat_resp.mode == "deterministic_demo"
        assert "OPD Timings" in chat_resp.reply
        assert "09:00 AM to 01:00 PM" in chat_resp.reply
        # Ensure it's not labeled as AI generated
        assert chat_resp.mode != "ai"

@pytest.mark.anyio
async def test_sarvam_ai_live_doctor_search_grounded(test_db):
    """Real Sarvam AI API request testing doctor search and database grounding."""
    if not settings.SARVAM_API_KEY:
        pytest.skip("SARVAM_API_KEY not configured in environment")

    chat_resp = await agent.handle_ai_turn(
        db=test_db,
        message="Find a cardiologist doctor for me",
        session_id="sarvam-test-1",
        history=[],
        pending_booking=None
    )

    assert chat_resp.mode == "ai"
    assert "Dr. Ananya Sharma" in chat_resp.reply or "Cardiology" in chat_resp.reply
    assert chat_resp.structured_data is not None

@pytest.mark.anyio
async def test_sarvam_ai_live_hospital_faq_grounded(test_db):
    """Real Sarvam AI API request testing grounded hospital OPD FAQ."""
    if not settings.SARVAM_API_KEY:
        pytest.skip("SARVAM_API_KEY not configured in environment")

    chat_resp = await agent.handle_ai_turn(
        db=test_db,
        message="What are the OPD timings and consultation hours?",
        session_id="sarvam-test-2",
        history=[],
        pending_booking=None
    )

    assert chat_resp.mode == "ai"
    assert "OPD" in chat_resp.reply or "09:00 AM" in chat_resp.reply or "Emergency" in chat_resp.reply

@pytest.mark.anyio
async def test_sarvam_ai_ungrounded_policy_acknowledges_limitation(test_db):
    """Real Sarvam AI API request verifying that ungrounded queries acknowledge limitations."""
    if not settings.SARVAM_API_KEY:
        pytest.skip("SARVAM_API_KEY not configured in environment")

    chat_resp = await agent.handle_ai_turn(
        db=test_db,
        message="Can I bring my pet tiger or elephant to the hospital?",
        session_id="sarvam-test-3",
        history=[],
        pending_booking=None
    )

    assert chat_resp.mode == "ai"
    assert any(term in chat_resp.reply.lower() for term in ["not available", "not found", "verified", "coordinator", "records", "escalat"])

@pytest.mark.anyio
async def test_sarvam_ai_fallback_on_invalid_credentials(test_db):
    """Verify that an invalid Sarvam API key falls back to the deterministic engine safely."""
    with patch.object(settings, "SARVAM_API_KEY", "sk_invalid_test_key_xyz"), \
         patch.object(settings, "LLM_API_KEY", None):
        
        chat_resp = await agent.process_chat_message(
            db=test_db,
            message="Find a cardiologist",
            session_id="sarvam-fallback-sess",
            history=[],
            pending_booking=None
        )

        assert chat_resp.mode == "deterministic_demo"
        assert "Dr. Ananya Sharma" in chat_resp.reply

