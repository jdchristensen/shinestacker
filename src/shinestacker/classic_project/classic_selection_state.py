# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101
from .. common_project.selection_state import SelectionState


class ClassicSelectionState(SelectionState):
    def __init__(self, actions, sub_actions, action_index,
                 subaction_index=-1, job_index=-1, widget_type=None):
        super().__init__(job_index, action_index, subaction_index)
        self.actions = actions
        self.sub_actions = sub_actions
        if widget_type is not None:
            self.widget_type = widget_type

    @property
    def is_sub_action(self):
        return self.subaction_index != -1

    @property
    def action(self):
        return None if self.actions is None or \
            not 0 <= self.action_index < len(self.actions) else self.actions[self.action_index]

    @property
    def sub_action(self):
        return None if self.sub_actions is None or \
            self.subaction_index == -1 else self.sub_actions[self.subaction_index]

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

    def copy(self):
        return ClassicSelectionState(
            self.actions,
            self.sub_actions,
            self.action_index,
            self.subaction_index,
            self.job_index,
            self.widget_type
        )


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
