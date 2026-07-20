import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import get_visual_llm
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

def run_test_text():
    try:
        print("\n--- Testing LangChain Text-Only ChatOpenAI ---")
        llm = ChatOpenAI(
            base_url="https://jmapi01.jaguarmicro.com/v1",
            api_key="sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ",
            model="gpt-5.4",
            temperature=0.0
        )
        res = llm.invoke("Hello")
        print("Text Success! Response:")
        print(res.content)
    except Exception as e:
        print("Text Error:")
        import traceback
        traceback.print_exc()

def run_test_image():
    try:
        print("\n--- Testing LangChain Multimodal ChatOpenAI with real image ---")
        llm = ChatOpenAI(
            base_url="https://jmapi01.jaguarmicro.com/v1",
            api_key="sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ",
            model="gpt-5.4",
            temperature=0.0
        )
        
        image_path = Path("/mnt/e/flow/03_JBP_PNR/res/1_1_flowtool_intro.png")
        if not image_path.exists():
            print(f"Error: image not found at {image_path}")
            return
            
        import base64
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(image_path))
        with open(image_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode("utf-8")
            
        data_url = f"data:{mime_type};base64,{encoded}"
        message = HumanMessage(
            content=[
                {"type": "text", "text": "Describe this schematic/diagram/table in detail in Chinese."},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        )
        print("Sending real image to gpt-5.4...")
        res = llm.invoke([message])
        print("Real Image Success! Response:")
        print(res.content)
    except Exception as e:
        print("Real Image Error:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test_image()

