import json

import pytest

from backend.tests.test_routes.test_doctors import create_test_doctors
from backend.tests.test_routes.test_teams import create_teams
from tests.utils.users import login_test_user


def add_working_hours(client, amount_users=1, amount_practices=1, amount_wh=1):
    users = create_test_doctors(client, amount_users)
    create_teams(client, amount_practices)
    for i in range(amount_wh):
        user = users[i % amount_users]
        login_test_user(client, user["email"])
        practice_id = i % amount_practices
        data = {
            "day_of_week": "Monday",
            "start_time": "10:00",
            "end_time": "14:00",
            "practice_id": str(practice_id),
        }
        client.post(
            url="/working_hours/create",
            content=json.dumps(data),
        )


def test_create_working_hours(client, user_logged_in):
    # Test adding working hours
    data = {
        "day_of_week": "Monday",
        "start_time": "10:00",
        "end_time": "14:00",
        "practice_id": "1",
    }
    # Test adding working hours
    response = client.post(
        url="/working_hours/create",
        content=json.dumps(data),
    )
    assert response.status_code == 200
    assert response.json()["start_time"] == "10:00"
    assert response.json()["end_time"] == "14:00"


@pytest.mark.parametrize(
    "day_of_week,start_time,end_time",
    [
        ("Monday1", "10:00", "13:00"),
        ("Monday", "110:00", "13:00"),
        ("Monday", "10:00", "131:00"),
        ("Monday", "10:70", "13:00"),
        ("Monday", "10:00", "13:90"),
    ],
)
def test_create_working_hours_wrong_fields(
    client, day_of_week, start_time, end_time, user_logged_in
):
    # Test adding working hours
    data = {
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": end_time,
        "practice_id": 1,
    }
    response = client.post(
        url="/working_hours/create",
        content=json.dumps(data),
    )
    assert response.status_code == 422


def test_retrieve_working_hours(client, user_logged_in):
    add_working_hours(client)
    response = client.get("/working_hours/get/1")
    assert response.status_code == 200
    assert response.json()["day_of_week"] == "Monday"


def test_update_working_hours(client, user_logged_in):
    add_working_hours(client)
    data = {
        "day_of_week": "Monday",
        "start_time": "10:00",
        "end_time": "21:37",
        "practice_id": 1,
    }

    response = client.put("/working_hours/update/1", content=json.dumps(data))
    assert response.json()["msg"] == "Successfully updated data."
    response = client.get("/working_hours/get/1")
    assert response.json()["end_time"] == "21:37"


def test_delete_working_hours(client, user_logged_in):
    add_working_hours(client)
    response = client.delete("/working_hours/delete/1")
    assert response.json()["msg"] == "Successfully deleted data."
    response = client.get("/working_hours/get/1")
    assert response.status_code == 404


def test_get_doctors_working_hours(client):
    response = client.get("/working_hours/get_doctor/1")
    assert response.status_code == 200
    assert len(response.json()) == 0

    add_working_hours(
        client,
        amount_users=3,
        amount_practices=2,
        amount_wh=10,
    )
    response = client.get("/working_hours/get_doctor/2")
    assert response.status_code == 200
    assert 10 > len(response.json()) > 0
