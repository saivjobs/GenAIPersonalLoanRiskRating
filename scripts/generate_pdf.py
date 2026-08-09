from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

root = Path(__file__).resolve().parents[1]
md_path = root / "EXECUTIVE_SUMMARY.md"
pdf_path = root / "EXECUTIVE_SUMMARY.pdf"

if not md_path.exists():
    raise SystemExit(f"Missing {md_path}")

text = md_path.read_text(encoding="utf-8")
# Simple markdown to plain text: remove headings and triple dashes
lines = []
for raw in text.splitlines():
    s = raw.strip()
    if s.startswith('#'):
        # make heading uppercase
        s = s.lstrip('#').strip()
        if s:
            s = s.upper()
    if s == '---':
        continue
    lines.append(s)

c = canvas.Canvas(str(pdf_path), pagesize=letter)
width, height = letter
margin = 40
y = height - margin
textobj = c.beginText(margin, y)
textobj.setFont("Helvetica", 11)

# wrap long lines to ~90 chars
import textwrap
for line in lines:
    if not line:
        textobj.textLine("")
        continue
    wrapped = textwrap.wrap(line, width=90)
    for w in wrapped:
        textobj.textLine(w)
    # small spacing after paragraphs
    if not line.endswith(':'):
        textobj.textLine("")

c.drawText(textobj)
c.showPage()
c.save()
print(f"Wrote PDF: {pdf_path}")
