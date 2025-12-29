# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=R1716, C0302, R0911, R0903
import os
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea, QDialog, QMessageBox
from .. config.constants import constants
from .. gui.project_model import ActionConfig
from .. gui.project_view import ProjectView
from .. gui.gui_logging import QTextEditLogger
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.run_worker import JobLogWorker, ProjectLogWorker
from .job_widget import JobWidget
from .selection_state import SelectionState
from .progress_mapper import ProgressMapper
from .element_operations import ElementOperations
from .progress_signal_handler import ProgressSignalHandler, SignalConnector
from .selection_navigation_manager import SelectionNavigationManager
from .element_action_manager import ElementActionManager


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
        self.actions_layout_horizontal = False
        self.subactions_layout_vertical = False
        self.progress_handler = ProgressSignalHandler(
            self.progress_mapper,
            self._find_action_widget,
            self._scroll_to_widget
        )
        self.selection_nav = SelectionNavigationManager(
            project_holder,
            self.selection_state,
            self._selection_callback
        )
        self.element_action = ElementActionManager(
            project_holder,
            self.selection_state,
            {
                'mark_modified': self.mark_as_modified,
                'refresh_ui': self.refresh_ui,
                'set_copy_buffer': self.set_copy_buffer,
                'has_copy_buffer': self.has_copy_buffer,
                'get_copy_buffer': self.copy_buffer,
                'ensure_selected_visible': self._ensure_selected_visible,
                'get_parent_widget': self.parent,
                'get_clone_postfix': lambda: self.CLONE_POSTFIX
            }
        )
        self.element_action.set_selection_navigation(self.selection_nav)
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

    def _selection_callback(self, widget_type, job_index, action_index=None, subaction_index=None):
        if widget_type == 'job':
            self._select_job(job_index)
        elif widget_type == 'action':
            self._select_action(job_index, action_index)
        elif widget_type == 'subaction':
            self._select_subaction(job_index, action_index, subaction_index)

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
        key_map = {
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Home: "home",
            Qt.Key_End: "end"
        }
        if key in key_map:
            if self.selection_nav.handle_key_navigation(key_map[key]):
                event.accept()
                return
        if key in [Qt.Key_Return, Qt.Key_Enter]:
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

    def _scroll_to_widget(self, widget):
        if not widget or not self.scroll_area:
            return
        if not widget.isVisible() or widget.height() == 0:
            QTimer.singleShot(10, lambda: self._scroll_to_widget(widget))
            return
        viewport_height = self.scroll_area.viewport().height()
        widget_height = widget.height()
        if widget_height <= viewport_height:
            y_margin = (viewport_height - widget_height) // 2
        else:
            y_margin = 0
        self.scroll_area.ensureWidgetVisible(widget, 0, y_margin)

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
        self.selected_widget = None

    def clear_project(self):
        self.clear_job_list()
        self._reset_selection()
        self.update_delete_action_state_requested.emit()

    def add_job_widget(self, job):
        if not self.enforce_stop_run():
            return
        job_widget = JobWidget(job, self.dark_theme,
                               self.actions_layout_horizontal,
                               self.subactions_layout_vertical)
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

    def enforce_stop_run(self):
        if self.is_running():
            reply = QMessageBox.question(
                self,
                "Stop Run Warning",
                "Modifying the project requrires to stop the run. "
                "Are you sure you want to stop the run?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop()
                return True
            return False
        return True

    def delete_element(self):
        if self.enforce_stop_run():
            return self.element_action.delete_element(self.parent(), True)
        return None

    def copy_element(self):
        self.element_action.copy_element()

    def paste_element(self):
        if self.enforce_stop_run():
            self.element_action.paste_element()

    def cut_element(self):
        if self.enforce_stop_run():
            self.element_action.cut_element()

    def clone_element(self):
        if self.enforce_stop_run():
            self.element_action.clone_element()

    def enable(self):
        self.element_action.enable()

    def disable(self):
        self.element_action.disable()

    def enable_all(self):
        self.element_action.enable_all()

    def disable_all(self):
        self.element_action.disable_all()

    def move_element_up(self):
        if self.enforce_stop_run():
            self.element_action.move_element_up()

    def move_element_down(self):
        if self.enforce_stop_run():
            self.element_action.move_element_down()

    def set_enabled(self, enabled):
        self._set_enabled(*self.selection_state.to_tuple(), enabled)

    def set_style_sheet(self, dark_theme):
        pass

    def set_enabled_all(self, enabled):
        if not self.enforce_stop_run():
            return
        for job in self.project().jobs:
            job.set_enabled_all(enabled)
        self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} All")
        self.refresh_ui()

    def _set_enabled(self, job_idx, action_idx, subaction_idx, enabled):
        if not self.enforce_stop_run():
            return
        if self.selection_state.is_subaction_selected():
            if (0 <= job_idx < self.num_project_jobs() and
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions)):
                action = self.project().jobs[job_idx].sub_actions[action_idx]
                if 0 <= subaction_idx < len(action.sub_actions):
                    action.sub_actions[subaction_idx].set_enabled(enabled)
                    self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Sub-action")
        elif self.selection_state.is_action_selected():
            if 0 <= job_idx < self.num_project_jobs() and \
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions):
                self.project().jobs[job_idx].sub_actions[action_idx].set_enabled(enabled)
                self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Action")
        elif self.selection_state.is_job_selected():
            if 0 <= job_idx < self.num_project_jobs():
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

    def add_action(self, type_name):
        if not self.enforce_stop_run():
            return
        job_index = self.selection_state.job_index
        if job_index < 0:
            if self.num_project_jobs() > 0:
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
        if not self.enforce_stop_run():
            return
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        if job_index < 0 or action_index < 0:
            return
        if 0 <= job_index < self.num_project_jobs():
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

    def horizontal_actions_layout(self, horizontal=True):
        if self.actions_layout_horizontal != horizontal:
            self.actions_layout_horizontal = horizontal
            for job_widget in self.job_widgets:
                job_widget.set_horizontal_layout(horizontal)
            self.progress_handler.set_horizontal_layout(
                self.menu_manager.horizontal_layout_action.isChecked())
            txt = "horizontal" if horizontal else "vertical"
            self.vertical_subactions_layout(vertical=horizontal)
            self.show_status_message_requested.emit(f"Actions layout set to {txt}", 2000)

    def vertical_subactions_layout(self, vertical=True):
        if self.subactions_layout_vertical != vertical:
            self.subactions_layout_vertical = vertical
            for job_widget in self.job_widgets:
                for action_widget in job_widget.child_widgets:
                    action_widget.set_horizontal_layout(not vertical)
                    image_horizontal = vertical
                    for subaction_widget in action_widget.child_widgets:
                        subaction_widget.set_image_orientation(image_horizontal)
                    if vertical:
                        action_widget.child_container_layout.setSpacing(5)
                    else:
                        action_widget.child_container_layout.setSpacing(2)

    def refresh_ui(self):
        old_state = self.selection_state.copy()
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)
        self.selection_nav.restore_selection(old_state)

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
        self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.run_all_jobs_action.setEnabled(True)
        self.menu_manager.stop_action.setEnabled(False)

    def is_running(self):
        return self._worker is not None and self._worker.isRunning()

    def _connect_worker_signals(self, worker):
        SignalConnector.connect_worker_signals(worker, self, self.progress_handler)

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
        if self._worker:
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

    def refresh_and_select_job(self, job_idx):
        self.refresh_ui()
        if 0 <= job_idx < len(self.job_widgets):
            self._select_job(job_idx)

    def select_first_job(self):
        if self.job_widgets:
            self._select_job_widget(self.job_widgets[0])
