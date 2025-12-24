# pylint: disable=C0114, C0115, C0116, R0903, R0904, R1702, R0917, R0913, R0902, E0611, E1131, E1121
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog
from .. config.constants import constants
from .. gui.project_editor import ProjectEditor
from .list_container import ListContainer


class ClassicProjectEditor(ProjectEditor, ListContainer):
    refresh_ui_signal = Signal(int, int)
    enable_sub_actions_requested = Signal(bool)

    def __init__(self, project_holder, parent=None):
        ProjectEditor.__init__(self, project_holder, parent)
        ListContainer.__init__(self, None, None)

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
