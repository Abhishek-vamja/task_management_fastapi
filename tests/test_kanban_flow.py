import pytest
import secrets
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    # Register and login a unique user
    suffix = secrets.token_hex(4)
    username = f"test_{suffix}"
    email = f"test_{suffix}@example.com"
    password = "Password123"

    # Register
    reg_res = client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "full_name": "Test User"
    })
    assert reg_res.status_code == 201

    # Login
    login_res = client.post("/auth/login", data={
        "username": email,
        "password": password
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_board_crud_and_tasks(auth_headers):
    # 1. Create a board
    board_payload = {
        "name": "Sprint Board",
        "description": "Sprint tracking",
        "type": "team",
        "privacy": "private",
        "accent_color": "purple",
        "icon": "briefcase",
        "columns": ["todo", "in_progress", "done"]
    }
    board_res = client.post("/boards/", json=board_payload, headers=auth_headers)
    assert board_res.status_code == 201
    board_data = board_res.json()
    assert board_data["name"] == "Sprint Board"
    board_id = board_data["id"]

    # 2. Get my boards
    get_boards = client.get("/boards/", headers=auth_headers)
    assert get_boards.status_code == 200
    assert any(b["id"] == board_id for b in get_boards.json())

    # 3. Create tasks on this board
    t1_payload = {
        "title": "Task One",
        "description": "First task description",
        "status": "todo",
        "priority": "high",
        "tag": "Backend",
        "board_id": board_id,
        "position": 0
    }
    t2_payload = {
        "title": "Task Two",
        "description": "Second task description",
        "status": "todo",
        "priority": "low",
        "tag": "Frontend",
        "board_id": board_id,
        "position": 1
    }

    t1_res = client.post("/tasks/", json=t1_payload, headers=auth_headers)
    assert t1_res.status_code == 201
    t1_id = t1_res.json()["id"]

    t2_res = client.post("/tasks/", json=t2_payload, headers=auth_headers)
    assert t2_res.status_code == 201
    t2_id = t2_res.json()["id"]

    # 4. Get board tasks
    tasks_res = client.get(f"/boards/{board_id}/tasks", headers=auth_headers)
    assert tasks_res.status_code == 200
    tasks_data = tasks_res.json()
    assert len(tasks_data) == 2
    assert tasks_data[0]["id"] == t1_id
    assert tasks_data[1]["id"] == t2_id

    # 5. Bulk reorder tasks (swap positions & status)
    reorder_payload = {
        "tasks": [
            {"id": t1_id, "position": 1, "status": "in_progress"},
            {"id": t2_id, "position": 0, "status": "in_progress"}
        ]
    }
    reorder_res = client.put("/tasks/reorder", json=reorder_payload, headers=auth_headers)
    assert reorder_res.status_code == 200

    # Verify positions updated
    tasks_after = client.get(f"/boards/{board_id}/tasks", headers=auth_headers)
    assert tasks_after.status_code == 200
    sorted_tasks = sorted(tasks_after.json(), key=lambda x: x["position"])
    assert sorted_tasks[0]["id"] == t2_id
    assert sorted_tasks[0]["position"] == 0
    assert sorted_tasks[0]["status"] == "in_progress"
    assert sorted_tasks[1]["id"] == t1_id
    assert sorted_tasks[1]["position"] == 1
    assert sorted_tasks[1]["status"] == "in_progress"


def test_member_invitation_flow(auth_headers):
    # Create board
    board_res = client.post("/boards/", json={
        "name": "Team Space",
        "columns": ["todo", "done"]
    }, headers=auth_headers)
    board_id = board_res.json()["id"]

    # Register another user
    suffix = secrets.token_hex(4)
    invitee_email = f"invitee_{suffix}@example.com"
    invitee_pwd = "Password123"
    client.post("/auth/register", json={
        "username": f"invitee_{suffix}",
        "email": invitee_email,
        "password": invitee_pwd,
        "full_name": "Invited Developer"
    })

    # 1. Invite the member (should add directly since user exists)
    invite_res = client.post(f"/boards/{board_id}/invite", json={
        "email": invitee_email,
        "role": "developer"
    }, headers=auth_headers)
    assert invite_res.status_code == 200
    assert invite_res.json()["status"] == "added_directly"

    # Verify member list
    members_res = client.get(f"/boards/{board_id}/members", headers=auth_headers)
    assert members_res.status_code == 200
    assert any(m["user"]["email"] == invitee_email for m in members_res.json())


if __name__ == "__main__":
    print("Running integration tests...")
    # Mock fixture
    headers = auth_headers.__wrapped__() if hasattr(auth_headers, "__wrapped__") else auth_headers()
    print("Testing board CRUD and tasks...")
    test_board_crud_and_tasks(headers)
    print("Testing member invitation flow...")
    test_member_invitation_flow(headers)
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")

