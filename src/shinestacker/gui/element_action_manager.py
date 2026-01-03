# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from .. config.constants import constants
from .. gui.project_handler import ProjectHandler


class ElementActionManager(ProjectHandler, QObject):
    CLONE_POSTFIX = ' (clone)'

    def __init__(self, project_holder, parent=None):
        ProjectHandler.__init__(self, project_holder)
        QObject.__init__(self, parent)

    def confirm_delete_message(self, type_name, element_name, parent_widget):
        return QMessageBox.question(
            parent_widget, "Confirm Delete",
            f"Are you sure you want to delete {type_name} '{element_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

    def paste_job_logic(self, copy_buffer, job_index, clone_buffer):
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

    def clone_element(self):
        if self.is_job_selected():
            self.clone_job()
        elif self.is_action_selected() or self.is_subaction_selected():
            self.clone_action()

    def is_job_selected(self):
        raise NotImplementedError

    def is_action_selected(self):
        raise NotImplementedError

    def is_subaction_selected(self):
        raise NotImplementedError
