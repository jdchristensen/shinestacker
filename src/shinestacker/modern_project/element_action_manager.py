# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from .. config.constants import constants
from .. gui.project_handler import ProjectHandler
from .element_operations import ElementOperations


class ElementActionManager(ProjectHandler, QObject):
    def __init__(self, project_holder, selection_state, view_callbacks):
        ProjectHandler.__init__(self, project_holder)
        QObject.__init__(self)
        self.element_ops = ElementOperations(project_holder)
        self.selection_state = selection_state
        self.callbacks = view_callbacks
        self.selection_nav = None

    def set_selection_navigation(self, selection_nav):
        self.selection_nav = selection_nav

    def delete_element(self, parent_widget, confirm=True):
        if self.selection_state.is_job_selected():
            return self._delete_job(self.selection_state.job_index, parent_widget, confirm)
        if self.selection_state.is_action_selected():
            return self._delete_action(
                self.selection_state.job_index, self.selection_state.action_index,
                parent_widget, confirm)
        if self.selection_state.is_subaction_selected():
            return self._delete_subaction(
                self.selection_state.job_index, self.selection_state.action_index,
                self.selection_state.subaction_index, parent_widget, confirm)
        return None

    def _delete_job(self, job_index, parent_widget, confirm=True):
        if confirm:
            if 0 <= job_index < self.num_project_jobs():
                job = self.project().jobs[job_index]
                reply = QMessageBox.question(
                    parent_widget, "Confirm Delete",
                    f"Are you sure you want to delete job '{job.params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return None
            else:
                return None
        deleted_job = self.element_ops.delete_job(job_index)
        if deleted_job:
            self.callbacks['mark_modified'](True, "Delete Job")
            if self.selection_nav:
                self.selection_nav.select_previous_widget()
            self.callbacks['refresh_ui']()
        return deleted_job

    def _delete_action(self, job_index, action_index, parent_widget, confirm=True):
        if confirm:
            if 0 <= job_index < self.num_project_jobs():
                job = self.project().jobs[job_index]
                if 0 <= action_index < len(job.sub_actions):
                    action = job.sub_actions[action_index]
                    reply = QMessageBox.question(
                        parent_widget, "Confirm Delete",
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
            self.callbacks['mark_modified'](True, "Delete Action")
            if self.selection_nav:
                self.selection_nav.select_previous_widget()
            self.callbacks['refresh_ui']()
        return deleted_action

    def _delete_subaction(self, job_index, action_index, subaction_index,
                          parent_widget, confirm=True):
        if confirm:
            if 0 <= job_index < self.num_project_jobs():
                job = self.project().jobs[job_index]
                if 0 <= action_index < len(job.sub_actions):
                    action = job.sub_actions[action_index]
                    if 0 <= subaction_index < len(action.sub_actions):
                        subaction = action.sub_actions[subaction_index]
                        reply = QMessageBox.question(
                            parent_widget, "Confirm Delete",
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
            self.callbacks['mark_modified'](True, "Delete Sub-action")
            if self.selection_nav:
                self.selection_nav.select_previous_widget()
            self.callbacks['refresh_ui']()
        return deleted_subaction

    def copy_element(self):
        if self.selection_state.is_job_selected():
            self.copy_job()
        elif self.selection_state.is_action_selected():
            self.copy_action()
        elif self.selection_state.is_subaction_selected():
            self.copy_subaction()

    def copy_job(self):
        job_clone = self.element_ops.copy_job(self.selection_state.job_index)
        if job_clone:
            self.callbacks['set_copy_buffer'](job_clone)

    def copy_action(self):
        if not self.selection_state.is_action_selected():
            return
        job_idx, action_idx, _ = self.selection_state.to_tuple()
        job_clone = self.element_ops.copy_action(job_idx, action_idx)
        if job_clone:
            self.callbacks['set_copy_buffer'](job_clone)

    def copy_subaction(self):
        if not self.selection_state.is_subaction_selected():
            return
        job_idx, action_idx, subaction_idx = self.selection_state.to_tuple()
        job_clone = self.element_ops.copy_subaction(job_idx, action_idx, subaction_idx)
        if job_clone:
            self.callbacks['set_copy_buffer'](job_clone)

    def paste_element(self):
        if not self.callbacks['has_copy_buffer']():
            return
        copy_buffer = self.callbacks['get_copy_buffer']()
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            self.paste_subaction()
        elif self.selection_state.is_job_selected():
            self.paste_job()
        elif self.selection_state.is_action_selected():
            self.paste_action()
        elif self.selection_state.is_subaction_selected():
            self.paste_subaction()

    def paste_job(self):
        if not self.callbacks['has_copy_buffer']():
            return
        copy_buffer = self.callbacks['get_copy_buffer']()
        if copy_buffer.type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return
            current_job = self.project().jobs[self.selection_state.job_index]
            new_action_index = len(current_job.sub_actions)
            current_job.sub_actions.insert(new_action_index, copy_buffer.clone())
            self.callbacks['mark_modified'](True, "Paste Action")
            self.selection_state.set_action(self.selection_state.job_index, new_action_index)
            self.callbacks['refresh_ui']()
            self.callbacks['ensure_selected_visible']()
            return
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(
                max(self.selection_state.job_index + 1, 0), self.num_project_jobs())
        self.callbacks['mark_modified'](True, "Paste Job")
        self.project().jobs.insert(new_job_index, copy_buffer.clone())
        self.selection_state.set_job(new_job_index)
        self.callbacks['refresh_ui']()
        self.callbacks['ensure_selected_visible']()

    def paste_action(self):
        if not self.callbacks['has_copy_buffer']():
            return
        if self.selection_state.job_index < 0:
            return
        copy_buffer = self.callbacks['get_copy_buffer']()
        if copy_buffer.type_name not in constants.ACTION_TYPES:
            return
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= 0:
            new_action_index = self.selection_state.action_index + 1
        else:
            new_action_index = len(job.sub_actions)
        job.sub_actions.insert(new_action_index, copy_buffer.clone())
        self.callbacks['mark_modified'](True, "Paste Action")
        self.selection_state.set_action(self.selection_state.job_index, new_action_index)
        self.callbacks['refresh_ui']()
        self.callbacks['ensure_selected_visible']()

    def paste_subaction(self):
        if not self.callbacks['has_copy_buffer']():
            return
        if self.selection_state.job_index < 0 or self.selection_state.action_index < 0:
            return
        copy_buffer = self.callbacks['get_copy_buffer']()
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
        self.callbacks['mark_modified'](True, "Paste Sub-action")
        self.selection_state.set_subaction(
            self.selection_state.job_index,
            self.selection_state.action_index,
            new_subaction_index)
        self.callbacks['refresh_ui']()
        self.callbacks['ensure_selected_visible']()

    def cut_element(self):
        element = self.delete_element(self.callbacks['get_parent_widget'](), False)
        if element:
            self.callbacks['set_copy_buffer'](element)

    def clone_element(self):
        if self.selection_state.is_job_selected():
            self.clone_job()
        elif self.selection_state.is_action_selected():
            self.clone_action()
        elif self.selection_state.is_subaction_selected():
            self.clone_action()

    def clone_job(self):
        if not self.selection_state.is_job_selected():
            return
        if not 0 <= self.selection_state.job_index < self.num_project_jobs():
            return
        job = self.project().jobs[self.selection_state.job_index]
        job_clone = job.clone(name_postfix=self.callbacks['get_clone_postfix']())
        new_job_index = self.selection_state.job_index + 1
        self.callbacks['mark_modified'](True, "Duplicate Job")
        self.project().jobs.insert(new_job_index, job_clone)
        self.selection_state.set_job(new_job_index)
        self.callbacks['refresh_ui']()

    def clone_action(self):
        if self.selection_state.widget_type == 'action':
            job_index = self.selection_state.job_index
            action_index = self.selection_state.action_index
            if (0 <= job_index < self.num_project_jobs() and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                action_clone = action.clone(name_postfix=self.callbacks['get_clone_postfix']())
                new_action_index = action_index + 1
                self.callbacks['mark_modified'](True, "Duplicate Action")
                job.sub_actions.insert(new_action_index, action_clone)
                self.selection_state.action_index = new_action_index
                self.selection_state.subaction_index = -1
                self.selection_state.widget_type = 'action'
                self.callbacks['refresh_ui']()
        elif self.selection_state.widget_type == 'subaction':
            job_index = self.selection_state.job_index
            action_index = self.selection_state.action_index
            subaction_index = self.selection_state.subaction_index
            if (0 <= job_index < self.num_project_jobs() and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                if (action.type_name == constants.ACTION_COMBO and
                        0 <= subaction_index < len(action.sub_actions)):
                    subaction = action.sub_actions[subaction_index]
                    subaction_clone = subaction.clone(
                        name_postfix=self.callbacks['get_clone_postfix']())
                    new_subaction_index = subaction_index + 1
                    self.callbacks['mark_modified'](True, "Duplicate Sub-action")
                    action.sub_actions.insert(new_subaction_index, subaction_clone)
                    self.selection_state.subaction_index = new_subaction_index
                    self.selection_state.widget_type = 'subaction'
                    self.callbacks['refresh_ui']()

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
            self.callbacks['mark_modified'](True, "Shift Job")
            self.selection_state.set_job(new_index)
            self.callbacks['refresh_ui']()

    def _shift_action(self, delta):
        if not self.selection_state.is_action_selected():
            return
        job_idx, action_idx, _ = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_action(job_idx, action_idx, delta)
        if new_index != action_idx:
            self.callbacks['mark_modified'](True, "Shift Action")
            self.selection_state.set_action(job_idx, new_index)
            self.callbacks['refresh_ui']()

    def _shift_subaction(self, delta):
        if not self.selection_state.is_subaction_selected():
            return
        job_idx, action_idx, subaction_idx = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_subaction(job_idx, action_idx, subaction_idx, delta)
        if new_index != subaction_idx:
            self.callbacks['mark_modified'](True, "Shift Sub-action")
            self.selection_state.set_subaction(job_idx, action_idx, new_index)
            self.callbacks['refresh_ui']()
