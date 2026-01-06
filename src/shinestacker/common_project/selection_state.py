# pylint: disable=C0114, C0115, C0116, R1716, R0904


class SelectionState:
    def __init__(self, job_index=-1, action_index=-1, subaction_index=-1):
        self.widget_type = ''
        self.set_indices(job_index, action_index, subaction_index)

    def set_indices(self, job_idx, action_idx, subaction_idx):
        self.job_index = job_idx
        self.action_index = action_idx
        self.subaction_index = subaction_idx
        if subaction_idx >= 0:
            self.widget_type = 'subaction'
        elif action_idx >= 0:
            self.widget_type = 'action'
        elif job_idx >= 0:
            self.widget_type = 'job'
        else:
            self.widget_type = None

    def reset(self):
        self.set_indices(-1, -1, -1)
        self.widget_type = None

    def set_job(self, job_index):
        self.set_indices(job_index, -1, -1)
        self.widget_type = 'job'

    def set_action(self, job_index, action_index):
        self.set_indices(job_index, action_index, -1)
        self.widget_type = 'action'

    def set_subaction(self, job_index, action_index, subaction_index):
        self.set_indices(job_index, action_index, subaction_index)
        self.widget_type = 'subaction'

    def is_job_selected(self):
        return self.widget_type == 'job' and self.job_index >= 0

    def is_action_selected(self):
        return self.widget_type == 'action' and self.job_index >= 0 and self.action_index >= 0

    def is_subaction_selected(self):
        return self.widget_type == 'subaction' and \
            self.job_index >= 0 and self.action_index >= 0 and self.subaction_index >= 0

    def is_valid(self):
        return self.widget_type in ('job', 'action', 'subaction')

    def to_tuple(self):
        return self.get_indices()

    def from_tuple(self, indices_tuple):
        if len(indices_tuple) >= 3:
            self.set_indices(*indices_tuple[:3])

    def copy_from(self, other_state):
        self.set_indices(
            other_state.job_index, other_state.action_index, other_state.subaction_index)
        self.widget_type = other_state.widget_type

    def get_indices(self):
        return (self.job_index, self.action_index, self.subaction_index)

    def are_indices_valid(self):
        return self.job_index >= 0

    def are_action_indices_valid(self):
        return self.job_index >= 0 and self.action_index >= 0

    def are_subaction_indices_valid(self):
        return self.job_index >= 0 and self.action_index >= 0 and self.subaction_index >= 0

    def set_job_indices(self, job_index):
        self.set_indices(job_index, -1, -1)
        self.widget_type = 'job'

    def set_action_indices(self, job_index, action_index):
        self.set_indices(job_index, action_index, -1)
        self.widget_type = 'action'

    def set_subaction_indices(self, job_index, action_index, subaction_index):
        self.set_indices(job_index, action_index, subaction_index)
        self.widget_type = 'subaction'

    def equals(self, job_index, action_index, subaction_index):
        return self.job_index == job_index and \
            self.action_index == action_index and self.subaction_index == subaction_index

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
        new_state = SelectionState()
        new_state.copy_from(self)
        return new_state
