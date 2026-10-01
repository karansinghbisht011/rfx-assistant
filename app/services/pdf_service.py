"""RFQ PDF. Mock buyer details are placeholders, not verified customer information."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.rfq import RFQ
from app.services.quantities import format_quantity

INK = colors.HexColor("#1B2A41")
TEAL = colors.HexColor("#0E7C7B")
BORDER = colors.HexColor("#D9D3C7")


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_rfq_pdf(rfq: RFQ) -> bytes:
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], textColor=INK, fontSize=20, alignment=0, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], textColor=INK, fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, textColor=colors.HexColor("#5B6577"))
    cell = ParagraphStyle("cell", parent=body, fontSize=9.5, leading=12)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=rfq.name, author=rfq.buyer_details.company_name,
    )
    buyer = rfq.buyer_details
    story = [
        Paragraph(_esc(buyer.company_name), title),
        Paragraph(f"{_esc(buyer.address)}<br/>{_esc(buyer.contact)}", small),
        Spacer(1, 8 * mm),
        Paragraph("Request for Quotation", ParagraphStyle("h", parent=title, fontSize=15, textColor=TEAL)),
        Spacer(1, 2 * mm),
    ]

    meta = Table(
        [
            [Paragraph("<b>RFQ name</b>", cell), Paragraph(_esc(rfq.name), cell)],
            [Paragraph("<b>RFQ reference</b>", cell), Paragraph(_esc(rfq.rfq_id), cell)],
            [Paragraph("<b>Date</b>", cell), Paragraph(rfq.created_at.strftime("%d %B %Y"), cell)],
        ],
        colWidths=[40 * mm, 130 * mm],
    )
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story += [meta, Spacer(1, 6 * mm)]

    rows = [["No.", "Item", "Quantity", "Unit"]]
    for n, item in enumerate(rfq.items, start=1):
        name = item.catalogue_title or item.original_text
        rows.append(
            [str(n), Paragraph(_esc(name), cell), format_quantity(item.quantity), item.unit or ""]
        )
    table = Table(rows, colWidths=[14 * mm, 104 * mm, 28 * mm, 24 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), INK),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F3EC")]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)

    kept = [i for i in rfq.items if i.match_status == "unmatched" and not i.buyer_selected]
    if kept:
        story += [Spacer(1, 6 * mm), Paragraph("<b>Notes</b>", body)]
        for item in kept:
            story.append(Paragraph(f"• “{_esc(item.original_text)}” is listed in the buyer's own wording.", small))

    doc.build(story)
    return buffer.getvalue()
