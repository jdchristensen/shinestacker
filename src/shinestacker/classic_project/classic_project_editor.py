# pylint: disable=C0114, C0115, C0116, R0903, R0904, R1702, R0917, R0913, R0902, E0611, E1131, E1121
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMessageBox, QDialog
from .. config.constants import constants
from .. gui.project_editor import ProjectEditor
from .list_container import ListContainer, ActionPosition


def new_row_after_delete(action_row, pos: ActionPosition):
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


def new_row_after_insert(action_row, pos: ActionPosition, delta):
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


def new_row_after_paste(action_row, pos: ActionPosition):
    return new_row_after_insert(action_row, pos, 0)


def new_row_after_clone(job, action_row, is_sub_action, cloned):
    return action_row + 1 if is_sub_action else \
        sum(1 + len(action.sub_actions)
            for action in job.sub_actions[:job.sub_actions.index(cloned)])


class ClassicProjectEditor(ProjectEditor, ListContainer):
    refresh_ui_signal = Signal(int, int)
    enable_delete_action_signal = Signal(bool)
    enable_sub_actions_requested = Signal(bool)

    def __init__(self, project_holder, parent=None):
        ProjectEditor.__init__(self, project_holder, parent)
        ListContainer.__init__(self, None, None)

    def get_current_job(self):
        return self.project_job(self.current_job_index())

    def get_current_action(self):
        return self.get_action_at(self.current_action_index())

    def has_selected_jobs(self):
        return self.num_selected_jobs() > 0

    def has_selected_actions(self):
        return self.num_selected_actions() > 0

    def has_selection(self):
        return self.has_selected_jobs() or self.has_selected_actions()

    def has_selected_jobs_and_actions(self):
        return self.has_selected_jobs() and self.has_selected_actions()

    def has_selected_sub_action(self):
        if self.has_selected_jobs_and_actions():
            job_index = min(self.current_job_index(), self.num_project_jobs() - 1)
            action_index = self.current_action_index()
            if job_index >= 0:
                job = self.project_job(job_index)
                current_action, is_sub_action = \
                    self.get_current_action_at(job, action_index)
                selected_sub_action = current_action is not None and \
                    not is_sub_action and current_action.type_name == constants.ACTION_COMBO
                return selected_sub_action
        return False

    def find_action_position(self, job_index, ui_index):
        if not 0 <= job_index < self.num_project_jobs():
            return (None, None, -1)
        actions = self.project_job(job_index).sub_actions
        counter = -1
        for action in actions:
            counter += 1
            if counter == ui_index:
                return (action, None, -1)
            for sub_action_index, sub_action in enumerate(action.sub_actions):
                counter += 1
                if counter == ui_index:
                    return (action, sub_action, sub_action_index)
        return (None, None, -1)

    def shift_job(self, delta):
        job_index = self.current_job_index()
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < self.num_project_jobs():
            jobs = self.project_jobs()
            self.mark_as_modified(True, "Shift Job")
            jobs.insert(new_index, jobs.pop(job_index))
            self.refresh_ui_signal.emit(new_index, -1)

    def shift_action(self, delta):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None:
            if not pos.is_sub_action:
                new_index = pos.action_index + delta
                if 0 <= new_index < len(pos.actions):
                    self.mark_as_modified(True, "Shift Action")
                    pos.actions.insert(new_index, pos.actions.pop(pos.action_index))
            else:
                new_index = pos.sub_action_index + delta
                if 0 <= new_index < len(pos.sub_actions):
                    self.mark_as_modified(True, "Shift Sub-action")
                    pos.sub_actions.insert(new_index, pos.sub_actions.pop(pos.sub_action_index))
            new_row = new_row_after_insert(action_row, pos, delta)
            self.refresh_ui_signal.emit(job_row, new_row)

    def move_element_up(self):
        if self.job_list_has_focus():
            self.shift_job(-1)
        elif self.action_list_has_focus():
            self.shift_action(-1)

    def move_element_down(self):
        if self.job_list_has_focus():
            self.shift_job(+1)
        elif self.action_list_has_focus():
            self.shift_action(+1)

    def clone_job(self):
        job_index = self.current_job_index()
        if 0 <= job_index < self.num_project_jobs():
            job_clone = self.project_job(job_index).clone(self.CLONE_POSTFIX)
            new_job_index = job_index + 1
            self.mark_as_modified(True, "Duplicate Job")
            self.project_jobs().insert(new_job_index, job_clone)
            self.set_current_job(new_job_index)
            self.set_current_action(new_job_index)
            self.refresh_ui_signal.emit(new_job_index, -1)

    def clone_action(self):
        job_row, action_row, pos = self.get_current_action()
        if not pos.actions:
            return
        self.mark_as_modified(True, "Duplicate Action")
        job = self.project_job(job_row)
        if pos.is_sub_action:
            cloned = pos.sub_action.clone(self.CLONE_POSTFIX)
            pos.sub_actions.insert(pos.sub_action_index + 1, cloned)
        else:
            cloned = pos.action.clone(self.CLONE_POSTFIX)
            job.sub_actions.insert(pos.action_index + 1, cloned)
        new_row = new_row_after_clone(job, action_row, pos.is_sub_action, cloned)
        self.refresh_ui_signal.emit(job_row, new_row)

    def clone_element(self):
        if self.job_list_has_focus():
            self.clone_job()
        elif self.action_list_has_focus():
            self.clone_action()

    def delete_job(self, confirm=True):
        current_index = self.current_job_index()
        if 0 <= current_index < self.num_project_jobs():
            if confirm:
                reply = QMessageBox.question(
                    self.parent(), "Confirm Delete",
                    "Are you sure you want to delete job "
                    f"'{self.project_job(current_index).params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                self.take_job(current_index)
                self.mark_as_modified(True, "Delete Job")
                current_job = self.project_jobs().pop(current_index)
                self.clear_action_list()
                self.refresh_ui_signal.emit(-1, -1)
                return current_job
        return None

    def delete_action(self, confirm=True):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None:
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
            if confirm:
                reply = QMessageBox.question(
                    self.parent(),
                    "Confirm Delete",
                    "Are you sure you want to delete action "
                    f"'{self.action_text(current_action, pos.is_sub_action, indent=False)}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                if pos.is_sub_action:
                    self.mark_as_modified(True, "Delete Action")
                    pos.action.pop_sub_action(pos.sub_action_index)
                else:
                    self.mark_as_modified(True, "Delete Sub-action")
                    self.project_job(job_row).pop_sub_action(pos.action_index)
                new_row = new_row_after_delete(action_row, pos)
                self.refresh_ui_signal.emit(job_row, new_row)
            return current_action
        return None

    def delete_element(self, confirm=True):
        if self.job_list_has_focus():
            element = self.delete_job(confirm)
        elif self.action_list_has_focus():
            element = self.delete_action(confirm)
        else:
            element = None
        return element

    def edit_action(self, action):
        dialog = self.action_config_dialog(action)
        if dialog.exec() == QDialog.Accepted:
            self.on_job_selected(self.current_job_index())

    def connect_signals(self):
        self._job_list.itemDoubleClicked.connect(self.on_job_edit)
        self._action_list.itemDoubleClicked.connect(self.on_action_edit)

    def on_job_edit(self, item):
        index = self.job_list().row(item)
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            dialog = self.action_config_dialog(job)
            if dialog.exec() == QDialog.Accepted:
                current_row = self.current_job_index()
                if current_row >= 0:
                    self.job_list_item(current_row).setText(job.params['name'])
                self.refresh_ui()

    def on_action_edit(self, item):
        job_index = self.current_job_index()
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            action_index = self.action_list().row(item)
            current_action, is_sub_action = self.get_current_action_at(job, action_index)
            if current_action:
                if not is_sub_action:
                    self.enable_sub_actions_requested.emit(
                        current_action.type_name == constants.ACTION_COMBO)
                dialog = self.action_config_dialog(current_action)
                if dialog.exec() == QDialog.Accepted:
                    self.on_job_selected(job_index)
                    self.refresh_ui_signal.emit(-1, -1)
                    self.set_current_job(job_index)
                    self.set_current_action(action_index)

    def copy_job(self):
        current_index = self.current_job_index()
        if 0 <= current_index < self.num_project_jobs():
            self.set_copy_buffer(self.project_job(current_index).clone())

    def copy_action(self):
        _job_row, _action_row, pos = self.get_current_action()
        if pos.actions is not None:
            self.set_copy_buffer(pos.sub_action.clone()
                                 if pos.is_sub_action else pos.action.clone())

    def copy_element(self):
        if self.job_list_has_focus():
            self.copy_job()
        elif self.action_list_has_focus():
            self.copy_action()

    def paste_job(self):
        if self.copy_buffer().type_name != constants.ACTION_JOB:
            return
        new_job_index = min(max(self.current_job_index(), 0), self.num_project_jobs() - 1)
        self.mark_as_modified(True, "Paste Job")
        self.project_jobs().insert(new_job_index, self.copy_buffer())
        self.set_current_job(new_job_index)
        self.set_current_action(new_job_index)
        self.refresh_ui_signal.emit(new_job_index, -1)

    def paste_action(self):
        job_row, action_row, pos = self.get_current_action()
        if pos is not None and pos.actions is not None:
            if not pos.is_sub_action:
                if self.copy_buffer().type_name not in constants.ACTION_TYPES:
                    return
                self.mark_as_modified(True, "Paste Action")
                pos.actions.insert(pos.action_index, self.copy_buffer())
            else:
                if pos.action.type_name != constants.ACTION_COMBO or \
                   self.copy_buffer().type_name not in constants.SUB_ACTION_TYPES:
                    return
                self.mark_as_modified(True, "Paste Sub-action")
                pos.sub_actions.insert(pos.sub_action_index, self.copy_buffer())
            new_row = new_row_after_paste(action_row, pos)
            self.refresh_ui_signal.emit(job_row, new_row)

    def paste_element(self):
        if self.has_copy_buffer():
            if self.job_list_has_focus():
                self.paste_job()
            elif self.action_list_has_focus():
                self.paste_action()

    def cut_element(self):
        self.set_copy_buffer(self.delete_element(False))

    def undo(self):
        job_row = self.current_job_index()
        action_row = self.current_action_index()
        if self.filled_undo():
            self.set_project(self.pop_undo())
            self.refresh_ui_signal.emit(-1, -1)
            len_jobs = self.num_project_jobs()
            if len_jobs > 0:
                job_row = min(job_row, len_jobs - 1)
                self.set_current_job(job_row)
                len_actions = self.action_list_count()
                if len_actions > 0:
                    action_row = min(action_row, len_actions)
                    self.set_current_action(action_row)

    def set_enabled(self, enabled):
        current_action = None
        if self.job_list_has_focus():
            job_row = self.current_job_index()
            if 0 <= job_row < self.num_project_jobs():
                current_action = self.project_job(job_row)
            action_row = -1
        elif self.action_list_has_focus():
            job_row, action_row, pos = self.get_current_action()
            current_action = pos.sub_action if pos.is_sub_action else pos.action
        else:
            action_row = -1
        if current_action:
            if current_action.enabled() != enabled:
                if enabled:
                    self.mark_as_modified(True, "Enable")
                else:
                    self.mark_as_modified(True, "Disable")
                current_action.set_enabled(enabled)
                self.refresh_ui_signal.emit(job_row, action_row)

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)

    def set_enabled_all(self, enable=True):
        self.mark_as_modified(True, "Enable All")
        job_row = self.current_job_index()
        action_row = self.current_action_index()
        for j in self.project_jobs():
            j.set_enabled_all(enable)
        self.refresh_ui_signal.emit(job_row, action_row)

    def enable_all(self):
        self.set_enabled_all(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def get_current_action_at(self, job, action_index):
        action_counter = -1
        current_action = None
        is_sub_action = False
        for action in job.sub_actions:
            action_counter += 1
            if action_counter == action_index:
                current_action = action
                break
            if len(action.sub_actions) > 0:
                for sub_action in action.sub_actions:
                    action_counter += 1
                    if action_counter == action_index:
                        current_action = sub_action
                        is_sub_action = True
                        break
                if current_action:
                    break

        return current_action, is_sub_action
