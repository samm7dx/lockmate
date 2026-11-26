"""Combine all study guide .md files into a single PDF using markdown -> HTML -> Playwright print-to-pdf with Mermaid rendering."""
import asyncio
import glob
import re
from pathlib import Path

from playwright.async_api import async_playwright

GUIDE_DIR = Path(__file__).resolve().parent / "hackathon-study-guide"
HTML_OUTPUT = Path(__file__).resolve().parent / "hackathon-study-guide.html"
PDF_OUTPUT = Path(__file__).resolve().parent / "hackathon-study-guide.pdf"
MERMAID_JS = Path(__file__).resolve().parent / "mermaid.min.js"

# Regex to match fenced code blocks with mermaid language
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)


def convert_md_to_html(md_text: str) -> str:
    """Convert markdown to HTML, preserving mermaid blocks as renderable divs."""
    import markdown

    # 1. Extract mermaid blocks and replace with placeholders
    placeholders = []
    def stash_mermaid(match):
        placeholders.append(match.group(1))
        return f"\n\n<!-- MERMAID_PLACEHOLDER_{len(placeholders)-1} -->\n\n"

    without_mermaid = MERMAID_BLOCK_RE.sub(stash_mermaid, md_text)

    # 2. Convert the rest to HTML (without codehilite so mermaid isn't mangled)
    html = markdown.markdown(
        without_mermaid,
        extensions=["tables", "fenced_code", "toc", "attr_list"],
        extension_configs={
            "toc": {"permalink": False},
        },
    )

    # 3. Reinsert mermaid blocks as renderable divs
    def restore_mermaid(match):
        idx = int(match.group(1))
        diagram = placeholders[idx]
        # Escape HTML special chars in the diagram
        from html import escape
        return f'<div class="mermaid">{escape(diagram)}</div>'

    html = re.sub(
        r"<!-- MERMAID_PLACEHOLDER_(\d+) -->",
        restore_mermaid,
        html,
    )

    return html


# 1. Collect .md files in numeric order
md_files = sorted(glob.glob(str(GUIDE_DIR / "*.md")))

# 2. Convert markdown to HTML per file
sections = []
for md_path in md_files:
    text = Path(md_path).read_text(encoding="utf-8")
    sections.append(convert_md_to_html(text))

# 3. Build full HTML document with Mermaid JS
title = "LOCKMATE Hackathon Study Guide"
body = "\n".join(sections)

# Read mermaid.min.js content to inline it
mermaid_js_content = MERMAID_JS.read_text(encoding="utf-8")

html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
    size: A4;
    margin: 1.6cm 1.5cm 1.6cm 1.5cm;
}}
body {{
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.5;
    color: #1a1a1a;
}}
h1 {{
    font-size: 18pt;
    color: #0b4f8a;
    border-bottom: 2px solid #0b4f8a;
    padding-bottom: 4px;
    margin-top: 0;
    page-break-before: always;
    break-before: page;
}}
h1:first-of-type {{
    page-break-before: avoid;
    break-before: auto;
}}
h2 {{ font-size: 14pt; color: #0b4f8a; margin-top: 18px; border-bottom: 1px solid #cfe3f5; padding-bottom: 2px; }}
h3 {{ font-size: 12pt; color: #333; margin-top: 14px; }}
h4 {{ font-size: 10.5pt; color: #555; margin-top: 10px; }}
p {{ margin: 6px 0; }}
code {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8.5pt;
    background: #f4f6f8;
    padding: 1px 3px;
    border-radius: 2px;
}}
pre {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8pt;
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-left: 3px solid #0b4f8a;
    padding: 8px 10px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    page-break-inside: avoid;
    line-height: 1.3;
}}
pre code {{ background: none; padding: 0; }}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    font-size: 8.5pt;
    page-break-inside: auto;
}}
th, td {{
    border: 1px solid #c9d4e0;
    padding: 4px 6px;
    text-align: left;
    vertical-align: top;
}}
th {{ background: #eaf2fb; color: #0b4f8a; font-weight: bold; }}
tr:nth-child(even) td {{ background: #fafbfc; }}
blockquote {{
    border-left: 3px solid #0b4f8a;
    background: #f0f6fc;
    margin: 8px 0;
    padding: 4px 10px;
    color: #444;
}}
ul, ol {{ margin: 6px 0; padding-left: 22px; }}
li {{ margin: 2px 0; }}
hr {{ border: none; border-top: 1px solid #ddd; margin: 14px 0; }}
.mermaid {{
    text-align: center;
    margin: 12px 0;
    page-break-inside: avoid;
}}
.mermaid svg {{
    max-width: 100%;
    height: auto;
}}
</style>
</head>
<body>
{body}
<script>
{mermaid_js_content}
</script>
<script>
mermaid.initialize({{ 
    startOnLoad: false,
    theme: 'default',
    flowchart: {{ useMaxWidth: true, htmlLabels: true }},
    sequence: {{ useMaxWidth: true }},
    securityLevel: 'loose'
}});
</script>
</body>
</html>"""

HTML_OUTPUT.write_text(html_doc, encoding="utf-8")


async def render_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable console logging for debugging
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
        
        # Navigate to the HTML file
        await page.goto(HTML_OUTPUT.resolve().as_uri(), wait_until="networkidle")
        
        # Explicitly run mermaid
        result = await page.evaluate("""() => {
            return mermaid.run({ querySelector: '.mermaid' }).then(() => 'ok').catch(e => 'error: ' + e.message);
        }""")
        print(f"Mermaid run result: {result}")
        
        # Wait for mermaid to render
        try:
            await page.wait_for_function(
                """() => {
                    const mermaids = document.querySelectorAll('.mermaid');
                    return mermaids.length > 0 && Array.from(mermaids).every(m => m.querySelector('svg') !== null);
                }""",
                timeout=30000,
            )
            total = await page.evaluate('document.querySelectorAll(".mermaid").length')
            print(f"All {total} mermaid diagrams rendered")
        except Exception as e:
            print(f"Wait for mermaid timeout: {e}")
            count = await page.evaluate("""() => {
                const mermaids = document.querySelectorAll('.mermaid');
                return Array.from(mermaids).filter(m => m.querySelector('svg') !== null).length;
            }""")
            total = await page.evaluate('document.querySelectorAll(".mermaid").length')
            print(f"Rendered {count} out of {total} diagrams")
        
        # Small extra wait for layout to settle
        await page.wait_for_timeout(1000)
        
        # Generate PDF
        await page.pdf(
            path=str(PDF_OUTPUT),
            format="A4",
            margin={"top": "1.6cm", "right": "1.5cm", "bottom": "1.6cm", "left": "1.5cm"},
            print_background=True,
            prefer_css_page_size=True,
        )
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(render_pdf())
    size = PDF_OUTPUT.stat().st_size
    print(f"Created: {PDF_OUTPUT}")
    print(f"Files merged: {len(md_files)}")
    print(f"Size: {size / 1024:.1f} KB")