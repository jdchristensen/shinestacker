# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, R0912, R0911, R0904
from .. common_project.element_action_manager import ElementActionManager


class ModernElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, parent=None):
        super().__init__(project_holder, parent)
        self.selection_state = selection_state
        self.selection_nav = None

    def set_selection_navigation(self, selection_nav):
        self.selection_nav = selection_nav

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
