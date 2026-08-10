import pytest
import secrets
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    suffix = secrets.token_hex(4)
    username = f"ai_user_{suffix}"
    email = f"ai_user_{suffix}@example.com"
    password = "Password123"

    # Register
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "full_name": "AI Tester"
    })

    # Login
    login_res = client.post("/auth/login", data={
        "username": email,
        "password": password
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ai_confirmation_flow(auth_headers):
    # 1. Send command to create task
    chat_payload = {
        "question": "create task Build Logo with description build premium vector asset",
        "is_static": False
    }
    res1 = client.post("/ai-chat/", json=chat_payload, headers=auth_headers)
    assert res1.status_code == 200
    ans1 = res1.json()["answer"]
    
    # Verify we got the draft confirmation prompt
    assert "Would you like me to create this task? (Yes/No)" in ans1
    assert "Build Logo" in ans1

    # 2. Confirm the task creation by saying "Yes"
    confirm_payload = {
        "question": "Yes",
        "is_static": False
    }
    res2 = client.post("/ai-chat/", json=confirm_payload, headers=auth_headers)
    assert res2.status_code == 200
    ans2 = res2.json()["answer"]

    # Verify task was successfully created
    assert "Task created successfully" in ans2
    assert "Build Logo" in ans2
