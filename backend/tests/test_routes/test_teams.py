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
    from backend.apis.v1.route_login import get_current_user_from_token

    test_app.dependency_overrides[get_current_user_from_token] = lambda: mock_user
    test_app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    yield TestClient(test_app)

    # Clean up
    test_app.dependency_overrides.clear()


def test_create_team(client, db_session):
    data = {"name": "Team1"}

    response = client.post("/team/create", data=data, follow_redirects=False)

    # Now it will see the actual redirect response
    assert response.status_code == 302
    assert response.headers["location"] == "/"

    # Verify team is in DB
    team_in_db = db_session.query(Team).filter_by(name="Team1").first()
    assert team_in_db is not None
    assert team_in_db.owner.nick == "Mock"


def create_teams(client, amount=1):
    for i in range(amount):
        data = {"name": f"team{i}"}
        client.post("/team/create", data=data)


def test_read_team(client):
    create_teams(client)
    # The URL is /team/{id}, not /team/get/{id}
    response = client.get(url="/team/1")
    assert response.status_code == 200
    # Response is HTML, so we check if the name is in the text
    assert "team0" in response.text
