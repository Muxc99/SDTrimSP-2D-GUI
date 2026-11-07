"""Modeless result table with lazy cell display and spreadsheet clipboard support."""
import csv
import io

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QApplication, QAbstractItemView, QDialog, QHBoxLayout,
    QHeaderView, QLabel, QMenu, QPushButton, QTableView, QVBoxLayout)


class ResultsFrameModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None

    def set_frame(self, frame):
        if frame is self.frame:
            return
        self.beginResetModel()
        self.frame = frame
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or self.frame is None else len(self.frame)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or self.frame is None else len(self.frame.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return str(self.frame.iat[index.row(), index.column()])
        if index.isValid() and role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self.frame.columns[section]) if self.frame is not None else None
        return str(section + 1)


class ResultsDataTable(QTableView):
    def __init__(self, translate, parent=None):
        super().__init__(parent)
        self.tr_label = translate
        self.setModel(ResultsFrameModel(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setDefaultSectionSize(150)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
            event.accept()
            return
        super().keyPressEvent(event)

    def copy_selection(self, include_headers=False):
        selection = self.selectionModel().selection()
        if not selection:
            return
        frame = self.model().frame
        # Whole columns and rectangular selections avoid per-cell Python/Qt calls.
        if len(selection) == 1:
            area = selection[0]
            block = frame.iloc[area.top():area.bottom() + 1, area.left():area.right() + 1]
            QApplication.clipboard().setText(block.to_csv(sep=chr(9), index=False, header=include_headers))
            return
        rows = sorted({r for area in selection for r in range(area.top(), area.bottom() + 1)})
        columns = sorted({c for area in selection for c in range(area.left(), area.right() + 1)})
        output = io.StringIO(newline='')
        writer = csv.writer(output, delimiter='\t', lineterminator='\n')
        if include_headers:
            writer.writerow([str(frame.columns[c]) for c in columns])
        for row in rows:
            writer.writerow([str(frame.iat[row, col]) if any(
                area.top() <= row <= area.bottom() and area.left() <= col <= area.right()
                for area in selection) else '' for col in columns])
        QApplication.clipboard().setText(output.getvalue())

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        copy = menu.addAction(self.tr_label('复制选中数据', 'Copy selected data'))
        headers = menu.addAction(self.tr_label('复制（含列名）', 'Copy with headers'))
        copy.setEnabled(self.selectionModel().hasSelection())
        headers.setEnabled(copy.isEnabled())
        menu.addSeparator()
        select_all = menu.addAction(self.tr_label('全选', 'Select all'))
        action = menu.exec(event.globalPos())
        if action == copy:
            self.copy_selection()
        elif action == headers:
            self.copy_selection(True)
        elif action == select_all:
            self.selectAll()


class ResultsDataDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setModal(False)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        self.resize(1000, 540)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        self.table = ResultsDataTable(owner.tr, self)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        layout.addLayout(buttons)
        self.copy_button = QPushButton()
        self.headers_button = QPushButton()
        self.select_button = QPushButton()
        self.close_button = QPushButton()
        for button in (self.copy_button, self.headers_button, self.select_button):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)
        self.copy_button.clicked.connect(lambda: self.table.copy_selection())
        self.headers_button.clicked.connect(lambda: self.table.copy_selection(True))
        self.select_button.clicked.connect(self.table.selectAll)
        self.close_button.clicked.connect(self.close)
        self.table.selectionModel().selectionChanged.connect(self.update_copy_buttons)
        self.update_frame(None)

    def update_copy_buttons(self, *args):
        enabled = self.table.selectionModel().hasSelection()
        self.copy_button.setEnabled(enabled)
        self.headers_button.setEnabled(enabled)

    def update_frame(self, frame):
        self.table.model().set_frame(frame)
        rows = self.table.model().rowCount()
        columns = self.table.model().columnCount()
        tr = self.owner.tr
        self.setWindowTitle(tr('结果数据表', 'Result data table'))
        self.summary.setText(tr(
            f'{rows} 行 × {columns} 列（只读） · 拖选 / Shift 扩选 / Ctrl 多选 · Ctrl+C 复制，Ctrl+A 全选',
            f'{rows} rows × {columns} columns (read-only) · Drag / Shift to extend / Ctrl for multiple selections · Ctrl+C copy, Ctrl+A select all'))
        self.copy_button.setText(tr('复制选中数据', 'Copy selected data'))
        self.headers_button.setText(tr('复制（含列名）', 'Copy with headers'))
        self.select_button.setText(tr('全选', 'Select all'))
        self.close_button.setText(tr('关闭', 'Close'))
        self.update_copy_buttons()
