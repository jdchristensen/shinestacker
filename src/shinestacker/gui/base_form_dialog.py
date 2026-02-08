# pylint: disable=C0114, C0115, C0116, R0903, E0611
from PySide6.QtWidgets import QFormLayout, QDialog, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt


def create_form_layout(parent):
    layout = QFormLayout(parent)
    layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
    layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
    layout.setLabelAlignment(Qt.AlignLeft)
    return layout


class BaseFormDialog(QDialog):
    def __init__(self, title, width=500, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(width, self.height())
        self.ok_button = None
        self.cancel_button = None
        self.form_layout = create_form_layout(self)
        self.group_style = """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """

    def add_row_to_layout(self, item):
        self.form_layout.addRow(item)

    def create_ok_cancel(self):
        button_box = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(self.ok_button)
        button_box.addWidget(cancel_button)
        self.add_row_to_layout(button_box)
        self.ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
