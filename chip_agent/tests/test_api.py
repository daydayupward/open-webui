from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@patch("src.main.graph")
def test_chat_completions(mock_graph):
    mock_graph.invoke.return_value = {
        "messages": [AIMessage(content="[PDK Expert] The metal pitch is 36nm.")]
    }
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "What is N5 M3 pitch?"}]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert "PDK" in data["choices"][0]["message"]["content"]

def test_list_models():
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"][0]["id"] == "chip-agentic-rag"

