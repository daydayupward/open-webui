import os
import re

root_dir = '/home/eason/proj/open-webui/jbprag'
for root, _, files in os.walk(root_dir):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            if 'summarizer' in content:
                print(f"Found 'summarizer' in {path}")
            if 'summarize' in content:
                print(f"Found 'summarize' in {path}")
