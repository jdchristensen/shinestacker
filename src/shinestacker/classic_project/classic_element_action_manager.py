# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101, R0911
from .. config.constants import constants
from .. gui.element_action_manager import ElementActionManager
from .classic_selection_state import rows_to_state


class ClassicElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, callbacks, parent=None):
        super().__init__(project_holder, parent)
        self.selection_state = selection_state
        self.callbacks = callbacks

    @staticmethod
    def new_row_after_delete(action_row, pos):
        if pos.is_sub_action:
            new_row = action_row if pos.sub_action_index < len(pos.sub_actions) else action_row - 1
        else:
            if pos.action_index == 0:
                new_row = 0 if len(pos.actions) > 0 else -1
            elif pos.action_index < len(pos.actions):
                new_row = action_row
            elif pos.action_index == len(pos.actions):
                new_row = action_row - len(pos.actions[pos.action_index - 1].sub_actions) - 1
            else:
                new_row = None
        return new_row

    @staticmethod
    def new_row_after_clone(job, action_row, is_sub_action, cloned):
        return action_row + 1 if is_sub_action else \
            sum(1 + len(action.sub_actions)
                for action in job.sub_actions[:job.sub_actions.index(cloned)])

    @staticmethod
    def new_row_after_insert(action_row, pos, delta):
        new_row = action_row
        if not pos.is_sub_action:
            new_index = pos.action_index + delta
            if 0 <= new_index < len(pos.actions):
                new_row = 0
                for action in pos.actions[:new_index]:
                    new_row += 1 + len(action.sub_actions)
        else:
            new_index = pos.sub_action_index + delta
            if 0 <= new_index < len(pos.sub_actions):
                new_row = 1 + new_index
                for action in pos.actions[:pos.action_index]:
                    new_row += 1 + len(action.sub_actions)
        return new_row

    @staticmethod
    def new_row_after_paste(action_row, pos):
        return ClassicElementActionManager.new_row_after_insert(action_row, pos, 0)

    def is_job_selected(self):
        return self.selection_state.is_job_selected()

    def is_action_selected(self):
        return self.selection_state.is_action_selected()

    def is_subaction_selected(self):
        return self.selection_state.is_subaction_selected()

    def get_selected_job_index(self):
        return self.selection_state.job_index

    def is_valid_selection(self):
        return self.selection_state.is_valid()

    def delete_element(self, confirm=True):
        selection = self.selection_state
        if selection.is_job_selected():
            if not 0 <= selection.job_index < self.num_project_jobs():
                return None
            job = self.project().jobs[selection.job_index]
            if confirm and self.confirm_delete_message('job', job.params.get('name', '')):
                return None
            self.mark_as_modified(True, "Delete Job")
            deleted_job = self.project().jobs.pop(selection.job_index)
            self.callbacks['refresh_ui'](rows_to_state(self.project(), -1, -1))
            return deleted_job
        if selection.is_action_selected() or selection.is_subaction_selected():
            element = selection.sub_action if selection.is_subaction_selected() \
                else selection.action
            container = selection.sub_actions if selection.is_subaction_selected() \
                else selection.actions
            index = selection.sub_action_index if selection.is_subaction_selected() \
                else selection.action_index
            if not element or not container or index < 0 or index >= len(container):
                return None
            element_type = "sub-action" if selection.is_subaction_selected() else "action"
            if confirm and self.confirm_delete_message(
                    element_type, element.params.get('name', '')):
                return None
            self.mark_as_modified(True, f"Delete {element_type}")
            deleted_element = container.pop(index)
            current_action_row = selection.get_action_row()
            new_row = self.new_row_after_delete(current_action_row, selection)
            self.callbacks['refresh_ui'](
                rows_to_state(self.project(), selection.job_index, new_row))
            return deleted_element
        return None

    def copy_job(self):
        if not self.selection_state.is_job_selected():
            return
        job_index = self.selection_state.job_index
        if 0 <= job_index < self.num_project_jobs():
            job_clone = self.project().jobs[job_index].clone()
            self.set_copy_buffer(job_clone)

    def copy_action(self):
        selection = self.selection_state
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return
        if selection.is_subaction_selected():
            if selection.sub_action is not None:
                self.set_copy_buffer(selection.sub_action.clone())
        else:
            if selection.action is not None:
                self.set_copy_buffer(selection.action.clone())

    def copy_subaction(self):
        self.copy_action()

    def paste_element(self):
        if not self.has_copy_buffer():
            return
        copy_buffer = self.copy_buffer()
        selection = self.selection_state
        if selection.is_job_selected():
            self._paste_job(copy_buffer, selection)
        elif selection.is_action_selected() or selection.is_subaction_selected():
            self._paste_action(copy_buffer, selection)

    def _paste_job(self, copy_buffer, selection):
        success, element_type, index = self.paste_job_logic(
            copy_buffer, selection.job_index, False)
        if not success:
            return
        if element_type == 'action':
            self.mark_as_modified(True, "Paste Action")
            self.callbacks['refresh_ui'](rows_to_state(self.project(), selection.job_index, -1))
        else:
            self.mark_as_modified(True, "Paste Job")
            self.callbacks['refresh_ui'](rows_to_state(self.project(), index, -1))

    def _paste_action(self, copy_buffer, selection):
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            target_action = None
            insertion_index = 0
            if selection.is_subaction_selected():
                if selection.action and selection.action.type_name == constants.ACTION_COMBO:
                    target_action = selection.action
                    insertion_index = len(selection.sub_actions)
            else:
                if selection.action and selection.action.type_name == constants.ACTION_COMBO:
                    target_action = selection.action
                    insertion_index = len(selection.action.sub_actions)
            if target_action is not None:
                self.mark_as_modified(True, "Paste Sub-action")
                target_action.sub_actions.insert(insertion_index, copy_buffer)
                current_action_row = selection.get_action_row()
                new_row = self.new_row_after_paste(current_action_row, selection)
                self.callbacks['refresh_ui'](
                    rows_to_state(self.project(), selection.job_index, new_row))
                return
        if copy_buffer.type_name in constants.ACTION_TYPES:
            if not selection.is_subaction_selected():
                if not selection.actions:
                    return
                new_action_index = 0 if len(selection.actions) == 0 else selection.action_index + 1
                self.mark_as_modified(True, "Paste Action")
                selection.actions.insert(new_action_index, copy_buffer)
                current_action_row = selection.get_action_row()
                new_row = self.new_row_after_paste(current_action_row, selection)
                self.callbacks['refresh_ui'](
                    rows_to_state(self.project(), selection.job_index, new_row))

    def cut_element(self):
        element = self.delete_element(False)
        if element:
            self.set_copy_buffer(element)

    def clone_job(self):
        selection = self.selection_state
        if not selection.is_job_selected():
            return
        if 0 <= selection.job_index < self.num_project_jobs():
            self.mark_as_modified(True, "Duplicate Job")
            job = self.project().jobs[selection.job_index]
            job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
            new_job_index = selection.job_index + 1
            self.project().jobs.insert(new_job_index, job_clone)
            self.callbacks['refresh_ui'](rows_to_state(self.project(), new_job_index, -1))

    def clone_action(self):
        selection = self.selection_state
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return
        if not selection.actions:
            return
        self.mark_as_modified(True, "Duplicate Action")
        job = self.project().jobs[selection.job_index]
        if selection.is_subaction_selected():
            cloned = selection.sub_action.clone(name_postfix=self.CLONE_POSTFIX)
            selection.sub_actions.insert(selection.sub_action_index + 1, cloned)
        else:
            cloned = selection.action.clone(name_postfix=self.CLONE_POSTFIX)
            job.sub_actions.insert(selection.action_index + 1, cloned)
        current_action_row = selection.get_action_row()
        new_row = self.new_row_after_clone(
            job, current_action_row, selection.is_subaction_selected(), cloned)
        self.callbacks['refresh_ui'](rows_to_state(self.project(), selection.job_index, new_row))

    def _shift_job(self, delta):
        selection = self.selection_state
        if not selection.is_job_selected():
            return
        job_index = selection.job_index
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            self.mark_as_modified(True, "Shift Job")
            jobs = self.project().jobs
            jobs.insert(new_index, jobs.pop(job_index))
            self.callbacks['refresh_ui'](rows_to_state(self.project(), new_index, -1))

    def _shift_action(self, delta):
        selection = self.selection_state
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return
        if selection.is_subaction_selected():
            if not selection.sub_actions:
                return
            new_index = selection.sub_action_index + delta
            if 0 <= new_index < len(selection.sub_actions):
                self.mark_as_modified(True, "Shift Sub-action")
                selection.sub_actions.insert(
                    new_index, selection.sub_actions.pop(selection.sub_action_index))
        else:
            if not selection.actions:
                return
            new_index = selection.action_index + delta
            if 0 <= new_index < len(selection.actions):
                self.mark_as_modified(True, "Shift Action")
                selection.actions.insert(new_index, selection.actions.pop(selection.action_index))
        current_action_row = selection.get_action_row()
        new_row = self.new_row_after_insert(current_action_row, selection, delta)
        self.callbacks['refresh_ui'](rows_to_state(self.project(), selection.job_index, new_row))

    def _shift_subaction(self, delta):
        self._shift_action(delta)

    def set_enabled(self, enabled):
        selection = self.selection_state
        if not selection.is_valid():
            return
        if selection.is_job_selected():
            if 0 <= selection.job_index < self.num_project_jobs():
                job = self.project().jobs[selection.job_index]
                if job.enabled() != enabled:
                    self._set_element_enabled(job, enabled, "Job")
                    self.callbacks['refresh_ui'](
                        rows_to_state(self.project(), selection.job_index, -1))
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = selection.sub_action if selection.is_subaction_selected() \
                else selection.action
            if element and element.enabled() != enabled:
                element_type = "Sub-action" if selection.is_subaction_selected() else "Action"
                self._set_element_enabled(element, enabled, element_type)
                self.callbacks['refresh_ui'](
                    rows_to_state(self.project(), selection.job_index, selection.get_action_row()))

    def _refresh_after_enable_all(self):
        selection = self.selection_state
        job_row = selection.job_index if selection.is_valid() else -1
        action_row = selection.get_action_row() if selection.is_valid() else -1
        self.callbacks['refresh_ui'](rows_to_state(self.project(), job_row, action_row))
