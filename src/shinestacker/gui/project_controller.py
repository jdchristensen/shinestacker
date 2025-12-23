# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0914, R0912, R0904, R0915, W0718
import os
import os.path
import traceback
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QMessageBox, QFileDialog
from .. core.core_utils import get_app_base_path
from .. core.exceptions import InvalidProjectError
from .project_holder import ProjectIOHandler
from .new_project import fill_new_project


CURRENT_PROJECT_FILE_VERSION = 1


class ProjectController(ProjectIOHandler, QObject):
    update_title_requested = Signal()
    refresh_ui_requested = Signal(int, int)
    activate_window_requested = Signal()
    add_recent_file_requested = Signal(str)
    set_enabled_file_open_close_actions_requested = Signal(bool)
    status_message_requested = Signal(str)

    def __init__(self, project_holder, project_editor, parent):
        QObject.__init__(self, parent)
        ProjectIOHandler.__init__(self, project_holder)
        self.parent = parent
        self.project_editor = project_editor

    def refresh_ui(self, job_row=-1, action_row=-1):
        self.refresh_ui_requested.emit(job_row, action_row)

    def job_list(self):
        return self.project_editor.job_list()

    def action_list(self):
        return self.project_editor.action_list()

    def current_job_index(self):
        return self.project_editor.current_job_index()

    def current_action_index(self):
        return self.project_editor.current_action_index()

    def set_current_job(self, index):
        return self.project_editor.set_current_job(index)

    def set_current_action(self, index):
        return self.project_editor.set_current_action(index)

    def job_list_count(self):
        return self.project_editor.job_list_count()

    def action_list_count(self):
        return self.project_editor.action_list_count()

    def job_list_item(self, index):
        return self.project_editor.job_list_item(index)

    def action_list_item(self, index):
        return self.project_editor.action_list_item(index)

    def job_list_has_focus(self):
        return self.project_editor.job_list_has_focus()

    def action_list_has_focus(self):
        return self.project_editor.action_list_has_focus()

    def clear_job_list(self):
        self.project_editor.clear_job_list()

    def clear_action_list(self):
        self.project_editor.clear_action_list()

    def num_selected_jobs(self):
        return self.project_editor.num_selected_jobs()

    def num_selected_actions(self):
        return self.project_editor.num_selected_actions()

    def get_current_action_at(self, job, action_index):
        return self.project_editor.get_current_action_at(job, action_index)

    def get_action_at(self, action_row):
        return self.project_editor.get_action_at(action_row)

    def get_current_action(self):
        return self.get_action_at(self.current_action_index())

    def action_config_dialog(self, action):
        return self.project_editor.action_config_dialog(action)

    def on_job_selected(self, index):
        return self.project_editor.on_job_selected(index)

    def update_title(self):
        self.update_title_requested.emit()

    def close_project(self):
        if self.check_unsaved_changes():
            ProjectIOHandler.reset_project(self)
            return True
        return False

    def new_project(self):
        if not self.check_unsaved_changes():
            return False
        os.chdir(get_app_base_path())
        ProjectIOHandler.reset_project(self)
        if fill_new_project(self.project(), self.parent):
            self.set_modified(True)
        return True

    def open_project(self, file_path=False):
        if not self.check_unsaved_changes():
            return False, ''
        if file_path is False:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent, "Open Project", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                abs_file_path = ProjectIOHandler.open_project(self, file_path)
                self.set_enabled_file_open_close_actions_requested.emit(True)
                self.add_recent_file_requested.emit(abs_file_path)
                self.refresh_ui(0, -1)
                return True, ''
            except InvalidProjectError as e:
                QMessageBox.critical(self.parent, "Error", str(e))
                return False, str(e)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                msg = f"Cannot open file {file_path}:\n{str(e)}"
                QMessageBox.critical(self.parent, "Error", msg)
                return False, msg
        return False, ''

    def save_project(self):
        path = self.current_file_path()
        if path:
            self.do_save(path)
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "Save Project As", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self.do_save(file_path)
            self.set_current_file_path(file_path)
            os.chdir(os.path.dirname(file_path))

    def do_save(self, file_path):
        ProjectIOHandler.do_save(self, file_path)
        self.add_recent_file_requested.emit(file_path)

    def check_unsaved_changes(self):
        if self.modified():
            reply = QMessageBox.question(
                self.parent, "Unsaved Changes",
                "The project has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_project()
                return True
            return reply == QMessageBox.Discard
        return True
