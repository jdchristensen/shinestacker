# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=W0613
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QMessageBox, QApplication, QDialog)
from .. config.constants import constants
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.colors import ColorPalette
from .. common_project.run_worker import JobLogWorker, ProjectLogWorker
from .. common_project.project_view import ProjectView
from .. common_project.selection_state import SelectionState
from .tab_widget import TabWidgetWithPlaceholder
from .gui_run import RunWindow
from .list_container import ListContainer, get_action_row


def rows_to_state(project, job_row, action_row):
    if job_row < 0:
        return None
    if action_row < 0:
        state = SelectionState(job_row, -1, -1)
        state.widget_type = 'job'
        return state
    job = project.jobs[job_row]
    current_row = -1
    for i, action in enumerate(job.sub_actions):
        current_row += 1
        if current_row == action_row:
            state = SelectionState(job_row, i, -1)
            state.widget_type = 'action'
            return state
        if action.sub_actions:
            for sub_idx, _ in enumerate(action.sub_actions):
                current_row += 1
                if current_row == action_row:
                    state = SelectionState(job_row, i, sub_idx)
                    state.widget_type = 'subaction'
                    return state
    state = SelectionState(job_row, -1, -1)
    state.widget_type = 'job'
    return state


class ClassicProjectView(ProjectView, ListContainer):
    def __init__(self, project_holder, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, dark_theme, parent)
        ListContainer.__init__(self, dark_theme)
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
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        self.set_style_sheet(dark_theme)
        self.job_list().enter_key_pressed.connect(self.edit_current_action)
        self.action_list().enter_key_pressed.connect(self.edit_current_action)
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

    def update_focus_styles(self):
        ListContainer.update_focus_styles(self)

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
                actions = None
                if job_row >= 0:
                    job = self.project_job(job_row)
                    actions = job.sub_actions if job else None
                action_row = get_action_row(restore_state, actions)
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

    def delete_element(self, selection=None, update_project=True, confirm=True):
        self._sync_selection_to_action_manager()
        deleted_element = None
        old_selection = self._get_selection_state().copy() if selection is None \
            else selection.copy()
        if selection is None:
            if update_project:
                deleted_element, _removal_state, new_selection = \
                    self.element_action.delete_element(confirm)
                if new_selection is not False:
                    self.refresh_ui(new_selection)
            else:
                deleted_element = None
                self.refresh_ui()
        elif selection.is_valid():
            job_idx = selection.job_index
            if job_idx >= 0:
                new_job_idx = max(0, min(job_idx, self.num_project_jobs() - 1))
                self.refresh_ui(rows_to_state(self.project(), new_job_idx, -1))
        return deleted_element, old_selection

    def copy_element(self):
        self._sync_selection_to_action_manager()
        ProjectView.copy_element(self)

    def paste_element(self, selection=None, update_project=True):
        self._sync_selection_to_action_manager()
        success = False
        old_selection = self._get_selection_state().copy() if selection is None \
            else selection.copy()
        if selection is None:
            if update_project:
                success = self.element_action.paste_element()
                if success:
                    current_state = self._get_selection_state()
                    actions = None
                    if current_state.job_index >= 0:
                        job = self.project_job(current_state.job_index)
                        if job:
                            actions = job.sub_actions
                    action_row = get_action_row(current_state, actions)
                    self.refresh_ui(rows_to_state(
                        self.project(), current_state.job_index, action_row))
            else:
                self.refresh_ui()
        if selection and selection.is_valid():
            self.refresh_ui(
                rows_to_state(
                    self.project(), selection.job_index, -1))
        return success, old_selection

    def cut_element(self):
        self._sync_selection_to_action_manager()
        deleted_element = None
        old_selection = self._get_selection_state().copy()
        deleted_element, _removal_state, new_selection = self.element_action.cut_element()
        if deleted_element:
            if new_selection:
                self.refresh_ui(new_selection)
            else:
                self.refresh_ui()
        return deleted_element, old_selection

    def clone_element(self, selection=None, update_project=True, confirm=True):
        old_selection = self._get_selection_state().copy() if selection is None \
            else selection.copy()
        success = False
        if selection is None:
            if update_project:
                success, new_state = self.element_action.clone_element()
                if success:
                    self.refresh_ui(restore_state=new_state)
            else:
                self.refresh_ui()
        elif selection and selection.is_valid():
            job_idx = selection.job_index
            if job_idx >= 0:
                new_job_idx = max(0, min(job_idx, self.num_project_jobs() - 1))
                self.refresh_ui(rows_to_state(self.project(), new_job_idx, -1))
        return success, old_selection

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
                self.widget_enable_signal.emit(self.selection_state, enabled)
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

    def _before_shift_element(self):
        self._sync_selection_to_action_manager()
        return True

    def _update_ui_after_shift_element(self, old_selection, selection, success, new_selection):
        if selection is None:
            if success:
                self.refresh_ui(new_selection)
            else:
                self.refresh_ui()
        elif selection.is_valid():
            job_idx = selection.job_index
            if job_idx >= 0:
                new_job_idx = max(0, min(job_idx, self.num_project_jobs() - 1))
                self.refresh_ui(rows_to_state(self.project(), new_job_idx, -1))
            else:
                self.refresh_ui()
        else:
            self.refresh_ui()

    def _get_current_subaction_index(self):
        if not self.selection_state.is_subaction_selected():
            return -1
        return self.selection_state.subaction_index

    def _before_add_action(self):
        self._sync_selection_to_action_manager()
        return True

    def _update_ui_after_add_action(self, action, position):
        selection = self.selection_state
        gui_insert_pos = self.get_insertion_position(selection)[0]
        self.add_list_item(self.action_list(), action, False, gui_insert_pos)
        self.set_current_action(gui_insert_pos)

    def current_job_index(self):
        return ListContainer.current_job_index(self)

    def _before_add_sub_action(self):
        self._sync_selection_to_action_manager()
        return True

    def _update_ui_after_add_sub_action(self, sub_action, position):
        job_index, action_index, insert_index = position
        gui_insert_pos = self._calculate_gui_sub_action_position(
            job_index, action_index, insert_index)
        self.add_list_item(self.action_list(), sub_action, True, gui_insert_pos)
        self.set_current_action(gui_insert_pos)
        self.action_list_item(gui_insert_pos).setSelected(True)

    def _calculate_gui_sub_action_position(self, job_index, action_index, subaction_index):
        job = self.project_job(job_index)
        row = 0
        for i in range(action_index):
            if i < len(job.sub_actions):
                row += 1
                action = job.sub_actions[i]
                row += len(action.sub_actions)
        row += subaction_index + 1
        return row

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
                self.widget_updated_signal.emit(rows_to_state(self.project(), index, -1))

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
                        rows_to_state(self.project(), job_index, action_index))

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
                self.selection_state.set_indices(
                    pos.job_index, pos.action_index, pos.subaction_index)
                self.selection_state.widget_type = pos.widget_type
        elif self.job_list_has_focus() and self.num_selected_jobs() > 0:
            job_idx = self.current_job_index()
            if 0 <= job_idx < self.num_project_jobs():
                self.selection_state.set_indices(job_idx, -1, -1)
                self.selection_state.widget_type = 'job'
        else:
            self.selection_state.reset()
        return self.selection_state.copy()

    def _ensure_selected_visible(self):
        pass

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
