"""
Fix unicode chars and ln= deprecation in generate_project_pdf.py
"""
with open('tools/generate_project_pdf.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace unicode chars with ASCII
content = content.replace('\u2014', '--')
content = content.replace('\u2013', '-')
content = content.replace('\u2019', "'")
content = content.replace('\u2018', "'")
content = content.replace('\u201c', '"')
content = content.replace('\u201d', '"')
content = content.replace('\u2022', '-')
content = content.replace('\u2605', '*')
content = content.replace('\u2139', 'i')
content = content.replace('\u26a0', '!')
content = content.replace('\u2b50', '*')
content = content.replace('\u2714', 'OK')
content = content.replace('\u2718', 'X')

# Replace ln=True / ln=False (fpdf2 v2.5+ deprecation)
content = content.replace(', ln=True)', ', new_x="LMARGIN", new_y="NEXT")')
content = content.replace(', ln=False)', ')')
content = content.replace(', ln=True,', ', new_x="LMARGIN", new_y="NEXT",')

with open('tools/generate_project_pdf_v2.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed and saved as generate_project_pdf_v2.py')

