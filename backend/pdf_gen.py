from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_report(query_id: str, query_text: str, candidates: list):
    os.makedirs("./reports", exist_ok=True)
    pdf_path = f"./reports/{query_id}.pdf"

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1F2121"),
        spaceAfter=30,
    )

    story.append(
        Paragraph("PharmaRep Master — Drug Repurposing Report", title_style)
    )
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph(f"<b>Query:</b> {query_text}", styles["Normal"]))
    story.append(
        Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    if not candidates:
        story.append(Paragraph("No candidates found.", styles["Normal"]))
    else:
        story.append(
            Paragraph(
                f"<b>Top {len(candidates)} Candidates</b>", styles["Heading2"]
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        for i, c in enumerate(candidates[:10], 1):
            story.append(
                Paragraph(
                    f"{i}. {c.get('drug', 'Unknown')}", styles["Heading3"]
                )
            )
            story.append(
                Paragraph(
                    f"<b>Score:</b> {c.get('final_score', 0.0):.3f}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Mechanism:</b> {c.get('mechanism', 'N/A')}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Diseases:</b> {', '.join(c.get('diseases', []))}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"<b>Sources:</b> {c.get('sources_count', 0)}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    logger.info(f"PDF report saved to {pdf_path}")
