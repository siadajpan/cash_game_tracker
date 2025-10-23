import json

import pytest


def create_practices(client, amount=1):
    for i in range(amount):
        data = {
            "email": f"test_email{i}@test.com",
            "password": "test_password",
            "name": f"practice{i}",
            "postcode": "5000",
            "city": "Test",
            "address": "test address",
        }
        client.post(url="/practices/create", content=json.dumps(data))


@pytest.mark.parametrize("apartment_number", ["150", ""])
def test_create_practice(client, apartment_number):
    data = {
        "email": "test_email@test.com",
        "password": "test_password",
        "name": "practice1",
        "postcode": "5000",
        "city": "Test",
        "address": "test address",
    }
    response = client.post(url="/practices/create", content=json.dumps(data))
    assert response.status_code == 200
    assert response.json()["name"] == "practice1"
    assert response.json()["postcode"] == "5000"
    assert response.json()["city"] == "Test"
    assert response.json()["address"] == "test address"
    assert response.json()["id"] is not None
    assert response.json()["user_id"] is not None


def test_read_practice(client):
    create_practices(client)
    response = client.get(url="/practices/get/1")
    assert response.status_code == 200
    assert response.json()["name"] == "practice0"


def test_read_practices(client):
    create_practices(client, amount=10)
    response = client.get(url="/practices/all")
    assert response.status_code == 200
    assert len(response.json()) == 10
