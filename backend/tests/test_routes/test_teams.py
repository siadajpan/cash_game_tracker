import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.staticfiles import StaticFiles

from backend.core.config import STATIC_DIR
from backend.db.models.team import Team
from backend.db.models.user import User
from backend.webapps.base import api_router
from backend.webapps.team import route_team

@pytest.fixture
def client(db_session):
    test_app = FastAPI()
    test_app.include_router(api_router)

    # Ensure a mock user exists
    mock_user = db_session.query(User).first()
    if not mock_user:
        mock_user = User(email="mock@example.com", hashed_password="pass", nick="Mock")
        db_session.add(mock_user)
        db_session.commit()
        db_session.refresh(mock_user)

    # Override the dependencies to use test session and mock user
    test_app.dependency_overrides[route_team.get_db] = lambda: db_session
    test_app.dependency_overrides[route_team.get_current_user] = lambda: mock_user
    test_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    yield TestClient(test_app)

    # Clean up
    test_app.dependency_overrides.clear()

def test_create_team(client, db_session):
    data = {"name": "Team1"}

    response = client.post("/team/create", data=data, allow_redirects=False)

    # Now it will see the actual redirect response
    assert response.status_code == 302
    assert response.headers["location"] == "/?msg=Team%20created%20successfully"

    # Verify team is in DB
    team_in_db = db_session.query(Team).filter_by(name="Team1").first()
    assert team_in_db is not None
    assert team_in_db.owner.nick == "Mock"

# def test_create_team(client, db_session):
#     data = {"name": "Team1"}
#
#     response = client.post("/team/create", data=data)
#
#     # POST redirects after success
#     assert response.status_code == 302
#     assert response.headers["location"] == "/?msg=Team created successfully"
#
#     # Verify team is in DB
#     team_in_db = db_session.query(Team).filter_by(name="Team1").first()
#     assert team_in_db is not None
#
# def test_create_team(client, db_session):
#     data = {"name": "team1"}
#
#     mock_user = db_session.query(User).first()  # or create a mock user
#
#     with patch("backend.webapps.team.route_team.get_current_user", return_value=mock_user):
#         response = client.post("/team/create", data=data)
#         assert response.status_code == 302

def test_read_practice(client):
    create_teams(client)
    response = client.get(url="/team/get/1")
    assert response.status_code == 200
    assert response.json()["name"] == "practice0"


def test_read_practices(client):
    create_teams(client, amount=10)
    response = client.get(url="/team/all")
    assert response.status_code == 200
    assert len(response.json()) == 10
