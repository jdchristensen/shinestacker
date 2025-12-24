# pylint: disable=C0114, C0115, C0116, R0903, R0904, R1702, R0917, R0913, R0902, E0611, E1131, E1121
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog
from .. config.constants import constants
from .. gui.project_editor import ProjectEditor
from .list_container import ListContainer
from .classic_project_view import new_row_after_insert


class ClassicProjectEditor(ProjectEditor, ListContainer):
    refresh_ui_signal = Signal(int, int)
    enable_delete_action_signal = Signal(bool)
    enable_sub_actions_requested = Signal(bool)

    def __init__(self, project_holder, parent=None):
        ProjectEditor.__init__(self, project_holder, parent)
        ListContainer.__init__(self, None, None)

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

    def shift_job(self, delta):
        job_index = self.current_job_index()
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project_jobs()
            self.mark_as_modified(True, "Shift Job")
            jobs.insert(new_index, jobs.pop(job_index))
            self.refresh_ui_signal.emit(new_index, -1)

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
            self.refresh_ui_signal.emit(job_row, new_row)

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

    def edit_action(self, action):
        dialog = self.action_config_dialog(action)
        if dialog.exec() == QDialog.Accepted:
            self.on_job_selected(self.current_job_index())

    def connect_signals(self):
        self._job_list.itemDoubleClicked.connect(self.on_job_edit)
        self._action_list.itemDoubleClicked.connect(self.on_action_edit)

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
                    self.refresh_ui_signal.emit(-1, -1)
                    self.set_current_job(job_index)
                    self.set_current_action(action_index)

    def refresh_and_set_status(self, status):
        job_row, action_row, _pos = status
        self.refresh_ui_signal.emit(job_row, action_row)

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
                self.refresh_ui_signal.emit(job_row, action_row)

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
        self.refresh_ui_signal.emit(job_row, action_row)

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)

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
