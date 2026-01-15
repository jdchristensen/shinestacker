# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101, R0911, R0801
from .. common_project.element_action_manager import ElementActionManager
from .list_container import get_action_row, rows_to_state


class ClassicElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, parent=None):
        super().__init__(project_holder, parent)
        self.selection_state = selection_state

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
