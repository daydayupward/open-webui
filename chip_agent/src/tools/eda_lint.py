import re
from typing import Dict, List, Any

def lint_eda_script(script: str) -> Dict[str, Any]:
    """
    Validates EDA scripts (Tcl/Skill) for syntax safety and structure.
    Checks:
    - Bracket pairing: '{}' and '[]' mismatch.
    - Restricted commands list: prevents malicious system executions or unwanted exits.
    """
    issues = []
    suggestions = []
    
    # 1. Bracket pairing validation using a simple stack
    stack = []
    brackets = {
        '}': '{',
        ']': '['
    }
    
    for i, char in enumerate(script):
        if char in brackets.values():
            stack.append((char, i))
        elif char in brackets.keys():
            expected = brackets[char]
            if not stack:
                issues.append(f"Mismatched closing bracket '{char}' at index {i}.")
            else:
                top_char, top_idx = stack.pop()
                if top_char != expected:
                    issues.append(f"Mismatched bracket type: expected '{brackets[top_char]}', found '{char}' at index {i}.")
                    
    # Remaining open brackets in stack
    while stack:
        char, idx = stack.pop()
        issues.append(f"Unclosed opening bracket '{char}' at index {idx}.")
        
    # 2. Restricted commands check
    # We want to check for Tcl/Skill dangerous/restricted commands.
    # Standard restricted commands for safety and sandbox:
    restricted_cmds = ["exec", "system", "sh", "bash", "exit", "rm", "mv", "socket"]
    
    # Simple regex word boundary check
    for cmd in restricted_cmds:
        # e.g. matching 'exec' or 'system' as a command word (usually at the start of a line or after a semicolon/bracket)
        pattern = r"\b" + re.escape(cmd) + r"\b"
        if re.search(pattern, script):
            issues.append(f"Restricted command usage detected: '{cmd}'.")
            suggestions.append(f"Avoid using system-level restricted command '{cmd}' in EDA tool scripts.")
            
    passed = len(issues) == 0
    
    return {
        "passed": passed,
        "issues": issues,
        "suggestions": suggestions
    }
