# pylint: disable=C0114, C0115, C0116, E0611, R0903
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ..gui.colors import ColorPalette


class JobWidget(QFrame):
    clicked = Signal()
    double_clicked = Signal()

    def __init__(self, job_name="Untitled Job", dark_theme=False, parent=None):
        super().__init__(parent)
        self._selected = False
        self._dark_theme = dark_theme
        self.setMinimumHeight(50)
        self.setProperty("selected", False)
        self.setProperty("dark_theme", dark_theme)
        self.setFocusPolicy(Qt.NoFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.name_label = QLabel(job_name)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        font = QFont()
        font.setBold(True)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)
        self.setLayout(layout)
        self.setAttribute(Qt.WA_Hover, True)
        self._update_stylesheet()

    def _update_stylesheet(self):
        if self._dark_theme:
            border_color = ColorPalette.LIGHT_BLUE.hex()
            selected_bg = ColorPalette.DARK_BLUE.hex()
            hover_bg = ColorPalette.MEDIUM_BLUE.hex()
        else:
            border_color = ColorPalette.DARK_BLUE.hex()
            selected_bg = ColorPalette.LIGHT_BLUE.hex()
            hover_bg = ColorPalette.MEDIUM_BLUE.hex()
        stylesheet = f"""
            JobWidget {{
                border: 2px solid #{border_color};
                border-radius: 4px;
                margin: 2px;
                background-color: palette(window);
            }}
            JobWidget[selected="true"] {{
                background-color: #{selected_bg};
            }}
            JobWidget:hover {{
                background-color: #{hover_bg};
            }}
        """
        self.setStyleSheet(stylesheet)

    # pylint: disable=C0103
    def mousePressEvent(self, event):
        self.clicked.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        event.accept()
    # pylint: enable=C0103

    def set_selected(self, selected):
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self._update_stylesheet()
        self.style().unpolish(self)
        self.style().polish(self)

    def set_dark_theme(self, dark_theme):
        self._dark_theme = dark_theme
        self.setProperty("dark_theme", dark_theme)
        self._update_stylesheet()
        self.style().unpolish(self)
        self.style().polish(self)

    def set_job_name(self, name):
        self.name_label.setText(name)
