import requests
import json

url = "http://localhost:8000/v1/chat/completions"
headers = {"Content-Type": "application/json"}
data = {
    "model": "chip-agentic-rag",
    "messages": [{"role": "user", "content": "What is static timing analysis?"}],
    "stream": True
}

try:
    response = requests.post(url, headers=headers, json=data, stream=True)
    print("Status Code:", response.status_code)
    print("Streaming Response:")
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("data: "):
                data_str = decoded_line[6:]
                if data_str.strip() == "[DONE]":
                    print("\n[STREAM DONE]")
                    break
                try:
                    chunk = json.loads(data_str)
                    content = chunk['choices'][0]['delta'].get('content')
                    if content:
                        print(content, end="", flush=True)
                except Exception as e:
                    print(f"\nError parsing chunk: {e} for line: {decoded_line}")
except Exception as e:
    print("Failed:", e)
