# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101
from dataclasses import dataclass


@dataclass
class ClassicSelectionState:
    actions: list
    sub_actions: list
    action_index: int
    sub_action_index: int = -1
    job_index: int = -1
    widget_type: str = None

    @property
    def is_sub_action(self) -> bool:
        return self.sub_action_index != -1

    @property
    def action(self):
        return None if self.actions is None else self.actions[self.action_index]

    @property
    def sub_action(self):
        return None if self.sub_actions is None or \
                       self.sub_action_index == -1 \
                       else self.sub_actions[self.sub_action_index]

    def is_job_selected(self):
        return self.widget_type == 'job'

    def is_action_selected(self):
        return self.widget_type == 'action'

    def is_subaction_selected(self):
        return self.widget_type == 'subaction'

    def is_valid(self):
        return self.widget_type is not None

    def to_tuple(self):
        return (self.job_index, self.action_index, self.sub_action_index)

    def copy(self):
        return ClassicSelectionState(
            actions=self.actions,
            sub_actions=self.sub_actions,
            action_index=self.action_index,
            sub_action_index=self.sub_action_index,
            job_index=self.job_index,
            widget_type=self.widget_type
        )

    def reset(self):
        self.actions = None
        self.sub_actions = None
        self.action_index = -1
        self.sub_action_index = -1
        self.job_index = -1
        self.widget_type = None

    def set_job(self, job_index):
        self.job_index = job_index
        self.action_index = -1
        self.sub_action_index = -1
        self.widget_type = 'job'

    def set_action(self, job_index, action_index):
        self.job_index = job_index
        self.action_index = action_index
        self.sub_action_index = -1
        self.widget_type = 'action'

    def set_subaction(self, job_index, action_index, subaction_index):
        self.job_index = job_index
        self.action_index = action_index
        self.sub_action_index = subaction_index
        self.widget_type = 'subaction'
