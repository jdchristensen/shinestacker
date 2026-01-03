# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, R0912, R0911
from .. config.constants import constants
from .. gui.element_action_manager import ElementActionManager
from .element_operations import ElementOperations
from .selection_state import indices_to_state


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
            return self._delete_job(self.selection_state.job_index, confirm)
        if self.selection_state.is_action_selected():
            return self._delete_action(
                self.selection_state.job_index, self.selection_state.action_index, confirm)
        if self.selection_state.is_subaction_selected():
            return self._delete_subaction(
                self.selection_state.job_index, self.selection_state.action_index,
                self.selection_state.subaction_index, confirm)
        return None

    def _delete_job(self, job_index, confirm=True):
        if not 0 <= job_index < self.num_project_jobs():
            return None
        job = self.project().jobs[job_index]
        if confirm and self.confirm_delete_message('job', job.params.get('name', '')):
            return None
        self.mark_as_modified(True, "Delete Job")
        deleted_job = self.project().jobs.pop(job_index)
        new_indices = self.new_indices_after_delete(self.selection_state)
        self.callbacks['refresh_ui'](indices_to_state(*new_indices))
        return deleted_job

    def _delete_action(self, job_index, action_index, confirm=True):
        if not 0 <= job_index < self.num_project_jobs():
            return None
        job = self.project().jobs[job_index]
        if not 0 <= action_index < len(job.sub_actions):
            return None
        action = job.sub_actions[action_index]
        if confirm and self.confirm_delete_message('action', action.params.get('name', '')):
            return None
        self.mark_as_modified(True, "Delete Action")
        deleted_action = job.sub_actions.pop(action_index)
        new_indices = self.new_indices_after_delete(self.selection_state)
        self.callbacks['refresh_ui'](indices_to_state(*new_indices))
        return deleted_action

    def _delete_subaction(self, job_index, action_index, subaction_index, confirm=True):
        if not 0 <= job_index < self.num_project_jobs():
            return None
        job = self.project().jobs[job_index]
        if not 0 <= action_index < len(job.sub_actions):
            return None
        action = job.sub_actions[action_index]
        if not 0 <= subaction_index < len(action.sub_actions):
            return None
        subaction = action.sub_actions[subaction_index]
        if confirm and self.confirm_delete_message('sub-action', subaction.params.get('name', '')):
            return None
        self.mark_as_modified(True, "Delete Sub-action")
        deleted_subaction = action.sub_actions.pop(subaction_index)
        new_indices = self.new_indices_after_delete(self.selection_state)
        self.callbacks['refresh_ui'](indices_to_state(*new_indices))
        return deleted_subaction

    def set_enabled(self, enabled):
        if not self.selection_state.is_valid():
            return
        if self.selection_state.is_job_selected():
            job_index = self.selection_state.job_index
            if 0 <= job_index < self.num_project_jobs():
                job = self.project().jobs[job_index]
                if job.enabled() != enabled:
                    self._set_element_enabled(job, enabled, "Job")
                    self.callbacks['refresh_ui']()
        elif self.selection_state.is_action_selected() \
                or self.selection_state.is_subaction_selected():
            element = self._get_selected_action()
            if element and element.enabled() != enabled:
                element_type = "Sub-action" \
                    if self.selection_state.is_subaction_selected() else "Action"
                self._set_element_enabled(element, enabled, element_type)
                self.callbacks['refresh_ui']()

    def _get_selected_action(self):
        if self.selection_state.is_action_selected():
            job_idx = self.selection_state.job_index
            action_idx = self.selection_state.action_index
            if (0 <= job_idx < self.num_project_jobs() and
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions)):
                return self.project().jobs[job_idx].sub_actions[action_idx]
        elif self.selection_state.is_subaction_selected():
            job_idx = self.selection_state.job_index
            action_idx = self.selection_state.action_index
            subaction_idx = self.selection_state.subaction_index
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
        self.callbacks['refresh_ui']()

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
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            self.paste_subaction()
        elif self.selection_state.is_job_selected():
            self.paste_job()
        elif self.selection_state.is_action_selected():
            self.paste_action()
        elif self.selection_state.is_subaction_selected():
            self.paste_subaction()

    def paste_job(self):
        if not self.has_copy_buffer():
            return
        copy_buffer = self.copy_buffer()
        success, element_type, index = self.paste_job_logic(
            copy_buffer, self.selection_state.job_index, True)
        if not success:
            return
        if element_type == 'action':
            self.mark_as_modified(True, "Paste Action")
            self.selection_state.set_action(self.selection_state.job_index, index)
        else:
            self.mark_as_modified(True, "Paste Job")
            self.selection_state.set_job(index)
        self.callbacks['refresh_ui']()
        self.callbacks['ensure_selected_visible']()

    def paste_action(self):
        if not self.has_copy_buffer():
            return
        if self.selection_state.job_index < 0:
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name not in constants.ACTION_TYPES:
            return
        self.mark_as_modified(True, "Paste Action")
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= 0:
            new_action_index = self.selection_state.action_index + 1
        else:
            new_action_index = len(job.sub_actions)
        job.sub_actions.insert(new_action_index, copy_buffer.clone())
        self.selection_state.set_action(self.selection_state.job_index, new_action_index)
        self.callbacks['refresh_ui']()
        self.callbacks['ensure_selected_visible']()

    def paste_subaction(self):
        if not self.has_copy_buffer():
            return
        if self.selection_state.job_index < 0 or self.selection_state.action_index < 0:
            return
        copy_buffer = self.copy_buffer()
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= len(job.sub_actions):
            return
        action = job.sub_actions[self.selection_state.action_index]
        if action.type_name != constants.ACTION_COMBO:
            return
        if copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
            return
        self.mark_as_modified(True, "Paste Sub-action")
        if self.selection_state.subaction_index >= 0:
            new_subaction_index = self.selection_state.subaction_index + 1
        else:
            new_subaction_index = 0
        action.sub_actions.insert(new_subaction_index, copy_buffer.clone())
        self.selection_state.set_subaction(
            self.selection_state.job_index,
            self.selection_state.action_index,
            new_subaction_index)
        self.callbacks['refresh_ui']()
        self.callbacks['ensure_selected_visible']()

    def cut_element(self):
        element = self.delete_element(False)
        if element:
            self.set_copy_buffer(element)

    def clone_job(self):
        if not self.selection_state.is_job_selected():
            return
        if not 0 <= self.selection_state.job_index < self.num_project_jobs():
            return
        self.mark_as_modified(True, "Duplicate Job")
        job = self.project().jobs[self.selection_state.job_index]
        job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
        new_job_index = self.selection_state.job_index + 1
        self.project().jobs.insert(new_job_index, job_clone)
        self.selection_state.set_job(new_job_index)
        self.callbacks['refresh_ui']()

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
                self.selection_state.action_index = new_action_index
                self.selection_state.subaction_index = -1
                self.selection_state.widget_type = 'action'
                self.callbacks['refresh_ui']()
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
                    self.selection_state.subaction_index = new_subaction_index
                    self.selection_state.widget_type = 'subaction'
                    self.callbacks['refresh_ui']()

    def _shift_job(self, delta):
        if not self.selection_state.is_job_selected():
            return
        job_idx, _, _ = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_job(job_idx, delta)
        if new_index != job_idx:
            self.mark_as_modified(True, "Shift Job")
            self.selection_state.set_job(new_index)
            self.callbacks['refresh_ui']()

    def _shift_action(self, delta):
        if not self.selection_state.is_action_selected():
            return
        job_idx, action_idx, _ = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_action(job_idx, action_idx, delta)
        if new_index != action_idx:
            self.mark_as_modified(True, "Shift Action")
            self.selection_state.set_action(job_idx, new_index)
            self.callbacks['refresh_ui']()

    def _shift_subaction(self, delta):
        if not self.selection_state.is_subaction_selected():
            return
        job_idx, action_idx, subaction_idx = self.selection_state.to_tuple()
        new_index = self.element_ops.shift_subaction(job_idx, action_idx, subaction_idx, delta)
        if new_index != subaction_idx:
            self.mark_as_modified(True, "Shift Sub-action")
            self.selection_state.set_subaction(job_idx, action_idx, new_index)
            self.callbacks['refresh_ui']()

    def _refresh_after_enable_all(self):
        self.callbacks['refresh_ui']()
