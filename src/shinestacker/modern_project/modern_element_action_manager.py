# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, R0912, R0911, R0904
from .. config.constants import constants
from .. common_project.element_action_manager import ElementActionManager
from .. common_project.selection_state import SelectionState


class ModernElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, parent=None):
        super().__init__(project_holder, parent)
        self.selection_state = selection_state
        self.selection_nav = None

    def set_selection_navigation(self, selection_nav):
        self.selection_nav = selection_nav

    def delete_element(self, confirm=True):
        if not self.selection_state.is_valid():
            return None, None, None
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        subaction_index = self.selection_state.subaction_index
        if not 0 <= job_index < self.num_project_jobs():
            return None, None, None
        job = self.project().jobs[job_index]
        if self.selection_state.is_subaction_selected():
            if not 0 <= action_index < len(job.sub_actions):
                return None, None, None
            action = job.sub_actions[action_index]
            if not 0 <= subaction_index < len(action.sub_actions):
                return None, None, None
            element = action.sub_actions[subaction_index]
            element_type = 'sub-action'
            position = (job_index, action_index, subaction_index)
            removal_state = SelectionState()
            removal_state.set_subaction(job_index, action_index, subaction_index)
        elif self.selection_state.is_action_selected():
            if not 0 <= action_index < len(job.sub_actions):
                return None, None, None
            element = job.sub_actions[action_index]
            element_type = 'action'
            position = (job_index, action_index, -1)
            removal_state = SelectionState()
            removal_state.set_action(job_index, action_index)
        else:
            element = job
            element_type = 'job'
            position = (job_index, -1, -1)
            removal_state = SelectionState()
            removal_state.set_job(job_index)
        if confirm and not self.confirm_delete_message(
                element_type, element.params.get('name', '')):
            return None, None, None
        self.mark_as_modified(True, f"Delete {element_type.title()}", "delete", position)
        if self.selection_state.is_subaction_selected():
            deleted_element = job.sub_actions[action_index].sub_actions.pop(subaction_index)
        elif self.selection_state.is_action_selected():
            deleted_element = job.sub_actions.pop(action_index)
        else:
            deleted_element = self.project().jobs.pop(job_index)
        old_state = self.selection_state.copy()
        new_state = self.new_state_after_delete(old_state)
        return removal_state, new_state, deleted_element

    def set_enabled(self, enabled, selection=None, update_project=True):
        if selection is None:
            selection = self.selection_state
        if not selection.is_valid():
            return
        if update_project:
            self._set_enabled_with_project_update(selection, enabled)

    def _set_enabled_with_project_update(self, selection, enabled):
        if selection.is_job_selected():
            job_index = selection.job_index
            if 0 <= job_index < self.num_project_jobs():
                job = self.project().jobs[job_index]
                if job.enabled() != enabled:
                    action_text = "Enable" if enabled else "Disable"
                    self.mark_as_modified(True, f"{action_text} Job", "edit", (job_index, -1, -1))
                    self._set_element_enabled(job, enabled, "Job")
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = self._get_element_from_selection(selection)
            if element and element.enabled() != enabled:
                action_text = "Enable" if enabled else "Disable"
                element_type = "Sub-action" if selection.is_subaction_selected() else "Action"
                if selection.is_subaction_selected():
                    position = (selection.job_index, selection.action_index,
                                selection.subaction_index)
                else:
                    position = (selection.job_index, selection.action_index, -1)
                self.mark_as_modified(True, f"{action_text} {element_type}", "edit", position)
                self._set_element_enabled(element, enabled, element_type)

    def _get_element_from_selection(self, selection):
        if selection.is_action_selected():
            job_idx = selection.job_index
            action_idx = selection.action_index
            if (0 <= job_idx < self.num_project_jobs() and
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions)):
                return self.project().jobs[job_idx].sub_actions[action_idx]
        elif selection.is_subaction_selected():
            job_idx = selection.job_index
            action_idx = selection.action_index
            subaction_idx = selection.subaction_index
            if (0 <= job_idx < self.num_project_jobs() and
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions)):
                action = self.project().jobs[job_idx].sub_actions[action_idx]
                if 0 <= subaction_idx < len(action.sub_actions):
                    return action.sub_actions[subaction_idx]
        return None

    def set_enabled_all(self, enabled):
        action = "Enable" if enabled else "Disable"
        self.mark_as_modified(True, f"{action} All", "edit_all", (-1, -1, -1))
        for job in self.project().jobs:
            job.set_enabled_all(enabled)

    def paste_element(self):
        if not self.has_copy_buffer():
            return False
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            return self.paste_subaction()
        if self.selection_state.is_job_selected():
            return self.paste_job()
        if self.selection_state.is_action_selected():
            return self.paste_action()
        if self.selection_state.is_subaction_selected():
            return self.paste_subaction()
        return False

    def paste_job(self):
        if not self.has_copy_buffer():
            return False
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return False
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return False
            new_action_index = len(self.project().jobs[self.selection_state.job_index].sub_actions)
            success, _index = self.paste_job_logic(
                copy_buffer, self.selection_state.job_index,
                "Paste Action", "paste", (self.selection_state.job_index, new_action_index, -1))
            if success:
                self.selection_state.copy_from(self.new_state_after_insert(self.selection_state, 0))
            return success
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(self.selection_state.job_index + 1, 0), self.num_project_jobs())
        success, _index = self.paste_job_logic(
            copy_buffer, self.selection_state.job_index,
            "Paste Job", "paste", (new_job_index, -1, -1))
        if success:
            self.selection_state.copy_from(self.new_state_after_insert(self.selection_state, 1))
        return success

    def paste_action(self):
        if not self.has_copy_buffer():
            return False
        if self.selection_state.job_index < 0:
            return False
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name not in constants.ACTION_TYPES:
            return False
        job = self.project().jobs[self.selection_state.job_index]
        new_state = self.new_state_after_insert(
            self.selection_state, 1 if self.selection_state.action_index >= 0 else 0)
        new_action_index = new_state.action_index
        self.mark_as_modified(
            True, "Paste Action", "paste",
            (self.selection_state.job_index, new_action_index, -1))
        job.sub_actions.insert(new_action_index, copy_buffer.clone())
        self.selection_state.set_action(new_state.job_index, new_state.action_index)
        return True

    def paste_subaction(self):
        if not self.has_copy_buffer():
            return False
        if self.selection_state.job_index < 0 or self.selection_state.action_index < 0:
            return False
        copy_buffer = self.copy_buffer()
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= len(job.sub_actions):
            return False
        action = job.sub_actions[self.selection_state.action_index]
        if action.type_name != constants.ACTION_COMBO:
            return False
        if copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
            return False
        if self.selection_state.subaction_index >= 0:
            new_state = self.new_state_after_insert(
                self.selection_state, 1)
            new_subaction_index = new_state.subaction_index
        else:
            new_state = SelectionState(self.selection_state.job_index,
                                       self.selection_state.action_index, 0)
            new_subaction_index = 0
        self.mark_as_modified(
            True, "Paste Sub-action", "paste",
            (self.selection_state.job_index, self.selection_state.action_index,
             new_subaction_index))
        action.sub_actions.insert(new_subaction_index, copy_buffer.clone())
        self.selection_state.copy_from(new_state)
        return True

    def cut_element(self):
        removal_state, new_state, deleted_element = self.delete_element(False)
        if deleted_element:
            self.set_copy_buffer(deleted_element)
        return removal_state, new_state, deleted_element

    def _shift_job(self, delta):
        if not self.selection_state.is_job_selected():
            return False
        prev_sel = self.selection_state.copy()
        new_index = self._op_shift_job(
            prev_sel.job_index, delta)
        if new_index != prev_sel.job_index:
            self.selection_state.set_job(new_index)
            return True
        return False

    def _shift_action(self, delta):
        if not self.selection_state.is_action_selected():
            return False
        prev_sel = self.selection_state.copy()
        new_index = self._op_shift_action(
            prev_sel.job_index, prev_sel.action_index, delta)
        if new_index != prev_sel.action_index:
            self.selection_state.set_action(prev_sel.job_index, new_index)
            return True
        return False

    def _shift_subaction(self, delta):
        if not self.selection_state.is_subaction_selected():
            return False
        prev_sel = self.selection_state.copy()
        new_index = self._op_shift_subaction(
            prev_sel.job_index, prev_sel.action_index, prev_sel.subaction_index, delta)
        if new_index != prev_sel.subaction_index:
            self.selection_state.set_subaction(prev_sel.job_index, prev_sel.action_index, new_index)
            return True
        return False
