# pylint: disable=C0114, C0115, C0116, E0611, R0903
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class JobWidget(QFrame):
    def __init__(self, job_name="Untitled Job", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self.setFrameStyle(QFrame.Box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.name_label = QLabel(job_name)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        font = QFont()
        font.setBold(True)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)
        self.setLayout(layout)

    def set_job_name(self, name):
        self.name_label.setText(name)
