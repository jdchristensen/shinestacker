# pylint: disable=C0103, C0114, C0115, C0116, E0611, R0903, R0915, R0914, R0917, R0913, R0902
import os
import math
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QWidget, QGridLayout, QScrollArea, QLabel,
                               QSizePolicy, QVBoxLayout)
from .colors import ColorPalette


class MultiModuleStatusContainer(QWidget):
    contentSizeChanged = Signal()

    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.container_widget = QWidget()
        self.layout = QVBoxLayout(self.container_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.scroll_area.setWidget(self.container_widget)
        main_layout.addWidget(self.scroll_area)
        self.status_widgets = []
        self.setMinimumHeight(0)
        self.setMaximumHeight(400)
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.contentSizeChanged.emit)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(100)

    def add_module(self, module_name):
        label = QLabel(module_name)
        label.setStyleSheet("QLabel { font-weight: bold; margin: 0px; padding: 0px; }")
        label.setContentsMargins(0, 0, 0, 0)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.layout.addWidget(label)
        status_widget = PreprocessingStatusWidget()
        self.layout.addWidget(status_widget)
        self.status_widgets.append(status_widget)
        QTimer.singleShot(10, self.contentSizeChanged.emit)
        return len(self.status_widgets) - 1

    def add_frame(self, filename, total_actions, idx=-1):
        if self.status_widgets:
            self.status_widgets[idx].add_frame(filename, total_actions)
            QTimer.singleShot(10, self.contentSizeChanged.emit)

    def update_frame_status(self, frame_id, status_id, idx=-1):
        if self.status_widgets:
            self.status_widgets[idx].update_frame_status(frame_id, status_id)

    def get_content_height(self):
        return self.container_widget.sizeHint().height()


class FrameStatusBox(QWidget):
    def __init__(self, filename, frame_id, total_actions):
        super().__init__()
        self.filename = filename
        self.total_actions = total_actions
        self.frame_id = frame_id
        self.status_id = 0
        self.border_color = QColor(100, 100, 100)
        self.fill_color = QColor(200, 200, 200)
        self.custom_tooltip = None
        self.update_tooltip()
        self.setMinimumSize(20, 15)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

    def update_status(self, status_id):
        pending_color = (200, 200, 200)
        init_color = (255, 255, 255)
        completed_color = (76, 175, 80)
        failed_color = (244, 67, 54)
        self.status_id = status_id
        if status_id == 0:
            self.fill_color = QColor(*pending_color)
        elif status_id == 1000:
            self.fill_color = QColor(*completed_color)
        elif status_id == 1001:
            self.fill_color = QColor(*failed_color)
        else:
            progress = status_id / 10.0
            r = int(init_color[0] * (1 - progress) + completed_color[0] * progress)
            g = int(init_color[1] * (1 - progress) + completed_color[1] * progress)
            b = int(init_color[2] * (1 - progress) + completed_color[2] * progress)
            self.fill_color = QColor(r, g, b)
        self.update_tooltip()
        self.update()

    def update_tooltip(self):
        if self.status_id == 0:
            status_text = "Pending"
        elif self.status_id == 1000:
            status_text = "Completed"
        elif self.status_id == 1001:
            status_text = "Failed"
        else:
            status_text = f"Processing step {self.status_id}"
        self.tooltip_text = f"File: {os.path.basename(self.filename)}\nStatus: {status_text}"

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = 1
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.fillRect(rect, self.fill_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(rect)

    def enterEvent(self, _event):
        if not self.custom_tooltip:
            self.custom_tooltip = QLabel(self.tooltip_text, self.window())
            self.custom_tooltip.setStyleSheet(f"""
                QLabel {{
                    background-color: #FFFFCC;
                    color: #{ColorPalette.DARK_BLUE.hex()};
                    border: 1px solid black;
                    padding: 2px;
                }}
            """)
            self.custom_tooltip.adjustSize()
        global_pos = self.mapToGlobal(self.rect().topRight())
        parent_pos = self.window().mapFromGlobal(global_pos)
        self.custom_tooltip.move(parent_pos.x() + 2, parent_pos.y())
        self.custom_tooltip.show()

    def leaveEvent(self, _event):
        if self.custom_tooltip:
            self.custom_tooltip.hide()


class PreprocessingStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.frame_widgets = []
        self.MIN_BOX_WIDTH = 30
        self.MAX_BOX_WIDTH = 80
        self.ASPECT_RATIO = 3.0 / 4.0
        self.current_box_width = self.MAX_BOX_WIDTH
        self.current_box_height = int(self.current_box_width * self.ASPECT_RATIO)

    def add_frame(self, filename, total_actions):
        frame_id = len(self.frame_widgets)
        frame_widget = FrameStatusBox(filename, frame_id, total_actions)
        self.frame_widgets.append(frame_widget)
        self._update_layout()

    def update_frame_status(self, frame_id, status_id):
        if 0 <= frame_id < len(self.frame_widgets):
            self.frame_widgets[frame_id].update_status(status_id)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_layout()

    def _calculate_optimal_box_width(self):
        if not self.frame_widgets:
            return self.MAX_BOX_WIDTH
        available_width = self.width() - 10
        spacing = self.grid_layout.spacing()
        max_possible_cols = max(1, available_width // (self.MIN_BOX_WIDTH + spacing))
        needed_cols = min(len(self.frame_widgets), max_possible_cols)
        calculated_width = (available_width - (needed_cols - 1) * spacing) // needed_cols
        return max(self.MIN_BOX_WIDTH, min(self.MAX_BOX_WIDTH, calculated_width))

    def _update_layout(self):
        if not self.frame_widgets:
            return
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                self.grid_layout.removeWidget(widget)
        self.current_box_width = self._calculate_optimal_box_width()
        self.current_box_height = int(self.current_box_width * self.ASPECT_RATIO)
        available_width = self.width() - 10
        spacing = self.grid_layout.spacing()
        max_cols = max(1, available_width // (self.current_box_width + spacing))
        num_cols = min(len(self.frame_widgets), max_cols)
        for widget in self.frame_widgets:
            widget.setFixedSize(self.current_box_width, self.current_box_height)
        for i, widget in enumerate(self.frame_widgets):
            row = i // num_cols
            col = i % num_cols
            self.grid_layout.addWidget(widget, row, col)
        num_rows = math.ceil(len(self.frame_widgets) / num_cols) if num_cols > 0 else 0
        total_height = num_rows * (self.current_box_height + spacing)
        self.setMinimumHeight(total_height + 10)
