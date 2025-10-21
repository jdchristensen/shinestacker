# pylint: disable=C0114, C0115, C0116, E0611
from PIL.TiffImagePlugin import IFDRational
from PySide6.QtWidgets import QLabel, QTextEdit
from PySide6.QtCore import Qt
from .. algorithms.exif import exif_dict
from .. gui.config_dialog import ConfigDialog


class ExifData(ConfigDialog):  # Inherit from ConfigDialog
    def __init__(self, exif, parent=None):
        self.exif = exif
        super().__init__("EXIF Data", parent)
        self.reset_button.setVisible(False)
        self.cancel_button.setVisible(False)
        self.ok_button.setFixedWidth(100)
        self.button_box.setAlignment(Qt.AlignCenter)

    def create_form_content(self):
        if self.exif is None:
            data = {}
        else:
            data = exif_dict(self.exif)
        if len(data) > 0:
            for k, (_, d) in data.items():
                if isinstance(d, IFDRational):
                    d = f"{d.numerator}/{d.denominator}"
                d_str = str(d)
                if "<<<" not in d_str and k != 'IPTCNAA':
                    if len(d_str) <= 40:
                        self.container_layout.addRow(f"<b>{k}:</b>", QLabel(d_str))
                    else:
                        text_edit = QTextEdit()
                        text_edit.setPlainText(d_str)
                        text_edit.setReadOnly(True)
                        text_edit.setFixedHeight(100)
                        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                        text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
                        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                        text_edit.setFixedWidth(400)
                        self.container_layout.addRow(f"<b>{k}:</b>", text_edit)
