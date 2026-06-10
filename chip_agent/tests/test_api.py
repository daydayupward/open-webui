from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_chat_completions():
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "What is N5 M3 pitch?"}]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert "PDK" in data["choices"][0]["message"]["content"]
