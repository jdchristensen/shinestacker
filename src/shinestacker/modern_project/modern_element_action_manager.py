# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, R0912, R0911, R0904
from .. config.constants import constants
from .. gui.element_action_manager import ElementActionManager
from .element_operations import ElementOperations
from .modern_selection_state import indices_to_state, ModernSelectionState


class ModernElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, view_callbacks, parent=None):
        super().__init__(project_holder, parent)
        self.element_ops = ElementOperations(project_holder)
        self.selection_state = selection_state
        self.callbacks = view_callbacks
        self.selection_nav = None

    def new_indices_after_delete(self, state):
        job_idx, act_idx, sub_idx = state.to_tuple()
        if job_idx < 0:
            return (-1, -1, -1)
        if sub_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return (-1, -1, -1)
            job = self.project_job(job_idx)
            if act_idx >= len(job.sub_actions):
                return (job_idx, -1, -1)
            action = job.sub_actions[act_idx]
            num_sub = len(action.sub_actions) + 1
            if sub_idx < num_sub - 1:
                return (job_idx, act_idx, sub_idx)
            return (job_idx, act_idx, sub_idx - 1)
        if act_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return (-1, -1, -1)
            job = self.project_job(job_idx)
            num_act = len(job.sub_actions) + 1
            if act_idx >= num_act:
                return (job_idx, -1, -1)
            if act_idx < num_act - 1:
                return (job_idx, act_idx, -1)
            if act_idx == 0:
                return (job_idx, -1, -1)
            return (job_idx, act_idx - 1, -1)
        num_jobs = self.num_project_jobs() + 1
        if job_idx >= num_jobs:
            return (-1, -1, -1)
        if job_idx < num_jobs - 1:
            return (job_idx, -1, -1)
        if job_idx == 0:
            return (-1, -1, -1)
        return (job_idx - 1, -1, -1)

    def new_indices_after_clone(self, state):
        job_idx, act_idx, sub_idx = state.to_tuple()
        if sub_idx >= 0:
            return (job_idx, act_idx, sub_idx + 1)
        if act_idx >= 0:
            return (job_idx, act_idx + 1, -1)
        return (job_idx + 1, -1, -1)

    def new_indices_after_insert(self, state, delta):
        job_idx, act_idx, sub_idx = state.to_tuple()
        if job_idx < 0:
            return (-1, -1, -1)
        if sub_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return (job_idx, act_idx, sub_idx)
            job = self.project_job(job_idx)
            if act_idx >= len(job.sub_actions):
                return (job_idx, act_idx, sub_idx)
            action = job.sub_actions[act_idx]
            num_sub = len(action.sub_actions) + 1
            new_sub_idx = sub_idx + delta
            if 0 <= new_sub_idx < num_sub:
                return (job_idx, act_idx, new_sub_idx)
        elif act_idx >= 0:
            if job_idx >= self.num_project_jobs():
                return (job_idx, act_idx, -1)
            job = self.project_job(job_idx)
            num_act = len(job.sub_actions) + 1
            new_act_idx = act_idx + delta
            if 0 <= new_act_idx < num_act:
                return (job_idx, new_act_idx, -1)
        else:
            num_jobs = self.num_project_jobs() + 1
            new_job_idx = job_idx + delta
            if 0 <= new_job_idx < num_jobs:
                return (new_job_idx, -1, -1)
        return (job_idx, act_idx, sub_idx)

    def set_selection_navigation(self, selection_nav):
        self.selection_nav = selection_nav

    def is_job_selected(self):
        return self.selection_state.is_job_selected()

    def is_action_selected(self):
        return self.selection_state.is_action_selected()

    def is_subaction_selected(self):
        return self.selection_state.is_subaction_selected()

    def get_selected_job_index(self):
        return self.selection_state.job_index

    def delete_element(self, confirm=True):
        if self.selection_state.is_job_selected():
            return self._delete_job(confirm)
        if self.selection_state.is_action_selected():
            return self._delete_action(confirm)
        if self.selection_state.is_subaction_selected():
            return self._delete_subaction(confirm)
        return None

    def _delete_job(self, confirm=True):
        job_index = self.selection_state.job_index
        if not 0 <= job_index < self.num_project_jobs():
            raise IndexError(f"Job index {job_index} out of range in data model")
        job = self.project().jobs[job_index]
        if confirm and not self.confirm_delete_message('job', job.params.get('name', '')):
            return None
        self.mark_as_modified(True, "Delete Job")
        deleted_job = self.project().jobs.pop(job_index)
        old_state = self.selection_state.copy()
        removal_state = ModernSelectionState()
        removal_state.set_job(job_index)
        self.callbacks['remove_widget'](removal_state)
        new_indices = self.new_indices_after_delete(old_state)
        new_state = indices_to_state(*new_indices)
        self.selection_state.copy_from(new_state)
        self.callbacks['update_selection'](new_state)
        if new_state:
            self.callbacks['ensure_selected_visible']()
        return deleted_job

    def _delete_action(self, confirm=True):
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        if not 0 <= job_index < self.num_project_jobs():
            raise IndexError(f"Job index {job_index} out of range")
        job = self.project().jobs[job_index]
        if not 0 <= action_index < len(job.sub_actions):
            raise IndexError(f"Action index {action_index} out of range for job {job_index}")
        action = job.sub_actions[action_index]
        if confirm and not self.confirm_delete_message('action', action.params.get('name', '')):
            return None
        self.mark_as_modified(True, "Delete Action")
        deleted_action = job.sub_actions.pop(action_index)
        old_state = self.selection_state.copy()
        removal_state = ModernSelectionState()
        removal_state.set_action(job_index, action_index)
        self.callbacks['remove_widget'](removal_state)
        new_indices = self.new_indices_after_delete(old_state)
        new_state = indices_to_state(*new_indices)
        self.callbacks['update_selection'](new_state)
        if new_state:
            self.callbacks['ensure_selected_visible']()
        return deleted_action

    def _delete_subaction(self, confirm=True):
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        subaction_index = self.selection_state.subaction_index
        if not 0 <= job_index < self.num_project_jobs():
            raise IndexError(f"Job index {job_index} out of range")
        job = self.project().jobs[job_index]
        if not 0 <= action_index < len(job.sub_actions):
            raise IndexError(f"Action index {action_index} out of range for job {job_index}")
        action = job.sub_actions[action_index]
        if not 0 <= subaction_index < len(action.sub_actions):
            raise IndexError(
                f"Subaction index {subaction_index} out of range for action {action_index}")
        subaction = action.sub_actions[subaction_index]
        if confirm and not self.confirm_delete_message(
                'sub-action', subaction.params.get('name', '')):
            return None
        self.mark_as_modified(True, "Delete Sub-action")
        deleted_subaction = action.sub_actions.pop(subaction_index)
        old_state = self.selection_state.copy()
        removal_state = ModernSelectionState()
        removal_state.set_subaction(job_index, action_index, subaction_index)
        self.callbacks['remove_widget'](removal_state)
        new_indices = self.new_indices_after_delete(old_state)
        new_state = indices_to_state(*new_indices)
        self.callbacks['update_selection'](new_state)
        if new_state:
            self.callbacks['ensure_selected_visible']()
        return deleted_subaction

    def set_enabled(self, enabled, selection=None, update_project=True):
        if selection is None:
            selection = self.selection_state
        if not selection.is_valid():
            return
        if update_project:
            self._set_enabled_with_project_update(selection, enabled)
        else:
            self._set_enabled_ui_only(selection)

    def _set_enabled_with_project_update(self, selection, enabled):
        if selection.is_job_selected():
            job_index = selection.job_index
            if 0 <= job_index < self.num_project_jobs():
                job = self.project().jobs[job_index]
                if job.enabled() != enabled:
                    self._set_element_enabled(job, enabled, "Job")
                    current_indices = selection.to_tuple()
                    self.callbacks['refresh_ui'](indices_to_state(*current_indices))
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = self._get_element_from_selection(selection)
            if element and element.enabled() != enabled:
                element_type = "Sub-action" if selection.is_subaction_selected() else "Action"
                self._set_element_enabled(element, enabled, element_type)
                current_indices = selection.to_tuple()
                self.callbacks['refresh_ui'](indices_to_state(*current_indices))

    def _set_enabled_ui_only(self, selection):
        current_indices = selection.to_tuple()
        self.callbacks['refresh_ui'](indices_to_state(*current_indices))

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
        self.mark_as_modified(True, f"{action} All")
        for job in self.project().jobs:
            job.set_enabled_all(enabled)

    def copy_job(self):
        job_clone = self.element_ops.copy_job(self.selection_state.job_index)
        if job_clone:
            self.set_copy_buffer(job_clone)

    def copy_action(self):
        if not self.selection_state.is_action_selected():
            return
        job_idx, action_idx, _ = self.selection_state.to_tuple()
        job_clone = self.element_ops.copy_action(job_idx, action_idx)
        if job_clone:
            self.set_copy_buffer(job_clone)

    def copy_subaction(self):
        if not self.selection_state.is_subaction_selected():
            return
        job_idx, action_idx, subaction_idx = self.selection_state.to_tuple()
        job_clone = self.element_ops.copy_subaction(job_idx, action_idx, subaction_idx)
        if job_clone:
            self.set_copy_buffer(job_clone)

    def paste_element(self):
        if not self.has_copy_buffer():
            return False
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            return self.paste_subaction()
        if self.selection_state.is_job_selected():
            return self.paste_job()
        if self.selection_state.is_action_selected():
            return self.paste_action()
        if self.selection_state.is_subaction_selected():
            return self.paste_subaction()
        return False

    def paste_job(self):
        if not self.has_copy_buffer():
            return False
        copy_buffer = self.copy_buffer()
        success, element_type, _index = self.paste_job_logic(
            copy_buffer, self.selection_state.job_index, True)
        if not success:
            return False
        if element_type == 'action':
            self.mark_as_modified(True, "Paste Action")
            new_indices = self.new_indices_after_insert(self.selection_state, 0)
            self.selection_state.set_action(new_indices[0], new_indices[1])
        else:
            self.mark_as_modified(True, "Paste Job")
            new_indices = self.new_indices_after_insert(self.selection_state, 1)
            self.selection_state.set_job(new_indices[0])
        return True

    def paste_action(self):
        if not self.has_copy_buffer():
            return False
        if self.selection_state.job_index < 0:
            return False
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name not in constants.ACTION_TYPES:
            return False
        self.mark_as_modified(True, "Paste Action")
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= 0:
            new_indices = self.new_indices_after_insert(self.selection_state, 1)
            new_action_index = new_indices[1]
        else:
            new_indices = self.new_indices_after_insert(self.selection_state, 0)
            new_action_index = new_indices[1]
        job.sub_actions.insert(new_action_index, copy_buffer.clone())
        self.selection_state.set_action(new_indices[0], new_indices[1])
        return True

    def paste_subaction(self):
        if not self.has_copy_buffer():
            return False
        if self.selection_state.job_index < 0 or self.selection_state.action_index < 0:
            return False
        copy_buffer = self.copy_buffer()
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= len(job.sub_actions):
            return False
        action = job.sub_actions[self.selection_state.action_index]
        if action.type_name != constants.ACTION_COMBO:
            return False
        if copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
            return False
        self.mark_as_modified(True, "Paste Sub-action")
        if self.selection_state.subaction_index >= 0:
            new_indices = self.new_indices_after_insert(self.selection_state, 1)
            new_subaction_index = new_indices[2]
        else:
            new_indices = (self.selection_state.job_index,
                           self.selection_state.action_index, 0)
            new_subaction_index = 0
        action.sub_actions.insert(new_subaction_index, copy_buffer.clone())
        self.selection_state.set_subaction(new_indices[0], new_indices[1], new_indices[2])
        return True

    def cut_element(self):
        element = self.delete_element(False)
        if element:
            self.set_copy_buffer(element)

    def clone_element(self):
        if self.selection_state.is_job_selected():
            return self.clone_job()
        if self.selection_state.is_action_selected() or \
                self.selection_state.is_subaction_selected():
            return self.clone_action()
        return False

    def clone_job(self):
        if not self.selection_state.is_job_selected():
            return False
        if not 0 <= self.selection_state.job_index < self.num_project_jobs():
            return False
        self.mark_as_modified(True, "Duplicate Job")
        job = self.project().jobs[self.selection_state.job_index]
        job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
        new_job_index = self.selection_state.job_index + 1
        self.project().jobs.insert(new_job_index, job_clone)
        return True

    def clone_action(self):
        if self.selection_state.widget_type == 'action':
            job_index = self.selection_state.job_index
            action_index = self.selection_state.action_index
            if (0 <= job_index < self.num_project_jobs() and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                self.mark_as_modified(True, "Duplicate Action")
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                action_clone = action.clone(name_postfix=self.CLONE_POSTFIX)
                new_action_index = action_index + 1
                job.sub_actions.insert(new_action_index, action_clone)
                return True
        elif self.selection_state.widget_type == 'subaction':
            job_index = self.selection_state.job_index
            action_index = self.selection_state.action_index
            subaction_index = self.selection_state.subaction_index
            if (0 <= job_index < self.num_project_jobs() and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                if (action.type_name == constants.ACTION_COMBO and
                        0 <= subaction_index < len(action.sub_actions)):
                    self.mark_as_modified(True, "Duplicate Sub-action")
                    subaction = action.sub_actions[subaction_index]
                    subaction_clone = subaction.clone(name_postfix=self.CLONE_POSTFIX)
                    new_subaction_index = subaction_index + 1
                    action.sub_actions.insert(new_subaction_index, subaction_clone)
                    return True
        return False

    def _shift_job(self, delta):
        if not self.selection_state.is_job_selected():
            return False
        job_idx, _, _ = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_job(job_idx, delta)
        if new_index != job_idx:
            self.mark_as_modified(True, "Shift Job")
            new_indices = (new_index, -1, -1)
            self.selection_state.set_job(new_index)
            self.callbacks['refresh_ui'](indices_to_state(*new_indices))
            return True
        return False

    def _shift_action(self, delta):
        if not self.selection_state.is_action_selected():
            return False
        job_idx, action_idx, _ = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_action(job_idx, action_idx, delta)
        if new_index != action_idx:
            self.mark_as_modified(True, "Shift Action")
            new_indices = (job_idx, new_index, -1)
            self.selection_state.set_action(job_idx, new_index)
            self.callbacks['refresh_ui'](indices_to_state(*new_indices))
            return True
        return False

    def _shift_subaction(self, delta):
        if not self.selection_state.is_subaction_selected():
            return False
        job_idx, action_idx, subaction_idx = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_subaction(job_idx, action_idx, subaction_idx, delta)
        if new_index != subaction_idx:
            self.mark_as_modified(True, "Shift Sub-action")
            new_indices = (job_idx, action_idx, new_index)
            self.selection_state.set_subaction(job_idx, action_idx, new_index)
            self.callbacks['refresh_ui'](indices_to_state(*new_indices))
            return True
        return False

    def _refresh_after_enable_all(self):
        self.callbacks['refresh_ui']()
