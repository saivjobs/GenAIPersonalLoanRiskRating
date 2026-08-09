from pathlib import Path
from pptx import Presentation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch

root = Path(__file__).resolve().parents[1]
prs_path = root / 'ARCHITECTURE_SLIDE_OPTIMIZED.pptx'
pdf_out = root / 'ARCHITECTURE_PRESENTATION.pdf'

if not prs_path.exists():
    raise SystemExit('Optimized PPTX not found; run create_optimized_pptx.py first')

prs = Presentation(str(prs_path))
width, height = letter
margin = 48
c = canvas.Canvas(str(pdf_out), pagesize=letter)

for slide in prs.slides:
    # Title: assume first textbox is title
    title = ''
    bullets = []
    img_path = root / 'ARCHITECTURE.png'
    notes = ''
    # Extract shapes text
    for shape in slide.shapes:
        if shape.has_text_frame:
            text = '\n'.join([p.text for p in shape.text_frame.paragraphs if p.text])
            # Heuristic: title is the largest font or first text box
            if not title:
                title = text
            else:
                bullets.append(text)
    # Notes
    if slide.has_notes_slide:
        notes = slide.notes_slide.notes_text_frame.text
    # Draw page
    c.setFont('Helvetica-Bold', 20)
    c.drawString(margin, height - margin - 10, title)
    # Bullets left
    c.setFont('Helvetica', 12)
    y = height - margin - 50
    for b in bullets:
        for line in b.splitlines():
            c.drawString(margin, y, u'• ' + line)
            y -= 16
        y -= 6
    # Image right
    if img_path.exists():
        img = ImageReader(str(img_path))
        # Fit image to right half
        max_w = width/2 - margin
        max_h = height - 2*margin
        iw, ih = img.getSize()
        scale = min(max_w/iw, max_h/ih)
        w = iw*scale
        h = ih*scale
        x = width - margin - w
        y_img = height - margin - h
        c.drawImage(img, x, y_img, width=w, height=h)
    c.showPage()
    # Speaker notes page
    c.setFont('Helvetica-Bold', 16)
    c.drawString(margin, height - margin - 10, 'Speaker Notes')
    c.setFont('Helvetica', 11)
    y = height - margin - 40
    for line in notes.splitlines():
        c.drawString(margin, y, line)
        y -= 14
    c.showPage()

c.save()
print(f'Wrote presentation PDF: {pdf_out}')
