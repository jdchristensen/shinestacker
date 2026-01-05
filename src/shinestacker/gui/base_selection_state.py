# pylint: disable=C0114, C0115, C0116, R1716


class BaseSelectionState:
    def __init__(self):
        self.job_index = -1
        self.action_index = -1
        self.subaction_index = -1
        self.widget_type = None

    def reset(self):
        self.job_index = -1
        self.action_index = -1
        self.subaction_index = -1
        self.widget_type = None

    def set_job(self, job_index):
        self.job_index = job_index
        self.action_index = -1
        self.subaction_index = -1
        self.widget_type = 'job'

    def set_action(self, job_index, action_index):
        self.job_index = job_index
        self.action_index = action_index
        self.subaction_index = -1
        self.widget_type = 'action'

    def set_subaction(self, job_index, action_index, subaction_index):
        self.job_index = job_index
        self.action_index = action_index
        self.subaction_index = subaction_index
        self.widget_type = 'subaction'

    def to_tuple(self):
        return (self.job_index, self.action_index, self.subaction_index)

    def from_tuple(self, indices_tuple):
        if len(indices_tuple) >= 3:
            self.job_index, self.action_index, self.subaction_index = indices_tuple[:3]

    def copy_from(self, other_state):
        self.job_index = other_state.job_index
        self.action_index = other_state.action_index
        self.subaction_index = other_state.subaction_index
        self.widget_type = other_state.widget_type
