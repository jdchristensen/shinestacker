# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101, R0911, R0801
from .. common_project.element_action_manager import ElementActionManager
from .list_container import get_action_row, rows_to_state


class ClassicElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, parent=None):
        super().__init__(project_holder, parent)
        self.selection_state = selection_state

    @staticmethod
    def state_to_rows(project, selection_state):
        if not selection_state or not selection_state.is_valid():
            return (-1, -1)
        job_row = selection_state.job_index
        if selection_state.is_job_selected():
            return (job_row, -1)
        if selection_state.job_index < 0:
            return (-1, -1)
        job = project.jobs[selection_state.job_index]
        action_row = 0
        for i, action in enumerate(job.sub_actions):
            if i == selection_state.action_index:
                if selection_state.is_subaction_selected():
                    action_row += selection_state.subaction_index + 1
                return (job_row, action_row)
            action_row += 1
            action_row += len(action.sub_actions)
        return (job_row, -1)

    def get_current_action_row(self, selection_state=None):
        if selection_state is None:
            selection_state = self.selection_state
        _, action_row = self.state_to_rows(self.project(), selection_state)
        return action_row

    def _shift_job(self, delta):
        selection = self.selection_state
        if not selection.is_job_selected():
            return False
        job_index = selection.job_index
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project().jobs
            jobs.insert(new_index, jobs.pop(job_index))
            new_selection = rows_to_state(self.project(), new_index, -1)
            return new_selection
        return False

    def _shift_action(self, delta):
        selection = self.selection_state
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return False
        if selection.is_subaction_selected():
            sub_actions = self.get_sub_actions(selection)
            if not sub_actions:
                return False
            new_index = selection.subaction_index + delta
            if 0 <= new_index < len(sub_actions):
                sub_actions.insert(
                    new_index, sub_actions.pop(selection.subaction_index))
            else:
                return False
        else:
            if not self.get_job_actions(selection):
                return False
            new_index = selection.action_index + delta
            actions = self.get_job_actions(selection)
            if 0 <= new_index < len(actions):
                actions.insert(new_index, actions.pop(selection.action_index))
            else:
                return False
        return self.new_state_after_insert(selection, delta)

    def _shift_subaction(self, delta):
        return self._shift_action(delta)

    def set_enabled(self, enabled, selection=None):
        if selection is None:
            selection = self.selection_state
        if not selection.is_valid():
            return False
        new_selection = False
        if selection.is_job_selected():
            if 0 <= selection.job_index < self.num_project_jobs():
                job = self.project().jobs[selection.job_index]
                if job.enabled() != enabled:
                    action_text = "Enable" if enabled else "Disable"
                    self.mark_as_modified(
                        True, f"{action_text} Job", "edit", (selection.job_index, -1, -1))
                    self._set_element_enabled(job, enabled, "Job")
                    new_selection = rows_to_state(self.project(), selection.job_index, -1)
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = self.get_action(selection)
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
                new_selection = rows_to_state(
                    self.project(), selection.job_index,
                    get_action_row(selection, self.get_job_actions(selection)))
        return new_selection
