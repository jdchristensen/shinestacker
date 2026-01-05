# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=R1716, C0302, R0911, R0903, W0718, W0613, R0801
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
from .modern_selection_state import ModernSelectionState
from .progress_mapper import ProgressMapper
from .element_operations import ElementOperations
from .progress_signal_handler import ProgressSignalHandler, SignalConnector
from .selection_navigation_manager import SelectionNavigationManager
from .modern_element_action_manager import ModernElementActionManager
from .action_widget import ActionWidget
from .sub_action_widget import SubActionWidget


class ModernProjectView(ProjectView):
    update_delete_action_state_requested = Signal()
    show_status_message_requested = Signal(str, int)

    def __init__(self, project_holder, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, dark_theme, parent)
        self.job_widgets = []
        self.scroll_area = None
        self.scroll_content = None
        self.project_layout = None
        self.selected_widget = None
        self.selection_state = ModernSelectionState()
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
        self.element_action = ModernElementActionManager(
            project_holder,
            self.selection_state,
            {
                'refresh_ui': self.refresh_ui,
                'ensure_selected_visible': self._ensure_selected_visible,
                'remove_widget': self._remove_widget,
                'update_selection': self._update_selection,
            },
            self.parent()
        )
        self._saved_selection = None
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
        job_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
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
            action_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
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
                subaction_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
        if len(self.job_widgets) == 1:
            self._on_widget_clicked(job_widget, 'job', 0)

    def _refresh_job_widget_signals(self):
        for i, job_widget in enumerate(self.job_widgets):
            try:
                job_widget.clicked.disconnect()
            except Exception:
                pass
            job_widget.clicked.connect(
                lambda checked=False, w=job_widget, idx=i:
                self._on_widget_clicked(w, 'job', idx))
            try:
                job_widget.enabled_toggled.disconnect()
            except Exception:
                pass
            job_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
            for action_idx, action_widget in enumerate(job_widget.child_widgets):
                try:
                    action_widget.clicked.disconnect()
                except Exception:
                    pass
                action_widget.clicked.connect(
                    lambda checked=False, w=action_widget, j_idx=i, a_idx=action_idx:
                    self._on_widget_clicked(w, 'action', j_idx, a_idx))
                try:
                    action_widget.enabled_toggled.disconnect()
                except Exception:
                    pass
                action_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
                for subaction_idx, subaction_widget in enumerate(action_widget.child_widgets):
                    try:
                        subaction_widget.clicked.disconnect()
                    except Exception:
                        pass
                    subaction_widget.clicked.connect(
                        lambda checked=False, w=subaction_widget,
                        j_idx=i, a_idx=action_idx, s_idx=subaction_idx:
                        self._on_widget_clicked(w, 'subaction', j_idx, a_idx, s_idx))
                    try:
                        subaction_widget.enabled_toggled.disconnect()
                    except Exception:
                        pass
                    subaction_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)

    def _refresh_after_structure_change(self):
        self._refresh_job_widget_signals()

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

    def _on_widget_enabled_toggled(self, enabled):
        widget = self.sender()
        if not widget:
            return
        for job_idx, job_widget in enumerate(self.job_widgets):
            if widget == job_widget:
                self.widget_enable_signal.emit((job_idx, -1, -1, 'job'), enabled)
                return
            for action_idx, action_widget in enumerate(job_widget.child_widgets):
                if widget == action_widget:
                    self.widget_enable_signal.emit((job_idx, action_idx, -1, 'action'), enabled)
                    return
                for subaction_idx, subaction_widget in enumerate(action_widget.child_widgets):
                    if widget == subaction_widget:
                        self.widget_enable_signal.emit(
                            (job_idx, action_idx, subaction_idx, 'subaction'), enabled)
                        return

    def _on_job_double_clicked(self, job_index):
        job_widget = self.job_widgets[job_index]
        self._on_widget_clicked(job_widget, 'job', job_index)
        job = self.project_job(job_index)
        if job:
            self.action_dialog = ActionConfigDialog(
                job, self.current_file_directory(), self.parent())
            if self.action_dialog.exec() == QDialog.Accepted:
                self._update_job_widget(job_index, job)
                self.widget_updated_signal.emit((job_index, -1, -1, 'job'))

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
                self.widget_updated_signal.emit((job_index, action_index, -1, 'action'))

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
                self.widget_updated_signal.emit(
                    (job_index, action_index, subaction_index, 'subaction'))

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

    def delete_element(self, selection=None, update_project=True, confirm=True):
        if selection is None:
            old_selection = self.selection_state.copy()
            if update_project:
                result = self.element_action.delete_element(confirm)
            else:
                result = None
            if result:
                self.widget_deleted_signal.emit((
                    old_selection.job_index,
                    old_selection.action_index,
                    old_selection.subaction_index,
                    old_selection.widget_type
                ))
            return result
        self._remove_widget(selection)
        return None

    def copy_element(self):
        self.element_action.copy_element()

    def cut_element(self):
        if self.enforce_stop_run():
            old_state = self.selection_state.copy() if self.selection_state else None
            self.element_action.cut_element()
            if old_state and old_state.is_valid():
                self.widget_deleted_signal.emit((
                    old_state.job_index,
                    old_state.action_index,
                    old_state.subaction_index,
                    old_state.widget_type
                ))

    def paste_element(self, selection=None, update_project=True):
        if selection is None:
            old_selection = self.selection_state.copy()
            if update_project:
                result = self.element_action.paste_element()
                if result:
                    self._paste_element_ui_only(old_selection)
            else:
                result = self._paste_element_ui_only(old_selection)
            if result and old_selection and old_selection.is_valid():
                self.widget_pasted_signal.emit((
                    old_selection.job_index,
                    old_selection.action_index,
                    old_selection.subaction_index,
                    old_selection.widget_type
                ))
            return result
        self._paste_element_ui_only(selection)
        return None

    def _paste_element_ui_only(self, selection):
        if not selection or not selection.is_valid():
            return False
        try:
            job_idx = selection.job_index
            if not 0 <= job_idx < self.num_project_jobs():
                return False
            job = self.project().jobs[job_idx]
            if not self.element_action.has_copy_buffer():
                return False
            copy_buffer = self.element_action.copy_buffer()
            if selection.is_job_selected():
                if copy_buffer.type_name != constants.ACTION_JOB:
                    return False
                element = copy_buffer.clone()
                new_job_idx = job_idx + 1
                self._insert_job_widget(new_job_idx, element)
                new_widget = self.job_widgets[new_job_idx]
                self.selection_state.set_job(new_job_idx)
            elif selection.is_action_selected():
                if copy_buffer.type_name not in constants.ACTION_TYPES:
                    return False
                element = copy_buffer.clone()
                action_idx = selection.action_index
                new_action_idx = action_idx + 1
                self._insert_action_widget(job_idx, new_action_idx, element)
                new_widget = self.job_widgets[job_idx].child_widgets[new_action_idx]
                self.selection_state.set_action(job_idx, new_action_idx)
            elif selection.is_subaction_selected():
                if copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
                    return False
                element = copy_buffer.clone()
                action_idx = selection.action_index
                subaction_idx = selection.subaction_index
                action = job.sub_actions[action_idx]
                if action.type_name != constants.ACTION_COMBO:
                    return False
                new_subaction_idx = subaction_idx + 1
                self._insert_subaction_widget(job_idx, action_idx, new_subaction_idx, element)
                new_widget = self.job_widgets[
                    job_idx].child_widgets[action_idx].child_widgets[new_subaction_idx]
                self.selection_state.set_subaction(job_idx, action_idx, new_subaction_idx)
            else:
                return False
            if self.selected_widget:
                self.selected_widget.set_selected(False)
            new_widget.set_selected(True)
            self.selected_widget = new_widget
            self.update_delete_action_state_requested.emit()
            return True
        except Exception:
            pass
        self.refresh_ui()
        return False

    def clone_element(self, selection=None, update_project=True, confirm=True):
        if selection is None:
            old_selection = self.selection_state.copy()
            if update_project:
                result = self.element_action.clone_element()
                if result:
                    self._clone_element_ui_only(old_selection)
            else:
                result = self._clone_element_ui_only(old_selection)
            if result:
                self.widget_cloned_signal.emit((
                    old_selection.job_index,
                    old_selection.action_index,
                    old_selection.subaction_index,
                    old_selection.widget_type
                ))
            return result
        self._clone_element_ui_only(selection)
        return None

    def _clone_element_ui_only(self, selection):
        if not selection or not selection.is_valid():
            return False
        try:
            job_idx = selection.job_index
            if not 0 <= job_idx < self.num_project_jobs():
                return False
            job = self.project().jobs[job_idx]
            if selection.is_job_selected():
                element = self.project_job(job_idx)
                new_job_idx = job_idx + 1
                self._insert_job_widget(new_job_idx, element.clone(
                    name_postfix=self.element_action.CLONE_POSTFIX))
                new_widget = self.job_widgets[new_job_idx]
                self.selection_state.set_job(new_job_idx)
            elif selection.is_action_selected():
                action_idx = selection.action_index
                if not 0 <= action_idx < len(job.sub_actions):
                    return False
                element = job.sub_actions[action_idx]
                new_action_idx = action_idx + 1
                self._insert_action_widget(
                    job_idx, new_action_idx, element.clone(
                        name_postfix=self.element_action.CLONE_POSTFIX))
                new_widget = self.job_widgets[job_idx].child_widgets[new_action_idx]
                self.selection_state.set_action(job_idx, new_action_idx)
            elif selection.is_subaction_selected():
                action_idx = selection.action_index
                subaction_idx = selection.subaction_index
                if not 0 <= action_idx < len(job.sub_actions):
                    return False
                action = job.sub_actions[action_idx]
                if not 0 <= subaction_idx < len(action.sub_actions):
                    return False
                element = action.sub_actions[subaction_idx]
                new_subaction_idx = subaction_idx + 1
                self._insert_subaction_widget(
                    job_idx, action_idx, new_subaction_idx, element.clone(
                        name_postfix=self.element_action.CLONE_POSTFIX))
                new_widget = self.job_widgets[
                    job_idx].child_widgets[action_idx].child_widgets[new_subaction_idx]
                self.selection_state.set_subaction(job_idx, action_idx, new_subaction_idx)
            else:
                return False
            if self.selected_widget:
                self.selected_widget.set_selected(False)
            new_widget.set_selected(True)
            self.selected_widget = new_widget
            self.update_delete_action_state_requested.emit()
            return True
        except Exception:
            pass
        self.refresh_ui()
        return False

    def _get_widget_from_selection(self, selection):
        if not selection or not selection.is_valid():
            return None
        if selection.is_job_selected():
            if 0 <= selection.job_index < len(self.job_widgets):
                return self.job_widgets[selection.job_index]
        elif selection.is_action_selected():
            if 0 <= selection.job_index < len(self.job_widgets):
                job_widget = self.job_widgets[selection.job_index]
                if 0 <= selection.action_index < len(job_widget.child_widgets):
                    return job_widget.child_widgets[selection.action_index]
        elif selection.is_subaction_selected():
            if 0 <= selection.job_index < len(self.job_widgets):
                job_widget = self.job_widgets[selection.job_index]
                if 0 <= selection.action_index < len(job_widget.child_widgets):
                    action_widget = job_widget.child_widgets[selection.action_index]
                    if 0 <= selection.subaction_index < len(action_widget.child_widgets):
                        return action_widget.child_widgets[selection.subaction_index]
        return None

    def _update_widget_enable_state(self, selection, enabled):
        widget = self._get_widget_from_selection(selection)
        if widget:
            widget.set_enabled_and_update(enabled)

    def enable(self, selection=None, update_project=True):
        if selection is None:
            selection = self.selection_state
        if update_project:
            self.element_action.set_enabled(True, update_project=True)
            if update_project:
                self.widget_enable_signal.emit((
                    self.selection_state.job_index,
                    self.selection_state.action_index,
                    self.selection_state.subaction_index,
                    self.selection_state.widget_type
                ), True)
        self._update_widget_enable_state(selection, True)

    def disable(self, selection=None, update_project=True):
        if selection is None:
            selection = self.selection_state
        if update_project:
            self.element_action.set_enabled(False, update_project=True)
            if update_project:
                self.widget_enable_signal.emit((
                    self.selection_state.job_index,
                    self.selection_state.action_index,
                    self.selection_state.subaction_index,
                    self.selection_state.widget_type
                ), False)
        self._update_widget_enable_state(selection, False)

    def enable_all(self, update_project=True):
        if update_project:
            self.element_action.set_enabled_all(True)
            self.widget_enable_all_signal.emit(True)
        self._update_all_widgets_enabled(True)

    def disable_all(self, update_project=True):
        if update_project:
            self.element_action.set_enabled_all(False)
            self.widget_enable_all_signal.emit(False)
        self._update_all_widgets_enabled(False)

    def _update_all_widgets_enabled(self, enabled):
        for job_widget in self.job_widgets:
            job_widget.data_object.params['enabled'] = enabled
            job_widget.update(job_widget.data_object)
            for action_widget in job_widget.child_widgets:
                action_widget.data_object.params['enabled'] = enabled
                action_widget.update(action_widget.data_object)
                for subaction_widget in action_widget.child_widgets:
                    subaction_widget.data_object.params['enabled'] = enabled
                    subaction_widget.update(subaction_widget.data_object)

    def move_element_up(self, selection=None, update_project=True):
        if selection is None:
            old_selection = self.selection_state.copy()
            if update_project and self.enforce_stop_run():
                result = self.element_action.move_element_up()
            else:
                result = False
            if result and old_selection and old_selection.is_valid():
                self.widget_moved_up_signal.emit((
                    old_selection.job_index,
                    old_selection.action_index,
                    old_selection.subaction_index,
                    old_selection.widget_type
                ))
            return result
        if selection and selection.is_valid():
            self.refresh_ui()
        return False

    def move_element_down(self, selection=None, update_project=True):
        if selection is None:
            old_selection = self.selection_state.copy()
            if update_project and self.enforce_stop_run():
                result = self.element_action.move_element_down()
            else:
                result = False
            if result and old_selection and old_selection.is_valid():
                self.widget_moved_down_signal.emit((
                    old_selection.job_index,
                    old_selection.action_index,
                    old_selection.subaction_index,
                    old_selection.widget_type
                ))
            return result
        if selection and selection.is_valid():
            self.refresh_ui()
        return False

    def set_enabled(self, enabled):
        self._set_enabled(*self.selection_state.to_tuple(), enabled)

    def set_style_sheet(self, dark_theme):
        pass

    def set_enabled_all(self, enabled):
        if not self.enforce_stop_run():
            return
        for job in self.project().jobs:
            job.set_enabled_all(enabled)
        self.mark_as_modified(
            True, f"{'Enable' if enabled else 'Disable'} All", "edit_all", (-1, -1, -1))
        self.refresh_ui()

    def _set_enabled(self, job_idx, action_idx, subaction_idx, enabled):
        if not self.enforce_stop_run():
            return
        if self.selection_state.is_subaction_selected():
            if (0 <= job_idx < self.num_project_jobs() and
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions)):
                action = self.project().jobs[job_idx].sub_actions[action_idx]
                if 0 <= subaction_idx < len(action.sub_actions):
                    self.mark_as_modified(
                        True, f"{'Enable' if enabled else 'Disable'} Sub-action", "edit",
                        (job_idx, action_idx, subaction_idx))
                    action.sub_actions[subaction_idx].set_enabled(enabled)
        elif self.selection_state.is_action_selected():
            if 0 <= job_idx < self.num_project_jobs() and \
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions):
                self.mark_as_modified(
                    True, f"{'Enable' if enabled else 'Disable'} Action", "edit",
                    (job_idx, action_idx, -1))
                self.project().jobs[job_idx].sub_actions[action_idx].set_enabled(enabled)
        elif self.selection_state.is_job_selected():
            if 0 <= job_idx < self.num_project_jobs():
                self.mark_as_modified(
                    True, f"{'Enable' if enabled else 'Disable'} Job", "edit", (job_idx, -1, -1))
                self.project().jobs[job_idx].set_enabled(enabled)
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
            return False
        job_index = self.selection_state.job_index
        if job_index < 0:
            if self.num_project_jobs() > 0:
                QMessageBox.warning(self.parent(),
                                    "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self.parent(),
                                    "No Job Added", "Please add a job first.")
            return False
        action = ActionConfig(type_name)
        action.parent = self.project().jobs[job_index]
        self.action_dialog = ActionConfigDialog(
            action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            new_action_index = len(self.project().jobs[job_index].sub_actions)
            self.mark_as_modified(True, "Add Action", "add", (job_index, new_action_index, -1))
            self.project().jobs[job_index].add_sub_action(action)
            self.selection_state.set_action(job_index, new_action_index)
            self.selection_state.subaction_index = -1
            self.selection_state.widget_type = 'action'
            self.refresh_ui()
            self.widget_added_signal.emit((job_index, new_action_index, -1))
            return True
        return False

    def add_sub_action(self, type_name):
        if not self.enforce_stop_run():
            return False
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        if job_index < 0 or action_index < 0:
            return False
        if 0 <= job_index < self.num_project_jobs():
            job = self.project().jobs[job_index]
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if action.type_name != constants.ACTION_COMBO:
                    return False
                if self.selection_state.is_subaction_selected():
                    insert_index = self.selection_state.subaction_index + 1
                else:
                    insert_index = len(action.sub_actions)
                sub_action = ActionConfig(type_name)
                self.action_dialog = ActionConfigDialog(
                    sub_action, self.current_file_directory(), self.parent())
                if self.action_dialog.exec() == QDialog.Accepted:
                    self.mark_as_modified(
                        True, "Add Sub-action", "add", (job_index, action_index, insert_index))
                    action.sub_actions.insert(insert_index, sub_action)
                    self.selection_state.subaction_index = insert_index
                    self.selection_state.widget_type = 'subaction'
                    self.refresh_ui()
                    self.widget_added_signal.emit((job_index, action_index, insert_index))
                    return True
        return False

    def update_added_element(self, indices_tuple):
        job_idx, action_idx, subaction_idx = indices_tuple
        try:
            if not 0 <= job_idx < self.num_project_jobs():
                return False
            job = self.project().jobs[job_idx]
            if subaction_idx != -1:
                if not 0 <= action_idx < len(job.sub_actions):
                    return False
                action = job.sub_actions[action_idx]
                if not 0 <= subaction_idx < len(action.sub_actions):
                    return False
                subaction = action.sub_actions[subaction_idx]
                self._insert_subaction_widget(job_idx, action_idx, subaction_idx, subaction)
            elif action_idx != -1:
                if not 0 <= action_idx < len(job.sub_actions):
                    return False
                action = job.sub_actions[action_idx]
                self._insert_action_widget(job_idx, action_idx, action)
            else:
                self._insert_job_widget(job_idx, job)
            return True
        except Exception:
            pass
        return False

    def update_widget(self, selection=None, update_project=True):
        if selection is None:
            selection = self.selection_state
        if not selection.is_valid():
            return
        if selection.is_job_selected():
            job_idx = selection.job_index
            if 0 <= job_idx < len(self.job_widgets):
                job_widget = self.job_widgets[job_idx]
                job_widget.update(job_widget.data_object)
        elif selection.is_action_selected():
            job_idx = selection.job_index
            action_idx = selection.action_index
            if (0 <= job_idx < len(self.job_widgets) and
                    0 <= action_idx < self.job_widgets[job_idx].num_child_widgets()):
                action_widget = self.job_widgets[job_idx].child_widgets[action_idx]
                action_widget.update(action_widget.data_object)
        elif selection.is_subaction_selected():
            job_idx = selection.job_index
            action_idx = selection.action_index
            subaction_idx = selection.subaction_index
            if (0 <= job_idx < len(self.job_widgets) and
                    0 <= action_idx < self.job_widgets[job_idx].num_child_widgets()):
                action_widget = self.job_widgets[job_idx].child_widgets[action_idx]
                if 0 <= subaction_idx < action_widget.num_child_widgets():
                    subaction_widget = action_widget.child_widgets[subaction_idx]
                    subaction_widget.update(subaction_widget.data_object)

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

    def refresh_ui(self, restore_state=None):
        old_state = restore_state if restore_state else self.selection_state.copy()
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)
        if old_state:
            self.selection_nav.restore_selection(old_state)
            self._ensure_selected_visible()

    def _update_selection(self, state):
        if not state or not state.is_valid():
            if self.selected_widget:
                self.selected_widget.set_selected(False)
            self.selected_widget = None
            self.selection_state.reset()
            return
        self.selection_state.copy_from(state)
        if state.is_job_selected():
            if 0 <= state.job_index < len(self.job_widgets):
                widget = self.job_widgets[state.job_index]
                if self.selected_widget:
                    self.selected_widget.set_selected(False)
                widget.set_selected(True)
                self.selected_widget = widget
        elif state.is_action_selected():
            if 0 <= state.job_index < len(self.job_widgets) and \
                    0 <= state.action_index < self.job_widgets[state.job_index].num_child_widgets():
                job_widget = self.job_widgets[state.job_index]
                widget = job_widget.child_widgets[state.action_index]
                if self.selected_widget:
                    self.selected_widget.set_selected(False)
                widget.set_selected(True)
                self.selected_widget = widget
        elif state.is_subaction_selected():
            if 0 <= state.job_index < len(self.job_widgets) and \
                    0 <= state.action_index < self.job_widgets[state.job_index].num_child_widgets():
                job_widget = self.job_widgets[state.job_index]
                action_widget = job_widget.child_widgets[state.action_index]
                if 0 <= state.subaction_index < action_widget.num_child_widgets():
                    widget = action_widget.child_widgets[state.subaction_index]
                    if self.selected_widget:
                        self.selected_widget.set_selected(False)
                    widget.set_selected(True)
                    self.selected_widget = widget

    def _remove_widget(self, state):
        if not state.is_valid():
            raise ValueError(f"Invalid removal state: {state.to_tuple()}")
        if state.is_job_selected():
            if not 0 <= state.job_index < len(self.job_widgets):
                raise IndexError(
                    f"Job index {state.job_index} out of range "
                    f"(0-{len(self.job_widgets) - 1})")
            return self._remove_job_widget(state.job_index)
        if state.is_action_selected():
            if not 0 <= state.job_index < len(self.job_widgets):
                raise IndexError(
                    f"Job index {state.job_index} out of range "
                    f"(0-{len(self.job_widgets) - 1})")
            job_widget = self.job_widgets[state.job_index]
            if not 0 <= state.action_index < len(job_widget.child_widgets):
                raise IndexError(
                    f"Action index {state.action_index} out of range "
                    f"for job {state.job_index} (0-{len(job_widget.child_widgets) - 1})")
            return self._remove_action_widget(state.job_index, state.action_index)
        if state.is_subaction_selected():
            if not 0 <= state.job_index < len(self.job_widgets):
                raise IndexError(
                    f"Job index {state.job_index} out of range "
                    f"(0-{len(self.job_widgets) - 1})")
            job_widget = self.job_widgets[state.job_index]
            if not 0 <= state.action_index < len(job_widget.child_widgets):
                raise IndexError(
                    f"Action index {state.action_index} out of range "
                    f"for job {state.job_index} (0-{len(job_widget.child_widgets) - 1})")
            action_widget = job_widget.child_widgets[state.action_index]
            if not 0 <= state.subaction_index < len(action_widget.child_widgets):
                raise IndexError(
                    f"Subaction index {state.subaction_index} out of range "
                    f"for action {state.action_index} (0-{len(action_widget.child_widgets) - 1})")
            return self._remove_subaction_widget(
                state.job_index, state.action_index, state.subaction_index)
        raise ValueError(f"Unknown widget type in state: {state.widget_type}")

    def _remove_job_widget(self, job_index):
        if not 0 <= job_index < len(self.job_widgets):
            raise IndexError(f"Job index {job_index} out of range (0-{len(self.job_widgets) - 1})")
        widget = self.job_widgets.pop(job_index)
        self.project_layout.removeWidget(widget)
        widget.clicked.disconnect()
        widget.double_clicked.disconnect()
        widget.deleteLater()
        self._refresh_job_widget_signals()
        return True

    def _remove_action_widget(self, job_index, action_index):
        if not 0 <= job_index < len(self.job_widgets):
            return False
        job_widget = self.job_widgets[job_index]
        if not 0 <= action_index < len(job_widget.child_widgets):
            return False
        action_widget = job_widget.child_widgets.pop(action_index)
        job_widget.child_container_layout.removeWidget(action_widget)
        try:
            action_widget.clicked.disconnect()
            action_widget.double_clicked.disconnect()
        except Exception:
            pass
        action_widget.deleteLater()
        self._refresh_job_widget_signals()
        return True

    def _remove_subaction_widget(self, job_index, action_index, subaction_index):
        if not 0 <= job_index < len(self.job_widgets):
            return False
        job_widget = self.job_widgets[job_index]
        if not 0 <= action_index < len(job_widget.child_widgets):
            return False
        action_widget = job_widget.child_widgets[action_index]
        if not 0 <= subaction_index < len(action_widget.child_widgets):
            return False
        subaction_widget = action_widget.child_widgets.pop(subaction_index)
        action_widget.child_container_layout.removeWidget(subaction_widget)
        try:
            subaction_widget.clicked.disconnect()
            subaction_widget.double_clicked.disconnect()
        except Exception:
            pass
        subaction_widget.deleteLater()
        self._refresh_job_widget_signals()
        return True

    def _insert_job_widget(self, job_index, job):
        if not 0 <= job_index <= len(self.job_widgets):
            return None
        job_widget = JobWidget(job, self.dark_theme,
                               self.actions_layout_horizontal,
                               self.subactions_layout_vertical)
        job_widget.setFocusPolicy(Qt.NoFocus)
        job_widget.clicked.connect(lambda: self._on_widget_clicked(job_widget, 'job', job_index))
        job_widget.double_clicked.connect(lambda: self._on_job_double_clicked(job_index))
        self.job_widgets.insert(job_index, job_widget)
        self.project_layout.insertWidget(job_index, job_widget)
        return job_widget

    def _insert_action_widget(self, job_index, action_index, action):
        if not 0 <= job_index < len(self.job_widgets):
            return None
        job_widget = self.job_widgets[job_index]
        if not 0 <= action_index <= len(job_widget.child_widgets):
            return None
        action_widget = ActionWidget(action, self.dark_theme, self.subactions_layout_vertical)
        action_widget.clicked.connect(
            lambda: self._on_widget_clicked(action_widget, 'action', job_index, action_index))
        action_widget.double_clicked.connect(
            lambda: self._on_action_double_clicked(job_index, action_index))
        job_widget.child_widgets.insert(action_index, action_widget)
        job_widget.child_container_layout.insertWidget(action_index, action_widget)
        return action_widget

    def _insert_subaction_widget(self, job_index, action_index, subaction_index, subaction):
        if not 0 <= job_index < len(self.job_widgets):
            return None
        job_widget = self.job_widgets[job_index]
        if not 0 <= action_index < len(job_widget.child_widgets):
            return None
        action_widget = job_widget.child_widgets[action_index]
        if not 0 <= subaction_index <= len(action_widget.child_widgets):
            return None
        subaction_widget = SubActionWidget(subaction, self.dark_theme,
                                           horizontal_images=not self.subactions_layout_vertical)
        subaction_widget.clicked.connect(lambda: self._on_widget_clicked(
            subaction_widget, 'subaction', job_index, action_index, subaction_index))
        subaction_widget.double_clicked.connect(lambda: self._on_subaction_double_clicked(
            job_index, action_index, subaction_index))
        action_widget.child_widgets.insert(subaction_index, subaction_widget)
        action_widget.child_container_layout.insertWidget(subaction_index, subaction_widget)
        return subaction_widget

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

    def save_current_selection(self):
        self._saved_selection = self.selection_state.copy() if self.selection_state else None

    def restore_saved_selection(self):
        if self._saved_selection is None:
            return
        self.selection_nav.restore_selection(self._saved_selection)
        self._saved_selection = None

    def refresh_and_restore_selection(self):
        if self._saved_selection:
            old_state = self._saved_selection
            self.clear_job_list()
            for job in self.project_jobs():
                self.add_job_widget(job)
            ProjectView.refresh_ui(self)
            self.selection_nav.restore_selection(old_state)
            self._saved_selection = None
