import openai

def list_models():
    try:
        client = openai.OpenAI(
            base_url="https://jmapi01.jaguarmicro.com/v1",
            api_key="sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ"
        )
        print("Fetching model list...")
        models = client.models.list()
        for m in models.data:
            print(f"- {m.id}")
    except Exception as e:
        print("Error listing models:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_models()
