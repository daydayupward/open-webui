from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@patch("src.main.graph")
def test_chat_completions(mock_graph):
    mock_graph.invoke.return_value = {
        "final_answer": "[PDK Expert] The metal pitch is 36nm.",
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
    assert "id" in data
    assert data["object"] == "chat.completion"

@patch("src.main.graph")
def test_chat_completions_multi_turn(mock_graph):
    mock_graph.invoke.return_value = {
        "final_answer": "[EDA Script Expert] Innovus floorplan script created.",
        "messages": [AIMessage(content="[EDA Script Expert] Innovus floorplan script created.")]
    }
    multi_turn_payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi! How can I help you today?"},
            {"role": "user", "content": "Write an Innovus floorplan script."}
        ],
        "model": "chip-agentic-rag"
    }
    response = client.post(
        "/v1/chat/completions",
        json=multi_turn_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert "Innovus" in data["choices"][0]["message"]["content"]
    
    # Assert that graph was called with all four messages parsed correctly
    called_state = mock_graph.invoke.call_args[0][0]
    assert len(called_state["messages"]) == 4
    assert called_state["messages"][0].content == "You are a helpful assistant."
    assert called_state["messages"][1].content == "Hello!"
    assert called_state["messages"][2].content == "Hi! How can I help you today?"
    assert called_state["messages"][3].content == "Write an Innovus floorplan script."

def test_list_models():
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"][0]["id"] == "chip-agentic-rag"
