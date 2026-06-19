import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

from app.models.database import Variant, Gene, Evidence, Paper, Report as ReportModel


class PDFReportGenerator:
    def generate_report(self, variant: Variant, gene: Gene, report: ReportModel,
                        evidence_list: list[dict]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'],
            fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1a365d")
        )
        heading_style = ParagraphStyle(
            'CustomHeading', parent=styles['Heading2'],
            fontSize=14, spaceAfter=6, spaceBefore=12, textColor=colors.HexColor("#2b6cb0")
        )
        body_style = ParagraphStyle(
            'CustomBody', parent=styles['Normal'],
            fontSize=10, spaceAfter=4, leading=14, alignment=TA_JUSTIFY
        )
        small_style = ParagraphStyle(
            'Small', parent=styles['Normal'],
            fontSize=8, textColor=colors.gray
        )

        elements = []

        elements.append(Paragraph(f"Sydney — Variant Intelligence Report", title_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2b6cb0")))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph(f"<b>Variant:</b> {variant.hgvs_c or variant.protein_change or 'N/A'}", body_style))
        elements.append(Paragraph(f"<b>Gene:</b> {gene.symbol} — {gene.full_name or ''}", body_style))
        elements.append(Paragraph(f"<b>Clinical Significance:</b> {variant.clinical_significance or 'Not determined'}", body_style))
        elements.append(Paragraph(f"<b>Confidence Level:</b> {report.confidence_level}", body_style))
        elements.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("1. Executive Summary", heading_style))
        summary = report.executive_summary or report.evidence_overview or "No summary available."
        elements.append(Paragraph(summary, body_style))
        elements.append(Spacer(1, 8))

        elements.append(Paragraph("2. Clinical Significance", heading_style))
        sig = report.clinical_significance or variant.clinical_significance or "Not determined."
        elements.append(Paragraph(f"Clinical significance: <b>{sig}</b>", body_style))
        elements.append(Paragraph(f"ClinVar ID: {variant.clinvar_id or 'N/A'}", body_style))
        elements.append(Paragraph(f"Review Status: {variant.review_status or 'N/A'}", body_style))
        if variant.gnomad_af is not None:
            af = variant.gnomad_af
            one_in = int(1 / af) if af > 0 else float("inf")
            elements.append(Paragraph(f"gnomAD v4 allele frequency: {af:.6f} (1 in {one_in:,})", body_style))
        else:
            elements.append(Paragraph("gnomAD v4 allele frequency: Absent from gnomAD", body_style))
        elements.append(Spacer(1, 8))

        elements.append(Paragraph("3. Evidence Overview", heading_style))
        elements.append(Paragraph(
            f"This variant has <b>{report.evidence_volume}</b> supporting studies. "
            f"Evidence quality score: <b>{report.evidence_quality:.2f}</b>. "
            f"Study agreement: <b>{report.study_agreement:.2f}</b>.",
            body_style
        ))
        elements.append(Spacer(1, 8))

        if evidence_list:
            elements.append(Paragraph("4. Supporting Studies", heading_style))
            for i, ev in enumerate(evidence_list[:10], 1):
                title = ev.get("title", "Unknown")[:100]
                pmid = ev.get("pmid", "N/A")
                year = ev.get("year", "N/A")
                score = ev.get("evidence_score", 0)
                elements.append(Paragraph(
                    f"<b>[{i}]</b> {title} "
                    f"<i>(PMID: {pmid}, {year})</i> — "
                    f"Score: {score:.2f}",
                    body_style
                ))
            elements.append(Spacer(1, 8))

        if report.disease_associations:
            elements.append(Paragraph("5. Disease Associations", heading_style))
            for d in report.disease_associations:
                if isinstance(d, dict):
                    elements.append(Paragraph(f"• {d.get('name', str(d))}", body_style))
                else:
                    elements.append(Paragraph(f"• {d}", body_style))
            elements.append(Spacer(1, 8))

        elements.append(Paragraph("6. Confidence Assessment", heading_style))
        elements.append(Paragraph(
            f"Confidence Level: <b>{report.confidence_level}</b> "
            f"(Score: {report.confidence_score:.2f})",
            body_style
        ))
        if report.confidence_assessment:
            elements.append(Paragraph(report.confidence_assessment, body_style))
        elements.append(Spacer(1, 12))

        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e0")))
        elements.append(Paragraph(
            f"Sydney — Biomedical Variant Intelligence Platform | Generated {datetime.now().strftime('%Y-%m-%d')}",
            small_style
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
