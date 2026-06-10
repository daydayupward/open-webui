import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Load environment variables
load_dotenv()

def get_llm():
    base_url = os.getenv("OPENAI_API_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", "nvidia-nemotron-3-super-120b-a12b-fp8")
    
    # Fallback default configuration if env vars are missing
    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=0.0
    )

def get_embeddings():
    base_url = os.getenv("OPENAI_API_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("EMBEDDING_MODEL", "bge-m3")
    
    return OpenAIEmbeddings(
        model=model,
        openai_api_base=base_url,
        openai_api_key=api_key
    )
