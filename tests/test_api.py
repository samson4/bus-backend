from fastapi.testclient import TestClient as TestClient
from ..main.py import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == "Server is running"
