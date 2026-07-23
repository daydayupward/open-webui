import json
import httpx

url = "http://localhost:8000/v1/chat/completions"
payload = {
    "model": "jbprag",
    "messages": [
        {
            "role": "user",
            "content": "在 innovusUG 中，使用 mixed placer 的流程图和流程步骤是什么？"
        }
    ],
    "temperature": 0.0,
    "stream": True
}

print("=== Sending request to API ===")
with httpx.stream("POST", url, json=payload, timeout=120.0) as r:
    for line in r.iter_lines():
        if line.strip():
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    print("\n=== Stream Done ===")
                    break
                try:
                    data = json.loads(data_str)
                    # Check if it's a source event
                    if "event" in data and data["event"].get("type") == "source":
                        print(f"\n[Source Event]: {data['event']['data']['source']['name']}")
                        for doc in data['event']['data']['document']:
                            print(f"  Chunk content snippet: {doc[:150]}")
                    elif "choices" in data:
                        content = data["choices"][0]["delta"].get("content", "")
                        print(content, end="", flush=True)
                except Exception as e:
                    print(f"\nError parsing line: {line} | Error: {e}")
