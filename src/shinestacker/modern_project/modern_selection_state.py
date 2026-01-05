# pylint: disable=C0114, C0115, C0116, R1716
from .. common_project.base_selection_state import BaseSelectionState


class ModernSelectionState(BaseSelectionState):
    def is_job_selected(self):
        return self.widget_type == 'job' and self.job_index >= 0

    def is_action_selected(self):
        return self.widget_type == 'action' and self.job_index >= 0 and self.action_index >= 0

    def is_subaction_selected(self):
        return (self.widget_type == 'subaction' and
                self.job_index >= 0 and
                self.action_index >= 0 and
                self.subaction_index >= 0)

    def is_valid(self):
        return self.widget_type in ('job', 'action', 'subaction')

    def from_tuple(self, indices_tuple):
        super().from_tuple(indices_tuple)
        self.widget_type = self._determine_widget_type()

    def _determine_widget_type(self):
        if self.job_index >= 0 and self.action_index < 0:
            return 'job'
        if self.job_index >= 0 and self.action_index >= 0 and self.subaction_index < 0:
            return 'action'
        if self.job_index >= 0 and self.action_index >= 0 and self.subaction_index >= 0:
            return 'subaction'
        return None

    def equals(self, job_index, action_index, subaction_index):
        return (self.job_index == job_index and
                self.action_index == action_index and
                self.subaction_index == subaction_index)

    def is_within_bounds(self, total_jobs, job_actions_count=None, action_subactions_count=None):
        if not 0 <= self.job_index < total_jobs:
            return False
        if self.widget_type == 'job':
            return True
        if job_actions_count is not None and not 0 <= self.action_index < job_actions_count:
            return False
        if self.widget_type == 'action':
            return True
        if action_subactions_count is not None and not \
                0 <= self.subaction_index < action_subactions_count:
            return False
        return True

    def copy(self):
        new_state = ModernSelectionState()
        new_state.copy_from(self)
        return new_state


def indices_to_state(job_index, action_index, subaction_index):
    if job_index < 0:
        return None
    state = ModernSelectionState()
    if subaction_index >= 0:
        state.set_subaction(job_index, action_index, subaction_index)
    elif action_index >= 0:
        state.set_action(job_index, action_index)
    else:
        state.set_job(job_index)
    return state
