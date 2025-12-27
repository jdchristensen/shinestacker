# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QMessageBox, QApplication, QDialog)
from .. config.constants import constants
from .. gui.project_view import ProjectView
from .. gui.colors import ColorPalette
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.project_model import ActionConfig
from .. gui.run_worker import JobLogWorker, ProjectLogWorker
from .tab_widget import TabWidgetWithPlaceholder
from .gui_run import RunWindow
from .list_container import ListContainer, ActionPosition


def new_row_after_clone(job, action_row, is_sub_action, cloned):
    return action_row + 1 if is_sub_action else \
        sum(1 + len(action.sub_actions)
            for action in job.sub_actions[:job.sub_actions.index(cloned)])


def new_row_after_delete(action_row, pos: ActionPosition):
    if pos.is_sub_action:
        new_row = action_row if pos.sub_action_index < len(pos.sub_actions) else action_row - 1
    else:
        if pos.action_index == 0:
            new_row = 0 if len(pos.actions) > 0 else -1
        elif pos.action_index < len(pos.actions):
            new_row = action_row
        elif pos.action_index == len(pos.actions):
            new_row = action_row - len(pos.actions[pos.action_index - 1].sub_actions) - 1
        else:
            new_row = None
    return new_row


def new_row_after_paste(action_row, pos: ActionPosition):
    return new_row_after_insert(action_row, pos, 0)


def new_row_after_insert(action_row, pos: ActionPosition, delta):
    new_row = action_row
    if not pos.is_sub_action:
        new_index = pos.action_index + delta
        if 0 <= new_index < len(pos.actions):
            new_row = 0
            for action in pos.actions[:new_index]:
                new_row += 1 + len(action.sub_actions)
    else:
        new_index = pos.sub_action_index + delta
        if 0 <= new_index < len(pos.sub_actions):
            new_row = 1 + new_index
            for action in pos.actions[:pos.action_index]:
                new_row += 1 + len(action.sub_actions)
    return new_row


class ClassicProjectView(ProjectView, ListContainer):
    enable_sub_actions_requested = Signal(bool)

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
        self.action_list().itemSelectionChanged.connect(update_delete_action_state)
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

    def refresh_and_set_status(self, status):
        job_row, action_row, _pos = status
        self.refresh_ui(job_row, action_row)

    def refresh_and_select_job(self, job_idx):
        self.refresh_ui(job_idx)

    def refresh_ui(self, job_row=-1, action_row=-1):
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
                    not is_sub_action and current_action.type_name == constants.ACTION_COMBO
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
                               lambda id_str: self.stop_worker(self.get_tab_position(id_str)),
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
        self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.run_all_jobs_action.setEnabled(True)
        self.menu_manager.stop_action.setEnabled(False)

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
        worker.run_completed_signal.connect(
            lambda run_id: self.handle_run_completed(window, run_id))
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
            return
        if current_index >= 0:
            job = self.project_job(current_index)
            validation_result = self.validate_output_paths_for_job(job)
            if not validation_result['valid']:
                proceed = self.show_validation_warning(validation_result, is_single_job=True)
                if not proceed:
                    return
            if job.enabled():
                job_name = job.params["name"]
                labels = [[(self.action_text(a), a.enabled()) for a in job.sub_actions]]
                r = self.get_retouch_path(job)
                retouch_paths = [] if len(r) == 0 else [(job_name, r)]
                new_window, id_str = self.create_new_window(f"{job_name} [Job]",
                                                            labels, retouch_paths)
                worker = JobLogWorker(job, id_str)
                self.connect_worker_signals(worker, new_window)
                self.menu_manager.run_job_action.setEnabled(False)
                self.menu_manager.run_all_jobs_action.setEnabled(False)
                self.start_thread(worker)
                self._workers.append(worker)
            else:
                QMessageBox.warning(self, "Can't run Job",
                                    "Job " + job.params["name"] + " is disabled.")
                return
        self.menu_manager.stop_action.setEnabled(True)

    def run_all_jobs(self):
        validation_result = self.validate_output_paths_for_project()
        if not validation_result['valid']:
            proceed = self.show_validation_warning(validation_result, is_single_job=False)
            if not proceed:
                return
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
        self.menu_manager.run_job_action.setEnabled(False)
        self.menu_manager.run_all_jobs_action.setEnabled(False)
        self.start_thread(worker)
        self._workers.append(worker)
        self.menu_manager.stop_action.setEnabled(True)

    def stop(self):
        tab_position = self.tab_widget.count()
        if tab_position > 0:
            self.stop_worker(tab_position - 1)
            self.menu_manager.stop_action.setEnabled(False)

    def handle_end_message(self, status, id_str, message):
        self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.run_all_jobs_action.setEnabled(True)
        tab = self.get_tab_at_position(id_str)
        tab.close_button.setEnabled(True)
        tab.stop_button.setEnabled(False)
        if hasattr(tab, 'retouch_widget') and tab.retouch_widget is not None:
            tab.retouch_widget.setEnabled(True)

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

    def delete_job(self, confirm=True):
        current_index = self.current_job_index()
        if 0 <= current_index < self.num_project_jobs():
            if confirm:
                reply = QMessageBox.question(
                    self.parent(), "Confirm Delete",
                    "Are you sure you want to delete job "
                    f"'{self.project_job(current_index).params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                self.take_job(current_index)
                self.mark_as_modified(True, "Delete Job")
                current_job = self.project_jobs().pop(current_index)
                self.clear_action_list()
                self.refresh_ui(-1, -1)
                return current_job
        return None

    def delete_action(self, confirm=True):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None:
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
            if confirm:
                reply = QMessageBox.question(
                    self.parent(),
                    "Confirm Delete",
                    "Are you sure you want to delete action "
                    f"'{self.action_text(current_action, pos.is_sub_action, indent=False)}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                if pos.is_sub_action:
                    self.mark_as_modified(True, "Delete Action")
                    pos.action.pop_sub_action(pos.sub_action_index)
                else:
                    self.mark_as_modified(True, "Delete Sub-action")
                    self.project_job(job_row).pop_sub_action(pos.action_index)
                new_row = new_row_after_delete(action_row, pos)
                self.refresh_ui(job_row, new_row)
            return current_action
        return None

    def delete_element(self, confirm=True):
        if self.job_list_has_focus():
            element = self.delete_job(confirm)
        elif self.action_list_has_focus():
            element = self.delete_action(confirm)
        else:
            element = None
        return element

    def copy_job(self):
        current_index = self.current_job_index()
        if 0 <= current_index < self.num_project_jobs():
            self.set_copy_buffer(self.project_job(current_index).clone())

    def copy_action(self):
        _job_row, _action_row, pos = self.get_current_action()
        if pos.actions is not None:
            self.set_copy_buffer(pos.sub_action.clone()
                                 if pos.is_sub_action else pos.action.clone())

    def copy_element(self):
        if self.job_list_has_focus():
            self.copy_job()
        elif self.action_list_has_focus():
            self.copy_action()

    def paste_job(self):
        if self.copy_buffer().type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return
            if self.copy_buffer().type_name not in constants.ACTION_TYPES:
                return
            current_job = self.project_job(self.current_job_index())
            new_action_index = len(current_job.sub_actions)
            current_job.sub_actions.insert(new_action_index, self.copy_buffer())
            self.set_current_action(new_action_index)
            self.refresh_ui(self.current_job_index(), -1)
            return
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(self.current_job_index() + 1, 0), self.num_project_jobs() - 1)
        self.mark_as_modified(True, "Paste Job")
        self.project_jobs().insert(new_job_index, self.copy_buffer())
        self.set_current_job(new_job_index)
        self.set_current_action(new_job_index)
        self.refresh_ui(new_job_index, -1)

    def paste_action(self):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None and pos.actions is not None:
            copy_buffer = self.copy_buffer()
            if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
                target_action = None
                insertion_index = 0
                if pos.is_sub_action:
                    if pos.action.type_name == constants.ACTION_COMBO:
                        target_action = pos.action
                        insertion_index = len(pos.sub_actions)
                else:
                    if pos.action is not None and pos.action.type_name == constants.ACTION_COMBO:
                        target_action = pos.action
                        insertion_index = len(pos.action.sub_actions)
                if target_action is not None:
                    self.mark_as_modified(True, "Paste Sub-action")
                    target_action.sub_actions.insert(insertion_index, copy_buffer)
                    new_row = new_row_after_paste(action_row, pos)
                    self.refresh_ui(job_row, new_row)
                    return
            if copy_buffer.type_name in constants.ACTION_TYPES:
                if not pos.is_sub_action:
                    new_action_index = 0 if len(pos.actions) == 0 else pos.action_index + 1
                    self.mark_as_modified(True, "Paste Action")
                    pos.actions.insert(new_action_index, copy_buffer)
                    new_row = new_row_after_paste(action_row, pos)
                    self.refresh_ui(job_row, new_row)

    def paste_element(self):
        if self.has_copy_buffer():
            if self.job_list_has_focus():
                self.paste_job()
            elif self.action_list_has_focus():
                self.paste_action()

    def cut_element(self):
        self.set_copy_buffer(self.delete_element(False))

    def clone_job(self):
        job_index = self.current_job_index()
        if 0 <= job_index < self.num_project_jobs():
            job_clone = self.project_job(job_index).clone(self.CLONE_POSTFIX)
            new_job_index = job_index + 1
            self.mark_as_modified(True, "Duplicate Job")
            self.project_jobs().insert(new_job_index, job_clone)
            self.set_current_job(new_job_index)
            self.set_current_action(new_job_index)
            self.refresh_ui(new_job_index, -1)

    def clone_action(self):
        job_row, action_row, pos = self.get_current_action()
        if not pos.actions:
            return
        self.mark_as_modified(True, "Duplicate Action")
        job = self.project_job(job_row)
        if pos.is_sub_action:
            cloned = pos.sub_action.clone(self.CLONE_POSTFIX)
            pos.sub_actions.insert(pos.sub_action_index + 1, cloned)
        else:
            cloned = pos.action.clone(self.CLONE_POSTFIX)
            job.sub_actions.insert(pos.action_index + 1, cloned)
        new_row = new_row_after_clone(job, action_row, pos.is_sub_action, cloned)
        self.refresh_ui(job_row, new_row)

    def clone_element(self):
        if self.job_list_has_focus():
            self.clone_job()
        elif self.action_list_has_focus():
            self.clone_action()

    def set_enabled(self, enabled):
        current_action = None
        if self.job_list_has_focus():
            job_row = self.current_job_index()
            if 0 <= job_row < self.num_project_jobs():
                current_action = self.project_job(job_row)
            action_row = -1
        elif self.action_list_has_focus():
            job_row, action_row, pos = self.get_current_action()
            current_action = pos.sub_action if pos.is_sub_action else pos.action
        else:
            action_row = -1
        if current_action:
            if current_action.enabled() != enabled:
                if enabled:
                    self.mark_as_modified(True, "Enable")
                else:
                    self.mark_as_modified(True, "Disable")
                current_action.set_enabled(enabled)
                self.refresh_ui(job_row, action_row)

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)

    def set_enabled_all(self, enable=True):
        self.mark_as_modified(True, "Enable All")
        job_row = self.current_job_index()
        action_row = self.current_action_index()
        for j in self.project_jobs():
            j.set_enabled_all(enable)
        self.refresh_ui(job_row, action_row)

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def shift_job(self, delta):
        job_index = self.current_job_index()
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project_jobs()
            self.mark_as_modified(True, "Shift Job")
            jobs.insert(new_index, jobs.pop(job_index))
            self.refresh_ui(new_index, -1)

    def shift_action(self, delta):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None:
            if not pos.is_sub_action:
                new_index = pos.action_index + delta
                if 0 <= new_index < len(pos.actions):
                    self.mark_as_modified(True, "Shift Action")
                    pos.actions.insert(new_index, pos.actions.pop(pos.action_index))
            else:
                new_index = pos.sub_action_index + delta
                if 0 <= new_index < len(pos.sub_actions):
                    self.mark_as_modified(True, "Shift Sub-action")
                    pos.sub_actions.insert(new_index, pos.sub_actions.pop(pos.sub_action_index))
            new_row = new_row_after_insert(action_row, pos, delta)
            self.refresh_ui(job_row, new_row)

    def move_element_up(self):
        if self.job_list_has_focus():
            self.shift_job(-1)
        elif self.action_list_has_focus():
            self.shift_action(-1)

    def move_element_down(self):
        if self.job_list_has_focus():
            self.shift_job(+1)
        elif self.action_list_has_focus():
            self.shift_action(+1)

    def add_action(self, type_name):
        current_index = self.current_job_index()
        if current_index < 0:
            if self.num_project_jobs() > 0:
                QMessageBox.warning(self.parent(),
                                    "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self.parent(),
                                    "No Job Added", "Please add a job first.")
            return False
        action = ActionConfig(type_name)
        action.parent = self.get_current_job()
        self.action_dialog = ActionConfigDialog(
            action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            self.mark_as_modified("Add Action")
            self.project_job(current_index).add_sub_action(action)
            self.add_list_item(self.action_list(), action, False)
            return True
        return False

    def add_sub_action(self, type_name):
        current_job_index = self.current_job_index()
        current_action_index = self.current_action_index()
        if current_job_index < 0 or current_action_index < 0 or \
           current_job_index >= self.num_project_jobs():
            return False
        job = self.project_job(current_job_index)
        action = None
        action_counter = -1
        for act in job.sub_actions:
            action_counter += 1
            if action_counter == current_action_index:
                action = act
                break
            action_counter += len(act.sub_actions)
        if not action or action.type_name != constants.ACTION_COMBO:
            return False
        sub_action = ActionConfig(type_name)
        self.action_dialog = ActionConfigDialog(
            sub_action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            self.mark_as_modified("Add Sub-action")
            action.add_sub_action(sub_action)
            self.on_job_selected(current_job_index)
            self.set_current_action(current_action_index)
            self.action_list_item(current_action_index).setSelected(True)
            return True
        return False

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

    def get_action_at(self, action_row):
        job_row = self.current_job_index()
        if job_row < 0 or action_row < 0:
            return (job_row, action_row, None)
        action, sub_action, sub_action_index = self.find_action_position(job_row, action_row)
        if not action:
            return (job_row, action_row, None)
        job = self.project_job(job_row)
        if sub_action:
            return (job_row, action_row,
                    ActionPosition(job.sub_actions, action.sub_actions,
                                   job.sub_actions.index(action), sub_action_index))
        return (job_row, action_row,
                ActionPosition(job.sub_actions, None, job.sub_actions.index(action)))

    def action_config_dialog(self, action):
        return ActionConfigDialog(action, self.current_file_directory(), self.parent())

    def on_job_edit(self, item):
        index = self.job_list().row(item)
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            dialog = self.action_config_dialog(job)
            if dialog.exec() == QDialog.Accepted:
                current_row = self.current_job_index()
                if current_row >= 0:
                    self.job_list_item(current_row).setText(job.params['name'])
                self.refresh_ui()

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
                dialog = self.action_config_dialog(current_action)
                if dialog.exec() == QDialog.Accepted:
                    self.on_job_selected(job_index)
                    self.refresh_ui()
                    self.set_current_job(job_index)
                    self.set_current_action(action_index)

    def handle_run_completed(self, window, run_id):
        window.handle_run_completed(run_id)
        self.menu_manager.stop_action.setEnabled(False)
        self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.run_all_jobs_action.setEnabled(True)

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
