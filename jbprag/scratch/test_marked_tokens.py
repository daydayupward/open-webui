import json

# Let's inspect what Markdown.svelte receives and how citationExtension matches [1]
# We can check citationExtension regex directly in python!

import re

def test_citation_regex(text):
    print("=== Testing Input Text ===")
    print(text)
    
    # citationExtension regex in JS:
    # rule = /^(\[(?:\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\])+/
    rule = re.compile(r'^(\[(?:\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\])+')
    
    lines = text.splitlines()
    for line_idx, line in enumerate(lines):
        print(f"\nLine {line_idx+1}: {repr(line)}")
        # Check all substring matches
        for m in re.finditer(r'\[\d+\]', line):
            print(f"   Found citation pattern '{m.group(0)}' at pos {m.start()}")

test_citation_regex("""**参考来源**:
- [1] innovusUG.pdf
- [2] DBcom.pdf

正文回答：CTS 流程说明 [1], [2]。
""")
