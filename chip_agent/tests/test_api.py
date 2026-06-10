from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage

# Patch build_graph before importing app
with patch("src.main.build_graph") as mock_build_graph:
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "messages": [AIMessage(content="[PDK Expert] The metal pitch is 36nm.")]
    }
    mock_build_graph.return_value = mock_graph

    from src.main import app
    from fastapi.testclient import TestClient
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

def test_list_models():
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"][0]["id"] == "chip-agentic-rag"

