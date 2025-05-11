from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Image as PDFImage, PageBreak, Spacer
)
from reportlab.lib.units import inch
from model.report import TestStatus

from .pdf_config import (
    HEADER_FONT_SIZE, CELL_FONT_SIZE,
    TOTAL_LABEL_FONT_SIZE, TOTAL_VALUE_FONT_SIZE,
    COL_WIDTHS
)

# ——— Style Constants —————————————————————————————————————————————
BASE_TABLE_STYLE = [
    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
]
HEADER_STYLE = [
    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ('LINEABOVE', (0, 0), (-1, 0), 1, colors.darkgrey),
    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
]
TOTAL_ROW_STYLE = [
    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ('SPAN', (0, -1), (1, -1)),  # span label and count
    ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
]

# ——— Helpers —————————————————————————————————————————————————————
def _get_image(source, max_w, max_h):
    img = PDFImage(source)
    img._restrictSize(max_w, max_h)
    return img


def _styled_table(data, col_widths, style_cmds):
    table = Table(data, col_widths)
    table.setStyle(TableStyle(style_cmds))
    return table


def draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    w, _ = letter
    canvas.drawCentredString(w/2.0, 0.5*inch, f"Page {doc.page}")
    canvas.restoreState()


def draw_header(canvas, doc):
    canvas.saveState()

    # Primary logo (left)
    logo_path = doc.metadata.get('logo_path', 'static/dummy.png')
    logo_w, logo_h = 1.0 * inch, 0.3 * inch
    x_left = doc.leftMargin
    y = letter[1] - doc.topMargin + (logo_h / 2)
    canvas.drawImage(
        logo_path, x_left, y,
        width=logo_w, height=logo_h,
        preserveAspectRatio=True, mask='auto'
    )

    # Secondary logo (right)
    second_logo_path = doc.metadata.get('second_logo_path', 'static/dummy2.png')
    x_right = doc.leftMargin + doc.width - logo_w  # right-align within content width
    canvas.drawImage(
        second_logo_path, x_right, y,
        width=logo_w, height=logo_h,
        preserveAspectRatio=True, mask='auto'
    )

    # Line below header
    line_y = letter[1] - doc.topMargin
    canvas.setStrokeColor(colors.grey)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, line_y, doc.leftMargin + doc.width, line_y)

    canvas.restoreState()


def draw_header_and_footer(canvas, doc):
    draw_header(canvas, doc)
    draw_footer(canvas, doc)

# ——— Main PDF Builder —————————————————————————————————————————————
def build_pdf(path: str, df, metadata: dict, pie_bytes: bytes):
    # Attach metadata for header/footer
    SimpleDocTemplate.metadata = metadata

    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        rightMargin=30, leftMargin=30,
        topMargin=70, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = styles['Title']
    title_style.fontSize = 24
    title_style.spaceAfter = 20

    heading_style = ParagraphStyle('Heading', parent=styles['Heading1'], fontSize=14, spaceAfter=12)
    normal_style = styles['Normal']

    content = []

    # — Cover page —
    logo1 = _get_image(metadata.get('logo_path', 'static/dummy.png'), 2.4 * inch, 0.5 * inch)
    logo2 = _get_image(metadata.get('second_logo_path', 'static/dummy2.png'), 2.4 * inch, 0.5 * inch)

    # Create a row with both logos
    content.append(_styled_table(
        [[logo1, logo2]],
        [doc.width / 2, doc.width / 2],  # colWidths as second positional argument
        [('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
    ))
    content.append(Spacer(1, 50))

    # Truck image
    truck_image = _get_image(metadata.get('truck', 'static/car.jpg'), 5.5 * inch, 2.5 * inch)
    content.append(truck_image)
    content.append(Spacer(1, 50))

    # — Report metadata & summary —
    content.append(Paragraph('<b>Test Report</b>', title_style))
    meta_fields = [
        ('tester', 'Tester'), ('date', 'Date'), ('version', 'Software Version'),
        ('hardware_version', 'Hardware Version'), ('battery_arxml_version', 'Battery-CAN ARXML Version'),
        ('energy_arxml_version', 'Energy-CAN ARXML Version'), ('cdd_version', 'CDD Version'),
    ]

    cover_note = metadata.get('cover_note', (
        "   In accordance with applicable legal regulations, test reports for products and services "
        "must be retained for at least 6 years after the completion of the tests. This retention "
        "period begins at the end of the calendar year in which the test was conducted; we recommend "
        "archiving for at least 10 years."
    ))
    box_para = Paragraph(cover_note, normal_style)
    box_style = [
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]
    content.append(_styled_table([[box_para]], [doc.width], box_style))
    main_info = [[label, metadata.get(key, '')] for key, label in meta_fields if metadata.get(key)]
    if main_info:
        content.append(_styled_table(main_info, [1.5*inch, 4*inch], BASE_TABLE_STYLE + HEADER_STYLE))
    content.append(PageBreak())

    summary = metadata.get('counts', {})
    if summary:
        sum_data = [['Total', len(df)]] + [[label, summary.get(key, 0)] for key, label in [
            (TestStatus.PASS.value, 'Pass'), (TestStatus.FAIL.value, 'Fail'), (TestStatus.NOT_TESTED.value, 'Not Tested')
        ]]
        content.append(Paragraph('Summary:', heading_style))
        content.append(_styled_table(sum_data, [1.5*inch, 4*inch], BASE_TABLE_STYLE + HEADER_STYLE))
    content.append(Spacer(1, 100))

    if pie_bytes:
        pie = _get_image(BytesIO(pie_bytes), 4*inch, 4*inch)
        content.append(pie)

    content.append(PageBreak())

    # — Test Cases Table —
    content.append(PageBreak())
    content.append(Paragraph('<b>Test Cases</b>', heading_style))
    col_titles = ['Test Case ID', 'Test Case Description', 'Test Status', 'Comments']
    header = [Paragraph(f'<b>{t}</b>', ParagraphStyle('hdr', alignment=TA_CENTER, fontSize=HEADER_FONT_SIZE)) for t in col_titles]
    data = [header]

    # Populate rows
    for record in df.itertuples(index=False):
        aligns = [TA_CENTER, TA_LEFT, TA_CENTER, TA_LEFT]
        row_cells = [Paragraph(str(val), ParagraphStyle('cell', alignment=align, fontSize=CELL_FONT_SIZE))
                     for val, align in zip(record, aligns)]
        data.append(row_cells)

    # Add total row
    total_row = [
        Paragraph('<b>Total Cases</b>', ParagraphStyle('total_lbl', alignment=TA_LEFT, fontSize=TOTAL_LABEL_FONT_SIZE)),
        Paragraph(f'<b>{len(df)}</b>', ParagraphStyle('total_val', alignment=TA_LEFT, fontSize=TOTAL_VALUE_FONT_SIZE)),
        '', ''
    ]
    data.append(total_row)

    # — Color the Test Status column per status —
    status_colors = {
        TestStatus.PASS.value: colors.limegreen,
        TestStatus.FAIL.value: colors.tomato,
        TestStatus.NOT_TESTED.value: colors.lightgrey,
    }
    status_styles = []
    # start=1 to skip header row
    for i, record in enumerate(df.itertuples(index=False), start=1):
        status_val = str(record[2])
        color = status_colors.get(status_val)
        if color:
            # Column index 2 corresponds to "Test Status"
            status_styles.append(('BACKGROUND', (2, i), (2, i), color))

    # Build and append the styled table
    content.append(
        _styled_table(
            data,
            COL_WIDTHS,
            BASE_TABLE_STYLE + HEADER_STYLE + TOTAL_ROW_STYLE + status_styles + [
                ('LEFTPADDING', (0,1), (0,-1), 6)
            ]
        )
    )

    # Build PDF
    doc.build(content, onFirstPage=draw_footer, onLaterPages=draw_header_and_footer)
