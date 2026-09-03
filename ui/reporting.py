from __future__ import annotations

from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

INK = colors.HexColor("#0B0F12")
MUTED = colors.HexColor("#5E6870")
ACCENT = colors.HexColor("#FF704D")
GREEN = colors.HexColor("#8BCB2E")
PANEL = colors.HexColor("#F4F1EA")


def _safe(text) -> str:
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_decision_report(*, source_name: str, question: str, profile, intel, best_method: dict | None, orchestration_text: str | None = None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=.58*inch, leftMargin=.58*inch, topMargin=.58*inch, bottomMargin=.58*inch, title="CampaignLab Decision Report")
    styles = getSampleStyleSheet()
    title = ParagraphStyle("clTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=INK, alignment=TA_LEFT, spaceAfter=8)
    h = ParagraphStyle("clH", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=8, spaceAfter=6)
    body = ParagraphStyle("clBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK)
    muted = ParagraphStyle("clMuted", parent=body, textColor=MUTED, fontSize=8.5)
    call = ParagraphStyle("clCall", parent=body, fontName="Helvetica-Bold", fontSize=11.5, leading=16, textColor=INK)
    story=[]
    story.append(Paragraph("CAMPAIGNLAB", ParagraphStyle("brand", parent=body, fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=GREEN, spaceAfter=3)))
    story.append(Paragraph("Decision Report", title))
    story.append(Paragraph("Where ideas face reality.", ParagraphStyle("tag", parent=body, fontName="Helvetica-Bold", fontSize=10.5, textColor=MUTED)))
    story.append(Spacer(1, 10))
    story.append(Table([["SOURCE", _safe(source_name)], ["GENERATED", datetime.now().strftime("%b %d, %Y %I:%M %p")]], colWidths=[1.0*inch, 5.7*inch], style=[("BACKGROUND",(0,0),(-1,-1),PANEL),("TEXTCOLOR",(0,0),(0,-1),MUTED),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(1,0),(1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8.5),("BOTTOMPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),6)]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("The decision", h))
    story.append(Paragraph(_safe(question or "No explicit business question was supplied. CampaignLab scanned for the strongest defensible analytical opportunities in the dataset."), call))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Evidence snapshot", h))
    data=[
        [Paragraph("<b>Rows</b>", muted), Paragraph(f"{profile.rows:,}", body), Paragraph("<b>Columns</b>", muted), Paragraph(f"{profile.columns:,}", body)],
        [Paragraph("<b>Missing</b>", muted), Paragraph(f"{profile.missing_rate:.1%}", body), Paragraph("<b>Duplicates</b>", muted), Paragraph(f"{profile.duplicate_rate:.1%}", body)],
        [Paragraph("<b>Likely grain</b>", muted), Paragraph(_safe(intel.grain_guess), body), Paragraph("<b>Question status</b>", muted), Paragraph(_safe(intel.question_assessment.get("status", "unknown").replace("_", " ").title()), body)]
    ]
    t=Table(data, colWidths=[.85*inch,2.15*inch,1.05*inch,2.65*inch])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PANEL),("BOX",(0,0),(-1,-1),.4,colors.HexColor("#D9D5CE")),("INNERGRID",(0,0),(-1,-1),.3,colors.HexColor("#E0DDD6")),("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.5),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story.append(t)
    if best_method:
        story.append(Spacer(1, 12)); story.append(Paragraph("Recommended analytical path", h))
        story.append(Paragraph(f"<b>{_safe(best_method.get('name'))}</b> - {_safe(best_method.get('answers'))}", body))
        story.append(Paragraph(f"Fit score: {_safe(best_method.get('score'))}/100 | Status: {_safe(best_method.get('implementation_status'))}", muted))
        for reason in (best_method.get("reasons") or [])[:2]: story.append(Paragraph(f"• {_safe(reason)}", body))
    warnings=[x for x in intel.quality_findings if x.get("level")=="warning"]
    if warnings:
        story.append(Spacer(1, 10)); story.append(Paragraph("What to watch", h))
        for w in warnings[:6]: story.append(Paragraph(f"• {_safe(w.get('finding'))}", body))
    if orchestration_text:
        story.append(PageBreak()); story.append(Paragraph("CampaignLab analysis", h)); story.append(Paragraph(_safe(orchestration_text).replace("\n", "<br/>"), body))
    doc.build(story)
    return buf.getvalue()
