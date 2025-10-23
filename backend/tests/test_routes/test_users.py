import json

import pytest
from sqlalchemy.exc import IntegrityError


def create_users(client, amount=1):
    users = []
    for i in range(amount):
        data = {
            "email": f"testemail{i}@email.com",
            "password": "testing",
        }
        users.append(data)
        client.post(url="/users/create", content=json.dumps(data))
    return users


def test_create_user(client):
    data = {
        "email": "testemail@email.com",
        "password": "testing",
    }
    response = client.post(url="/users/create", content=json.dumps(data))
    assert response.status_code == 200
    assert response.json()["email"] == "testemail@email.com"


def test_adding_same_user_twice(client):
    user = {
        "email": "testemail@email.com",
        "password": "testing",
    }
    response = client.post(url="/users/create", content=json.dumps(user))
    assert response.status_code == 200
    assert response.json()["email"] == "testemail@email.com"
    user2 = user.copy()

    with pytest.raises(IntegrityError):
        client.post(url="/users/create", content=json.dumps(user2))


def test_get_user(client):
    users = create_users(client, 1)
    email = users[0]["email"]
    response = client.get(url=f"/users/get/{email}")
    assert response.status_code == 200
    assert response.json()["email"] == email
