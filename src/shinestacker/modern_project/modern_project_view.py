# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=R1716, C0302, R0911, R0903
import os
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea, QDialog, QMessageBox
from .. config.constants import constants
from .. algorithms.utils import extension_supported, extension_pdf
from .. gui.project_model import ActionConfig
from .. gui.project_view import ProjectView
from .. gui.gui_logging import QTextEditLogger
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.run_worker import JobLogWorker, ProjectLogWorker
from .. gui.gui_images import GuiPdfView, GuiImageView, GuiOpenApp
from .job_widget import JobWidget
from .selection_state import SelectionState
from .progress_mapper import ProgressMapper
from .element_operations import ElementOperations


class SignalConnector:
    @staticmethod
    def connect_worker_signals(worker, view):
        for attr_name in dir(worker):
            if attr_name.endswith('_signal'):
                signal = getattr(worker, attr_name)
                handler_name = f'handle_{attr_name[:-7]}'  # Remove '_signal'
                handler = getattr(view, handler_name, None)
                if handler and callable(handler):
                    signal.connect(handler, Qt.ConnectionType.UniqueConnection)


class ModernProjectView(ProjectView):
    update_delete_action_state_requested = Signal()
    show_status_message_requested = Signal(str, int)
    enable_sub_actions_requested = Signal(bool)

    def __init__(self, project_holder, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, dark_theme, parent)
        self.job_widgets = []
        self.scroll_area = None
        self.scroll_content = None
        self.project_layout = None
        self.selected_widget = None
        self.selection_state = SelectionState()
        self.show_status_message = None
        self._worker = None
        self.progress_mapper = ProgressMapper()
        self.element_ops = ElementOperations(project_holder)
        self._setup_ui()
        self.change_theme(dark_theme)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFocusPolicy(Qt.NoFocus)
        self.scroll_content = QWidget()
        self.scroll_content.setFocusPolicy(Qt.NoFocus)
        self.scroll_content.setContentsMargins(2, 2, 2, 2)
        self.project_layout = QVBoxLayout(self.scroll_content)
        self.project_layout.setSpacing(2)
        self.project_layout.setContentsMargins(2, 2, 2, 2)
        self.project_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        main_splitter.addWidget(self.scroll_area)
        self.console_area = QTextEditLogger(self)
        self.add_gui_logger(self.console_area)
        console_layout = QVBoxLayout(self.console_area)
        self.console_area.text_edit.setFocusPolicy(Qt.ClickFocus)
        self.console_area.text_edit.installEventFilter(self)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.addWidget(self.console_area.text_edit)
        main_splitter.addWidget(self.console_area)
        main_splitter.setSizes([600, 200])
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
        ico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "gui", "ico", "shinestacker.png")
        self.console_area.handle_html_message(
            f"<img width=100 src='{ico_path}'><hr><br>")

    def connect_signals(self, update_delete_action_state, show_status_message, enable_sub_actions):
        self.update_delete_action_state_requested.connect(update_delete_action_state)
        self.show_status_message_requested.connect(show_status_message)
        self.enable_sub_actions_requested.connect(enable_sub_actions)

    # pylint: disable=C0103
    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()

    def eventFilter(self, obj, event):
        if obj == self.console_area.text_edit and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
                self.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if not self.job_widgets:
            return
        key = event.key()
        if key == Qt.Key_Up:
            self._select_previous_widget()
            event.accept()
        elif key == Qt.Key_Down:
            self._select_next_widget()
            event.accept()
        elif key == Qt.Key_Left:
            self._select_previous_widget()
            event.accept()
        elif key == Qt.Key_Right:
            self._select_next_widget()
            event.accept()
        elif key == Qt.Key_Home:
            self._select_first_job()
            event.accept()
        elif key == Qt.Key_End:
            self._select_last_job()
            event.accept()
        elif key in [Qt.Key_Return, Qt.Key_Enter]:
            if self.selection_state.is_job_selected():
                self._on_job_double_clicked(self.selection_state.job_index)
            elif self.selection_state.is_action_selected():
                self._on_action_double_clicked(
                    self.selection_state.job_index, self.selection_state.action_index)
            elif self.selection_state.is_subaction_selected():
                self._on_subaction_double_clicked(
                    self.selection_state.job_index, self.selection_state.action_index,
                    self.selection_state.subaction_index)
            event.accept()
        elif key == Qt.Key_Tab:
            super().keyPressEvent(event)
        elif key == Qt.Key_Backtab:
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        pos = self.mapFromGlobal(QCursor.pos())
        widget = self.childAt(pos)
        current_action = None
        if widget:
            while widget and widget != self:
                if hasattr(widget, 'data_object'):
                    current_action = widget.data_object
                    break
                widget = widget.parentWidget()
        if not current_action and self.selected_widget:
            if hasattr(self.selected_widget, 'data_object'):
                current_action = self.selected_widget.data_object
        if current_action:
            menu = self.create_common_context_menu(current_action)
            menu.exec(event.globalPos())
    # pylint: enable=C0103

    def has_selection(self):
        return self.selection_state.is_valid()

    def has_selected_sub_action(self):
        if self.selection_state.is_subaction_selected():
            return True
        if self.selection_state.is_action_selected() and self.selected_widget is not None:
            return self.selected_widget.data_object.type_name == constants.ACTION_COMBO
        return False

    def _build_progress_mapping(self, job_indices=None):
        self.progress_mapper.build_mapping(self.project(), job_indices)

    def _find_action_widget(self, job_idx, action_idx, subaction_idx=-1):
        if self.is_valid_job_index(job_idx):
            job_widget = self.job_widgets[job_idx]
            if 0 <= action_idx < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_idx]
                if subaction_idx == -1:
                    return action_widget
                if 0 <= subaction_idx < action_widget.num_child_widgets():
                    return action_widget.child_widgets[subaction_idx]
        return None

    @Slot(int, str, str)
    def handle_step_counts(self, _run_id, module_name, total_steps):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'show_progress'):
                widget.show_progress(total_steps, os.path.basename(module_name))

    @Slot(int, str, str)
    def handle_after_step(self, _run_id, module_name, current_step):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'update_progress'):
                widget.update_progress(current_step)

    @Slot(int, str)
    def handle_end_steps(self, _run_id, module_name):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'complete_progress'):
                widget.complete_progress()

    @Slot(int, str)
    def handle_begin_steps(self, _run_id, module_name):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'progress_bar'):
                if not widget.progress_bar.isVisible():
                    widget.progress_bar.start(1)
                    widget.progress_bar.setVisible(True)

    @Slot(int, str)
    def handle_before_action(self, _run_id, name):
        indices = self.progress_mapper.get_indices(name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'progress_bar'):
                widget.progress_bar.set_running_style()

    @Slot(int, str)
    def handle_after_action(self, _run_id, name):
        indices = self.progress_mapper.get_indices(name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'progress_bar'):
                widget.progress_bar.set_done_style()

    @Slot(int, str)
    def handle_run_stopped(self, _run_id, name):
        indices = self.progress_mapper.get_indices(name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'progress_bar'):
                widget.progress_bar.set_stopped_style()
        self._handle_end_of_run()

    @Slot(int, str)
    def handle_run_failed(self, _run_id, name):
        indices = self.progress_mapper.get_indices(name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'progress_bar'):
                widget.progress_bar.set_failed_style()
        self._handle_end_of_run()

    @Slot(str)
    def handle_add_status_box(self, module_name):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'add_status_box'):
                widget.add_status_box(module_name)

    @Slot(int, str, str, int)
    def handle_add_frame(self, module_name, filename, total_actions):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'add_frame'):
                widget.add_frame(module_name, filename, total_actions)

    @Slot(int, str, str, int)
    def handle_update_frame_status(self, module_name, filename, status_id):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'update_frame_status'):
                widget.update_frame_status(module_name, filename, status_id)

    @Slot(int, str, str, int)
    def handle_set_total_actions(self, module_name, filename, total_actions):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget and hasattr(widget, 'set_frame_total_actions'):
                widget.set_frame_total_actions(module_name, filename, total_actions)

    @Slot(int, str, str, str)
    def handle_save_plot(self, _run_id, module_name, _caption, path):
        indices = self.progress_mapper.get_indices(module_name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget:
                if extension_pdf(path):
                    image_view = GuiPdfView(path, widget, fixed_height=indices[2] == -1)
                elif extension_supported(path):
                    image_view = GuiImageView(path, widget, fixed_height=indices[2] == -1)
                else:
                    raise RuntimeError(f"Can't visualize file type {os.path.splitext(path)[1]}.")
                widget.add_image_view(image_view)

    @Slot(int, str, str, str)
    def handle_open_app(self, _run_id, name, app, path):
        indices = self.progress_mapper.get_indices(name)
        if indices:
            widget = self._find_action_widget(*indices)
            if widget:
                image_view = GuiOpenApp(app, path, widget, fixed_height=indices[2] == -1)
                widget.add_image_view(image_view)

    def _handle_end_of_run(self):
        self.menu_manager.stop_action.setEnabled(False)
        self.menu_manager.run_job_action.setEnabled(True)
        if self.num_project_jobs() > 1:
            self.menu_manager.run_all_jobs_action.setEnabled(True)

    def get_current_selected_action(self):
        if not self.selection_state.is_valid():
            return None
        job_idx = self.selection_state.job_index
        action_idx = self.selection_state.action_index
        subaction_idx = self.selection_state.subaction_index
        if not self.is_valid_job_index(job_idx):
            return None
        job = self.project().jobs[job_idx]
        if self.selection_state.is_job_selected():
            return job
        if not 0 <= action_idx < len(job.sub_actions):
            return None
        action = job.sub_actions[action_idx]
        if self.selection_state.is_action_selected():
            return action
        if 0 <= subaction_idx < len(action.sub_actions):
            return action.sub_actions[subaction_idx]
        return None

    def _select_next_widget(self):
        if self.selection_state.widget_type == 'job':
            if self._has_actions_in_job(self.selection_state.job_index):
                self._select_first_action_in_job(self.selection_state.job_index)
        elif self.selection_state.widget_type == 'action':
            if self._has_subactions_in_action(
                    self.selection_state.job_index, self.selection_state.action_index):
                self._select_first_subaction_in_action(
                    self.selection_state.job_index, self.selection_state.action_index)
            else:
                self._select_next_action_or_job()
        elif self.selection_state.widget_type == 'subaction':
            self._select_next_subaction_or_action_or_job()

    def _select_previous_widget(self):
        if self.selection_state.widget_type == 'subaction':
            if self.selection_state.subaction_index > 0:
                self._select_subaction(
                    self.selection_state.job_index, self.selection_state.action_index,
                    self.selection_state.subaction_index - 1
                )
            else:
                self._select_action(
                    self.selection_state.job_index, self.selection_state.action_index)
        elif self.selection_state.widget_type == 'action':
            if self.selection_state.action_index > 0:
                prev_action_index = self.selection_state.action_index - 1
                job_widget = self.job_widgets[self.selection_state.job_index]
                prev_action_widget = job_widget.child_widgets[prev_action_index]
                if prev_action_widget.num_child_widgets() > 0:
                    last_subaction_index = prev_action_widget.num_child_widgets() - 1
                    self._select_subaction(
                        self.selection_state.job_index, prev_action_index, last_subaction_index
                    )
                else:
                    self._select_action(self.selection_state.job_index, prev_action_index)
            else:
                self._select_job(self.selection_state.job_index)
        elif self.selection_state.widget_type == 'job':
            if self.selection_state.job_index > 0:
                self._select_job(self.selection_state.job_index - 1)

    def _select_job(self, job_index):
        if self.is_valid_job_index(job_index):
            job_widget = self.job_widgets[job_index]
            self._on_widget_clicked(job_widget, 'job', job_index)
            self._ensure_selected_visible()

    def _select_action(self, job_index, action_index):
        if self.is_valid_job_index(job_index):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                self._on_widget_clicked(action_widget, 'action', job_index, action_index)
                self._ensure_selected_visible()

    def _select_subaction(self, job_index, action_index, subaction_index):
        if self.is_valid_job_index(job_index):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                if 0 <= subaction_index < action_widget.num_child_widgets():
                    subaction_widget = action_widget.child_widgets[subaction_index]
                    self._on_widget_clicked(
                        subaction_widget, 'subaction', job_index, action_index, subaction_index)
                    self._ensure_selected_visible()

    def _select_first_job(self):
        if self.job_widgets:
            self._select_job(0)

    def _select_last_job(self):
        if self.job_widgets:
            self._select_job(len(self.job_widgets) - 1)

    def _select_first_action_in_job(self, job_index):
        self._select_action(job_index, 0)

    def _select_first_subaction_in_action(self, job_index, action_index):
        self._select_subaction(job_index, action_index, 0)

    def _has_actions_in_job(self, job_index):
        return self.job_widgets[job_index].num_child_widgets() > 0

    def _has_subactions_in_action(self, job_index, action_index):
        job_widget = self.job_widgets[job_index]
        action_widget = job_widget.child_widgets[action_index]
        return action_widget.num_child_widgets() > 0

    def _select_next_action_or_job(self):
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        if self.is_valid_job_index(job_index):
            job_widget = self.job_widgets[job_index]
            next_action_index = action_index + 1
            if next_action_index < job_widget.num_child_widgets():
                self._select_action(job_index, next_action_index)
            else:
                self._select_next_job()

    def _select_next_subaction_or_action_or_job(self):
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        subaction_index = self.selection_state.subaction_index
        if self.is_valid_job_index(job_index):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                next_subaction_index = subaction_index + 1
                if next_subaction_index < action_widget.num_child_widgets():
                    self._select_subaction(job_index, action_index, next_subaction_index)
                else:
                    self._select_next_action_or_job()

    def _select_previous_job_last_widget(self):
        prev_job_index = self.selection_state.job_index - 1
        if prev_job_index >= 0:
            prev_job_widget = self.job_widgets[prev_job_index]
            if prev_job_widget.num_child_widgets() > 0:
                last_action_index = prev_job_widget.num_child_widgets() - 1
                last_action_widget = prev_job_widget.child_widgets[last_action_index]
                if last_action_widget.num_child_widgets() > 0:
                    last_subaction_index = last_action_widget.num_child_widgets() - 1
                    self._select_subaction(prev_job_index, last_action_index, last_subaction_index)
                else:
                    self._select_action(prev_job_index, last_action_index)
            else:
                self._select_job(prev_job_index)

    def _select_next_job(self):
        if not self.job_widgets:
            return
        new_index = self.selection_state.job_index + 1
        if new_index < len(self.job_widgets):
            self._select_job(new_index)

    def _select_previous_job(self):
        if not self.job_widgets:
            return
        new_index = self.selection_state.job_index - 1
        if new_index >= 0:
            self._select_job(new_index)

    def _reset_selection(self):
        self.selected_widget = None
        self.selection_state.reset()

    def clear_job_list(self):
        for widget in self.job_widgets:
            widget.clicked.disconnect()
            widget.deleteLater()
        self.job_widgets.clear()
        if self.project_layout:
            while self.project_layout.count():
                item = self.project_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        self.selection_state.job_index = 0

    def clear_project(self):
        self.clear_job_list()
        self._reset_selection()
        self.update_delete_action_state_requested.emit()

    def add_job_widget(self, job):
        job_widget = JobWidget(job, self.dark_theme)
        job_widget.setFocusPolicy(Qt.NoFocus)
        job_index = len(self.job_widgets)
        job_widget.clicked.connect(
            lambda checked=False, w=job_widget, idx=job_index:
                self._on_widget_clicked(w, 'job', idx)
        )
        job_widget.double_clicked.connect(
            lambda checked=False, idx=job_index: self._on_job_double_clicked(idx)
        )
        self.job_widgets.append(job_widget)
        self.project_layout.addWidget(job_widget)
        for action_idx, action_widget in enumerate(job_widget.child_widgets):
            def make_action_click_handler(j_idx, a_idx, widget):
                def handler():
                    self._on_widget_clicked(widget, 'action', j_idx, a_idx)
                return handler
            action_widget.clicked.connect(
                make_action_click_handler(job_index, action_idx, action_widget))
            action_widget.double_clicked.connect(
                lambda checked=False, j_idx=job_index, a_idx=action_idx:
                self._on_action_double_clicked(j_idx, a_idx)
            )
            for subaction_idx, subaction_widget in enumerate(action_widget.child_widgets):
                def make_subaction_click_handler(j_idx, a_idx, s_idx, widget):
                    def handler():
                        self._on_widget_clicked(widget, 'subaction', j_idx, a_idx, s_idx)
                    return handler
                subaction_widget.clicked.connect(
                    make_subaction_click_handler(
                        job_index, action_idx, subaction_idx, subaction_widget)
                )
                subaction_widget.double_clicked.connect(
                    lambda checked=False, j_idx=job_index, a_idx=action_idx, s_idx=subaction_idx:
                    self._on_subaction_double_clicked(j_idx, a_idx, s_idx)
                )
        if len(self.job_widgets) == 1:
            self._on_widget_clicked(job_widget, 'job', 0)

    def _on_widget_clicked(self, widget, widget_type, job_index, action_index=None,
                           subaction_index=None):
        if self.selected_widget:
            self.selected_widget.set_selected(False)
        widget.set_selected(True)
        self.selected_widget = widget
        if widget_type == 'job':
            self.selection_state.set_job(job_index)
        elif widget_type == 'action':
            self.selection_state.set_action(job_index, action_index)
        elif widget_type == 'subaction':
            self.selection_state.set_subaction(job_index, action_index, subaction_index)
        self.update_delete_action_state_requested.emit()
        self.setFocus()

    def _on_job_double_clicked(self, job_index):
        job_widget = self.job_widgets[job_index]
        self._on_widget_clicked(job_widget, 'job', job_index)
        job = self.project_job(job_index)
        if job:
            self.action_dialog = ActionConfigDialog(
                job, self.current_file_directory(), self.parent())
            if self.action_dialog.exec() == QDialog.Accepted:
                self._update_job_widget(job_index, job)

    def _on_action_double_clicked(self, job_index, action_index):
        job_widget = self.job_widgets[job_index]
        action_widget = job_widget.child_widgets[action_index]
        self._on_widget_clicked(action_widget, 'action', job_index, action_index)
        job = self.project_job(job_index)
        action = job.sub_actions[action_index] if hasattr(job, 'sub_actions') else None
        if action:
            self.enable_sub_actions_requested.emit(action.type_name == constants.ACTION_COMBO)
            self.action_dialog = ActionConfigDialog(
                action, self.current_file_directory(), self.parent())
            if self.action_dialog.exec() == QDialog.Accepted:
                self._update_action_widget(job_index, action_index, action)

    def _on_subaction_double_clicked(self, job_index, action_index, subaction_index):
        job_widget = self.job_widgets[job_index]
        action_widget = job_widget.child_widgets[action_index]
        subaction_widget = action_widget.child_widgets[subaction_index]
        self._on_widget_clicked(
            subaction_widget, 'subaction', job_index, action_index, subaction_index)
        job = self.project_job(job_index)
        action = job.sub_actions[action_index] if hasattr(job, 'sub_actions') else None
        subaction = action.sub_actions[subaction_index] \
            if action and hasattr(action, 'sub_actions') else None
        if subaction:
            self.action_dialog = ActionConfigDialog(
                subaction, self.current_file_directory(), self.parent())
            if self.action_dialog.exec() == QDialog.Accepted:
                self._update_subaction_widget(job_index, action_index, subaction_index, subaction)

    def _update_job_widget(self, job_index, job):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            job_widget.update(job)

    def _update_action_widget(self, job_index, action_index, action):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                action_widget.update(action)

    def _update_subaction_widget(self, job_index, action_index, subaction_index, subaction):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                if 0 <= subaction_index < action_widget.num_child_widgets():
                    subaction_widget = action_widget.child_widgets[subaction_index]
                    subaction_widget.update(subaction)

    def _select_job_widget(self, widget):
        for i, job_widget in enumerate(self.job_widgets):
            if job_widget == widget:
                job_widget.set_selected(True)
                self.selection_state.job_index = i
            else:
                job_widget.set_selected(False)

    def delete_element(self, confirm=True):
        if self.selection_state.is_job_selected():
            return self._delete_job(self.selection_state.job_index, confirm)
        if self.selection_state.is_action_selected():
            return self._delete_action(
                self.selection_state.job_index, self.selection_state.action_index, confirm)
        if self.selection_state.is_subaction_selected():
            return self._delete_subaction(
                self.selection_state.job_index, self.selection_state.action_index,
                self.selection_state.subaction_index, confirm)
        return None

    def _delete_job(self, job_index, confirm=True):
        if confirm:
            if 0 <= job_index < len(self.project().jobs):
                job = self.project().jobs[job_index]
                reply = QMessageBox.question(
                    self.parent(), "Confirm Delete",
                    f"Are you sure you want to delete job '{job.params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return None
            else:
                return None
        deleted_job = self.element_ops.delete_job(job_index)
        if deleted_job:
            self.mark_as_modified(True, "Delete Job")
            self._select_previous_widget()
            self.refresh_ui()
        return deleted_job

    def _delete_action(self, job_index, action_index, confirm=True):
        if confirm:
            if 0 <= job_index < len(self.project().jobs):
                job = self.project().jobs[job_index]
                if 0 <= action_index < len(job.sub_actions):
                    action = job.sub_actions[action_index]
                    reply = QMessageBox.question(
                        self.parent(), "Confirm Delete",
                        "Are you sure you want to delete "
                        f"action '{action.params.get('name', '')}'?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return None
            else:
                return None
        deleted_action = self.element_ops.delete_action(job_index, action_index)
        if deleted_action:
            self.mark_as_modified(True, "Delete Action")
            self._select_previous_widget()
            self.refresh_ui()
        return deleted_action

    def _delete_subaction(self, job_index, action_index, subaction_index, confirm=True):
        if confirm:
            if 0 <= job_index < len(self.project().jobs):
                job = self.project().jobs[job_index]
                if 0 <= action_index < len(job.sub_actions):
                    action = job.sub_actions[action_index]
                    if 0 <= subaction_index < len(action.sub_actions):
                        subaction = action.sub_actions[subaction_index]
                        reply = QMessageBox.question(
                            self.parent(), "Confirm Delete",
                            "Are you sure you want to delete "
                            f"sub-action '{subaction.params.get('name', '')}'?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if reply != QMessageBox.Yes:
                            return None
            else:
                return None
        deleted_subaction = self.element_ops.delete_subaction(
            job_index, action_index, subaction_index)
        if deleted_subaction:
            self.mark_as_modified(True, "Delete Sub-action")
            self._select_previous_widget()
            self.refresh_ui()
        return deleted_subaction

    def copy_job(self):
        job_clone = self.element_ops.copy_job(self.selection_state.job_index)
        if job_clone:
            self.set_copy_buffer(job_clone)

    def copy_action(self):
        if not self.selection_state.is_action_selected():
            return
        job_idx, action_idx, _ = self.selection_state.to_tuple()
        job_clone = self.element_ops.copy_action(job_idx, action_idx)
        if job_clone:
            self.set_copy_buffer(job_clone)

    def copy_subaction(self):
        if not self.selection_state.is_subaction_selected():
            return
        job_idx, action_idx, subaction_idx = self.selection_state.to_tuple()
        job_clone = self.element_ops.copy_subaction(job_idx, action_idx, subaction_idx)
        if job_clone:
            self.set_copy_buffer(job_clone)

    def copy_element(self):
        if self.selection_state.is_job_selected():
            self.copy_job()
        elif self.selection_state.is_action_selected():
            self.copy_action()
        elif self.selection_state.is_subaction_selected():
            self.copy_subaction()

    def paste_job(self):
        if not self.has_copy_buffer():
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name != constants.ACTION_JOB:
            if len(self.project().jobs) == 0:
                return
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return
            current_job = self.project().jobs[self.selection_state.job_index]
            new_action_index = len(current_job.sub_actions)
            current_job.sub_actions.insert(new_action_index, copy_buffer.clone())
            self.mark_as_modified(True, "Paste Action")
            self.selection_state.set_action(self.selection_state.job_index, new_action_index)
            self.refresh_ui()
            self._ensure_selected_visible()
            return
        if len(self.project().jobs) == 0:
            new_job_index = 0
        else:
            new_job_index = min(
                max(self.selection_state.job_index + 1, 0), len(self.project().jobs))
        self.mark_as_modified(True, "Paste Job")
        self.project().jobs.insert(new_job_index, copy_buffer.clone())
        self.selection_state.set_job(new_job_index)
        self.refresh_ui()
        self._ensure_selected_visible()

    def paste_action(self):
        if not self.has_copy_buffer():
            return
        if self.selection_state.job_index < 0:
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name not in constants.ACTION_TYPES:
            return
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= 0:
            new_action_index = self.selection_state.action_index + 1
        else:
            new_action_index = len(job.sub_actions)
        job.sub_actions.insert(new_action_index, copy_buffer.clone())
        self.mark_as_modified(True, "Paste Action")
        self.selection_state.set_action(self.selection_state.job_index, new_action_index)
        self.refresh_ui()
        self._ensure_selected_visible()

    def paste_subaction(self):
        if not self.has_copy_buffer():
            return
        if self.selection_state.job_index < 0 or self.selection_state.action_index < 0:
            return
        copy_buffer = self.copy_buffer()
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= len(job.sub_actions):
            return
        action = job.sub_actions[self.selection_state.action_index]
        if action.type_name != constants.ACTION_COMBO:
            return
        if copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
            return
        if self.selection_state.subaction_index >= 0:
            new_subaction_index = self.selection_state.subaction_index + 1
        else:
            new_subaction_index = 0
        action.sub_actions.insert(new_subaction_index, copy_buffer.clone())
        self.mark_as_modified(True, "Paste Sub-action")
        self.selection_state.set_subaction(
            self.selection_state.job_index,
            self.selection_state.action_index,
            new_subaction_index)
        self.refresh_ui()
        self._ensure_selected_visible()

    def paste_element(self):
        if not self.has_copy_buffer():
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            self.paste_subaction()
        elif self.selection_state.is_job_selected():
            self.paste_job()
        elif self.selection_state.is_action_selected():
            self.paste_action()
        elif self.selection_state.is_subaction_selected():
            self.paste_subaction()

    def cut_element(self):
        element = self.delete_element(False)
        self.set_copy_buffer(element)

    def clone_job(self):
        if not self.selection_state.is_job_selected():
            return
        if not self.is_valid_job_index(self.selection_state.job_index):
            return
        job = self.project().jobs[self.selection_state.job_index]
        job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
        new_job_index = self.selection_state.job_index + 1
        self.mark_as_modified(True, "Duplicate Job")
        self.project().jobs.insert(new_job_index, job_clone)
        self.selection_state.set_job(new_job_index)
        self.refresh_ui()

    def clone_action(self):
        if self.selection_state.widget_type == 'action':
            job_index = self.selection_state.job_index
            action_index = self.selection_state.action_index
            if (0 <= job_index < len(self.project().jobs) and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                action_clone = action.clone(name_postfix=self.CLONE_POSTFIX)
                new_action_index = action_index + 1
                self.mark_as_modified(True, "Duplicate Action")
                job.sub_actions.insert(new_action_index, action_clone)
                self.selection_state.action_index = new_action_index
                self.selection_state.subaction_index = -1
                self.selection_state.widget_type = 'action'
                self.refresh_ui()
        elif self.selection_state.widget_type == 'subaction':
            job_index = self.selection_state.job_index
            action_index = self.selection_state.action_index
            subaction_index = self.selection_state.subaction_index
            if (0 <= job_index < len(self.project().jobs) and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                if (action.type_name == constants.ACTION_COMBO and
                        0 <= subaction_index < len(action.sub_actions)):
                    subaction = action.sub_actions[subaction_index]
                    subaction_clone = subaction.clone(name_postfix=self.CLONE_POSTFIX)
                    new_subaction_index = subaction_index + 1
                    self.mark_as_modified(True, "Duplicate Sub-action")
                    action.sub_actions.insert(new_subaction_index, subaction_clone)
                    self.selection_state.subaction_index = new_subaction_index
                    self.selection_state.widget_type = 'subaction'
                    self.refresh_ui()

    def clone_element(self):
        if self.selection_state.is_job_selected():
            self.clone_job()
        elif self.selection_state.is_action_selected():
            self.clone_action()
        elif self.selection_state.is_subaction_selected():
            self.clone_subaction()

    def disable(self):
        self.set_enabled(False)

    def enable(self):
        self.set_enabled(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def enable_all(self):
        self.set_enabled_all(True)

    def set_enabled(self, enabled):
        self._set_enabled(*self.selection_state.to_tuple(), enabled)

    def set_enabled_all(self, enabled):
        for job in self.project().jobs:
            job.set_enabled_all(enabled)
        self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} All")
        self.refresh_ui()

    def _set_enabled(self, job_idx, action_idx, subaction_idx, enabled):
        if self.selection_state.is_subaction_selected():
            if (0 <= job_idx < len(self.project().jobs) and
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions)):
                action = self.project().jobs[job_idx].sub_actions[action_idx]
                if 0 <= subaction_idx < len(action.sub_actions):
                    action.sub_actions[subaction_idx].set_enabled(enabled)
                    self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Sub-action")
        elif self.selection_state.is_action_selected():
            if 0 <= job_idx < len(self.project().jobs) and \
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions):
                self.project().jobs[job_idx].sub_actions[action_idx].set_enabled(enabled)
                self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Action")
        elif self.selection_state.is_job_selected():
            if 0 <= job_idx < len(self.project().jobs):
                self.project().jobs[job_idx].set_enabled(enabled)
                self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Job")
        self.refresh_ui()

    def _ensure_selected_visible(self):
        if not self.selected_widget or not self.scroll_area:
            return
        if not self.selected_widget.isVisible() or self.selected_widget.height() == 0:
            QTimer.singleShot(10, self._ensure_selected_visible)
            return
        viewport_height = self.scroll_area.viewport().height()
        widget_height = self.selected_widget.height()
        if widget_height <= viewport_height:
            y_margin = (viewport_height - widget_height) // 2
        else:
            y_margin = 0
        self.scroll_area.ensureWidgetVisible(self.selected_widget, 0, y_margin)

    def move_element_up(self):
        if self.selection_state.is_job_selected():
            self._shift_job(-1)
        elif self.selection_state.is_action_selected():
            self._shift_action(-1)
        elif self.selection_state.is_subaction_selected():
            self._shift_subaction(-1)

    def move_element_down(self):
        if self.selection_state.is_job_selected():
            self._shift_job(+1)
        elif self.selection_state.is_action_selected():
            self._shift_action(+1)
        elif self.selection_state.is_subaction_selected():
            self._shift_subaction(+1)

    def _shift_job(self, delta):
        if not self.selection_state.is_job_selected():
            return
        job_idx, _, _ = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_job(job_idx, delta)
        if new_index != job_idx:
            self.mark_as_modified(True, "Shift Job")
            self.selection_state.set_job(new_index)
            self.refresh_ui()

    def _shift_action(self, delta):
        if not self.selection_state.is_action_selected():
            return
        job_idx, action_idx, _ = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_action(job_idx, action_idx, delta)
        if new_index != action_idx:
            self.mark_as_modified(True, "Shift Action")
            self.selection_state.set_action(job_idx, new_index)
            self.refresh_ui()

    def _shift_subaction(self, delta):
        if not self.selection_state.is_subaction_selected():
            return
        job_idx, action_idx, subaction_idx = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_subaction(job_idx, action_idx, subaction_idx, delta)
        if new_index != subaction_idx:
            self.mark_as_modified(True, "Shift Sub-action")
            self.selection_state.set_subaction(job_idx, action_idx, new_index)
            self.refresh_ui()

    def add_action(self, type_name):
        job_index = self.selection_state.job_index
        if job_index < 0:
            if len(self.project().jobs) > 0:
                QMessageBox.warning(self.parent(),
                                    "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self.parent(),
                                    "No Job Added", "Please add a job first.")
            return
        action = ActionConfig(type_name)
        action.parent = self.project().jobs[job_index]
        self.action_dialog = ActionConfigDialog(
            action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            self.mark_as_modified(True, "Add Action")
            self.project().jobs[job_index].add_sub_action(action)
            self.selection_state.action_index = len(self.project().jobs[job_index].sub_actions) - 1
            self.selection_state.subaction_index = -1
            self.selection_state.widget_type = 'action'
            self.refresh_ui()

    def add_sub_action(self, type_name):
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        if job_index < 0 or action_index < 0:
            return
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if action.type_name != constants.ACTION_COMBO:
                    return
                sub_action = ActionConfig(type_name)
                self.action_dialog = ActionConfigDialog(
                    sub_action, self.current_file_directory(), self.parent())
                if self.action_dialog.exec() == QDialog.Accepted:
                    self.mark_as_modified(True, "Add Sub-action")
                    action.add_sub_action(sub_action)
                    self.selection_state.subaction_index = len(action.sub_actions) - 1
                    self.selection_state.widget_type = 'subaction'
                    self.refresh_ui()

    def refresh_ui(self):
        old_state = self.selection_state.copy()
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)
        self._restore_selection_from_state(old_state)

    def _restore_selection_from_state(self, old_state):
        if not old_state.is_valid():
            if self.job_widgets:
                self._select_job(0)
            else:
                self._reset_selection()
            return
        job_idx = old_state.job_index
        if not 0 <= job_idx < len(self.job_widgets):
            if self.job_widgets:
                self._select_job(0)
            else:
                self._reset_selection()
            return
        if old_state.is_job_selected():
            self._select_job(job_idx)
        elif old_state.is_action_selected():
            action_idx = old_state.action_index
            job_widget = self.job_widgets[job_idx]
            if 0 <= action_idx < job_widget.num_child_widgets():
                self._select_action(job_idx, action_idx)
            elif job_widget.num_child_widgets() > 0:
                self._select_action(job_idx, 0)
            else:
                self._select_job(job_idx)
        elif old_state.is_subaction_selected():
            action_idx = old_state.action_index
            subaction_idx = old_state.subaction_index
            job_widget = self.job_widgets[job_idx]
            if 0 <= action_idx < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_idx]
                if 0 <= subaction_idx < action_widget.num_child_widgets():
                    self._select_subaction(job_idx, action_idx, subaction_idx)
                elif action_widget.num_child_widgets() > 0:
                    self._select_subaction(job_idx, action_idx, 0)
                else:
                    self._select_action(job_idx, action_idx)
            elif job_widget.num_child_widgets() > 0:
                self._select_action(job_idx, 0)
            else:
                self._select_job(job_idx)

    def get_console_area(self):
        return self.console_area

    def run_job(self):
        current_index = self.selection_state.job_index
        if current_index < 0:
            QMessageBox.warning(
                self.parent(), "No Job Selected", "Please select a job first.")
            return
        job = self.project_job(current_index)
        validation_result = self.validate_output_paths_for_job(job)
        if not validation_result['valid']:
            proceed = self.show_validation_warning(validation_result, is_single_job=True)
            if not proceed:
                return
        self.refresh_ui()
        self._build_progress_mapping([current_index])
        if not job.enabled():
            QMessageBox.warning(
                self.parent(), "Can't run Job", f"Job {job.params['name']} is disabled.")
            return
        self._worker = JobLogWorker(job, self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.menu_manager.run_job_action.setEnabled(False)
        self.menu_manager.run_all_jobs_action.setEnabled(False)
        self.start_thread(self._worker)
        self.menu_manager.stop_action.setEnabled(True)

    def run_all_jobs(self):
        validation_result = self.validate_output_paths_for_project()
        if not validation_result['valid']:
            proceed = self.show_validation_warning(validation_result, is_single_job=False)
            if not proceed:
                return
        self.refresh_ui()
        self._build_progress_mapping()
        self._worker = ProjectLogWorker(self.project(), self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.menu_manager.run_job_action.setEnabled(False)
        self.menu_manager.run_all_jobs_action.setEnabled(False)
        self.start_thread(self._worker)
        self.menu_manager.stop_action.setEnabled(True)

    def stop(self):
        if self._worker:
            self._worker.stop()

    def _connect_worker_signals(self, worker):
        SignalConnector.connect_worker_signals(worker, self)

    @Slot(str, int, str, int)
    def handle_status_signal(self, message, _status, _error_message, timeout):
        self.show_status_message_requested.emit(message, timeout)

    @Slot(str, int, str, int)
    def handle_status_update(self, message, _status, _error_message, _progress):
        self.console_area.handle_html_message(f"<b>{message}</b>")

    @Slot(int, str, str)
    def handle_worker_end(self, _status, _id_str, _message):
        self.console_area.handle_html_message("-" * 80)
        self._worker = None

    @Slot(int, str)
    def handle_run_completed(self, _run_id, _name):
        self._handle_end_of_run()

    def quit(self):
        self._worker.stop()
        self.close()
        return True

    def change_theme(self, dark_theme):
        self.dark_theme = dark_theme
        for job_widget in self.job_widgets:
            job_widget.set_dark_theme(dark_theme)

    def current_job_index(self):
        return self.selection_state.job_index

    def refresh_and_set_status(self, _status):
        self.refresh_ui()

    def refresh_and_select_job(self, _job_idx):
        self.refresh_ui()

    def select_first_job(self):
        if self.job_widgets:
            self._select_job_widget(self.job_widgets[0])
