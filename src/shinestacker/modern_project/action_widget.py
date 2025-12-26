# pylint: disable=C0114, C0115, C0116, E0611, R0903
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QFrame, QSizePolicy
from .base_widget import BaseWidget
from .sub_action_widget import SubActionWidget
from .. gui.project_model import get_action_input_path, get_action_output_path
from .. gui.time_progress_bar import TimerProgressBar
from .. gui.processing_widget import MultiModuleStatusContainer


class ActionWidget(BaseWidget):
    def __init__(self, action, dark_theme=False, parent=None):
        super().__init__(action, 50, dark_theme, parent)
        in_path = get_action_input_path(action)[0]
        out_path = get_action_output_path(action)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i> → " \
            f"📂 <i>{self._format_path(out_path)}</i>"
        self._add_path_label(path_text)
        if hasattr(action, 'sub_actions') and action.sub_actions:
            subactions_container = QWidget()
            horizontal_layout = QHBoxLayout(subactions_container)
            horizontal_layout.setContentsMargins(0, 0, 0, 0)
            horizontal_layout.setSpacing(2)
        for sub_action in action.sub_actions:
            sub_action_widget = SubActionWidget(sub_action, dark_theme)
            horizontal_layout.addWidget(sub_action_widget)
            self.add_child_widget(sub_action_widget, add_to_layout=False)
            self.layout().addWidget(subactions_container)
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_layout.setSpacing(2)
        self.progress_bar = TimerProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_layout.addWidget(self.progress_bar)
        self.frames_status_box = MultiModuleStatusContainer(classic_view=False)
        self.frames_status_box.setVisible(False)
        self.frames_status_box.content_size_changed.connect(self._update_container_size)
        self.progress_layout.addWidget(self.frames_status_box)
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.image_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_scroll_area.setWidgetResizable(True)
        self.image_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.image_scroll_area.setFrameShape(QFrame.NoFrame)
        self.image_area_widget = QWidget()
        self.image_layout = QHBoxLayout(self.image_area_widget)
        self.image_layout.setSpacing(5)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setAlignment(Qt.AlignLeft)
        self.image_scroll_area.setWidget(self.image_area_widget)
        self.image_scroll_area.setVisible(False)
        self.progress_layout.addWidget(self.image_scroll_area)
        self.layout().addWidget(self.progress_container)
        self._has_frames_content = False
        self.image_views = []

    def _update_container_size(self):
        pass

    def widget_type(self):
        return 'ActionWidget'

    def update(self, data_object):
        super().update(data_object)
        in_path = get_action_input_path(data_object)[0]
        out_path = get_action_output_path(data_object)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i> → " \
            f"📂 <i>{self._format_path(out_path)}</i>"
        self._add_path_label(path_text)

    def show_progress(self, total_steps, label=""):
        self.progress_bar.setVisible(True)
        self.progress_bar.start(total_steps)
        if label:
            self.progress_bar.setFormat(f"{label} - %p%")
        if self._has_frames_content:
            self.frames_status_box.setVisible(True)

    def update_progress(self, current_step):
        self.progress_bar.setValue(current_step)

    def complete_progress(self):
        self.progress_bar.stop()
        self.progress_bar.setFormat("✓ " + self.progress_bar.format())
        QTimer.singleShot(2000, self.hide_progress)

    def hide_progress(self):
        self.progress_bar.setVisible(False)
        if not self._has_frames_content:
            self.frames_status_box.setVisible(False)

    def add_status_box(self, module_name):
        self.frames_status_box.setVisible(True)
        self.frames_status_box.add_module(module_name)
        self._has_frames_content = True

    def add_frame(self, module_name, filename, total_actions):
        self.frames_status_box.setVisible(True)
        self.frames_status_box.add_frame(module_name, filename, total_actions)
        self._has_frames_content = True

    def update_frame_status(self, module_name, filename, status_id):
        self.frames_status_box.update_frame_status(module_name, filename, status_id)

    def set_frame_total_actions(self, module_name, filename, total_actions):
        self.frames_status_box.set_frame_total_actions(module_name, filename, total_actions)

    def clear_frames_status(self):
        self.frames_status_box.clear()
        self.frames_status_box.setVisible(False)
        self._has_frames_content = False

    def add_image_view(self, image_view):
        self.image_views.append(image_view)
        self.image_layout.addWidget(image_view)
        self.image_scroll_area.setVisible(True)
        self._adjust_image_area_height()
        QTimer.singleShot(0, lambda: self.image_scroll_area.horizontalScrollBar().setValue(
            self.image_scroll_area.horizontalScrollBar().maximum()))

    def clear_images(self):
        for view in self.image_views:
            self.image_layout.removeWidget(view)
            view.deleteLater()
        self.image_views.clear()
        self.image_scroll_area.setVisible(False)
        self.image_scroll_area.setMinimumHeight(0)

    def _adjust_image_area_height(self):
        if not self.image_views:
            return
        max_height = max(view.sizeHint().height() for view in self.image_views)
        self.image_scroll_area.setMinimumHeight(max_height + 10)
