# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=W0613
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QMessageBox, QApplication, QDialog)
from .. config.constants import constants
from .. gui.colors import ColorPalette
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.project_model import ActionConfig
from .. common_project.run_worker import JobLogWorker, ProjectLogWorker
from .. common_project.project_view import ProjectView
from .tab_widget import TabWidgetWithPlaceholder
from .gui_run import RunWindow
from .list_container import ListContainer
from .classic_selection_state import ClassicSelectionState, rows_to_state
from .classic_element_action_manager import ClassicElementActionManager


class ClassicProjectView(ProjectView, ListContainer):
    def __init__(self, project_holder, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, dark_theme, parent)
        ListContainer.__init__(self)
        self.tab_widget = TabWidgetWithPlaceholder(dark_theme)
        self.tab_widget.resize(1000, 500)
        self._windows = []
        self._workers = []
        self.current_action_working_path = None
        self.current_action_input_path = None
        self.current_action_output_path = None
        self.browse_working_path_action = None
        self.browse_input_path_action = None
        self.browse_output_path_action = None
        self.job_retouch_path_action = None
        self.style_light = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.DARK_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.DARK_RED.hex()}; }}
        """
        self.style_dark = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.LIGHT_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.LIGHT_RED.hex()}; }}
        """
        self.list_style_sheet_light = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.LIGHT_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #F0F0F0;
            }}
        """
        self.list_style_sheet_dark = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.DARK_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #303030;
            }}
        """
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        self.selection_state = ClassicSelectionState(None, None, -1, -1, -1, None)
        self.element_action = ClassicElementActionManager(project_holder, self.parent())
        self._saved_selection = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        h_splitter = QSplitter(Qt.Orientation.Vertical)
        top_widget = QWidget()
        h_layout = QHBoxLayout(top_widget)
        h_layout.setContentsMargins(10, 0, 10, 10)
        vbox_left = QVBoxLayout()
        vbox_left.setSpacing(4)
        vbox_left.addWidget(QLabel("Jobs"))
        vbox_left.addWidget(self.job_list())
        vbox_right = QVBoxLayout()
        vbox_right.setSpacing(4)
        vbox_right.addWidget(QLabel("Actions"))
        vbox_right.addWidget(self.action_list())
        h_layout.addLayout(vbox_left)
        h_layout.addLayout(vbox_right)
        h_splitter.addWidget(top_widget)
        h_splitter.addWidget(self.tab_widget)
        self.setLayout(layout)
        layout.addWidget(h_splitter)
        self.job_list().itemDoubleClicked.connect(self.on_job_edit)
        self.action_list().itemDoubleClicked.connect(self.on_action_edit)

    def connect_signals(
            self, update_delete_action_state, set_enabled_sub_actions_gui):
        self.job_list().currentRowChanged.connect(self.on_job_selected)
        self.job_list().itemSelectionChanged.connect(update_delete_action_state)
        self.job_list().itemSelectionChanged.connect(self._get_selection_state)
        self.action_list().itemSelectionChanged.connect(update_delete_action_state)
        self.action_list().itemSelectionChanged.connect(self._get_selection_state)
        self.enable_sub_actions_requested.connect(set_enabled_sub_actions_gui)

    def get_tab_widget(self):
        return self.tab_widget

    def get_tab_and_position(self, id_str):
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if w.id_str() == id_str:
                return i, w
        return None, None

    def get_tab_at_position(self, id_str):
        _i, w = self.get_tab_and_position(id_str)
        return w

    def get_tab_position(self, id_str):
        i, _w = self.get_tab_and_position(id_str)
        return i

    def set_style_sheet(self, dark_theme):
        list_style_sheet = self.list_style_sheet_dark \
            if dark_theme else self.list_style_sheet_light
        self.job_list().setStyleSheet(list_style_sheet)
        self.action_list().setStyleSheet(list_style_sheet)

    def refresh_and_select_job(self, job_idx):
        self.refresh_ui(rows_to_state(self.project(), job_idx, -1))

    def refresh_ui(self, restore_state=None):
        job_row = -1
        action_row = -1
        if restore_state is not None:
            if restore_state.is_job_selected():
                job_row = restore_state.job_index
                action_row = -1
            elif restore_state.is_action_selected() or restore_state.is_subaction_selected():
                job_row = restore_state.job_index
                action_row = restore_state.get_action_row()
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_list_item(self.job_list(), job, False)
        if self.project_jobs():
            self.set_current_job(0)
        if job_row >= 0:
            self.set_current_job(job_row)
        if action_row >= 0:
            self.set_current_action(action_row)
        ProjectView.refresh_ui(self)

    def select_first_job(self):
        self.set_current_job(0)

    def has_selected_jobs(self):
        return self.num_selected_jobs() > 0

    def has_selected_actions(self):
        return self.num_selected_actions() > 0

    def has_selection(self):
        return self.has_selected_jobs() or self.has_selected_actions()

    def has_selected_jobs_and_actions(self):
        return self.has_selected_jobs() and self.has_selected_actions()

    def has_selected_sub_action(self):
        if self.has_selected_jobs_and_actions():
            job_index = min(self.current_job_index(), self.num_project_jobs() - 1)
            action_index = self.current_action_index()
            if job_index >= 0:
                job = self.project_job(job_index)
                current_action, is_sub_action = \
                    self.get_current_action_at(job, action_index)
                selected_sub_action = current_action is not None and \
                    (is_sub_action or current_action.type_name == constants.ACTION_COMBO)
                return selected_sub_action
        return False

    def get_current_action_at(self, job, action_index):
        action_counter = -1
        current_action = None
        is_sub_action = False
        for action in job.sub_actions:
            action_counter += 1
            if action_counter == action_index:
                current_action = action
                break
            if len(action.sub_actions) > 0:
                for sub_action in action.sub_actions:
                    action_counter += 1
                    if action_counter == action_index:
                        current_action = sub_action
                        is_sub_action = True
                        break
                if current_action:
                    break
        return current_action, is_sub_action

    def create_new_window(self, title, labels, retouch_paths):
        new_window = RunWindow(labels,
                               lambda id_str: self.close_window(self.get_tab_position(id_str)),
                               retouch_paths, self)
        self.tab_widget.addTab(new_window, title)
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        if title is not None:
            new_window.setWindowTitle(title)
        new_window.show()
        self.add_gui_logger(new_window)
        self._windows.append(new_window)
        return new_window, self.last_id_str()

    def close_window(self, tab_position):
        self._windows.pop(tab_position)
        self._workers.pop(tab_position)
        self.tab_widget.removeTab(tab_position)

    def stop_worker(self, tab_position):
        worker = self._workers[tab_position]
        worker.stop()

    def is_running(self):
        return any(worker.isRunning() for worker in self._workers if worker is not None)

    def connect_worker_signals(self, worker, window):
        worker.before_action_signal.connect(window.handle_before_action)
        worker.after_action_signal.connect(window.handle_after_action)
        worker.step_counts_signal.connect(window.handle_step_counts)
        worker.begin_steps_signal.connect(window.handle_begin_steps)
        worker.end_steps_signal.connect(window.handle_end_steps)
        worker.after_step_signal.connect(window.handle_after_step)
        worker.save_plot_signal.connect(window.handle_save_plot)
        worker.open_app_signal.connect(window.handle_open_app)
        worker.run_completed_signal.connect(self.handle_run_completed)
        worker.run_stopped_signal.connect(window.handle_run_stopped)
        worker.run_failed_signal.connect(window.handle_run_failed)
        worker.add_status_box_signal.connect(window.handle_add_status_box)
        worker.add_frame_signal.connect(window.handle_add_frame)
        worker.set_total_actions_signal.connect(window.handle_set_total_actions)
        worker.update_frame_status_signal.connect(window.handle_update_frame_status)
        worker.plot_manager.save_plot_signal.connect(window.handle_save_plot_via_manager)

    def run_job(self):
        current_index = self.current_job_index()
        if current_index < 0:
            msg = "No Job Selected" if self.num_project_jobs() > 0 else "No Job Added"
            QMessageBox.warning(self, msg, "Please select a job first.")
            return False
        if current_index < 0:
            return False
        job = self.project_job(current_index)
        validation_result = self.validate_output_paths_for_job(job)
        if not validation_result['valid']:
            proceed = self.show_validation_warning(validation_result, is_single_job=True)
            if not proceed:
                return False
        if not job.enabled():
            QMessageBox.warning(self, "Can't run Job",
                                "Job " + job.params["name"] + " is disabled.")
            return False
        job_name = job.params["name"]
        labels = [[(self.action_text(a), a.enabled()) for a in job.sub_actions]]
        r = self.get_retouch_path(job)
        retouch_paths = [] if len(r) == 0 else [(job_name, r)]
        new_window, id_str = self.create_new_window(f"{job_name} [Job]",
                                                    labels, retouch_paths)
        worker = JobLogWorker(job, id_str)
        self.connect_worker_signals(worker, new_window)
        self.start_thread(worker)
        self._workers.append(worker)
        return True

    def run_all_jobs(self):
        validation_result = self.validate_output_paths_for_project()
        if not validation_result['valid']:
            proceed = self.show_validation_warning(validation_result, is_single_job=False)
            if not proceed:
                return False
        labels = [[(self.action_text(a), a.enabled() and
                    job.enabled()) for a in job.sub_actions] for job in self.project_jobs()]
        project_name = ".".join(self.current_file_name().split(".")[:-1])
        if project_name == '':
            project_name = '[new]'
        retouch_paths = []
        for job in self.project_jobs():
            r = self.get_retouch_path(job)
            if len(r) > 0:
                retouch_paths.append((job.params["name"], r))
        new_window, id_str = self.create_new_window(f"{project_name} [Project]",
                                                    labels, retouch_paths)
        worker = ProjectLogWorker(self.project(), id_str)
        self.connect_worker_signals(worker, new_window)
        self.start_thread(worker)
        self._workers.append(worker)
        return True

    def stop(self):
        tab_position = self.tab_widget.count()
        if tab_position > 0:
            self.stop_worker(tab_position - 1)
            return True
        return False

    def handle_end_message(self, status, id_str, message):
        tab = self.get_tab_at_position(id_str)
        tab.close_button.setEnabled(True)
        if hasattr(tab, 'retouch_widget') and tab.retouch_widget is not None:
            tab.retouch_widget.setEnabled(True)
        self.run_finished_signal.emit()

    def _sync_selection_to_action_manager(self):
        current_selection = self._get_selection_state()
        if current_selection:
            self.element_action.selection_state = current_selection

    def edit_current_action(self):
        current_action = None
        job_row = self.current_job_index()
        if 0 <= job_row < self.num_project_jobs():
            job = self.project_job(job_row)
            if self.job_list_has_focus():
                current_action = job
            elif self.action_list_has_focus():
                job_row, _action_row, pos = self.get_current_action()
                if pos.actions is not None:
                    current_action = pos.action if not pos.is_sub_action else pos.sub_action
        if current_action is not None:
            self.edit_action(current_action)

    def delete_element(self, selection=None, update_project=True, confirm=True):
        if selection is None:
            old_state = self._get_selection_state()
            if update_project:
                deleted_element, new_selection = self.element_action.delete_element(confirm)
                if new_selection is not False:
                    self.refresh_ui(new_selection)
            else:
                deleted_element = None
                self.refresh_ui()
            if old_state and old_state.is_valid():
                self.widget_deleted_signal.emit((
                    old_state.job_index,
                    old_state.action_index,
                    old_state.subaction_index,
                    old_state.widget_type
                ))
            return deleted_element
        if selection and selection.is_valid():
            job_idx = selection.job_index
            if job_idx >= 0:
                new_job_idx = max(0, min(job_idx, self.num_project_jobs() - 1))
                self.refresh_ui(rows_to_state(self.project(), new_job_idx, -1))
        return None

    def copy_element(self):
        self._sync_selection_to_action_manager()
        self.element_action.copy_element()

    def paste_element(self, selection=None, update_project=True):
        if selection is None:
            self._sync_selection_to_action_manager()
            old_state = self._get_selection_state()
            if update_project:
                result = self.element_action.paste_element()
                if result:
                    current_state = self._get_selection_state()
                    self.refresh_ui(rows_to_state(
                        self.project(),
                        current_state.job_index,
                        current_state.get_action_row()))
            else:
                self.refresh_ui()
            if old_state and old_state.is_valid():
                self.widget_pasted_signal.emit((
                    old_state.job_index,
                    old_state.action_index,
                    old_state.subaction_index,
                    old_state.widget_type
                ))
            return result
        if selection and selection.is_valid():
            self.refresh_ui(
                rows_to_state(
                    self.project(), selection.job_index, -1))
        return None

    def cut_element(self):
        self._sync_selection_to_action_manager()
        old_state = self._get_selection_state()
        self.element_action.cut_element()
        if old_state and old_state.is_valid():
            self.widget_deleted_signal.emit((
                old_state.job_index,
                old_state.action_index,
                old_state.subaction_index,
                old_state.widget_type
            ))

    def clone_element(self, selection=None, update_project=True, confirm=True):
        if selection is None:
            old_state = self._get_selection_state()
            if update_project:
                success, new_state = self.element_action.clone_element()
                if success:
                    self.refresh_ui(restore_state=new_state)
            else:
                self.refresh_ui()
            if old_state and old_state.is_valid():
                self.widget_cloned_signal.emit((
                    old_state.job_index,
                    old_state.action_index,
                    old_state.subaction_index,
                    old_state.widget_type
                ))
        elif selection and selection.is_valid():
            job_idx = selection.job_index
            if job_idx >= 0:
                new_job_idx = max(0, min(job_idx, self.num_project_jobs() - 1))
                self.refresh_ui(rows_to_state(self.project(), new_job_idx, -1))

    def enable(self, selection=None, update_project=True):
        self._set_enabled(True, selection, update_project)

    def disable(self, selection=None, update_project=True):
        self._set_enabled(False, selection, update_project)

    def _set_enabled(self, enabled, selection=None, update_project=True):
        self._sync_selection_to_action_manager()
        new_selection = False
        if selection is None:
            new_selection = self.element_action.set_enabled(enabled)
            if update_project:
                self.widget_enable_signal.emit((
                    self.selection_state.job_index,
                    self.selection_state.action_index,
                    self.selection_state.subaction_index,
                    self.selection_state.widget_type
                ), enabled)
        else:
            if update_project:
                new_selection = self.element_action.set_enabled(enabled, selection)
            else:
                self.refresh_ui()
        if new_selection is not False:
            self.refresh_ui(new_selection)

    def enable_all(self, update_project=True):
        self._set_enabled_all(True, update_project)

    def disable_all(self, update_project=True):
        self._set_enabled_all(False, update_project)

    def _set_enabled_all(self, enabled, update_project=True):
        if update_project:
            self.element_action.set_enabled_all(enabled)
            self.widget_enable_all_signal.emit(enabled)
        self.refresh_ui(self.selection_state)

    def _position_to_action_row(self, position):
        job_idx, action_idx, sub_idx = position
        if job_idx < 0:
            return -1
        job = self.project_job(job_idx)
        row = 0
        for i in range(action_idx):
            if i < len(job.sub_actions):
                row += 1
                action = job.sub_actions[i]
                row += len(action.sub_actions)
        if sub_idx >= 0:
            row += sub_idx + 1
        return row

    def shift_element(self, delta, direction, selection=None, update_project=True):
        self._sync_selection_to_action_manager()
        if selection is None:
            old_state = self._get_selection_state()
            if update_project:
                pre_move_project = self.project().clone()
                from_position = self._get_current_position_tuple()
                new_selection = self.element_action.shift_element(delta)
                if new_selection is not False:
                    self.refresh_ui(new_selection)
                    to_position = self._get_current_position_tuple()
                    affected_position = from_position + to_position
                    self.save_undo_state(
                        pre_move_project, f"Move {direction}", "move", affected_position)
            else:
                new_selection = None
            if new_selection and old_state and old_state.is_valid():
                self.widget_moved_up_signal.emit((
                    old_state.job_index,
                    old_state.action_index,
                    old_state.subaction_index,
                    old_state.widget_type
                ))
            return new_selection
        if selection and selection.is_valid():
            job_idx = selection.job_index
            if job_idx >= 0:
                new_job_idx = max(0, min(job_idx, self.num_project_jobs() - 1))
                self.refresh_ui(rows_to_state(self.project(), new_job_idx, -1))
        return None

    def _get_current_subaction_index(self):
        if not self.selection_state.is_subaction_selected():
            return -1
        return self.selection_state.subaction_index

    def add_action(self, type_name):
        self._sync_selection_to_action_manager()
        current_job_index = self.current_job_index()
        if current_job_index < 0:
            if self.num_project_jobs() > 0:
                QMessageBox.warning(self.parent(), "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self.parent(), "No Job Added", "Please add a job first.")
            return False
        job = self.project_job(current_job_index)
        insert_index = len(job.sub_actions)
        selection = self.selection_state
        if selection.is_action_selected():
            if selection.action_index >= 0:
                insert_index = selection.action_index + 1
        elif selection.is_subaction_selected():
            if selection.action_index >= 0:
                insert_index = selection.action_index + 1
        action = ActionConfig(type_name)
        action.parent = self.get_current_job()
        self.action_dialog = ActionConfigDialog(
            action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            self.mark_as_modified(True, "Add Action", "add", (current_job_index, insert_index, -1))
            job.sub_actions.insert(insert_index, action)
            gui_insert_pos = self.get_insertion_position(selection)[0]
            self.add_list_item(self.action_list(), action, False, gui_insert_pos)
            self.widget_added_signal.emit((current_job_index, insert_index, -1))
            self.set_current_action(gui_insert_pos)
            return True
        return False

    def add_sub_action(self, type_name):
        self._sync_selection_to_action_manager()
        current_job_index = self.current_job_index()
        current_action_index = self.current_action_index()
        if current_job_index < 0 or current_action_index < 0 or \
                current_job_index >= self.num_project_jobs():
            return False
        job = self.project_job(current_job_index)
        selection = self.selection_state
        if not selection.is_action_selected() and not selection.is_subaction_selected():
            return False
        action_index = selection.action_index
        if action_index < 0 or action_index >= len(job.sub_actions):
            return False
        action = job.sub_actions[action_index]
        if action.type_name != constants.ACTION_COMBO:
            return False
        insert_index = len(action.sub_actions)
        if selection.is_subaction_selected():
            if selection.subaction_index >= 0:
                insert_index = selection.subaction_index + 1
        sub_action = ActionConfig(type_name)
        self.action_dialog = ActionConfigDialog(
            sub_action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            self.mark_as_modified(
                True, "Add Sub-action", "add", (current_job_index, action_index, insert_index))
            action.sub_actions.insert(insert_index, sub_action)
            gui_insert_pos = self.get_insertion_position(selection)[0]
            self.add_list_item(self.action_list(), sub_action, True, gui_insert_pos)
            self.widget_added_signal.emit((current_job_index, action_index, insert_index))
            self.set_current_action(gui_insert_pos)
            self.action_list_item(gui_insert_pos).setSelected(True)
            return True
        return False

    def update_added_element(self, _indices_tuple):
        self.refresh_ui()

    def update_widget(self, selection=None, update_project=True):
        self.refresh_ui()

    # pylint: disable=C0103
    def contextMenuEvent(self, event):
        item = self.job_list().itemAt(self.job_list().viewport().mapFrom(self, event.pos()))
        current_action = None
        if item:
            index = self.job_list().row(item)
            current_action = self.get_job_at(index)
            self.set_current_job(index)
        item = self.action_list().itemAt(self.action_list().viewport().mapFrom(self, event.pos()))
        if item:
            index = self.action_list().row(item)
            self.set_current_action(index)
            _job_row, _action_row, pos = self.get_action_at(index)
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
        if current_action:
            menu = self.create_common_context_menu(current_action)
            menu.exec(event.globalPos())
    # pylint: enable=C0103

    def get_current_selected_action(self):
        if self.job_list_has_focus():
            job_row = self.current_job_index()
            if 0 <= job_row < self.num_project_jobs():
                return self.project_job(job_row)
        elif self.action_list_has_focus():
            _job_row, _action_row, pos = self.get_current_action()
            if pos.actions is not None:
                return pos.action if not pos.is_sub_action else pos.sub_action
        return None

    def get_job_at(self, index):
        return None if index < 0 else self.project_job(index)

    def action_config_dialog(self, action):
        return ActionConfigDialog(action, self.current_file_directory(), self.parent())

    def on_job_edit(self, item):
        index = self.job_list().row(item)
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            pre_edit_project = self.project().clone()
            dialog = self.action_config_dialog(job)
            if dialog.exec() == QDialog.Accepted:
                self.save_undo_state(pre_edit_project, "Edit Job", "edit", (index, -1, -1))
                current_row = self.current_job_index()
                if current_row >= 0:
                    self.job_list_item(current_row).setText(job.params['name'])
                self.refresh_ui()
                self.widget_updated_signal.emit((index, -1, -1, 'job'))

    def on_action_edit(self, item):
        job_index = self.current_job_index()
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            action_index = self.action_list().row(item)
            current_action, is_sub_action = self.get_current_action_at(job, action_index)
            if current_action:
                if not is_sub_action:
                    self.enable_sub_actions_requested.emit(
                        current_action.type_name == constants.ACTION_COMBO)
                pre_edit_project = self.project().clone()
                dialog = self.action_config_dialog(current_action)
                if dialog.exec() == QDialog.Accepted:
                    widget_type = 'subaction' if is_sub_action else 'action'
                    subaction_index = -1
                    if is_sub_action:
                        subaction_index = self._get_current_subaction_index()
                    self.save_undo_state(
                        pre_edit_project, f"Edit {widget_type}", "edit",
                        (job_index, action_index, subaction_index))
                    self.on_job_selected(job_index)
                    self.refresh_ui()
                    self.set_current_job(job_index)
                    self.set_current_action(action_index)
                    self.widget_updated_signal.emit(
                        (job_index, action_index, subaction_index, widget_type))

    def on_job_selected(self, index):
        self.clear_action_list()
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            for action in job.sub_actions:
                self.add_list_item(self.action_list(), action, False)
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.add_list_item(self.action_list(), sub_action, True)
            self.select_signal.emit()
        self._get_selection_state()

    def _get_selection_state(self):
        if self.action_list_has_focus() and self.num_selected_actions() > 0:
            _job_row, _action_row, pos = self.get_current_action()
            if pos is not None:
                self.selection_state.actions = pos.actions
                self.selection_state.sub_actions = pos.sub_actions
                self.selection_state.action_index = pos.action_index
                self.selection_state.subaction_index = pos.subaction_index
                self.selection_state.job_index = pos.job_index
                self.selection_state.widget_type = pos.widget_type
        elif self.job_list_has_focus() and self.num_selected_jobs() > 0:
            job_idx = self.current_job_index()
            if 0 <= job_idx < self.num_project_jobs():
                self.selection_state.actions = None
                self.selection_state.sub_actions = None
                self.selection_state.action_index = -1
                self.selection_state.subaction_index = -1
                self.selection_state.job_index = job_idx
                self.selection_state.widget_type = 'job'
        else:
            self.selection_state.reset()
        return self.selection_state.copy()

    def _ensure_selected_visible(self):
        pass

    def _selection_callback(self, widget_type, job_index, _action_index=None,
                            _subaction_index=None):
        if widget_type == 'job':
            self.set_current_job(job_index)
        elif widget_type == 'action':
            self.set_current_job(job_index)
        elif widget_type == 'subaction':
            self.set_current_job(job_index)

    def handle_run_completed(self):
        self.run_finished_signal.emit()

    def quit(self):
        for worker in self._workers:
            worker.stop()
        self.close()
        return True

    def change_theme(self, dark_theme):
        self.dark_theme = dark_theme
        self.tab_widget.change_theme(dark_theme)
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        self.set_style_sheet(dark_theme)

    def save_current_selection(self):
        self._saved_selection = self._get_selection_state()

    def restore_saved_selection(self):
        if self._saved_selection is None:
            return
        self.refresh_ui(restore_state=self._saved_selection)
        self._saved_selection = None

    def refresh_and_restore_selection(self, entry=None):
        if entry:
            self.refresh_ui(restore_state=self._saved_selection)
        else:
            self.restore_saved_selection()
