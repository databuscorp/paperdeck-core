"""
PDF Composer using ReportLab.
Converts rendered SVG/PNG diagrams into embeddable PDF pages.
Supports full question paper layout with sections and question numbering.
"""
from __future__ import annotations

import io
import os
import tempfile
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable

# Optional: cairosvg for SVG → PNG conversion (better quality)
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


def svg_to_png_bytes(svg_content: str, width: int = 600, height: int = 400) -> bytes:
    """Convert SVG string to PNG bytes for embedding in PDF."""
    if CAIROSVG_AVAILABLE:
        return cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            output_width=width,
            output_height=height,
        )
    # Fallback: save SVG to temp file and use PIL to create a blank placeholder
    png_buf = io.BytesIO()
    if PIL_AVAILABLE:
        img = PILImage.new("RGB", (width, height), color=(255, 255, 255))
        img.save(png_buf, format="PNG")
    else:
        # Minimal 1x1 PNG header
        import base64
        png_buf.write(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        ))
    png_buf.seek(0)
    return png_buf.read()


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="PaperTitle",
        fontSize=18, leading=22, alignment=1, spaceAfter=8,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontSize=14, leading=18, alignment=0, spaceAfter=4,
        fontName="Helvetica-Bold",
        borderPad=4,
    ))
    styles.add(ParagraphStyle(
        name="QuestionText",
        fontSize=11, leading=15, alignment=0, spaceAfter=3,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        name="OptionText",
        fontSize=10, leading=14, leftIndent=20, spaceAfter=1,
        fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        name="MetaInfo",
        fontSize=9, leading=12, alignment=0,
        fontName="Helvetica-Oblique",
        textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        name="InstructionText",
        fontSize=10, leading=14, alignment=0, spaceAfter=2,
        fontName="Helvetica",
        textColor=colors.HexColor("#333333"),
    ))
    return styles


def _header_footer(canvas, doc, title: str = "", exam_name: str = ""):
    """Draw header and footer on each page."""
    canvas.saveState()
    # Header line
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - MARGIN + 8, PAGE_W - MARGIN, PAGE_H - MARGIN + 8)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, PAGE_H - MARGIN + 12, title or "Question Paper")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 12,
                           exam_name or "PaperDeck")
    # Footer
    canvas.line(MARGIN, MARGIN - 8, PAGE_W - MARGIN, MARGIN - 8)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(PAGE_W / 2, MARGIN - 18, f"Page {doc.page}")
    canvas.restoreState()


def generate_paper_pdf(paper_data: Dict[str, Any]) -> bytes:
    """
    Generate a complete PDF question paper.

    paper_data format:
    {
        "title": "JEE Mains Mock Test",
        "exam_name": "JEE Mains",
        "duration_minutes": 180,
        "total_marks": 360,
        "instructions": ["Instructions text..."],
        "sections": [
            {
                "name": "Section A - Physics",
                "questions": [
                    {
                        "number": 1,
                        "text": "Question text",
                        "options": [{"text": "...", "correct": False}, ...],
                        "marks": 4,
                        "negative_marks": -1,
                        "diagram_svg": "<svg>...</svg>",   # optional
                    }
                ]
            }
        ]
    }
    """
    buf = io.BytesIO()
    styles = _build_styles()
    title = paper_data.get("title", "Question Paper")
    exam_name = paper_data.get("exam_name", "")

    def on_page(canvas, doc):
        _header_footer(canvas, doc, title, exam_name)

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 0.5 * cm, bottomMargin=MARGIN + 0.5 * cm,
    )
    frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN,
                  id="normal")
    template = PageTemplate(id="main", frames=[frame], onPage=on_page)
    doc.addPageTemplates([template])

    story = []

    # Title block
    story.append(Paragraph(title, styles["PaperTitle"]))
    story.append(Spacer(1, 4 * mm))

    # Meta info row
    duration = paper_data.get("duration_minutes", 0)
    total_marks = paper_data.get("total_marks", 0)
    meta_data = [
        ["Duration:", f"{duration} minutes", "Total Marks:", str(total_marks)],
    ]
    meta_table = Table(meta_data, colWidths=[3 * cm, 5 * cm, 4 * cm, 3 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 3 * mm))

    # Instructions
    instructions = paper_data.get("instructions", [])
    if instructions:
        story.append(Paragraph("<b>General Instructions:</b>", styles["QuestionText"]))
        for instr in instructions:
            story.append(Paragraph(f"• {instr}", styles["InstructionText"]))
        story.append(Spacer(1, 3 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Spacer(1, 4 * mm))

    # Sections and Questions
    for section in paper_data.get("sections", []):
        sec_name = section.get("name", "Section")
        story.append(Paragraph(sec_name, styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Spacer(1, 3 * mm))

        for q in section.get("questions", []):
            q_elements = _build_question_flowables(q, styles)
            story.append(KeepTogether(q_elements))
            story.append(Spacer(1, 4 * mm))

        story.append(Spacer(1, 6 * mm))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def _build_question_flowables(q: Dict[str, Any], styles) -> List:
    """Build ReportLab flowables for a single question."""
    elements = []
    number = q.get("number", "")
    text = q.get("text", "")
    marks = q.get("marks", 4)
    neg = q.get("negative_marks", -1)
    options = q.get("options") or []
    diagram_svg = q.get("diagram_svg") or q.get("image_svg")

    # Question number + text
    q_header = f"<b>Q{number}.</b>&nbsp;&nbsp;{text}"
    marks_info = f"[{marks} marks, {neg}]"
    elements.append(Paragraph(q_header, styles["QuestionText"]))
    elements.append(Paragraph(marks_info, styles["MetaInfo"]))

    # Diagram (if any)
    if diagram_svg:
        try:
            png_bytes = svg_to_png_bytes(diagram_svg, width=400, height=260)
            img_buf = io.BytesIO(png_bytes)
            img = Image(img_buf, width=10 * cm, height=6.5 * cm)
            img.hAlign = "LEFT"
            elements.append(Spacer(1, 2 * mm))
            elements.append(img)
            elements.append(Spacer(1, 2 * mm))
        except Exception:
            pass   # skip diagram if conversion fails

    # Options
    if options:
        opt_labels = ["(A)", "(B)", "(C)", "(D)"]
        for i, opt in enumerate(options[:4]):
            opt_text = opt.get("text", "") if isinstance(opt, dict) else str(opt)
            label = opt_labels[i] if i < len(opt_labels) else f"({i + 1})"
            elements.append(Paragraph(f"{label}&nbsp;&nbsp;{opt_text}", styles["OptionText"]))

    return elements


def generate_diagram_pdf(rendered_diagram_data: Dict[str, Any]) -> bytes:
    """
    Generate a single-diagram PDF for preview / download.
    rendered_diagram_data: {"svg_content": "...", "title": "...", "description": "..."}
    """
    buf = io.BytesIO()
    styles = _build_styles()
    title = rendered_diagram_data.get("title", "Diagram")
    svg_content = rendered_diagram_data.get("svg_content", "")
    description = rendered_diagram_data.get("description", "")

    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN)
    frame = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN)
    template = PageTemplate(id="main", frames=[frame])
    doc.addPageTemplates([template])

    story = [
        Paragraph(title, styles["PaperTitle"]),
        Spacer(1, 8 * mm),
    ]
    if svg_content:
        try:
            png_bytes = svg_to_png_bytes(svg_content, width=600, height=420)
            img = Image(io.BytesIO(png_bytes), width=15 * cm, height=10.5 * cm)
            img.hAlign = "CENTER"
            story.append(img)
        except Exception as e:
            story.append(Paragraph(f"[Diagram rendering error: {e}]", styles["QuestionText"]))
    if description:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(description, styles["InstructionText"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()
