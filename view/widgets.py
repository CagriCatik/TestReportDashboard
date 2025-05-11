# view/widgets.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTableView, QPushButton, QLineEdit, QDateEdit,
    QCheckBox, QLabel, QHBoxLayout, QVBoxLayout, QFormLayout,
    QMessageBox, QStyledItemDelegate, QComboBox, QHeaderView
)
from PySide6.QtCore import Qt, QDate, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QAction

from model.report import TestStatus

import yaml
from pathlib import Path

# ─── locate project root (two levels up from this file) ───
ROOT = Path(__file__).resolve().parent.parent

# ─── now point at config/ui.yml in the project root ───
_cfg_path = ROOT / "config" / "ui.yml"

if not _cfg_path.is_file():
    raise FileNotFoundError(f"Config file not found at {_cfg_path}")

with _cfg_path.open("r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

class StatusDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems([s.value for s in TestStatus])
        return combo

    def setEditorData(self, editor, index):
        current = index.data(Qt.EditRole) or index.data()
        idx = editor.findText(current)
        editor.setCurrentIndex(idx if idx >= 0 else 0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)


class PandasTableModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._df = df

    def set_dataframe(self, df):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()):
        return 0 if self._df is None else self._df.shape[0]

    def columnCount(self, parent: QModelIndex = QModelIndex()):
        return 0 if self._df is None else self._df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        return str(self._df.iat[index.row(), index.column()])

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._df.columns[section]
        return str(section)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            self._df.iat[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        return False


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.status_col = None
        self.setWindowTitle("Test Report Generator")
        self.setGeometry(100, 100, 1000, 700)
        self._build_ui()

    def _build_ui(self):
        # --- Menu ---
        menubar = self.menuBar()
        for item in cfg['menu']['File']:
            act = QAction(item['text'], self)
            act.triggered.connect(getattr(self.controller, item['handler']))
            menubar.addAction(act)


        # --- Central widget & layout ---
        w = QWidget(); self.setCentralWidget(w)
        main_layout = QVBoxLayout(w)

        # --- Form inputs ---
        form = QFormLayout()
        # create inputs once
        self.tester_input           = QLineEdit()
        self.date_input             = QDateEdit()
        self.software_version_input = QLineEdit()
        self.hardware_version_input = QLineEdit()
        self.arxml_input            = QLineEdit()
        self.cdd_version_input      = QLineEdit()
        self.pdf_name_input         = QLineEdit()

        # date format & default
        fmt = cfg['date']['format']
        self.date_input.setDisplayFormat(fmt)
        if cfg['date']['default_to_today']:
            self.date_input.setDate(QDate.currentDate())

        # add rows from config
        fld = cfg['fields']
        form.addRow(fld['tester'],           self.tester_input)
        form.addRow(fld['date'],             self.date_input)
        form.addRow(fld['software_version'], self.software_version_input)
        form.addRow(fld['hardware_version'], self.hardware_version_input)
        form.addRow(fld['arxml_version'],    self.arxml_input)
        form.addRow(fld['cdd_version'],      self.cdd_version_input)
        form.addRow(fld['pdf_name'],         self.pdf_name_input)
        main_layout.addLayout(form)

        # --- Summary labels ---
        stats_layout = QHBoxLayout()
        self.total_label      = QLabel()
        self.pass_label       = QLabel()
        self.fail_label       = QLabel()
        self.not_tested_label = QLabel()
        for lbl in (self.total_label, self.pass_label,
                    self.fail_label, self.not_tested_label):
            stats_layout.addWidget(lbl)
        main_layout.addLayout(stats_layout)

        # --- Filters ---
        status_vals = cfg['status']['values']
        defaults    = cfg['status']['filters_default']
        filter_layout = QHBoxLayout()
        self.filter_pass = QCheckBox(status_vals[0])
        self.filter_fail = QCheckBox(status_vals[1])
        self.filter_not  = QCheckBox(status_vals[2])
        for cb, checked in zip((self.filter_pass, self.filter_fail, self.filter_not),
                               defaults):
            cb.setChecked(checked)
            cb.stateChanged.connect(self.apply_filters)
            filter_layout.addWidget(cb)
        main_layout.addLayout(filter_layout)

        # --- Table view ---
        self.table = QTableView()
        self.model = PandasTableModel()
        self.table.setModel(self.model)
        self._resize_columns()
        main_layout.addWidget(self.table)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.gen_pdf_btn = QPushButton(cfg['buttons']['generate_pdf'])
        self.gen_pdf_btn.clicked.connect(self.controller.generate_pdf)
        btn_layout.addWidget(self.gen_pdf_btn)
        main_layout.addLayout(btn_layout)

        # --- Feedback ---
        self.feedback = QLabel("")
        main_layout.addWidget(self.feedback)

    def _resize_columns(self):
        hdr = self.table.horizontalHeader()

        # allow manual sizing and set a default width (or use whatever value you prefer)
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setDefaultSectionSize(cfg.get('table', {}) \
            .get('default_section_size', hdr.defaultSectionSize()))

        # only try per‐column overrides if we actually have a DataFrame
        df = getattr(self.model, "_df", None)
        if df is not None:
            for idx, col in enumerate(df.columns):
                # fetch your YAML widths or skip if none
                w = cfg.get('table', {}) \
                    .get('column_widths', {}) \
                    .get(col)
                if w:
                    hdr.resizeSection(idx, w)

        # still stretch the last section
        hdr.setStretchLastSection(True)



    def apply_filters(self):
        if self.status_col is None:
            return
        for row in range(self.model.rowCount()):
            idx = self.model.index(row, self.status_col)
            status = idx.data()
            visible = (
                (status == TestStatus.PASS.value and self.filter_pass.isChecked()) or
                (status == TestStatus.FAIL.value and self.filter_fail.isChecked()) or
                (status == TestStatus.NOT_TESTED.value and self.filter_not.isChecked())
            )
            self.table.setRowHidden(row, not visible)

    def update_view(self, df, summary):
        # load new data into the model
        self.model.set_dataframe(df)
        # find status column index
        try:
            self.status_col = df.columns.get_loc("Test Status")
        except Exception:
            self.status_col = None
        # delegate for editing
        if self.status_col is not None:
            self.table.setItemDelegateForColumn(self.status_col, StatusDelegate())
        # update metrics
        self.total_label.setText(f"Total: {summary['total']}")
        counts = summary['counts']
        perc = summary['percent']
        self.pass_label.setText(f"Pass: {counts['Pass']} ({perc['Pass']})")
        self.fail_label.setText(f"Fail: {counts['Fail']} ({perc['Fail']})")
        self.not_tested_label.setText(f"Not Tested: {counts['Not Tested']} ({perc['Not Tested']})")
        # apply UI changes
        self.apply_filters()
        self._resize_columns()
        # force redraw
        self.table.reset()

    def show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)

    def get_metadata(self):
        return {
            'tester': self.tester_input.text(),
            'date': self.date_input.text(),
            'version': self.software_version_input.text(),
            'hardware_version': self.hardware_version_input.text(),
            'arxml_version': self.arxml_input.text(),
            'cdd_version': self.cdd_version_input.text(),
            'pdf_name': self.pdf_name_input.text()
        }

    def set_metadata(self, metadata):
        self.tester_input.setText(metadata.get('tester', ''))
        if metadata.get('date'):
            self.date_input.setDate(QDate.fromString(metadata['date'], "yyyy-MM-dd"))
        self.software_version_input.setText(metadata.get('version', ''))
        self.hardware_version_input.setText(metadata.get('hardware_version', ''))
        self.arxml_input.setText(metadata.get('arxml_version', ''))
        self.cdd_version_input.setText(metadata.get('cdd_version', ''))
        self.pdf_name_input.setText(metadata.get('pdf_name', ''))

    def set_feedback(self, text: str):
        self.feedback.setText(text)