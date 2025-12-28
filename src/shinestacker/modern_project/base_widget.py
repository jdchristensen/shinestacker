# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0913, R0917, R0902
import os
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QLayout, QScrollArea)
from ..gui.colors import ColorPalette


class BaseWidget(QFrame):
    clicked = Signal()
    double_clicked = Signal()
    enabled_toggled = Signal(bool)

    def __init__(self, data_object, min_height=40, dark_theme=False,
                 horizontal_layout=False, parent=None):
        super().__init__(parent)
        self.data_object = data_object
        self._selected = False
        self._enabled = True
        self._dark_theme = dark_theme
        self.horizontal_layout = horizontal_layout
        self.min_height = min_height
        self.path_label = None
        self.child_widgets = []
        self.top_container = None
        self.top_layout = None
        self.icons_container = None
        self.icons_layout = None
        self.path_label_in_top_row = None
        self.child_container = None
        self.child_container_layout = None
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_Hover, True)
        self.name_label = None
        self.enabled_icon = None
        self.path_label_in_top_row = True
        self._init_widget(data_object)
        self._update_stylesheet()
        self.enabled_toggled.connect(self._on_enabled_toggled)

    def _init_widget(self, data_object):
        self.setMinimumHeight(self.min_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(2)
        main_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.top_container = QWidget()
        self.top_layout = QHBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(4)
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.top_layout.addWidget(self.name_label)
        self.path_label = QLabel()
        self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.top_layout.addWidget(self.path_label, 1)
        self.icons_container = QWidget()
        self.icons_layout = QHBoxLayout(self.icons_container)
        self.icons_layout.setContentsMargins(0, 0, 0, 0)
        self.icons_layout.setSpacing(2)
        self.enabled_icon = QLabel()
        self.enabled_icon.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.enabled_icon.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.enabled_icon.mousePressEvent = self._on_enabled_icon_clicked
        self.icons_layout.addWidget(self.enabled_icon)
        self.top_layout.addWidget(self.icons_container)
        main_layout.addWidget(self.top_container)
        self.child_container = QWidget()
        if self.horizontal_layout:
            self.child_container_layout = QHBoxLayout()
        else:
            self.child_container_layout = QVBoxLayout()
        self.child_container_layout.setContentsMargins(0, 5, 0, 0)
        self.child_container_layout.setSpacing(5)
        self.child_container.setLayout(self.child_container_layout)
        main_layout.addWidget(self.child_container)
        self.setLayout(main_layout)
        self.update(data_object)

    def add_child_widget(self, child_widget, add_to_layout=True):
        self.child_widgets.append(child_widget)
        if add_to_layout:
            self.child_container_layout.addWidget(child_widget)

    def set_horizontal_layout(self, horizontal):
        if self.horizontal_layout != horizontal:
            self.horizontal_layout = horizontal
            main_layout = self.layout()
            old_container = self.child_container
            self.child_container = QWidget()
            if horizontal:
                self.child_container_layout = QHBoxLayout()
            else:
                self.child_container_layout = QVBoxLayout()
            self.child_container_layout.setContentsMargins(0, 5, 0, 0)
            self.child_container_layout.setSpacing(5)
            for widget in self.child_widgets:
                self.child_container_layout.addWidget(widget)
            self.child_container.setLayout(self.child_container_layout)
            main_layout.replaceWidget(old_container, self.child_container)
            old_container.deleteLater()

    def _add_path_label(self, text):
        self.path_label.setText(text)
        QTimer.singleShot(0, self._check_and_adjust_layout)

    def _check_and_adjust_layout(self):
        if not self.path_label.text():
            return
        available_width = self.top_container.width() - 20
        name_width = self.name_label.sizeHint().width()
        path_width = self.path_label.sizeHint().width()
        icons_width = self.icons_container.sizeHint().width()
        total_needed = name_width + path_width + icons_width + 20
        if total_needed > available_width and self.path_label_in_top_row:
            self.top_layout.removeWidget(self.path_label)
            self.layout().insertWidget(1, self.path_label)
            self.path_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.path_label_in_top_row = False
        elif total_needed <= available_width and not self.path_label_in_top_row:
            self.layout().removeWidget(self.path_label)
            self.top_layout.insertWidget(1, self.path_label)
            self.top_layout.setStretch(1, 1)
            self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.path_label_in_top_row = True

    def _on_enabled_icon_clicked(self, event):
        self._enabled = not self._enabled
        self._update_enabled_icon()
        self._update_stylesheet()
        self.enabled_toggled.emit(self._enabled)
        event.accept()

    def widget_type(self):
        return ''

    def _format_path(self, path):
        if os.path.isabs(path):
            return ".../" + os.path.basename(path)
        return path

    def num_child_widgets(self):
        return len(self.child_widgets)

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

    def _update_enabled_icon(self):
        if self._enabled:
            self.enabled_icon.setText("✅")
            self.enabled_icon.setToolTip("Disable")
        else:
            self.enabled_icon.setText("🚫")
            self.enabled_icon.setToolTip("Enable")

    def _on_enabled_toggled(self, enabled):
        self.data_object.params['enabled'] = enabled

    # pylint: disable=C0103
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.path_label and self.path_label.text():
            self._check_and_adjust_layout()

    def mousePressEvent(self, event):
        self.clicked.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        event.accept()

    def contextMenuEvent(self, event):
        widget = self
        while widget:
            if type(widget).__name__ == 'ModernProjectView':
                widget.contextMenuEvent(event)
                break
            widget = widget.parent()
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

    def scroll_area_css(self, orientation):
        size = 'width' if orientation == 'vertical' else 'height'
        return f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:{orientation} {{
                height: 6px;
                border: none;
                background: transparent;
            }}
            QScrollBar::handle:{orientation} {{
                background: #808080;
                border-radius: 6px;
                min-{size}: 20px;
            }}
            QScrollBar::handle:{orientation}:hover {{
                background: #404040;
            }}
            QScrollBar::add-line:{orientation}, QScrollBar::sub-line:{orientation} {{
                width: 0px;
                height: 0px;
            }}
        """


class ImgBaseWidget(BaseWidget):
    def __init__(self, data_object, min_height=40, dark_theme=False,
                 horizontal_layout=False, parent=None):
        super().__init__(data_object, min_height, dark_theme, horizontal_layout, parent)
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setWidgetResizable(True)
        self.image_scroll_area.setFrameShape(QFrame.NoFrame)
        self.image_views = []
        self.image_layout = None
        self.image_area_widget = None

    def clear_images(self):
        for view in self.image_views:
            if self.image_layout:
                self.image_layout.removeWidget(view)
            view.deleteLater()
        self.image_views.clear()
        self.image_scroll_area.setVisible(False)
        self.image_scroll_area.setMinimumHeight(0)
