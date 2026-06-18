with open('/home/eason/proj/open-webui/chip_agent/src/streaming.py', 'r') as f:
    for i, line in enumerate(f, 1):
        if 'summarize' in line:
            print(f"{i}: {line.strip()}")
