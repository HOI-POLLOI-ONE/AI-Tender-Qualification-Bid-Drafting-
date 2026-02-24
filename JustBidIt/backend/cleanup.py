import os
import re

def remove_comments(content):
    """Remove comments from Python code while preserving docstrings."""
    lines = content.split('\n')
    result = []
    in_docstring = False
    docstring_char = None
    
    for line in lines:
        stripped = line.lstrip()
        
        # Check for docstring
        if '"""' in line or "'''" in line:
            in_docstring = not in_docstring
            result.append(line)
        elif in_docstring:
            result.append(line)
        elif stripped.startswith('#'):
            # Skip comment-only lines but preserve structure
            if stripped == '#':
                pass
            else:
                pass
        else:
            # Remove inline comments
            if '#' in line and not in_docstring:
                # Don't remove # if it's inside a string
                in_string = False
                quote_char = None
                new_line = ""
                i = 0
                while i < len(line):
                    char = line[i]
                    if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                        if not in_string:
                            in_string = True
                            quote_char = char
                        elif char == quote_char:
                            in_string = False
                    elif char == '#' and not in_string:
                        # Found a comment, remove it
                        line = line[:i].rstrip()
                        break
                    i += 1
            
            if line.strip() or not line:  # Keep non-empty lines and blank lines
                result.append(line)
    
    # Remove leading/trailing blank lines and consolidate multiple blank lines
    while result and not result[0].strip():
        result.pop(0)
    while result and not result[-1].strip():
        result.pop()
    
    # Replace 3+ consecutive blank lines with 2
    final = []
    blank_count = 0
    for line in result:
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                final.append(line)
        else:
            blank_count = 0
            final.append(line)
    
    return '\n'.join(final)

# Process all Python files
py_files = [
    "main.py",
    "auth.py",
    "database.py",
    "models.py",
    "schemas.py",
    "routers/__init__.py",
    "routers/auth_router.py",
    "routers/company.py",
    "routers/compliance.py",
    "routers/copilot.py",
    "routers/tender.py",
    "services/__init__.py",
    "services/compliance_engine.py",
    "services/gemini_client.py",
    "services/pdf_extractor.py",
]

for py_file in py_files:
    filepath = os.path.join("/Users/Shreya Dubey/OneDrive/Desktop/AI-Tender-Qualification-Bid-Drafting-/AI-Tender-Qualification-Bid-Drafting-/JustBidIt/backend", py_file)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        cleaned = remove_comments(content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        print(f"✓ Cleaned: {py_file}")
    else:
        print(f"✗ Not found: {py_file}")

print("\nPython files cleaned!")
