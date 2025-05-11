# controller/main_controller.py

from pathlib import Path
from PySide6.QtWidgets import QFileDialog
from model.report import TestReport
from model.session import SessionManager
from view.widgets import MainWindow
from reports.pdf_builder import build_pdf

class MainController:
    # Point at ~/.config/session.json
    CONFIG_DIR = Path.home() / ".config" / "test_dashboard"
    SESSION_FILE = CONFIG_DIR / "test_dashboard_session.json"

    def __init__(self, app):
        self.app = app
        # ensure config directory exists
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        self.report = TestReport()
        self.session = SessionManager(self.SESSION_FILE)
        self.window = MainWindow(self)

        # Try loading last session if exists
        if self.SESSION_FILE.exists():
            self.load_session()

    def show(self):
        self.window.show()

    def load_excel(self):
        path, _ = QFileDialog.getOpenFileName(self.window, 
                                              "Open Excel", 
                                              "", 
                                              "Excel Files (*.xlsx *.xls)")
        if not path:
            return
        try:
            self.report.load_from_excel(path)
            summary = self.report.summary()
            self.window.update_view(self.report.df, summary)
            self.window.set_feedback(f"Loaded {len(self.report.df)} rows from Excel.")
        except Exception as e:
            self.window.show_error(str(e))

    def save_session(self):
        metadata = self.window.get_metadata()
        try:
            summary = self.report.summary()
            metadata.update(summary)
            self.session.save(self.report, metadata)
            self.window.set_feedback("Session saved.")
        except Exception as e:
            self.window.show_error(str(e))

    def load_session(self):
        try:
            report, metadata = self.session.load()
            self.report = report
            self.window.set_metadata(metadata)
            self.window.update_view(self.report.df, report.summary())
            self.window.set_feedback("Session loaded.")
        except Exception:
            pass


    def apply_filters(self):
        # Hide/show rows based on checkboxes
        # This is done automatically via model/view
        self.window.table.reset()  # force redraw

    def generate_pdf(self):
        metadata = self.window.get_metadata()
        name = metadata.get('pdf_name') or 'report'
        path, _ = QFileDialog.getSaveFileName(self.window, "Save PDF", f"{name}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            # Build pie chart bytes
            pie_bytes = self.report.pie_chart_bytes()
            # Update metadata with counts
            summary = self.report.summary()
            metadata.update(summary)
            build_pdf(path, self.report.df, metadata, pie_bytes)
            self.window.set_feedback(f"PDF saved: {path}")
        except Exception as e:
            self.window.show_error(str(e))