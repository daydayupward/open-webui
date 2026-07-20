import openai

def run_test_model(model_name, messages):
    try:
        client = openai.OpenAI(
            base_url="https://jmapi01.jaguarmicro.com/v1",
            api_key="sk-4FdTM7qOGWDEKoO86FweSAbkANjnPlshni1kiHv3gTKj1rrZ"
        )
        print(f"\n--- Testing model: {model_name} ---")
        res = client.chat.completions.create(
            model=model_name,
            messages=messages
        )
        print(f"Success for {model_name}!")
        print("Response:", res.choices[0].message.content)
    except Exception as e:
        print(f"Error for {model_name}: {e}")

def run_test():
    data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    # Test each with image input
    for model in ["deepseek-v4-pro", "gpt-5.4", "deepseek-v4-flash"]:
        run_test_model(model, [{
            "role": "user",
            "content": [
                {"type": "text", "text": "What is this image?"},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        }])

if __name__ == "__main__":
    run_test()


