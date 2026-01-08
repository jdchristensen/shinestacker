# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101, R0911, R0801
from .. config.constants import constants
from .. common_project.element_action_manager import ElementActionManager
from .classic_selection_state import rows_to_state


class ClassicElementActionManager(ElementActionManager):
    def __init__(self, project_holder, selection_state, parent=None):
        super().__init__(project_holder, parent)
        self.selection_state = selection_state

    @staticmethod
    def new_row_after_delete(action_row, pos):
        if pos.is_sub_action:
            new_row = action_row if pos.subaction_index < len(pos.sub_actions) else action_row - 1
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
            new_index = pos.subaction_index + delta
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
        deleted_element = None
        new_selection = False
        if selection.is_job_selected():
            if not 0 <= selection.job_index < self.num_project_jobs():
                return None, False
            job = self.project().jobs[selection.job_index]
            if confirm:
                if not self.confirm_delete_message('job', job.params.get('name', '')):
                    return None, False
            self.mark_as_modified(True, "Delete Job", "delete", (selection.job_index, -1, -1))
            deleted_element = self.project().jobs.pop(selection.job_index)
            new_selection = rows_to_state(self.project(), -1, -1)
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = selection.sub_action if selection.is_subaction_selected() \
                else selection.action
            container = selection.sub_actions if selection.is_subaction_selected() \
                else selection.actions
            index = selection.subaction_index if selection.is_subaction_selected() \
                else selection.action_index
            if not element or not container or index < 0 or index >= len(container):
                return None, False
            element_type = "sub-action" if selection.is_subaction_selected() else "action"
            if confirm:
                if not self.confirm_delete_message(element_type, element.params.get('name', '')):
                    return None, False
            action_type_str = "delete"
            if selection.is_subaction_selected():
                position = (selection.job_index, selection.action_index, selection.subaction_index)
            else:
                position = (selection.job_index, selection.action_index, -1)
            self.mark_as_modified(True, f"Delete {element_type}", action_type_str, position)
            deleted_element = container.pop(index)
            current_action_row = selection.get_action_row()
            new_row = self.new_row_after_delete(current_action_row, selection)
            new_selection = rows_to_state(self.project(), selection.job_index, new_row)
        return deleted_element, new_selection

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
            return False
        copy_buffer = self.copy_buffer()
        selection = self.selection_state
        if selection.is_job_selected():
            return self._paste_job(copy_buffer, selection)
        if selection.is_action_selected() or selection.is_subaction_selected():
            return self._paste_action(copy_buffer, selection)
        return False

    def _paste_job(self, copy_buffer, selection):
        if copy_buffer.type_name != constants.ACTION_JOB:
            if self.num_project_jobs() == 0:
                return False
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return False
            new_action_index = len(self.project().jobs[selection.job_index].sub_actions)
            success, _element_type, index = self.paste_job_logic(
                copy_buffer, selection.job_index, False,
                "Paste Action", "paste", (selection.job_index, new_action_index, -1))
            if success:
                self.selection_state.set_action(selection.job_index, index)
            return success
        if self.num_project_jobs() == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(selection.job_index + 1, 0), self.num_project_jobs())
        success, _element_type, index = self.paste_job_logic(
            copy_buffer, selection.job_index, False,
            "Paste Job", "paste", (new_job_index, -1, -1))
        if success:
            self.selection_state.set_job(index)
        return success

    def _paste_action(self, copy_buffer, selection):
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            target_action = None
            insertion_index = 0
            if selection.is_subaction_selected():
                if selection.action and selection.action.type_name == constants.ACTION_COMBO:
                    target_action = selection.action
                    insertion_index = len(selection.sub_actions)
                    self.selection_state.set_subaction(
                        selection.job_index, selection.action_index, insertion_index)
            else:
                if selection.action and selection.action.type_name == constants.ACTION_COMBO:
                    target_action = selection.action
                    insertion_index = len(selection.action.sub_actions)
                    self.selection_state.set_subaction(
                        selection.job_index, selection.action_index, insertion_index)
            if target_action is not None:
                self.mark_as_modified(
                    True, "Paste Sub-action", "paste",
                    (selection.job_index, selection.action_index, insertion_index))
                target_action.sub_actions.insert(insertion_index, copy_buffer)
                return True
        if copy_buffer.type_name in constants.ACTION_TYPES:
            if not selection.is_subaction_selected():
                if not selection.actions:
                    return False
                new_action_index = 0 if len(selection.actions) == 0 else selection.action_index + 1
                self.mark_as_modified(
                    True, "Paste Action", "paste", (selection.job_index, new_action_index, -1))
                selection.actions.insert(new_action_index, copy_buffer)
                self.selection_state.set_action(selection.job_index, new_action_index)
                return True
        return False

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
        return False, None

    def clone_job(self):
        selection = self.selection_state
        if not selection.is_job_selected():
            return False, None
        if 0 <= selection.job_index < self.num_project_jobs():
            self.mark_as_modified(True, "Duplicate Job", "clone", (selection.job_index, -1, -1))
            job = self.project().jobs[selection.job_index]
            job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
            new_job_index = selection.job_index + 1
            self.project().jobs.insert(new_job_index, job_clone)
            new_state = rows_to_state(self.project(), new_job_index, -1)
            return True, new_state
        return False, None

    def clone_action(self):
        selection = self.selection_state
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return False, None
        if not selection.actions:
            return False, None
        self.mark_as_modified(
            True, "Duplicate Action", "clone", (selection.job_index, selection.action_index, -1))
        job = self.project().jobs[selection.job_index]
        if selection.is_subaction_selected():
            cloned = selection.sub_action.clone(name_postfix=self.CLONE_POSTFIX)
            selection.sub_actions.insert(selection.subaction_index + 1, cloned)
        else:
            cloned = selection.action.clone(name_postfix=self.CLONE_POSTFIX)
            job.sub_actions.insert(selection.action_index + 1, cloned)
        current_action_row = selection.get_action_row()
        new_row = self.new_row_after_clone(
            job, current_action_row, selection.is_subaction_selected(), cloned)
        new_state = rows_to_state(self.project(), selection.job_index, new_row)
        return True, new_state

    def _shift_job(self, delta):
        selection = self.selection_state
        if not selection.is_job_selected():
            return False
        job_index = selection.job_index
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project().jobs
            jobs.insert(new_index, jobs.pop(job_index))
            new_selection = rows_to_state(self.project(), new_index, -1)
            return new_selection
        return False

    def _shift_action(self, delta):
        selection = self.selection_state
        if not (selection.is_action_selected() or selection.is_subaction_selected()):
            return False
        if selection.is_subaction_selected():
            if not selection.sub_actions:
                return False
            new_index = selection.subaction_index + delta
            if 0 <= new_index < len(selection.sub_actions):
                selection.sub_actions.insert(
                    new_index, selection.sub_actions.pop(selection.subaction_index))
            else:
                return False
        else:
            if not selection.actions:
                return False
            new_index = selection.action_index + delta
            if 0 <= new_index < len(selection.actions):
                selection.actions.insert(new_index, selection.actions.pop(selection.action_index))
            else:
                return False
        current_action_row = selection.get_action_row()
        new_row = self.new_row_after_insert(current_action_row, selection, delta)
        new_selection = rows_to_state(self.project(), selection.job_index, new_row)
        return new_selection

    def _shift_subaction(self, delta):
        return self._shift_action(delta)

    def set_enabled(self, enabled, selection=None):
        if selection is None:
            selection = self.selection_state
        if not selection.is_valid():
            return False
        new_selection = False
        if selection.is_job_selected():
            if 0 <= selection.job_index < self.num_project_jobs():
                job = self.project().jobs[selection.job_index]
                if job.enabled() != enabled:
                    action_text = "Enable" if enabled else "Disable"
                    self.mark_as_modified(
                        True, f"{action_text} Job", "edit", (selection.job_index, -1, -1))
                    self._set_element_enabled(job, enabled, "Job")
                    new_selection = rows_to_state(self.project(), selection.job_index, -1)
        elif selection.is_action_selected() or selection.is_subaction_selected():
            element = selection.sub_action if selection.is_subaction_selected() \
                else selection.action
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
                new_selection = rows_to_state(
                    self.project(), selection.job_index, selection.get_action_row())
        return new_selection
