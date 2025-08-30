# pylint: disable=C0114, C0115, C0116, R0903, E0611
from PySide6.QtWidgets import QFormLayout, QDialog
from PySide6.QtCore import Qt


def create_form_layout(parent):
    layout = QFormLayout(parent)
    layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
    layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
    layout.setLabelAlignment(Qt.AlignLeft)
    return layout


class BaseFormDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, self.height())
        self.form_layout = create_form_layout(self)

    def add_row_to_layout(self, item):
        self.form_layout.addRow(item)
