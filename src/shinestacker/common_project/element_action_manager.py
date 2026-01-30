# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, W0613, R0911, R0912, R0904
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox
from .. config.constants import constants
from .. common_project.selection_state import SelectionState
from .project_handler import ProjectHandler

CLONE_POSTFIX = ' (clone)'


class ElementActionManager(ProjectHandler, QObject):
    project_modified_signal = Signal(bool)

    def __init__(self, project_holder, selection_state, parent=None):
        ProjectHandler.__init__(self, project_holder)
        self.selection_state = selection_state
        QObject.__init__(self, parent)

    def new_state_after_op(self, state, delta):
        job_idx, act_idx, sub_idx = state.to_tuple()
        job = self.project_job(job_idx)
        if job is None:
            return SelectionState()
        if act_idx > len(job.sub_actions):
            return SelectionState(job_idx)
        if sub_idx >= 0:
            num_sub = len(job.sub_actions[act_idx].sub_actions)
            return SelectionState(job_idx, act_idx, min(sub_idx + delta, num_sub - 1))
        if act_idx >= 0:
            num_act = len(job.sub_actions)
            return SelectionState(job_idx, min(act_idx + delta, num_act - 1))
        num_job = self.num_project_jobs()
        return SelectionState(min(job_idx + delta, num_job - 1))

    def new_state_after_delete(self, state):
        return self.new_state_after_op(state, 0)

    def new_state_after_insert(self, state):
        return self.new_state_after_op(state, 1)

    def is_job_selected(self):
        return self.selection_state.is_job_selected()

    def is_action_selected(self):
        return self.selection_state.is_action_selected()

    def is_subaction_selected(self):
        return self.selection_state.is_subaction_selected()

    def is_valid_selection(self):
        return self.selection_state.is_valid()

    def get_action(self, selection):
        if not selection.is_action_selected() and not selection.is_subaction_selected():
            return None
        return self.project_element(*selection.to_tuple())

    def get_job_actions(self, selection):
        job = self.project_job(selection.job_index)
        return job.sub_actions if job is not None else None

    def get_subactions(self, selection):
        action = self.project_action(selection.job_index, selection.action_index)
        return action.sub_actions if action is not None else None

    def confirm_delete_message(self, type_name, element_name):
        return QMessageBox.question(
            self.parent(), "Confirm Delete",
            f"Are you sure you want to delete {type_name} '{element_name}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes

    def mark_as_modified(self, modified=True, description='', action_type=None,
                         affected_position=(-1, -1, -1)):
        ProjectHandler.mark_as_modified(self, modified, description, action_type, affected_position)
        self.project_modified_signal.emit(modified)

    def save_undo_state(self, pre_state, description='', action_type='',
                        affected_position=(-1, -1, -1)):
        ProjectHandler.save_undo_state(self, pre_state, description, action_type, affected_position)
        self.project_modified_signal.emit(True)

    def paste_element(self):
        if not self.has_copy_buffer():
            return False
        copy_buffer = self.copy_buffer()
        selection = self.selection_state
        if copy_buffer.type_name == constants.ACTION_JOB:
            return self._paste_job(copy_buffer, selection)
        if copy_buffer.type_name in constants.ACTION_TYPES:
            return self._paste_action(copy_buffer, selection)
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            return self._paste_subaction(copy_buffer, selection)
        return False

    def _paste_job(self, copy_buffer, selection):
        if self.num_project_jobs() == 0:
            insert_index = 0
        else:
            insert_index = selection.job_index + 1 \
                if selection.job_index >= 0 else self.num_project_jobs()
            insert_index = min(max(insert_index, 0), self.num_project_jobs())
        self.mark_as_modified(True, "Paste Job", "paste", (insert_index, -1, -1))
        self.project().jobs.insert(insert_index, copy_buffer.clone())
        self.selection_state.copy_from(SelectionState(insert_index))
        return True

    def _paste_action(self, copy_buffer, selection):
        if not 0 <= selection.job_index < self.num_project_jobs():
            return False
        job = self.project().jobs[selection.job_index]
        if selection.is_action_selected() or selection.is_subaction_selected():
            insert_index = selection.action_index + 1
        else:
            insert_index = len(job.sub_actions)
        insert_index = min(max(insert_index, 0), len(job.sub_actions))
        self.mark_as_modified(
            True, "Paste Action", "paste", (selection.job_index, insert_index, -1))
        job.sub_actions.insert(insert_index, copy_buffer.clone())
        self.selection_state.copy_from(SelectionState(selection.job_index, insert_index, -1))
        return True

    def _paste_subaction(self, copy_buffer, selection):
        if not 0 <= selection.job_index < self.num_project_jobs():
            return False
        job = self.project().jobs[selection.job_index]
        if selection.action_index < 0 or selection.action_index >= len(job.sub_actions):
            return False
        action = job.sub_actions[selection.action_index]
        if action.type_name != constants.ACTION_COMBO:
            return False
        if selection.is_subaction_selected():
            insert_index = selection.subaction_index + 1
        else:
            insert_index = len(action.sub_actions)
        insert_index = min(max(insert_index, 0), len(action.sub_actions))
        self.mark_as_modified(
            True, "Paste Sub-action", "paste",
            (selection.job_index, selection.action_index, insert_index))
        action.sub_actions.insert(insert_index, copy_buffer.clone())
        self.selection_state.copy_from(
            SelectionState(selection.job_index, selection.action_index, insert_index))
        return True

    def _op_delete_job(self, job_index):
        if 0 <= job_index < self.num_project_jobs():
            return self.project().jobs.pop(job_index)
        return None

    def _op_delete_action(self, job_index, action_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                return job.sub_actions.pop(action_index)
        return None

    def _op_delete_subaction(self, job_index, action_index, subaction_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if 0 <= subaction_index < len(action.sub_actions):
                    return action.sub_actions.pop(subaction_index)
        return None

    def shift_element(self, delta):
        if self.is_job_selected():
            return self._shift_job(delta)
        if self.is_action_selected():
            return self._shift_action(delta)
        if self.is_subaction_selected():
            return self._shift_subaction(delta)
        return False

    def _shift_job(self, delta):
        if not self.is_job_selected():
            return False
        job_index = self.selection_state.job_index
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project().jobs
            jobs.insert(new_index, jobs.pop(job_index))
            self.selection_state.set_job(new_index)
            return True
        return False

    def _shift_action(self, delta):
        if not self.is_action_selected():
            return False
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        if not 0 <= job_index < self.num_project_jobs():
            return False
        job = self.project().jobs[job_index]
        new_index = action_index + delta
        if 0 <= new_index < len(job.sub_actions):
            job.sub_actions.insert(new_index, job.sub_actions.pop(action_index))
            self.selection_state.set_action(job_index, new_index)
            return True
        return False

    def _shift_subaction(self, delta):
        if not self.is_subaction_selected():
            return False
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        subaction_index = self.selection_state.subaction_index
        if not 0 <= job_index < self.num_project_jobs():
            return False
        job = self.project().jobs[job_index]
        if not 0 <= action_index < len(job.sub_actions):
            return False
        action = job.sub_actions[action_index]
        new_index = subaction_index + delta
        if 0 <= new_index < len(action.sub_actions):
            action.sub_actions.insert(new_index, action.sub_actions.pop(subaction_index))
            self.selection_state.set_subaction(job_index, action_index, new_index)
            return True
        return False

    def copy_element(self):
        if self.selection_state and self.selection_state.is_valid():
            element = self.project_element(*self.selection_state.to_tuple())
            if element:
                self.set_copy_buffer(element.clone())

    def clone_element(self):
        selection = self.selection_state
        if selection.is_job_selected():
            job_index = self.selection_state.job_index
            if not 0 <= job_index < self.num_project_jobs():
                return False, None
            self.mark_as_modified(True, "Duplicate Job", "clone", (job_index, -1, -1))
            job = self.project_job(job_index)
            job_clone = job.clone(name_postfix=CLONE_POSTFIX)
            new_job_index = job_index + 1
            self.project_jobs().insert(new_job_index, job_clone)
            return job_clone is not None, SelectionState(new_job_index)
        if selection.is_action_selected() or selection.is_subaction_selected():
            if not self.get_job_actions(selection):
                return False, None
            label = "Subaction" if selection.is_subaction_selected() else "Action"
            self.mark_as_modified(
                True, f"Duplicate {label}", "clone",
                (selection.job_index, selection.action_index, selection.subaction_index))
            job = self.project_job(selection.job_index)
            cloned = self.get_action(selection).clone(name_postfix=CLONE_POSTFIX)
            if selection.is_subaction_selected():
                self.get_subactions(selection).insert(selection.subaction_index + 1, cloned)
            else:
                job.sub_actions.insert(selection.action_index + 1, cloned)
            new_state = self.new_state_after_insert(selection)
            return True, new_state
        return False, None

    def delete_element(self, confirm=True):
        if not self.selection_state.is_valid():
            return None, None
        position = self.selection_state.to_tuple()
        element = self.project_element(*position)
        element_type = self.selection_state.widget_type()
        if not element:
            return None, None
        if confirm and not self.confirm_delete_message(
                element_type, element.params.get('name', '')):
            return None, None
        self.mark_as_modified(True, f"Delete {element_type.title()}", "delete", position)
        if self.selection_state.is_subaction_selected():
            deleted_element = self._op_delete_subaction(*position)
        elif self.selection_state.is_action_selected():
            deleted_element = self._op_delete_action(*position[:2])
        else:
            deleted_element = self._op_delete_job(position[0])
        new_selection = self.new_state_after_delete(self.selection_state)
        return deleted_element, new_selection

    def cut_element(self):
        deleted_element, new_state = self.delete_element(False)
        if deleted_element:
            self.set_copy_buffer(deleted_element)
        return deleted_element, new_state

    def _set_element_enabled(self, element, enabled, element_type):
        element.set_enabled(enabled)

    def set_enabled_all(self, enabled):
        action = "Enable" if enabled else "Disable"
        self.mark_as_modified(True, f"{action} All")
        for job in self.project().jobs:
            job.set_enabled_all(enabled)

    def set_enabled(self, enabled, selection):
        if selection is None:
            selection = self.selection_state
        if not selection.is_valid():
            return False
        j, a, s = selection.job_index, selection.action_index, selection.subaction_index
        if not 0 <= j < self.num_project_jobs():
            return False
        job = self.project().jobs[j]
        if selection.is_job_selected():
            if job.enabled() != enabled:
                txt = "Enable" if enabled else "Disable"
                self.mark_as_modified(True, f"{txt} Job", "edit", (j, -1, -1))
                job.set_enabled(enabled)
                return True
        elif selection.is_action_selected() and 0 <= a < len(job.sub_actions):
            element = job.sub_actions[a]
            if element.enabled() != enabled:
                txt = "Enable" if enabled else "Disable"
                self.mark_as_modified(True, f"{txt} Action", "edit", (j, a, -1))
                element.set_enabled(enabled)
                return True
        elif selection.is_subaction_selected() and 0 <= a < len(job.sub_actions):
            action = job.sub_actions[a]
            if 0 <= s < len(action.sub_actions):
                element = action.sub_actions[s]
                if element.enabled() != enabled:
                    txt = "Enable" if enabled else "Disable"
                    self.mark_as_modified(True, f"{txt} Sub-action", "edit", (j, a, s))
                    element.set_enabled(enabled)
                    return True
        return False
