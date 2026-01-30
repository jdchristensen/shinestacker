# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, W0613, R0911, R0912, R0904
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox
from .. config.constants import constants
from .. common_project.selection_state import SelectionState
from .project_handler import ProjectHandler

CLONE_POSTFIX = ' (clone)'


class ElementActionManager(ProjectHandler, QObject):
    project_modified_signal = Signal(bool)

    def __init__(self, project_holder, selection_state, parent=None):
        ProjectHandler.__init__(self, project_holder)
        self.selection_state = selection_state
        QObject.__init__(self, parent)

    def new_state_after_op(self, state, delta):
        job_idx, act_idx, sub_idx = state.to_tuple()
        job = self.project_job(job_idx)
        if job is None:
            return SelectionState()
        if act_idx > len(job.sub_actions):
            return SelectionState(job_idx)
        if sub_idx >= 0:
            num_sub = len(job.sub_actions[act_idx].sub_actions)
            return SelectionState(job_idx, act_idx, min(sub_idx + delta, num_sub - 1))
        if act_idx >= 0:
            num_act = len(job.sub_actions)
            return SelectionState(job_idx, min(act_idx + delta, num_act - 1))
        num_job = self.num_project_jobs()
        return SelectionState(min(job_idx + delta, num_job - 1))

    def new_state_after_delete(self, state):
        return self.new_state_after_op(state, 0)

    def new_state_after_insert(self, state):
        return self.new_state_after_op(state, 1)

    def is_job_selected(self):
        return self.selection_state.is_job_selected()

    def is_action_selected(self):
        return self.selection_state.is_action_selected()

    def is_subaction_selected(self):
        return self.selection_state.is_subaction_selected()

    def is_valid_selection(self):
        return self.selection_state.is_valid()

    def get_action(self, selection):
        if not selection.is_action_selected() and not selection.is_subaction_selected():
            return None
        return self.project_element(*selection.to_tuple())

    def get_job_actions(self, selection):
        job = self.project_job(selection.job_index)
        return job.sub_actions if job is not None else None

    def get_subactions(self, selection):
        action = self.project_action(selection.job_index, selection.action_index)
        return action.sub_actions if action is not None else None

    def confirm_delete_message(self, type_name, element_name):
        return QMessageBox.question(
            self.parent(), "Confirm Delete",
            f"Are you sure you want to delete {type_name} '{element_name}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes

    def mark_as_modified(self, modified=True, description='', action_type=None,
                         affected_position=(-1, -1, -1)):
        ProjectHandler.mark_as_modified(self, modified, description, action_type, affected_position)
        self.project_modified_signal.emit(modified)

    def save_undo_state(self, pre_state, description='', action_type='',
                        affected_position=(-1, -1, -1)):
        ProjectHandler.save_undo_state(self, pre_state, description, action_type, affected_position)
        self.project_modified_signal.emit(True)

    def paste_element(self):
        if not self.has_copy_buffer():
            return False
        position = self.selection_state.to_tuple()
        if not self.valid_indices(*position):
            return False
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name == constants.ACTION_JOB:
            level = 0
            idx = (-1, -1)
        elif copy_buffer.type_name in constants.ACTION_TYPES:
            level = 1
            idx = (position[0], -1)
        elif copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            level = 2
            idx = (position[0], position[1])
            action = self.project_action(*idx)
            if not action or action.type_name != constants.ACTION_COMBO:
                return False
        else:
            return False
        container = self.project_container(*idx)
        if container is None:
            return False
        pos = position[level] if len(position) > level else -1
        insert_index = min(max(pos + 1 if pos >= 0 else len(container), 0), len(container))
        element_type = ["Job", "Action", "Subaction"][level]
        self.mark_as_modified(True, f"Paste {element_type}", "paste", position)
        container.insert(insert_index, copy_buffer.clone())
        new_position = list(position[:level]) + [insert_index] + [-1] * (2 - level)
        self.selection_state.from_tuple(new_position)
        return True

    def shift_element(self, delta):
        if not self.selection_state.is_valid():
            return False
        position = self.selection_state.to_tuple()
        idx, current_index = self._get_position_stack(position)
        if len(idx) == 0:
            return False
        container = self.project_container(*idx)
        if not container:
            return False
        new_index = current_index + delta
        if 0 <= new_index < len(container):
            container.insert(new_index, container.pop(current_index))
            if position[2] >= 0:
                self.selection_state.set_subaction(position[0], position[1], new_index)
            elif position[1] >= 0:
                self.selection_state.set_action(position[0], new_index)
            else:
                self.selection_state.set_job(new_index)
            return True
        return False

    def copy_element(self):
        if self.selection_state and self.selection_state.is_valid():
            element = self.project_element(*self.selection_state.to_tuple())
            if element:
                self.set_copy_buffer(element.clone())

    def _get_position_stack(self, position):
        if position[2] >= 0:
            return [position[0], position[1]], position[2]
        if position[1] >= 0:
            return [position[0]], position[1]
        if position[0] >= 0:
            return [-1], position[0]
        return [], -1

    def clone_element(self):
        position = self.selection_state.to_tuple()
        if not self.valid_indices(*position):
            return False, None
        self.mark_as_modified(
            True, f"Duplicate {self.selection_state.type().title()}", "clone", position)
        element = self.project_element(*position)
        new_selection = self.new_state_after_insert(self.selection_state)
        position = self.selection_state.to_tuple()
        idx, s = self._get_position_stack(position)
        if len(idx) == 0:
            return False, None
        container = self.project_container(*idx)
        container.insert(s + 1, element.clone(name_postfix=CLONE_POSTFIX))
        return True, new_selection

    def delete_element(self, confirm=True):
        if not self.selection_state.is_valid():
            return None, None
        position = self.selection_state.to_tuple()
        element = self.project_element(*position)
        if not element:
            return None, None
        element_type = self.selection_state.type()
        if confirm and not self.confirm_delete_message(
                element_type, element.params.get('name', '')):
            return None, None
        self.mark_as_modified(
            True, f"Delete {element_type.title()}", "delete", position)
        deleted_element = None
        idx, s = self._get_position_stack(position)
        if len(idx) == 0:
            return None, None
        container = self.project_container(*idx)
        if container and 0 <= s < len(container):
            deleted_element = container.pop(s)
        return deleted_element, self.new_state_after_delete(self.selection_state)

    def cut_element(self):
        deleted_element, new_state = self.delete_element(False)
        if deleted_element:
            self.set_copy_buffer(deleted_element)
        return deleted_element, new_state

    def _set_element_enabled(self, element, enabled, element_type):
        element.set_enabled(enabled)

    def set_enabled_all(self, enabled):
        action = "Enable" if enabled else "Disable"
        self.mark_as_modified(True, f"{action} All")
        for job in self.project().jobs:
            job.set_enabled_all(enabled)

    def set_enabled(self, enabled, selection):
        if selection is None:
            return False
        position = selection.to_tuple()
        element = self.project_element(*position)
        if not element or element.enabled() == enabled:
            return False
        txt = "Enable" if enabled else "Disable"
        self.mark_as_modified(True, f"{txt} {selection.type().title()}", "edit", position)
        element.set_enabled(enabled)
        return True
