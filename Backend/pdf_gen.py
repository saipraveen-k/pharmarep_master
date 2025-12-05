import logging
from typing import Dict, List
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

logger = logging.getLogger(__name__)

def generate_pdf_report(result: Dict, output_path: str):
    try:
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story: List = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=colors.HexColor("#1a6c80"),
            alignment=1,
            spaceAfter=18,
        )

        header_style = ParagraphStyle(
            "Header",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#2b7a8f"),
            spaceAfter=8,
        )

        normal = styles["Normal"]

        query = result.get("query", "")
        candidates = result.get("candidates", [])

        story.append(Paragraph("PharmaRep Master", title_style))
        story.append(Paragraph("Drug Repurposing Research Report", normal))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(f"<b>Query:</b> {query}", normal))
        story.append(
            Paragraph(
                f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                normal,
            )
        )
        story.append(
            Paragraph(f"<b>Total candidates:</b> {len(candidates)}", normal)
        )
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Top Candidates", header_style))
        table_data = [["Drug", "Score", "Sources", "Mechanism", "Primary Disease"]]
        for c in candidates[:10]:
            table_data.append(
                [
                    c.get("drug", ""),
                    f"{c.get('final_score', 0.0):.3f}",
                    str(c.get("sources_count", 0)),
                    (c.get("mechanism") or "")[:40],
                    (c.get("diseases", ["N/A"])[0])[:30]
                    if c.get("diseases")
                    else "N/A",
                ]
            )
        table = Table(
            table_data,
            colWidths=[1.5 * inch, 0.8 * inch, 0.8 * inch, 1.7 * inch, 1.5 * inch],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a6c80")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Candidate Details", header_style))
        for i, c in enumerate(candidates[:5], 1):
            story.append(
                Paragraph(
                    f"<b>{i}. {c.get('drug', '')}</b> (score {c.get('final_score', 0.0):.3f})",
                    normal,
                )
            )
            story.append(
                Paragraph(
                    f"<b>Mechanism:</b> {c.get('mechanism') or 'Not specified'}",
                    normal,
                )
            )
            story.append(
                Paragraph(
                    f"<b>Diseases:</b> {', '.join(c.get('diseases', [])) or 'N/A'}",
                    normal,
                )
            )
            story.append(
                Paragraph(
                    f"<b>Sources:</b> {', '.join(c.get('aggregated_meta', {}).get('sources', []))}",
                    normal,
                )
            )
            evidence = c.get("evidence", [])[:3]
            for ev in evidence:
                story.append(
                    Paragraph(
                        f"- [{ev.get('source')}] {ev.get('snippet', '')[:200]}",
                        normal,
                    )
                )
            story.append(Spacer(1, 0.15 * inch))

        story.append(PageBreak())
        story.append(Paragraph("Methodology", header_style))
        story.append(
            Paragraph(
                "PharmaRep Master orchestrates multiple AI workers to search papers, "
                "clinical trials, patents, and market data in parallel, then aggregates "
                "and ranks candidate drugs using a deterministic multi-source scoring "
                "formula with an optional LLM-assisted re-ranking step.",
                normal,
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Limitations & Disclaimer", header_style))
        story.append(
            Paragraph(
                "This report is for research purposes only and does not constitute "
                "medical or regulatory advice. All candidates must be independently "
                "validated by qualified experts before any clinical decisions.",
                normal,
            )
        )

        doc.build(story)
        logger.info(f"PDF report generated at {output_path}")
    except Exception as e:
        logger.error(f"Error generating PDF: {e}", exc_info=True)
        raise
