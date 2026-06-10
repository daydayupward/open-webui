import re

BLOCKED_COMMANDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "REPLACE", "TRUNCATE", "GRANT", "REVOKE", "INTO", "MERGE", "COPY"
}

ALLOWLIST_TABLES = {"project_metrics"}

def clean_sql_for_validation(sql: str) -> str:
    """
    Remove comments and single-quoted string literals to prevent SQL injection bypasses
    where blocked keywords or semicolons are hidden inside comments or strings.
    """
    in_single_comment = False
    in_multi_comment = False
    in_string = False
    string_char = None
    
    cleaned = []
    i = 0
    n = len(sql)
    
    while i < n:
        char = sql[i]
        
        if in_single_comment:
            if char == '\n':
                in_single_comment = False
                cleaned.append(char)
            i += 1
            continue
            
          # Handle multi-line comment
        if in_multi_comment:
            if char == '*' and i + 1 < n and sql[i+1] == '/':
                in_multi_comment = False
                i += 2
            else:
                i += 1
            continue
            
        if in_string:
            if char == string_char:
                if i + 1 < n and sql[i+1] == string_char:
                    i += 2
                else:
                    in_string = False
                    cleaned.append("'STRING'")
                    i += 1
            else:
                i += 1
            continue
            
        if char == '-' and i + 1 < n and sql[i+1] == '-':
            in_single_comment = True
            i += 2
            continue
            
        if char == '/' and i + 1 < n and sql[i+1] == '*':
            in_multi_comment = True
            i += 2
            continue
            
        if char == "'":
            in_string = True
            string_char = char
            i += 1
            continue
            
        cleaned.append(char)
        i += 1
        
    return "".join(cleaned)

def validate_sql_query(query: str) -> bool:
    if not query:
        return False
        
    # Clean query by removing comments and replacing string literals
    cleaned = clean_sql_for_validation(query)
    cleaned_stripped = cleaned.strip()
    
    # 1. Check starts with SELECT (case-insensitive)
    if not cleaned_stripped.upper().startswith("SELECT"):
        return False
        
    # 2. Check for multiple statements (semicolon check)
    # Semicolon is only allowed at the very end of the query (if at all)
    semicolon_idx = cleaned_stripped.find(';')
    if semicolon_idx != -1 and semicolon_idx < len(cleaned_stripped) - 1:
        return False
        
    # 3. Blocklist check for SQL operations
    tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', cleaned_stripped)
    for token in tokens:
        if token.upper() in BLOCKED_COMMANDS:
            return False
            
    # 4. Allowlist of tables check
    # Find all FROM/JOIN clauses and validate table names
    matches = list(re.finditer(r'\b(FROM|JOIN)\b', cleaned_stripped, re.IGNORECASE))
    for match in matches:
        start_idx = match.end()
        rest = cleaned_stripped[start_idx:]
        
        # Find end of the FROM/JOIN table list clause
        end_match = re.search(r'\b(WHERE|GROUP|ORDER|LIMIT|JOIN|UNION|FROM|WINDOW)\b|[);]', rest, re.IGNORECASE)
        clause = rest[:end_match.start()] if end_match else rest
        
        # Parse comma-separated list of table references/subqueries
        parts = clause.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.startswith('('):
                continue
                
            table_match = re.match(r'^([a-zA-Z0-9_\.\'"`]+)', part)
            if not table_match:
                return False
                
            table_name = table_match.group(1).strip('"`\'')
            base_table = table_name.split('.')[-1].lower()
            if base_table not in ALLOWLIST_TABLES:
                return False
                
    return True
