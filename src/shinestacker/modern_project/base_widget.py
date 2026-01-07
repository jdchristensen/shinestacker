# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0913, R0917, R0902
import os
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QLayout, QScrollArea)
from ..gui.gui_images import GuiPdfView, GuiOpenApp, GuiImageView
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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(5)
        self.main_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.top_container = QWidget()
        self.top_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.top_layout = QHBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(5)
        self.top_layout.setAlignment(Qt.AlignTop)
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.top_layout.addWidget(self.name_label)
        self.path_label = QLabel()
        self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.top_layout.addWidget(self.path_label, 1)
        self.icons_container = QWidget()
        self.icons_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        self.icons_layout = QHBoxLayout(self.icons_container)
        self.icons_layout.setContentsMargins(0, 0, 0, 0)
        self.icons_layout.setSpacing(5)
        self.icons_layout.setAlignment(Qt.AlignTop)
        self.enabled_icon = QLabel()
        self.enabled_icon.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.enabled_icon.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.enabled_icon.mousePressEvent = self._on_enabled_icon_clicked
        self.icons_layout.addWidget(self.enabled_icon)
        self.top_layout.addWidget(self.icons_container)
        self.main_layout.addWidget(self.top_container)
        self.child_container = QWidget()
        self.child_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        if self.horizontal_layout:
            self.child_container_layout = QHBoxLayout()
        else:
            self.child_container_layout = QVBoxLayout()
        self.child_container_layout.setContentsMargins(0, 5, 0, 0)
        self.child_container_layout.setSpacing(5)
        self.child_container_layout.setAlignment(Qt.AlignTop)
        self.child_container.setLayout(self.child_container_layout)
        self.main_layout.addWidget(self.child_container)
        self.setLayout(self.main_layout)
        self.update(data_object)

    def add_child_widget(self, child_widget, add_to_layout=True):
        self.child_widgets.append(child_widget)
        if add_to_layout:
            self.child_container_layout.addWidget(child_widget)

    def set_horizontal_layout(self, horizontal):
        if self.horizontal_layout != horizontal:
            self.horizontal_layout = horizontal
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
            self.main_layout.replaceWidget(old_container, self.child_container)
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
        icons_width = self.icons_container.minimumSizeHint().width()
        total_needed = name_width + path_width + icons_width + 20
        if total_needed > available_width and self.path_label_in_top_row:
            self.top_layout.removeWidget(self.path_label)
            self.main_layout.insertWidget(1, self.path_label)
            self.path_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.path_label_in_top_row = False
            self.top_layout.setStretch(2, 0)
            self.icons_container.setMaximumWidth(icons_width)
        elif total_needed <= available_width and not self.path_label_in_top_row:
            self.main_layout.removeWidget(self.path_label)
            self.top_layout.insertWidget(1, self.path_label)
            self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.path_label_in_top_row = True
            self.top_layout.setStretch(1, 1)
            self.top_layout.setStretch(2, 0)
            self.icons_container.setMaximumWidth(icons_width)
        self.icons_container.setFixedWidth(icons_width)

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

    def clear_all(self):
        for child in self.child_widgets:
            child.clear_all()

    def _on_enabled_toggled(self, enabled):
        self.data_object.params['enabled'] = enabled
        self._update_stylesheet()

    def set_enabled_and_update(self, enabled):
        self._enabled = enabled
        self._update_enabled_icon()
        self._update_stylesheet()

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
        self._update_stylesheet()

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

    def capture_widget_state(self):
        state = {
            'children': [child.capture_widget_state() for child in self.child_widgets]
        }
        return state

    def restore_widget_state(self, state):
        if not state:
            return
        if 'children' in state:
            for i, child_state in enumerate(state['children']):
                if i < len(self.child_widgets):
                    self.child_widgets[i].restore_widget_state(child_state)


class ImgBaseWidget(BaseWidget):
    def __init__(self, data_object, min_height=40, dark_theme=False,
                 horizontal_layout=False, parent=None, horizontal_images=True):
        super().__init__(data_object, min_height, dark_theme, horizontal_layout, parent)
        self.horizontal_images = horizontal_images
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setWidgetResizable(True)
        self.image_scroll_area.setFrameShape(QFrame.NoFrame)
        self.image_views = []
        self.image_layout = None
        self.image_area_widget = None
        self._setup_image_area()

    def _setup_image_area(self):
        if self.horizontal_images:
            self.image_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.image_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.image_scroll_area.setStyleSheet(self.scroll_area_css('horizontal'))
            self.image_layout = QHBoxLayout()
        else:
            self.image_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.image_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.image_scroll_area.setStyleSheet(self.scroll_area_css('vertical'))
            self.image_layout = QVBoxLayout()
        self.image_area_widget = QWidget()
        self.image_layout.setSpacing(5)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setAlignment(Qt.AlignTop)
        self.image_area_widget.setLayout(self.image_layout)
        self.image_scroll_area.setWidget(self.image_area_widget)
        self.image_scroll_area.setVisible(False)

    def set_image_orientation(self, horizontal):
        if self.horizontal_images == horizontal:
            return
        self.horizontal_images = horizontal
        current_views = list(self.image_views)
        self.image_views.clear()
        self.image_area_widget = QWidget()
        if horizontal:
            self.image_layout = QHBoxLayout()
        else:
            self.image_layout = QVBoxLayout()
        self.image_layout.setSpacing(5)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setAlignment(Qt.AlignTop)
        for view in current_views:
            self.image_views.append(view)
            self.image_layout.addWidget(view)
        self.image_area_widget.setLayout(self.image_layout)
        if horizontal:
            self.image_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.image_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.image_scroll_area.setStyleSheet(self.scroll_area_css('horizontal'))
        else:
            self.image_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.image_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.image_scroll_area.setStyleSheet(self.scroll_area_css('vertical'))
        self.image_scroll_area.setWidget(self.image_area_widget)
        if current_views:
            self.image_scroll_area.setVisible(True)
            self._adjust_image_area()
        else:
            self.image_scroll_area.setVisible(False)
            self.image_scroll_area.setMinimumHeight(0)

    def clear_all(self):
        self.clear_images()
        super().clear_all()

    def clear_images(self):
        for view in self.image_views:
            if self.image_layout:
                self.image_layout.removeWidget(view)
            view.deleteLater()
        self.image_views.clear()
        self.image_scroll_area.setVisible(False)
        self.image_scroll_area.setMinimumHeight(0)

    def add_image_view(self, image_view):
        self.image_views.append(image_view)
        self.image_layout.addWidget(image_view)
        self.image_scroll_area.setVisible(True)
        self._adjust_image_area()
        QTimer.singleShot(0, self.image_area_widget.adjustSize)

    def _adjust_image_area(self):
        if not self.image_views:
            return
        if self.horizontal_images:
            self._adjust_horizontal_area()
        else:
            self._adjust_vertical_area()

    def _adjust_horizontal_area(self):
        max_height = max(view.sizeHint().height() for view in self.image_views)
        total_width = 0
        for view in self.image_views:
            total_width += view.sizeHint().width()
        total_width += self.image_layout.spacing() * (len(self.image_views) - 1)
        self.image_area_widget.setFixedWidth(total_width)
        self.image_area_widget.setFixedHeight(max_height)
        scrollbar = self.image_scroll_area.horizontalScrollBar()
        scrollbar_height = scrollbar.sizeHint().height() if scrollbar.maximum() > 0 else 0
        self.image_scroll_area.setMinimumHeight(max_height + scrollbar_height)

    def _adjust_vertical_area(self):
        total_height = sum(view.sizeHint().height() for view in self.image_views)
        total_height += self.image_layout.spacing() * (len(self.image_views) - 1)
        total_height += 10
        max_width = max(view.sizeHint().width() for view in self.image_views)
        self.image_area_widget.setFixedHeight(total_height)
        self.image_area_widget.setFixedWidth(max_width)
        self.image_scroll_area.setMinimumHeight(min(total_height, 200))

    def capture_widget_state(self):
        state = super().capture_widget_state()
        state['image_views'] = []
        for view in self.image_views:
            if hasattr(view, 'file_path'):
                view_state = {
                    'file_path': view.file_path,
                    'type': type(view).__name__,
                }
                if hasattr(view, 'app'):
                    view_state['app'] = view.app
                state['image_views'].append(view_state)
        return state

    def restore_widget_state(self, state):
        super().restore_widget_state(state)
        self.clear_images()
        for view_state in state.get('image_views', []):
            file_path = view_state.get('file_path')
            view_type = view_state.get('type', 'GuiImageView')
            if file_path and os.path.exists(file_path):
                if view_type == 'GuiPdfView':
                    image_view = GuiPdfView(file_path, self)
                elif view_type == 'GuiOpenApp':
                    app = view_state.get('app', '')
                    image_view = GuiOpenApp(app, file_path, self)
                else:
                    image_view = GuiImageView(file_path, self)
                self.add_image_view(image_view)
