# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101, R0911
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from .. config.constants import constants
from .. gui.project_handler import ProjectHandler


class ClassicElementActionManager(ProjectHandler, QObject):
    def __init__(self, project_holder, callbacks):
        ProjectHandler.__init__(self, project_holder)
        QObject.__init__(self)
        self.callbacks = callbacks

    @staticmethod
    def new_row_after_delete(action_row, pos):
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

    @staticmethod
    def new_row_after_clone(job, action_row, is_sub_action, cloned):
        return action_row + 1 if is_sub_action else \
            sum(1 + len(action.sub_actions)
                for action in job.sub_actions[:job.sub_actions.index(cloned)])

    @staticmethod
    def new_row_after_insert(action_row, pos, delta):
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

    @staticmethod
    def new_row_after_paste(action_row, pos):
        return ClassicElementActionManager.new_row_after_insert(action_row, pos, 0)

    def delete_element(self, parent_widget, confirm=True):
        selection = self.callbacks['get_selection_state']()
        if selection.is_job_selected():
            if not 0 <= selection.job_index < self.num_project_jobs():
                return None
            job = self.project().jobs[selection.job_index]
            if confirm:
                reply = QMessageBox.question(
                    parent_widget, "Confirm Delete",
                    f"Are you sure you want to delete job '{job.params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return None
            deleted_job = self.project().jobs.pop(selection.job_index)
            self.callbacks['mark_modified'](True, "Delete Job")
            self.callbacks['refresh_ui']()
            return deleted_job
        if selection.is_action_selected() or selection.is_subaction_selected():
            element = selection.sub_action if selection.is_subaction_selected() \
                else selection.action
            container = selection.sub_actions if selection.is_subaction_selected() \
                else selection.actions
            index = selection.sub_action_index if selection.is_subaction_selected() \
                else selection.action_index
            if not element or not container or index < 0 or index >= len(container):
                return None
            if confirm:
                element_type = "sub-action" if selection.is_subaction_selected() else "action"
                reply = QMessageBox.question(
                    parent_widget, "Confirm Delete",
                    f"Are you sure you want to delete {element_type} "
                    f"'{element.params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return None
            deleted_element = container.pop(index)
            element_type = "Sub-action" if selection.is_subaction_selected() else "Action"
            self.callbacks['mark_modified'](True, f"Delete {element_type}")
            current_action_row = selection.get_action_row()
            new_row = self.new_row_after_delete(current_action_row, selection)
            self.callbacks['refresh_ui'](selection.job_index, new_row)
            return deleted_element
        return None

    def copy_element(self):
        selection = self.callbacks['get_selection_state']()
        if selection.is_job_selected():
            self.copy_job()
        elif selection.is_action_selected() or selection.is_subaction_selected():
            self.copy_action()

    def copy_job(self):
        selection = self.callbacks['get_selection_state']()
        if not selection.is_job_selected():
            return
        job_index = selection.job_index
        if 0 <= job_index < self.num_project_jobs():
            job_clone = self.project().jobs[job_index].clone()
            self.callbacks['set_copy_buffer'](job_clone)

    def copy_action(self):
        selection = self.callbacks['get_selection_state']()
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return
        if selection.is_subaction_selected():
            if selection.sub_action is not None:
                self.callbacks['set_copy_buffer'](selection.sub_action.clone())
        else:
            if selection.action is not None:
                self.callbacks['set_copy_buffer'](selection.action.clone())

    def paste_element(self):
        if not self.callbacks['has_copy_buffer']():
            return
        copy_buffer = self.callbacks['get_copy_buffer']()
        selection = self.callbacks['get_selection_state']()
        if selection.is_job_selected():
            self._paste_job(copy_buffer, selection)
        elif selection.is_action_selected() or selection.is_subaction_selected():
            self._paste_action(copy_buffer, selection)

    def _paste_job(self, copy_buffer, selection):
        if copy_buffer.type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return
            current_job = self.project().jobs[selection.job_index]
            new_action_index = len(current_job.sub_actions)
            current_job.sub_actions.insert(new_action_index, copy_buffer)
            self.callbacks['mark_modified'](True, "Paste Action")
            self.callbacks['refresh_ui'](selection.job_index, -1)
            return
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(selection.job_index + 1, 0), self.num_project_jobs() - 1)
        self.callbacks['mark_modified'](True, "Paste Job")
        self.project().jobs.insert(new_job_index, copy_buffer)
        self.callbacks['refresh_ui'](new_job_index, -1)

    def _paste_action(self, copy_buffer, selection):
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            target_action = None
            insertion_index = 0
            if selection.is_subaction_selected():
                if selection.action and selection.action.type_name == constants.ACTION_COMBO:
                    target_action = selection.action
                    insertion_index = len(selection.sub_actions)
            else:
                if selection.action and selection.action.type_name == constants.ACTION_COMBO:
                    target_action = selection.action
                    insertion_index = len(selection.action.sub_actions)
            if target_action is not None:
                self.callbacks['mark_modified'](True, "Paste Sub-action")
                target_action.sub_actions.insert(insertion_index, copy_buffer)
                current_action_row = selection.get_action_row()
                new_row = self.new_row_after_paste(current_action_row, selection)
                self.callbacks['refresh_ui'](selection.job_index, new_row)
                return
        if copy_buffer.type_name in constants.ACTION_TYPES:
            if not selection.is_subaction_selected():
                if not selection.actions:
                    return
                new_action_index = 0 if len(selection.actions) == 0 else selection.action_index + 1
                self.callbacks['mark_modified'](True, "Paste Action")
                selection.actions.insert(new_action_index, copy_buffer)
                current_action_row = selection.get_action_row()
                new_row = self.new_row_after_paste(current_action_row, selection)
                self.callbacks['refresh_ui'](selection.job_index, new_row)

    def cut_element(self):
        element = self.delete_element(self.callbacks['get_parent_widget'](), False)
        if element:
            self.callbacks['set_copy_buffer'](element)

    def clone_element(self):
        selection = self.callbacks['get_selection_state']()
        if selection.is_job_selected():
            self.clone_job()
        elif selection.is_action_selected() or selection.is_subaction_selected():
            self.clone_action()

    def clone_job(self):
        selection = self.callbacks['get_selection_state']()
        if not selection.is_job_selected():
            return
        if 0 <= selection.job_index < self.num_project_jobs():
            job = self.project().jobs[selection.job_index]
            job_clone = job.clone(name_postfix=self.callbacks['get_clone_postfix']())
            new_job_index = selection.job_index + 1
            self.callbacks['mark_modified'](True, "Duplicate Job")
            self.project().jobs.insert(new_job_index, job_clone)
            self.callbacks['refresh_ui'](new_job_index, -1)

    def clone_action(self):
        selection = self.callbacks['get_selection_state']()
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return
        if not selection.actions:
            return
        self.callbacks['mark_modified'](True, "Duplicate Action")
        job = self.project().jobs[selection.job_index]
        if selection.is_subaction_selected():
            cloned = selection.sub_action.clone(name_postfix=self.callbacks['get_clone_postfix']())
            selection.sub_actions.insert(selection.sub_action_index + 1, cloned)
        else:
            cloned = selection.action.clone(name_postfix=self.callbacks['get_clone_postfix']())
            job.sub_actions.insert(selection.action_index + 1, cloned)
        current_action_row = selection.get_action_row()
        new_row = self.new_row_after_clone(
            job, current_action_row, selection.is_subaction_selected(), cloned)
        self.callbacks['refresh_ui'](selection.job_index, new_row)

    def move_element_up(self):
        self._shift_element(-1)

    def move_element_down(self):
        self._shift_element(+1)

    def _shift_element(self, delta):
        selection = self.callbacks['get_selection_state']()
        if selection.is_job_selected():
            self._shift_job(delta)
        elif selection.is_action_selected() or selection.is_subaction_selected():
            self._shift_action(selection, delta)

    def _shift_job(self, delta):
        selection = self.callbacks['get_selection_state']()
        if not selection.is_job_selected():
            return
        job_index = selection.job_index
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project().jobs
            self.callbacks['mark_modified'](True, "Shift Job")
            jobs.insert(new_index, jobs.pop(job_index))
            self.callbacks['refresh_ui'](new_index, -1)

    def _shift_action(self, selection, delta):
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return
        if selection.is_subaction_selected():
            if not selection.sub_actions:
                return
            new_index = selection.sub_action_index + delta
            if 0 <= new_index < len(selection.sub_actions):
                self.callbacks['mark_modified'](True, "Shift Sub-action")
                selection.sub_actions.insert(
                    new_index, selection.sub_actions.pop(selection.sub_action_index))
        else:
            if not selection.actions:
                return
            new_index = selection.action_index + delta
            if 0 <= new_index < len(selection.actions):
                self.callbacks['mark_modified'](True, "Shift Action")
                selection.actions.insert(new_index, selection.actions.pop(selection.action_index))
        current_action_row = selection.get_action_row()
        new_row = self.new_row_after_insert(current_action_row, selection, delta)
        self.callbacks['refresh_ui'](selection.job_index, new_row)

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)

    def set_enabled(self, enabled):
        selection = self.callbacks['get_selection_state']()
        if not selection.is_valid():
            return
        if selection.is_job_selected():
            if 0 <= selection.job_index < self.num_project_jobs():
                job = self.project().jobs[selection.job_index]
                if job.enabled() != enabled:
                    self._set_element_enabled(job, enabled, "Job")
                    self.callbacks['refresh_ui'](selection.job_index, -1)
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = selection.sub_action if selection.is_subaction_selected() \
                else selection.action
            if element and element.enabled() != enabled:
                element_type = "Sub-action" if selection.is_subaction_selected() else "Action"
                self._set_element_enabled(element, enabled, element_type)
                self.callbacks['refresh_ui'](selection.job_index, selection.get_action_row())

    def _set_element_enabled(self, element, enabled, element_type):
        if enabled:
            self.callbacks['mark_modified'](True, f"Enable {element_type}")
        else:
            self.callbacks['mark_modified'](True, f"Disable {element_type}")
        element.set_enabled(enabled)

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def set_enabled_all(self, enable=True):
        selection = self.callbacks['get_selection_state']()
        job_row = selection.job_index if selection.is_valid() else -1
        action_row = selection.get_action_row() if selection.is_valid() else -1
        for job in self.project().jobs:
            job.set_enabled_all(enable)
        action = "Enable" if enable else "Disable"
        self.callbacks['mark_modified'](True, f"{action} All")
        self.callbacks['refresh_ui'](job_row, action_row)
