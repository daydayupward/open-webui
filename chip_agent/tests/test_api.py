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
    
    called_state = mock_graph.invoke.call_args[0][0]
    assert len(called_state["messages"]) == 4
    assert called_state["messages"][0].content == "You are a helpful assistant."
    assert called_state["messages"][1].content == "Hello!"
    assert called_state["messages"][2].content == "Hi! How can I help you today?"
    assert called_state["messages"][3].content == "Write an Innovus floorplan script."

@patch("src.main.astream_chat_completion_events")
def test_chat_completions_streaming(mock_stream_events):
    async def mock_generator(*args, **kwargs):
        yield "data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}\n\n"
        yield "data: [DONE]\n\n"
    mock_stream_events.return_value = mock_generator()
    
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hello"}], "stream": True}
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "Hello" in response.text
    assert "[DONE]" in response.text

def test_list_models():
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"][0]["id"] == "chip-agentic-rag"

def test_chat_completions_invalid_payload():
    # Missing 'messages' field
    response = client.post(
        "/v1/chat/completions",
        json={"model": "chip-agentic-rag"}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_chat_completions_invalid_types():
    # 'messages' is a string instead of array
    response = client.post(
        "/v1/chat/completions",
        json={"messages": "hello", "model": "chip-agentic-rag"}
    )
    assert response.status_code == 422
