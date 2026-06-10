from unittest.mock import patch, MagicMock
from src.experts.pdk_expert import pdk_expert_node
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document

@patch("src.experts.pdk_expert.get_vector_store")
@patch("src.experts.pdk_expert.get_embeddings")
@patch("src.experts.pdk_expert.get_llm")
def test_pdk_expert_node(mock_get_llm, mock_get_embeddings, mock_get_vector_store):
    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="[PDK Expert] The M3 pitch for N5 is 36nm.")
    mock_get_llm.return_value = mock_llm
    
    # Mock Vector Store
    mock_store = MagicMock()
    mock_store.similarity_search.return_value = [Document(page_content="N5 M3 metal pitch is 36nm.")]
    mock_get_vector_store.return_value = mock_store
    
    # Mock Embeddings
    mock_get_embeddings.return_value = MagicMock()

    state = {"messages": [HumanMessage(content="What is N5 M3 pitch?")]}
    result = pdk_expert_node(state)
    
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert "PDK" in result["messages"][0].content
    mock_store.similarity_search.assert_called_once_with("What is N5 M3 pitch?", k=3)
