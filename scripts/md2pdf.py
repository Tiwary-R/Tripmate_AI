"""Convert DOCUMENTATION.md -> DOCUMENTATION.pdf (pure Python, no system deps).

Emoji are stripped because the default PDF fonts have no colour-emoji glyphs (they'd render as boxes).
The text next to each emoji is kept, so meaning is preserved.
"""

import re
import sys

import markdown
from xhtml2pdf import pisa

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Travel_Agent\DOCUMENTATION.md"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"C:\Travel_Agent\DOCUMENTATION.pdf"
FOOTER = sys.argv[3] if len(sys.argv) > 3 else "TripMate AI - Technical Documentation"

# Remove emoji / pictographs / variation selectors (keep normal text, arrows, box-drawing chars).
_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF\uFE0F\u200d]",
    flags=re.UNICODE,
)

# Box-drawing, arrows and math symbols the built-in PDF fonts can't draw -> ASCII equivalents.
_TRANSLIT = {
    "─": "-", "│": "|", "┌": "+", "┐": "+", "└": "+", "┘": "+", "├": "+", "┤": "+",
    "┬": "+", "┴": "+", "┼": "+", "▼": "v", "▲": "^", "►": ">", "◄": "<", "▶": ">", "◀": "<", "➔": ">",
    "→": ">", "←": "<", "↔": "<>", "⇄": "<>", "≤": "<=", "≥": ">=", "·": "-", "•": "-",
    "₹": "Rs ", "—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
}

with open(SRC, encoding="utf-8") as f:
    text = f.read()
text = _EMOJI.sub("", text)
text = text.translate(str.maketrans(_TRANSLIT))

html_body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"])

CSS = """
@page { size: A4; margin: 1.8cm 1.6cm; @frame footer { -pdf-frame-content: footerContent;
        bottom: 0.8cm; margin-left: 1.6cm; margin-right: 1.6cm; height: 1cm; } }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt; color: #1c2333; line-height: 1.45; }
h1 { font-size: 20pt; color: #4b3fd1; border-bottom: 2px solid #4b3fd1; padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 14pt; color: #1d4ed8; border-bottom: 1px solid #cfd5e2; padding-bottom: 3px; margin-top: 18px; }
h3 { font-size: 11.5pt; color: #1f7a4d; margin-top: 14px; }
p, li { font-size: 9.5pt; }
code { font-family: Courier, monospace; font-size: 8.5pt; background: #f1f3f9; color: #b5176b; }
pre { background: #f6f8fc; border: 1px solid #e3e7ef; padding: 8px; font-family: Courier, monospace;
      font-size: 7.6pt; color: #1c2333; -pdf-keep-with-next: false; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th { background: #4b3fd1; color: #ffffff; font-size: 8.5pt; padding: 5px 6px; text-align: left; }
td { border: 1px solid #dde2ec; font-size: 8.5pt; padding: 4px 6px; vertical-align: top; }
tr:nth-child(even) td { background: #f7f8fc; }
a { color: #1d4ed8; text-decoration: none; }
hr { border: 0; border-top: 1px solid #dde2ec; margin: 14px 0; }
"""

HTML = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div id="footerContent" style="font-size:7.5pt;color:#6b7385;text-align:center;">
  {FOOTER} &nbsp;-&nbsp; page <pdf:pagenumber> of <pdf:pagecount>
</div>
{html_body}
</body></html>"""

with open(OUT, "wb") as out:
    result = pisa.CreatePDF(HTML, dest=out, encoding="utf-8")

if result.err:
    print("ERROR: PDF generation reported errors", file=sys.stderr)
    sys.exit(1)
print("PDF written:", OUT)
