import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core.config import settings


def login_test_user(client: TestClient, email: str):
    print(f"loging {email}")
    user = client.get(f"/users/get/{email}")
    print("user", user.json())

    if not user.json():
        user_data = {
            "email": email,
            "password": settings.TEST_USER_PASSWORD,
        }
        print("creating one")
        client.post(url=f"/users/create", content=json.dumps(user_data))
    login_data = {
        "username": email,
        "password": settings.TEST_USER_PASSWORD,
    }

    r = client.post("/login/token", data=login_data)
    print("token resp", r)
