# tests_report_app/reports/pdf_config.py
"""
Configuration for PDF table styling and sizing.
Adjust these values to change column widths and font sizes.
"""
from reportlab.lib.units import inch

# Font sizes
HEADER_FONT_SIZE      = 8  # table header font size
CELL_FONT_SIZE        = 8  # table cell font size
TOTAL_LABEL_FONT_SIZE = 8  # "Total Cases" label font size
TOTAL_VALUE_FONT_SIZE = 8  # total count font size

# Column widths (in inches)
# Order: Test Case ID, Test Case Description, Test Status, Comments
COL_WIDTHS = [
    1.5 * inch,
    3.0 * inch,
    0.75 * inch,
    1.5 * inch,
]
