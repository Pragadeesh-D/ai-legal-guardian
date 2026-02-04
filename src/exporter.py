
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

def generate_pdf_report(analysis_result):
    """
    Generates a PDF report from the JSON analysis result.
    Returns: BytesIO object
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = styles["Title"]
    story.append(Paragraph("Contract Risk Assessment Report", title_style))
    story.append(Spacer(1, 12))

    # Summary Section
    story.append(Paragraph("<b>Contract Type:</b> " + analysis_result.get("contract_type", "Unknown"), styles["Normal"]))
    story.append(Paragraph("<b>Overall Risk Score:</b> " + str(analysis_result.get("numeric_risk_score", "N/A")) + "/100 (" + analysis_result.get("overall_risk_score", "N/A") + ")", styles["Normal"]))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("<b>Executive Summary:</b>", styles["Heading2"]))
    story.append(Paragraph(analysis_result.get("summary", "No summary available."), styles["Normal"]))
    story.append(Spacer(1, 12))

    # Key Risks
    story.append(Paragraph("<b>Key Risks Identify:</b>", styles["Heading2"]))
    if "key_risks" in analysis_result and analysis_result["key_risks"]:
        for risk in analysis_result["key_risks"]:
            text = f"• <b>{risk.get('risk', '')}</b> (Severity: {risk.get('severity', '')})"
            story.append(Paragraph(text, styles["Normal"]))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("No major risks identified.", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Clause Analysis Table
    story.append(Paragraph("<b>Detailed Clause Analysis:</b>", styles["Heading2"]))
    
    data = [["Clause Concept", "Risk", "Review"]]
    if "clauses_analysis" in analysis_result:
        for clause in analysis_result["clauses_analysis"]:
            concept = Paragraph(clause.get("title", "Clause"), styles["Normal"])
            risk_level = clause.get("risk_level", "Low")
            explanation = Paragraph(clause.get("explanation", ""), styles["Normal"])
            data.append([concept, risk_level, explanation])

    table = Table(data, colWidths=[100, 60, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer
