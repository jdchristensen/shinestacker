from PySide6.QtWidgets import (QWidget, QGridLayout, QScrollArea, 
                               QSizePolicy, QVBoxLayout)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPainter, QPen
import math
import os

class FrameStatusBox(QWidget):
    def __init__(self, filename, frame_id):
        super().__init__()
        self.filename = filename
        self.frame_id = frame_id
        self.status_id = 0
        self.border_color = QColor(100, 100, 100)
        self.fill_color = QColor(200, 200, 200)
        self.setMinimumSize(20, 15)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setToolTip(f"File: {os.path.basename(filename)}\nStatus: Pending")
        
    def update_status(self, status_id):
        self.status_id = status_id
        if status_id == 0:
            self.fill_color = QColor(200, 200, 200)
        elif status_id == 1000:
            self.fill_color = QColor(76, 175, 80)
        elif status_id == 1001:
            self.fill_color = QColor(244, 67, 54)
        else:
            progress = status_id / 10.0
            self.fill_color = QColor(
                int(200 + (76 - 200) * progress),
                int(200 + (175 - 200) * progress),
                int(200 + (80 - 200) * progress)
            )
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
        self.setToolTip(f"File: {os.path.basename(self.filename)}\nStatus: {status_text}")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = 1
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.fillRect(rect, self.fill_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(rect)


class PreprocessingStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setMaximumHeight(400)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_area.setWidget(self.grid_container)
        self.main_layout.addWidget(self.scroll_area)
        self.frame_widgets = []
        self.MIN_BOX_WIDTH = 30
        self.MAX_BOX_WIDTH = 80
        self.ASPECT_RATIO = 3.0 / 4.0
        self.current_box_width = self.MAX_BOX_WIDTH
        self.current_box_height = int(self.current_box_width * self.ASPECT_RATIO)
        self.setFixedHeight(0)
        
    def add_frame(self, filename, total_actions=2):
        frame_id = len(self.frame_widgets)
        frame_widget = FrameStatusBox(filename, frame_id)
        frame_widget.total_actions = total_actions
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
        num_frames = len(self.frame_widgets)
        available_width = self.scroll_area.viewport().width() - 10
        spacing = self.grid_layout.spacing()
        max_possible_cols = max(1, available_width // (self.MIN_BOX_WIDTH + spacing))
        needed_cols = min(num_frames, max_possible_cols)
        calculated_width = (available_width - (needed_cols - 1) * spacing) // needed_cols
        return max(self.MIN_BOX_WIDTH, min(self.MAX_BOX_WIDTH, calculated_width))

    def _update_layout(self):
        if not self.frame_widgets:
            self.setFixedHeight(0)
            return
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.current_box_width = self._calculate_optimal_box_width()
        self.current_box_height = int(self.current_box_width * self.ASPECT_RATIO)
        available_width = self.scroll_area.viewport().width() - 10
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
        total_width = num_cols * (self.current_box_width + spacing)
        total_height = num_rows * (self.current_box_height + spacing)
        self.grid_container.setMinimumSize(total_width, total_height)
        needed_height = total_height + 10
        self.setFixedHeight(min(needed_height, 400))
