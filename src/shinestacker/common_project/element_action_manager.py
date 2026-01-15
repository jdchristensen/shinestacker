# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, W0613, R0911, R0912, R0904
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from .. config.constants import constants
from .. common_project.selection_state import SelectionState
from .project_handler import ProjectHandler


class ElementActionManager(ProjectHandler, QObject):
    CLONE_POSTFIX = ' (clone)'

    def __init__(self, project_holder, parent=None):
        ProjectHandler.__init__(self, project_holder)
        QObject.__init__(self, parent)

    def new_state_after_delete(self, state):
        job_idx, act_idx, sub_idx = state.to_tuple()
        if not state.are_indices_valid():
            return SelectionState()
        if sub_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return SelectionState()
            job = self.project_job(job_idx)
            if act_idx >= len(job.sub_actions):
                return SelectionState(job_idx)
            action = job.sub_actions[act_idx]
            num_sub = len(action.sub_actions) + 1
            if sub_idx < num_sub - 1:
                return SelectionState(job_idx, act_idx, sub_idx)
            return SelectionState(job_idx, act_idx, sub_idx - 1)
        if act_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return SelectionState()
            job = self.project_job(job_idx)
            num_act = len(job.sub_actions) + 1
            if act_idx >= num_act:
                return SelectionState(job_idx)
            if act_idx < num_act - 1:
                return SelectionState(job_idx, act_idx)
            if act_idx == 0:
                return SelectionState(job_idx)
            return (job_idx, act_idx - 1)
        num_jobs = self.num_project_jobs() + 1
        if job_idx >= num_jobs:
            return SelectionState()
        if job_idx < num_jobs - 1:
            return SelectionState(job_idx)
        if job_idx == 0:
            return SelectionState()
        return SelectionState(job_idx - 1)

    def new_state_after_clone(self, state):
        job_idx, act_idx, sub_idx = state.to_tuple()
        if sub_idx >= 0:
            return SelectionState(job_idx, act_idx, sub_idx + 1)
        if act_idx >= 0:
            return SelectionState(job_idx, act_idx + 1)
        return SelectionState(job_idx + 1)

    def new_state_after_insert(self, state, delta):
        job_idx, act_idx, sub_idx = state.to_tuple()
        if not state.are_indices_valid():
            return SelectionState()
        if sub_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return SelectionState(job_idx, act_idx, sub_idx)
            job = self.project_job(job_idx)
            if act_idx >= len(job.sub_actions):
                return SelectionState(job_idx, act_idx, sub_idx)
            action = job.sub_actions[act_idx]
            num_sub = len(action.sub_actions) + 1
            new_sub_idx = sub_idx + delta
            if 0 <= new_sub_idx < num_sub:
                return SelectionState(job_idx, act_idx, new_sub_idx)
        elif act_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return SelectionState(job_idx, act_idx)
            job = self.project_job(job_idx)
            num_act = len(job.sub_actions) + 1
            new_act_idx = act_idx + delta
            if 0 <= new_act_idx < num_act:
                return SelectionState(job_idx, new_act_idx)
        else:
            num_jobs = self.num_project_jobs() + 1
            new_job_idx = job_idx + delta
            if 0 <= new_job_idx < num_jobs:
                return SelectionState(new_job_idx)
        return SelectionState(job_idx, act_idx, sub_idx)

    def is_job_selected(self):
        return self.selection_state.is_job_selected()

    def is_action_selected(self):
        return self.selection_state.is_action_selected()

    def is_subaction_selected(self):
        return self.selection_state.is_subaction_selected()

    def get_selected_job_index(self):
        return self.selection_state.job_index

    def is_valid_selection(self):
        return self.selection_state.is_valid()

    def get_action(self, selection):
        if not selection.is_action_selected() and not selection.is_subaction_selected():
            return None
        job = self.project().jobs[selection.job_index]
        action = job.sub_actions[selection.action_index]
        if selection.is_subaction_selected():
            return action.sub_actions[selection.subaction_index]
        return action

    def get_job_actions(self, selection):
        if selection.job_index < 0:
            return None
        job = self.project().jobs[selection.job_index]
        return job.sub_actions

    def get_sub_actions(self, selection):
        if selection.job_index < 0 or selection.action_index < 0:
            return None
        job = self.project().jobs[selection.job_index]
        if selection.action_index >= len(job.sub_actions):
            return None
        return job.sub_actions[selection.action_index].sub_actions

    def confirm_delete_message(self, type_name, element_name):
        return QMessageBox.question(
            self.parent(), "Confirm Delete",
            f"Are you sure you want to delete {type_name} '{element_name}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes

    def paste_job_logic(self, copy_buffer, job_index, description="",
                        action_type="", affected_position=None):
        if affected_position:
            self.mark_as_modified(True, description, action_type, affected_position)
        if copy_buffer.type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return False, None
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return False, None
            current_job = self.project().jobs[job_index]
            new_action_index = len(current_job.sub_actions)
            element = copy_buffer.clone()
            current_job.sub_actions.insert(new_action_index, element)
            return True, new_action_index
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(job_index + 1, 0), self.num_project_jobs())
        element = copy_buffer.clone()
        self.project().jobs.insert(new_job_index, element)
        return True, new_job_index

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

    def _op_copy_job(self, job_index):
        if 0 <= job_index < self.num_project_jobs():
            return self.project_job(job_index).clone()
        return None

    def _op_copy_action(self, job_index, action_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                return job.sub_actions[action_index].clone()
        return None

    def _op_copy_subaction(self, job_index, action_index, subaction_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if 0 <= subaction_index < len(action.sub_actions):
                    return action.sub_actions[subaction_index].clone()
        return None

    def _op_shift_job(self, job_index, delta):
        jobs = self.project().jobs
        new_index = job_index + delta
        if 0 <= new_index < len(jobs):
            jobs.insert(new_index, jobs.pop(job_index))
            return new_index
        return job_index

    def _op_shift_action(self, job_index, action_index, delta):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            new_index = action_index + delta
            if 0 <= new_index < len(job.sub_actions):
                job.sub_actions.insert(new_index, job.sub_actions.pop(action_index))
                return new_index
        return action_index

    def _op_shift_subaction(self, job_index, action_index, subaction_index, delta):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                new_index = subaction_index + delta
                if 0 <= new_index < len(action.sub_actions):
                    action.sub_actions.insert(new_index, action.sub_actions.pop(subaction_index))
                    return new_index
        return subaction_index

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
        job_clone = self._op_copy_job(self.get_selected_job_index())
        if job_clone:
            self.set_copy_buffer(job_clone)

    def copy_action(self):
        if not self.is_action_selected():
            return
        selection = self.selection_state
        element_clone = self._op_copy_action(selection.job_index, selection.action_index)
        if element_clone:
            self.set_copy_buffer(element_clone)

    def copy_subaction(self):
        if not self.is_subaction_selected():
            return
        selection = self.selection_state
        element_clone = self._op_copy_subaction(
            selection.job_index, selection.action_index, selection.subaction_index)
        if element_clone:
            self.set_copy_buffer(element_clone)

    def clone_element(self):
        selection = self.selection_state
        if selection.is_job_selected():
            return self.clone_job()
        if selection.is_action_selected() or selection.is_subaction_selected():
            return self.clone_action()
        return False, None

    def clone_job(self):
        if not self.is_job_selected():
            return False, None
        job_index = self.get_selected_job_index()
        if not 0 <= job_index < self.num_project_jobs():
            return False, None
        self.mark_as_modified(True, "Duplicate Job", "clone", (job_index, -1, -1))
        job = self.project().jobs[job_index]
        job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
        new_job_index = job_index + 1
        self.project().jobs.insert(new_job_index, job_clone)
        return job_clone is not None, SelectionState(new_job_index)

    def clone_action(self):
        selection = self.selection_state
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return False, None
        if not self.get_job_actions(selection):
            return False, None
        self.mark_as_modified(
            True, "Duplicate Action", "clone",
            (selection.job_index, selection.action_index, selection.subaction_index))
        job = self.project().jobs[selection.job_index]
        if selection.is_subaction_selected():
            cloned = self.get_action(selection).clone(name_postfix=self.CLONE_POSTFIX)
            self.get_sub_actions(selection).insert(selection.subaction_index + 1, cloned)
        else:
            cloned = self.get_action(selection).clone(name_postfix=self.CLONE_POSTFIX)
            job.sub_actions.insert(selection.action_index + 1, cloned)
        new_state = self.new_state_after_clone(selection)
        return True, new_state

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
