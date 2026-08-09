from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import textwrap

root = Path(__file__).resolve().parents[1]
files = [
    "README.md",
    "PRESENTATION_GUIDE.md",
    "TECHNICAL_DEEP_DIVE.md",
    "EXECUTIVE_SUMMARY.md",
]
arch = root / "ARCHITECTURE.mmd"
out = root / "COMBINED_DOCUMENT.pdf"

# Collect text
sections = []
for fname in files:
    p = root / fname
    if p.exists():
        title = p.name
        content = p.read_text(encoding='utf-8')
        sections.append((title, content))
    else:
        sections.append((fname, f"(Missing {fname})\n"))

if arch.exists():
    arch_text = arch.read_text(encoding='utf-8')
else:
    arch_text = "(Architecture file not found)"

c = canvas.Canvas(str(out), pagesize=letter)
width, height = letter
margin = 48
usable_width = width - 2 * margin

def draw_section(title, text, start_y):
    y = start_y
    textobj = c.beginText(margin, y)
    textobj.setFont("Helvetica-Bold", 14)
    textobj.textLine(title)
    textobj.textLine("")
    textobj.setFont("Helvetica", 10)
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith('#'):
            heading = line.lstrip('#').strip().upper()
            textobj.textLine(heading)
            textobj.textLine("")
            continue
        if not line:
            textobj.textLine("")
            continue
        wrapped = textwrap.wrap(line, width=100)
        for w in wrapped:
            textobj.textLine(w)
    c.drawText(textobj)
    return

# We'll add each section to a new page for readability
for title, content in sections:
    c.showPage()
    draw_section(title, content, height - margin)

# Add architecture as its own page with a heading and code block
c.showPage()
textobj = c.beginText(margin, height - margin)
textobj.setFont("Helvetica-Bold", 14)
textobj.textLine("ARCHITECTURE (Mermaid source)")
textobj.textLine("")
textobj.setFont("Courier", 8)
for line in arch_text.splitlines():
    textobj.textLine(line)
c.drawText(textobj)

# Addition: list of generated artifacts
c.showPage()
textobj = c.beginText(margin, height - margin)
textobj.setFont("Helvetica-Bold", 14)
textobj.textLine("ADDITIONAL ARTIFACTS GENERATED IN REPO")
textobj.textLine("")
textobj.setFont("Helvetica", 10)
for f in ["EXECUTIVE_SUMMARY.pdf", "ARCHITECTURE_SLIDE.pptx", "ARCHITECTURE.mmd"]:
    textobj.textLine(f"- {f}")
c.drawText(textobj)

# Embed architecture image if present on its own page
img_path = root / 'ARCHITECTURE.png'
if img_path.exists():
    c.showPage()
    # Fit image to page with margins
    max_w = usable_width
    max_h = height - 2 * margin
    from PIL import Image
    im = Image.open(img_path)
    iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w = iw * scale
    h = ih * scale
    x = margin + (usable_width - w) / 2
    y = margin + (max_h - h) / 2
    c.drawImage(str(img_path), x, y, width=w, height=h, preserveAspectRatio=True)

c.showPage()
c.save()
print(f"Wrote combined PDF: {out}")
