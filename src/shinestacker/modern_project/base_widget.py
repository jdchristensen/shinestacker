# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0913, R0917, R0902
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QLayout
from ..gui.colors import ColorPalette


class BaseWidget(QFrame):
    clicked = Signal()
    double_clicked = Signal()
    enabled_toggled = Signal(bool)

    def __init__(self, data_object, min_height=40, dark_theme=False, parent=None):
        super().__init__(parent)
        self.data_object = data_object
        self._selected = False
        self._enabled = True
        self._dark_theme = dark_theme
        self.min_height = min_height
        self.path_label = None
        self.child_widgets = []
        self.setFocusPolicy(Qt.NoFocus)
        self._init_widget(data_object)
        self.setAttribute(Qt.WA_Hover, True)
        self._update_stylesheet()
        self.enabled_toggled.connect(self._on_enabled_toggled)

    def num_child_widgets(self):
        return len(self.child_widgets)

    def _init_widget(self, data_object):
        self.setMinimumHeight(self.min_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(2)
        main_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        header_layout.addWidget(self.name_label, 1)
        self.enabled_icon = QLabel()
        self.enabled_icon.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.enabled_icon.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.enabled_icon.mousePressEvent = self._on_enabled_icon_clicked
        header_layout.addWidget(self.enabled_icon, 0)
        main_layout.addLayout(header_layout)
        self.setLayout(main_layout)
        self.update(data_object)

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

    def add_child_widget(self, child_widget, add_to_layout=True):
        self.child_widgets.append(child_widget)
        if add_to_layout:
            self.layout().addWidget(child_widget)

    def _update_stylesheet(self):
        if self._dark_theme:
            border_color = ColorPalette.LIGHT_BLUE.hex()
            selected_bg = ColorPalette.DARK_BLUE.hex()
            hover_bg = ColorPalette.MEDIUM_BLUE.hex()
            disabled_border_color = ColorPalette.LIGHT_RED.hex()
            disabled_selected_bg = ColorPalette.DARK_RED.hex()
            disabled_hover_bg = ColorPalette.MEDIUM_RED.hex()
        else:
            border_color = ColorPalette.DARK_BLUE.hex()
            selected_bg = ColorPalette.LIGHT_BLUE.hex()
            hover_bg = ColorPalette.MEDIUM_BLUE.hex()
            disabled_border_color = ColorPalette.DARK_RED.hex()
            disabled_selected_bg = ColorPalette.LIGHT_RED.hex()
            disabled_hover_bg = ColorPalette.MEDIUM_RED.hex()
        widget_type = self.widget_type()
        if self._enabled:
            border = border_color
            selected = selected_bg
            hover = hover_bg
        else:
            border = disabled_border_color
            selected = disabled_selected_bg
            hover = disabled_hover_bg
        stylesheet = f"""
            {widget_type} {{
                border: 2px solid #{border};
                border-radius: 4px;
                margin: 2px;
                background-color: palette(window);
            }}
            {widget_type}[selected="true"] {{
                background-color: #{selected};
            }}
            {widget_type}:hover {{
                background-color: #{hover};
            }}
        """
        self.setStyleSheet(stylesheet)
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_enabled_icon_clicked(self, event):
        self._enabled = not self._enabled
        self._update_enabled_icon()
        self._update_stylesheet()
        self.enabled_toggled.emit(self._enabled)
        event.accept()

    def _update_enabled_icon(self):
        if self._enabled:
            self.enabled_icon.setText("✅")
        else:
            self.enabled_icon.setText("🚫")

    def _on_enabled_toggled(self, enabled):
        self.data_object.params['enabled'] = enabled

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

    def set_dark_theme(self, dark_theme):
        self._dark_theme = dark_theme
        self.setProperty("dark_theme", dark_theme)
        self._update_stylesheet()
        for child in self.child_widgets:
            child.set_dark_theme(dark_theme)

    def set_name(self, name):
        self.name_label.setText(name)

    def update(self, data_object):
        self.data_object = data_object
        name = f"<b>{data_object.params['name']}</b> [{data_object.type_name}]"
        self.set_name(name)
        self._enabled = data_object.params.get('enabled', True)
        self._update_enabled_icon()
