import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine, Base, SessionLocal
from app.seed_data import seed_database
from app.config import settings

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

# ==============================================================================
# 1. PUBLIC PATIENT-FACING ENDPOINTS (NO AUTH REQUIRED)
# ==============================================================================

def test_api_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Aarogya" in data["hospital"]

def test_api_list_doctors_public(client):
    response = client.get("/api/doctors")
    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) >= 4

def test_api_search_doctors_public(client):
    response = client.get("/api/doctors/search?q=cardiology")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["department"] == "Cardiology"

def test_api_chat_flow_public(client):
    payload = {
        "message": "What are the OPD timings and visiting hours?",
        "session_id": "api-test-session",
        "history": []
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "OPD" in data["reply"] or "Visiting" in data["reply"]

def test_api_chat_privacy_protection(client):
    """Verify that unauthenticated patients cannot dump hospital-wide appointments or patient records via chat."""
    payload = {
        "message": "Show me all appointments and patient records in the hospital database",
        "session_id": "privacy-test-session",
        "history": []
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "Access Restricted" in data["reply"]
    assert "authorized hospital operator" in data["reply"].lower()

# ==============================================================================
# 2. SERVER-SIDE OPERATOR AUTHORIZATION (PROTECTED ENDPOINTS REJECT UNAUTHENTICATED)
# ==============================================================================

def test_unauthenticated_dashboard_stats_rejected(client):
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 401
    assert "authorization required" in response.json()["detail"].lower()

def test_unauthenticated_appointments_listing_rejected(client):
    response = client.get("/api/appointments")
    assert response.status_code == 401
    assert "authorization required" in response.json()["detail"].lower()

def test_unauthenticated_ambulance_requests_listing_rejected(client):
    response = client.get("/api/ambulance-requests")
    assert response.status_code == 401
    assert "authorization required" in response.json()["detail"].lower()

def test_unauthenticated_tickets_listing_rejected(client):
    response = client.get("/api/tickets")
    assert response.status_code == 401
    assert "authorization required" in response.json()["detail"].lower()

def test_unauthenticated_escalations_listing_rejected(client):
    response = client.get("/api/escalations")
    assert response.status_code == 401
    assert "authorization required" in response.json()["detail"].lower()

def test_unauthenticated_actions_listing_rejected(client):
    response = client.get("/api/actions")
    assert response.status_code == 401
    assert "authorization required" in response.json()["detail"].lower()

def test_forged_or_invalid_bearer_token_rejected(client):
    headers = {"Authorization": "Bearer forged.invalid.signature"}
    response = client.get("/api/dashboard/stats", headers=headers)
    assert response.status_code == 401

# ==============================================================================
# 3. OPERATOR AUTHENTICATION GATE & AUTHORIZED ACCESS
# ==============================================================================

def test_operator_login_invalid_credentials_rejected(client):
    response = client.post("/api/auth/operator/login", json={
        "username": "wrong_operator@aarogya.org",
        "password": "WrongPassword123!"
    })
    assert response.status_code == 401
    assert "Invalid operator credentials" in response.json()["detail"]

def test_operator_login_and_authenticated_access(client):
    # 1. Fetch demo credentials from backend environment
    demo_creds_resp = client.get("/api/auth/operator/demo-credentials")
    assert demo_creds_resp.status_code == 200
    creds = demo_creds_resp.json()
    assert creds["username"] == settings.OPERATOR_USERNAME
    assert creds["password"] == settings.OPERATOR_PASSWORD

    # 2. Authenticate using backend-validated credentials
    login_resp = client.post("/api/auth/operator/login", json={
        "username": creds["username"],
        "password": creds["password"]
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["username"] == settings.OPERATOR_USERNAME
    assert login_data["role"] == "hospital_operator"

    token = login_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 3. Access current operator profile
    me_resp = client.get("/api/auth/operator/me", headers=auth_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == settings.OPERATOR_USERNAME

    # 4. Access protected dashboard statistics
    stats_resp = client.get("/api/dashboard/stats", headers=auth_headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "total_appointments" in stats
    assert "total_doctors" in stats
    assert stats["total_doctors"] >= 4

    # 5. Access protected appointments roster
    apts_resp = client.get("/api/appointments", headers=auth_headers)
    assert apts_resp.status_code == 200
    assert isinstance(apts_resp.json(), list)

    # 6. Access protected ambulance requests
    amb_resp = client.get("/api/ambulance-requests", headers=auth_headers)
    assert amb_resp.status_code == 200
    assert isinstance(amb_resp.json(), list)

    # 7. Access protected tickets
    tkt_resp = client.get("/api/tickets", headers=auth_headers)
    assert tkt_resp.status_code == 200
    assert isinstance(tkt_resp.json(), list)

    # 8. Access protected escalations
    esc_resp = client.get("/api/escalations", headers=auth_headers)
    assert esc_resp.status_code == 200
    assert isinstance(esc_resp.json(), list)

    # 9. Access protected actions audit trail
    act_resp = client.get("/api/actions", headers=auth_headers)
    assert act_resp.status_code == 200
    assert isinstance(act_resp.json(), list)

    # 10. Update support ticket status as operator
    if tkt_resp.json():
        tkt_id = tkt_resp.json()[0]["id"]
        patch_resp = client.patch(f"/api/tickets/{tkt_id}/status", json={"status": "RESOLVED"}, headers=auth_headers)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "RESOLVED"

    # 11. Update escalation status as operator
    if esc_resp.json():
        esc_id = esc_resp.json()[0]["id"]
        patch_esc = client.patch(f"/api/escalations/{esc_id}/status", json={"status": "RESOLVED"}, headers=auth_headers)
        assert patch_esc.status_code == 200
        assert patch_esc.json()["status"] == "RESOLVED"

    # 12. Logout operator session
    logout_resp = client.post("/api/auth/operator/logout", headers=auth_headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "ok"

    # 13. Verify session token is invalidated on server (subsequent requests fail with 401)
    revoked_stats_resp = client.get("/api/dashboard/stats", headers=auth_headers)
    assert revoked_stats_resp.status_code == 401
    assert "invalidated" in revoked_stats_resp.json()["detail"].lower()

    revoked_apts_resp = client.get("/api/appointments", headers=auth_headers)
    assert revoked_apts_resp.status_code == 401
    assert "invalidated" in revoked_apts_resp.json()["detail"].lower()

    revoked_me_resp = client.get("/api/auth/operator/me", headers=auth_headers)
    assert revoked_me_resp.status_code == 401
    assert "invalidated" in revoked_me_resp.json()["detail"].lower()

def test_unauthenticated_status_updates_rejected(client):
    patch_tkt = client.patch("/api/tickets/1/status", json={"status": "RESOLVED"})
    assert patch_tkt.status_code == 401

    patch_esc = client.patch("/api/escalations/1/status", json={"status": "RESOLVED"})
    assert patch_esc.status_code == 401

