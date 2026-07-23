import openai
import traceback

def check():
    try:
        client = openai.OpenAI(
            base_url="http://10.1.88.119:8100/v1",
            api_key="gpustack_8a84577e7871ac6c_2c3d4ef8e376a5d2fca5ceb8e1cc4221"
        )
        print("Models on GPUStack:")
        for m in client.models.list().data:
            print(f"- {m.id}")
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    check()
