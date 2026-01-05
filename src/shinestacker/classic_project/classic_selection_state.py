# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101
from dataclasses import dataclass
from .. common_project.base_selection_state import BaseSelectionState


@dataclass
class ClassicSelectionState:
    actions: list
    sub_actions: list
    action_index: int
    subaction_index: int = -1
    job_index: int = -1
    widget_type: str = None

    def __post_init__(self):
        self._state = BaseSelectionState()
        self._state.job_index = self.job_index
        self._state.action_index = self.action_index
        self._state.subaction_index = self.subaction_index
        self._state.widget_type = self.widget_type

    @property
    def is_sub_action(self):
        return self.subaction_index != -1

    @property
    def action(self):
        return None if self.actions is None else self.actions[self.action_index]

    @property
    def sub_action(self):
        return None if self.sub_actions is None or \
                       self.subaction_index == -1 \
                       else self.sub_actions[self.subaction_index]

    def is_job_selected(self):
        return self.widget_type == 'job'

    def is_action_selected(self):
        return self.widget_type == 'action'

    def is_subaction_selected(self):
        return self.widget_type == 'subaction'

    def is_valid(self):
        return self.widget_type is not None

    def to_tuple(self):
        return self._state.to_tuple()

    def from_tuple(self, indices_tuple):
        self._state.from_tuple(indices_tuple)
        self._sync_from_state()

    def copy(self):
        return ClassicSelectionState(
            actions=self.actions,
            sub_actions=self.sub_actions,
            action_index=self.action_index,
            subaction_index=self.subaction_index,
            job_index=self.job_index,
            widget_type=self.widget_type
        )

    def reset(self):
        self.actions = None
        self.sub_actions = None
        self._state.reset()
        self._sync_from_state()

    def set_job(self, job_index):
        self._state.set_job(job_index)
        self._sync_from_state()

    def set_action(self, job_index, action_index):
        self._state.set_action(job_index, action_index)
        self._sync_from_state()

    def set_subaction(self, job_index, action_index, subaction_index):
        self._state.set_subaction(job_index, action_index, subaction_index)
        self._sync_from_state()

    def get_action_row(self):
        if not (self.is_action_selected() or self.is_subaction_selected()):
            return -1
        row = -1
        for i, action in enumerate(self.actions):
            row += 1
            if i == self.action_index:
                if self.is_subaction_selected():
                    row += self.subaction_index + 1
                return row
            row += len(action.sub_actions)
        return -1

    def _sync_from_state(self):
        self.job_index = self._state.job_index
        self.action_index = self._state.action_index
        self.subaction_index = self._state.subaction_index
        self.widget_type = self._state.widget_type


def rows_to_state(project, job_row, action_row):
    if job_row < 0:
        return None
    if action_row < 0:
        return ClassicSelectionState(None, None, -1, -1, job_row, 'job')
    job = project.jobs[job_row]
    current_row = -1
    for i, action in enumerate(job.sub_actions):
        current_row += 1
        if current_row == action_row:
            return ClassicSelectionState(
                job.sub_actions,
                None,
                i,
                -1,
                job_row,
                'action'
            )
        if action.sub_actions:
            for sub_idx, _ in enumerate(action.sub_actions):
                current_row += 1
                if current_row == action_row:
                    return ClassicSelectionState(
                        job.sub_actions,
                        action.sub_actions,
                        i,
                        sub_idx,
                        job_row,
                        'subaction'
                    )
    return ClassicSelectionState(None, None, -1, -1, job_row, 'job')
