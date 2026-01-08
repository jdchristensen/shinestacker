# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, W0613
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from .. config.constants import constants
from .project_handler import ProjectHandler


class ElementActionManager(ProjectHandler, QObject):
    CLONE_POSTFIX = ' (clone)'

    def __init__(self, project_holder, parent=None):
        ProjectHandler.__init__(self, project_holder)
        QObject.__init__(self, parent)

    def is_job_selected(self):
        raise NotImplementedError

    def is_action_selected(self):
        raise NotImplementedError

    def is_subaction_selected(self):
        raise NotImplementedError

    def get_selected_job_index(self):
        raise NotImplementedError

    def confirm_delete_message(self, type_name, element_name):
        return QMessageBox.question(
            self.parent(), "Confirm Delete",
            f"Are you sure you want to delete {type_name} '{element_name}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes

    def paste_job_logic(self, copy_buffer, job_index, clone_buffer, description="",
                        action_type="", affected_position=None):
        if affected_position:
            self.mark_as_modified(True, description, action_type, affected_position)
        if copy_buffer.type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return False, None, None
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return False, None, None
            current_job = self.project().jobs[job_index]
            new_action_index = len(current_job.sub_actions)
            element = copy_buffer.clone() if clone_buffer else copy_buffer
            current_job.sub_actions.insert(new_action_index, element)
            return True, 'action', new_action_index
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(job_index + 1, 0), self.num_project_jobs())
        element = copy_buffer.clone() if clone_buffer else copy_buffer
        self.project().jobs.insert(new_job_index, element)
        return True, 'job', new_job_index

    def copy_element(self):
        if self.is_job_selected():
            self.copy_job()
        elif self.is_action_selected():
            self.copy_action()
        elif self.is_subaction_selected():
            self.copy_subaction()

    def copy_job(self):
        if not self.is_job_selected():
            return
        job_index = self.get_selected_job_index()
        if not 0 <= job_index < self.num_project_jobs():
            return
        job_clone = self.project().jobs[job_index].clone()
        self.set_copy_buffer(job_clone)

    def shift_element(self, delta):
        if self.is_job_selected():
            return self._shift_job(delta)
        if self.is_action_selected():
            return self._shift_action(delta)
        if self.is_subaction_selected():
            return self._shift_subaction(delta)
        return False

    def _set_element_enabled(self, element, enabled, element_type):
        element.set_enabled(enabled)

    def set_enabled_all(self, enabled):
        action = "Enable" if enabled else "Disable"
        self.mark_as_modified(True, f"{action} All")
        for job in self.project().jobs:
            job.set_enabled_all(enabled)
