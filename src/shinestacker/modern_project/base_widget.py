# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0913, R0917
import os
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ..gui.colors import ColorPalette


class BaseWidget(QFrame):
    clicked = Signal()
    double_clicked = Signal()

    def __init__(self, name, min_height=40, dark_theme=False, parent=None):
        super().__init__(parent)
        self._selected = False
        self._dark_theme = dark_theme
        self.min_height = min_height
        self.path_label = ''
        self.setFocusPolicy(Qt.NoFocus)
        self._init_widget(name)
        self.setAttribute(Qt.WA_Hover, True)
        self._update_stylesheet()

    def _init_widget(self, name):
        self.setMinimumHeight(self.min_height)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        font = QFont()
        font.setBold(True)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)
        self.path_label = None
        self.setLayout(layout)

    def widget_type(self):
        return ''

    def _format_path(self, path):
        if os.path.isabs(path):
            return ".../" + os.path.basename(path)
        return path

    def _add_path_label(self, text):
        if self.path_label is None:
            self.path_label = QLabel(text)
            self.layout().addWidget(self.path_label)
        else:
            self.path_label.setText(text)

    def _update_stylesheet(self):
        if self._dark_theme:
            border_color = ColorPalette.LIGHT_BLUE.hex()
            selected_bg = ColorPalette.DARK_BLUE.hex()
            hover_bg = ColorPalette.MEDIUM_BLUE.hex()
        else:
            border_color = ColorPalette.DARK_BLUE.hex()
            selected_bg = ColorPalette.LIGHT_BLUE.hex()
            hover_bg = ColorPalette.MEDIUM_BLUE.hex()
        widget_type = self.widget_type()
        stylesheet = f"""
            {widget_type} {{
                border: 2px solid #{border_color};
                border-radius: 4px;
                margin: 2px;
                background-color: palette(window);
            }}
            {widget_type}[selected="true"] {{
                background-color: #{selected_bg};
            }}
            {widget_type}:hover {{
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

    def set_name(self, name):
        self.name_label.setText(name)
