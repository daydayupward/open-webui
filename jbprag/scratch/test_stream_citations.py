import urllib.request
import json
import sys

url = "http://127.0.0.1:8000/v1/chat/completions"
data = {
    "messages": [{"role": "user", "content": "Explain the timing derating guidelines for late paths according to the nanometer designs book."}],
    "model": "chip-agentic-rag",
    "stream": True
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    print(f"Sending streaming request to {url}...")
    with urllib.request.urlopen(req, timeout=30) as response:
        print(f"Status Code: {response.status}")
        for line in response:
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
            print(line_str)
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code} - {e.reason}", file=sys.stderr)
    try:
        err_body = e.read().decode("utf-8")
        print("Error Body:", file=sys.stderr)
        print(err_body, file=sys.stderr)
    except Exception:
        pass
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
