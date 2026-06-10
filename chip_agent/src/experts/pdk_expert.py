import os
from typing import TypedDict, List
from langchain_core.messages import AnyMessage, SystemMessage
from src.utils import get_llm, get_embeddings
from src.vector_store import get_vector_store

class AgentState(TypedDict):
    messages: List[AnyMessage]

def pdk_expert_node(state: AgentState) -> dict:
    query = state["messages"][-1].content
    
    # Initialize embeddings and vector store
    embeddings = get_embeddings()
    connection_string = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/chip_design")
    collection_name = "pdk_rules"
    
    # Retrieve relevant context
    context = ""
    try:
        vector_store = get_vector_store(
            connection_string=connection_string,
            collection_name=collection_name,
            embeddings=embeddings
        )
        docs = vector_store.similarity_search(query, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        context = "No database context found due to connection issue."
        
    # Call LLM to generate final response
    llm = get_llm()
    system_prompt = SystemMessage(
        content=f"You are a specialized PDK Expert for backend chip physical design. "
                f"Your focus is process design kit rules, DRC limitations, LVS setup, pitch, and SPICE parameters. "
                f"Answer the user's question using the retrieved PDK context below. "
                f"If the context does not contain enough information, state that clearly but try to answer as best as possible.\n\n"
                f"Retrieved PDK Context:\n{context}"
    )
    
    messages = [system_prompt] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}
