# pylint: disable=C0114, C0115, C0116, W0246, E0611, R0917, R0913, R0912, R0911, R0904
from .. config.constants import constants
from .. common_project.element_action_manager import ElementActionManager
from .. common_project.selection_state import SelectionState
from .element_operations import ElementOperations


class ModernElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, parent=None):
        super().__init__(project_holder, parent)
        self.element_ops = ElementOperations(project_holder)
        self.selection_state = selection_state
        self.selection_nav = None

    def new_indices_after_delete(self, state):
        job_idx, act_idx, sub_idx = state.to_tuple()
        if not state.are_indices_valid():
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
        if not state.are_indices_valid():
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
        if not self.selection_state.is_valid():
            return None, None, None
        job_index = self.selection_state.job_index
        action_index = self.selection_state.action_index
        subaction_index = self.selection_state.subaction_index
        if not 0 <= job_index < self.num_project_jobs():
            return None, None, None
        job = self.project().jobs[job_index]
        if self.selection_state.is_subaction_selected():
            if not 0 <= action_index < len(job.sub_actions):
                return None, None, None
            action = job.sub_actions[action_index]
            if not 0 <= subaction_index < len(action.sub_actions):
                return None, None, None
            element = action.sub_actions[subaction_index]
            element_type = 'sub-action'
            position = (job_index, action_index, subaction_index)
            removal_state = SelectionState()
            removal_state.set_subaction(job_index, action_index, subaction_index)
        elif self.selection_state.is_action_selected():
            if not 0 <= action_index < len(job.sub_actions):
                return None, None, None
            element = job.sub_actions[action_index]
            element_type = 'action'
            position = (job_index, action_index, -1)
            removal_state = SelectionState()
            removal_state.set_action(job_index, action_index)
        else:
            element = job
            element_type = 'job'
            position = (job_index, -1, -1)
            removal_state = SelectionState()
            removal_state.set_job(job_index)
        if confirm and not self.confirm_delete_message(
                element_type, element.params.get('name', '')):
            return None, None, None
        self.mark_as_modified(True, f"Delete {element_type.title()}", "delete", position)
        if self.selection_state.is_subaction_selected():
            deleted_element = job.sub_actions[action_index].sub_actions.pop(subaction_index)
        elif self.selection_state.is_action_selected():
            deleted_element = job.sub_actions.pop(action_index)
        else:
            deleted_element = self.project().jobs.pop(job_index)
        old_state = self.selection_state.copy()
        new_indices = self.new_indices_after_delete(old_state)
        new_state = SelectionState(*new_indices)
        return removal_state, new_state, deleted_element

    def set_enabled(self, enabled, selection=None, update_project=True):
        if selection is None:
            selection = self.selection_state
        if not selection.is_valid():
            return
        if update_project:
            self._set_enabled_with_project_update(selection, enabled)

    def _set_enabled_with_project_update(self, selection, enabled):
        if selection.is_job_selected():
            job_index = selection.job_index
            if 0 <= job_index < self.num_project_jobs():
                job = self.project().jobs[job_index]
                if job.enabled() != enabled:
                    action_text = "Enable" if enabled else "Disable"
                    self.mark_as_modified(True, f"{action_text} Job", "edit", (job_index, -1, -1))
                    self._set_element_enabled(job, enabled, "Job")
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = self._get_element_from_selection(selection)
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
        self.mark_as_modified(True, f"{action} All", "edit_all", (-1, -1, -1))
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
        if copy_buffer.type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return False
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return False
            new_action_index = len(self.project().jobs[self.selection_state.job_index].sub_actions)
            success, _element_type, _index = self.paste_job_logic(
                copy_buffer, self.selection_state.job_index, True,
                "Paste Action", "paste", (self.selection_state.job_index, new_action_index, -1))
            if success:
                new_indices = self.new_indices_after_insert(self.selection_state, 0)
                self.selection_state.set_action(new_indices[0], new_indices[1])
            return success
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(self.selection_state.job_index + 1, 0), self.num_project_jobs())
        success, _element_type, _index = self.paste_job_logic(
            copy_buffer, self.selection_state.job_index, True,
            "Paste Job", "paste", (new_job_index, -1, -1))
        if success:
            new_indices = self.new_indices_after_insert(self.selection_state, 1)
            self.selection_state.set_job(new_indices[0])
        return success

    def paste_action(self):
        if not self.has_copy_buffer():
            return False
        if self.selection_state.job_index < 0:
            return False
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name not in constants.ACTION_TYPES:
            return False
        job = self.project().jobs[self.selection_state.job_index]
        if self.selection_state.action_index >= 0:
            new_indices = self.new_indices_after_insert(self.selection_state, 1)
            new_action_index = new_indices[1]
        else:
            new_indices = self.new_indices_after_insert(self.selection_state, 0)
            new_action_index = new_indices[1]
        self.mark_as_modified(
            True, "Paste Action", "paste",
            (self.selection_state.job_index, new_action_index, -1))
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
        if self.selection_state.subaction_index >= 0:
            new_indices = self.new_indices_after_insert(self.selection_state, 1)
            new_subaction_index = new_indices[2]
        else:
            new_indices = (self.selection_state.job_index,
                           self.selection_state.action_index, 0)
            new_subaction_index = 0
        self.mark_as_modified(
            True, "Paste Sub-action", "paste",
            (self.selection_state.job_index, self.selection_state.action_index,
             new_subaction_index))
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
        job_index = self.selection_state.job_index
        self.mark_as_modified(True, "Duplicate Job", "clone", (job_index, -1, -1))
        job = self.project().jobs[job_index]
        job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
        new_job_index = job_index + 1
        self.project().jobs.insert(new_job_index, job_clone)
        return True

    def clone_action(self):
        if self.selection_state.widget_type == 'action':
            job_index = self.selection_state.job_index
            action_index = self.selection_state.action_index
            if (0 <= job_index < self.num_project_jobs() and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                self.mark_as_modified(
                    True, "Duplicate Action", "clone", (job_index, action_index, -1))
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
                    self.mark_as_modified(
                        True, "Duplicate Sub-action", "clone",
                        (job_index, action_index, subaction_index))
                    subaction = action.sub_actions[subaction_index]
                    subaction_clone = subaction.clone(name_postfix=self.CLONE_POSTFIX)
                    new_subaction_index = subaction_index + 1
                    action.sub_actions.insert(new_subaction_index, subaction_clone)
                    return True
        return False

    def _shift_job(self, delta):
        if not self.selection_state.is_job_selected():
            return False
        prev_sel = self.selection_state.copy()
        new_index = self.element_ops.shift_job(
            prev_sel.job_index, delta)
        if new_index != prev_sel.job_index:
            self.selection_state.set_job(new_index)
            return True
        return False

    def _shift_action(self, delta):
        if not self.selection_state.is_action_selected():
            return False
        prev_sel = self.selection_state.copy()
        new_index = self.element_ops.shift_action(
            prev_sel.job_index, prev_sel.action_index, delta)
        if new_index != prev_sel.action_index:
            self.selection_state.set_action(prev_sel.job_index, new_index)
            return True
        return False

    def _shift_subaction(self, delta):
        if not self.selection_state.is_subaction_selected():
            return False
        prev_sel = self.selection_state.copy()
        new_index = self.element_ops.shift_subaction(
            prev_sel.job_index, prev_sel.action_index, prev_sel.subaction_index, delta)
        if new_index != prev_sel.subaction_index:
            self.selection_state.set_subaction(prev_sel.job_index, prev_sel.action_index, new_index)
            return True
        return False
