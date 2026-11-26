import markdown
import re
from pathlib import Path

text = Path('docs/hackathon-study-guide/01-project-overview-architecture.md').read_text(encoding='utf-8')
html = markdown.markdown(text, extensions=['tables', 'fenced_code', 'toc', 'codehilite', 'attr_list'])

# Find all pre/code blocks
for m in re.finditer(r'<pre[^>]*>.*?</pre>', html, re.DOTALL):
    block = m.group(0)
    if 'mermaid' in block or 'flowchart' in block or 'graph' in block:
        print('Block with diagram:', block[:300])
        print('---')

# Also just search for mermaid mentions
idx = html.find('flowchart')
if idx >= 0:
    print('HTML around flowchart:', html[max(0,idx-100):idx+200])
else:
    print('flowchart not in html')

# Check code classes
for m in re.finditer(r'<code[^>]*class="([^"]*)"', html):
    print('Code class:', m.group(1))