"""
Fix ALL unicode chars in generate_project_pdf.py - complete scrub
"""
import re

with open('tools/generate_project_pdf.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace ALL non-latin-1 characters
# First targeted replacements
replacements = {
    '\u2014': '--',    # em-dash
    '\u2013': '-',     # en-dash
    '\u2019': "'",     # right single quote
    '\u2018': "'",     # left single quote
    '\u201c': '"',     # left double quote
    '\u201d': '"',     # right double quote
    '\u2022': '-',     # bullet
    '\u2605': '*',     # star
    '\u2606': '*',     # star outline
    '\u2139': 'i',     # info
    '\u26a0': '!',     # warning
    '\u2b50': '*',     # star
    '\u2714': 'OK',    # checkmark
    '\u2718': 'X',     # cross
    '\u2192': '->',    # right arrow
    '\u2190': '<-',    # left arrow
    '\u2193': 'v',     # down arrow
    '\u2191': '^',     # up arrow
    '\u2713': 'OK',    # checkmark
    '\u2717': 'X',     # cross
    '\u00b7': '.',     # middle dot
    '\u00bb': '>>',    # right double angle
    '\u00ab': '<<',    # left double angle
}

for old, new in replacements.items():
    content = content.replace(old, new)

# Final safety: replace any remaining non-latin-1 with '?'
def safe_latin1(text):
    result = []
    for char in text:
        try:
            char.encode('latin-1')
            result.append(char)
        except UnicodeEncodeError:
            result.append('?')
    return ''.join(result)

# Apply to string content between quotes in pdf calls only
# Actually, do a full scrub of the output text (not Python syntax)
# We need to be careful not to break Python string literals
# Strategy: just replace all non-latin1 in the whole file
content = safe_latin1(content)

# Fix ln= deprecation
content = content.replace(', ln=True)', ', new_x="LMARGIN", new_y="NEXT")')
content = content.replace(', ln=False)', ')')
content = content.replace(', ln=True,', ', new_x="LMARGIN", new_y="NEXT",')

with open('tools/generate_project_pdf_v3.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - saved as generate_project_pdf_v3.py')

