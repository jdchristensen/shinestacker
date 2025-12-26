# pylint: disable=C0114, C0115, C0116, E0611, R0903
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QSizePolicy
from .base_widget import BaseWidget


class SubActionWidget(BaseWidget):
    MAX_SCROLL_HEIGHT = 200

    def __init__(self, data_object, dark_theme=False, parent=None):
        super().__init__(data_object, 35, dark_theme, parent)
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_layout.setSpacing(2)
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.image_scroll_area.setWidgetResizable(True)
        self.image_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_scroll_area.setMaximumHeight(self.MAX_SCROLL_HEIGHT)
        self.image_scroll_area.setFrameShape(QFrame.NoFrame)
        self.image_scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 6px;
                border: none;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #a0a0a0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #808080;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                width: 0px;
                height: 0px;
            }
        """)
        self.image_area_widget = QWidget()
        self.image_layout = QVBoxLayout(self.image_area_widget)
        self.image_layout.setSpacing(5)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setAlignment(Qt.AlignTop)
        self.image_scroll_area.setWidget(self.image_area_widget)
        self.image_scroll_area.setVisible(False)
        self.progress_layout.addWidget(self.image_scroll_area)
        self.layout().addWidget(self.progress_container)
        self.image_views = []

    def widget_type(self):
        return 'SubActionWidget'

    def add_image_view(self, image_view):
        self.image_views.append(image_view)
        self.image_layout.addWidget(image_view)
        self.image_scroll_area.setVisible(True)
        self._adjust_image_area_height()
        QTimer.singleShot(0, self.image_area_widget.adjustSize)

    def clear_images(self):
        for view in self.image_views:
            self.image_layout.removeWidget(view)
            view.deleteLater()
        self.image_views.clear()
        self.image_scroll_area.setVisible(False)

    def _adjust_image_area_height(self):
        if not self.image_views:
            return
        total_height = sum(view.sizeHint().height() for view in self.image_views)
        total_height += self.image_layout.spacing() * (len(self.image_views) - 1)
        total_height += 10
        max_width = max(view.sizeHint().width() for view in self.image_views) \
            if self.image_views else 0
        self.image_area_widget.setFixedHeight(total_height)
        self.image_area_widget.setFixedWidth(max_width)
        self.image_scroll_area.setMinimumHeight(min(total_height, self.MAX_SCROLL_HEIGHT))
