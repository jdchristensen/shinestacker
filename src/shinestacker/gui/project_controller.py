# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0914, R0912, R0904, R0915, W0718
import os
import os.path
import traceback
import json
import jsonpickle
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog
from .. config.constants import constants
from .. core.core_utils import get_app_base_path
from .project_holder import ProjectHandler
from .new_project import fill_new_project
from .project_model import Project


CURRENT_PROJECT_FILE_VERSION = 1


class ProjectController(ProjectHandler, QObject):
    update_title_requested = Signal()
    refresh_ui_requested = Signal(int, int)
    activate_window_requested = Signal()
    enable_save_actions_requested = Signal(bool)
    enable_sub_actions_requested = Signal(bool)
    add_recent_file_requested = Signal(str)
    set_enabled_file_open_close_actions_requested = Signal(bool)
    status_message_requested = Signal(str)

    def __init__(self, project_holder, project_editor, parent):
        QObject.__init__(self, parent)
        ProjectHandler.__init__(self, project_holder)
        self.parent = parent
        self.project_editor = project_editor

    def refresh_ui(self, job_row=-1, action_row=-1):
        self.refresh_ui_requested.emit(job_row, action_row)

    def save_actions_set_enabled(self, enabled):
        self.enable_save_actions_requested.emit(enabled)

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

    def connect_signals(self):
        self.job_list().itemDoubleClicked.connect(self.on_job_edit)
        self.action_list().itemDoubleClicked.connect(self.on_action_edit)

    def close_project(self):
        if self.check_unsaved_changes():
            ProjectHandler.close_project(self)
            self.set_current_file_path('')
            self.update_title()
            self.clear_job_list()
            self.clear_action_list()
            self.set_enabled_file_open_close_actions_requested.emit(False)
            self.status_message_requested.emit("Project closed.")

    def new_project(self):
        if not self.check_unsaved_changes():
            return
        os.chdir(get_app_base_path())
        self.set_current_file_path('')
        self.update_title()
        self.clear_job_list()
        self.clear_action_list()
        ProjectHandler.reset_project(self)
        self.save_actions_set_enabled(False)
        if fill_new_project(self.project(), self.parent):
            self.save_actions_set_enabled(True)
            self.set_modified(True)
        self.refresh_ui(0, -1)
        self.status_message_requested.emit("New project created.")
        self.set_enabled_file_open_close_actions_requested.emit(True)

    def open_project(self, file_path=False):
        if not self.check_unsaved_changes():
            return
        if file_path is False:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent, "Open Project", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                abs_file_path = os.path.abspath(file_path)
                with open(abs_file_path, 'r', encoding="utf-8") as file:
                    json_obj = json.load(file)
                project = Project.from_dict(json_obj['project'], json_obj['version'])
                if project is None:
                    msg = f"Project from file {file_path} produced a null project."
                    self.status_message_requested.emit(msg)
                    raise RuntimeError(msg)
                self.set_current_file_path(file_path)
                self.set_enabled_file_open_close_actions_requested.emit(True)
                self.set_project(project)
                self.mark_as_modified(False)
                self.add_recent_file_requested.emit(abs_file_path)
                self.project_editor.reset_undo()
                self.refresh_ui(0, -1)
                if self.job_list_count() > 0:
                    self.set_current_job(0)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                msg = f"Cannot open file {file_path}:\n{str(e)}"
                self.status_message_requested.emit(msg)
                QMessageBox.critical(
                    self.parent, "Error", msg)
                return
            if self.num_project_jobs() > 0:
                self.set_current_job(0)
                self.activate_window_requested.emit()
                self.save_actions_set_enabled(True)
                self.status_message_requested.emit(
                    f"Project file {os.path.basename(file_path)} loaded.")
            for job in self.project_jobs():
                if 'working_path' in job.params.keys():
                    working_path = job.params['working_path']
                    if not os.path.isdir(working_path):
                        msg = "Working path not found"
                        QMessageBox.warning(
                            self.parent, msg,
                            f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                        self.edit_action(job)
                for action in job.sub_actions:
                    if 'working_path' in job.params.keys():
                        working_path = job.params['working_path']
                        if working_path != '' and not os.path.isdir(working_path):
                            msg = "Working path not found"
                            QMessageBox.warning(
                                self.parent, msg,
                                f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                            self.edit_action(action)

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
        try:
            json_obj = jsonpickle.encode({
                'project': self.project().to_dict(),
                'version': CURRENT_PROJECT_FILE_VERSION
            })
            with open(file_path, 'w', encoding="utf-8") as f:
                f.write(json_obj)
            self.mark_as_modified(False)
            self.update_title_requested.emit()
            self.add_recent_file_requested.emit(file_path)
            self.status_message_requested.emit(
                f"Project file {os.path.basename(file_path)} saved.")
        except Exception as e:
            msg = f"Cannot save file:\n{str(e)}"
            self.status_message_requested.emit(msg)
            QMessageBox.critical(self.parent, "Error", msg)

    def check_unsaved_changes(self) -> bool:
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
                    self.refresh_ui()
                    self.set_current_job(job_index)
                    self.set_current_action(action_index)

    def edit_current_action(self):
        current_action = None
        job_row = self.current_job_index()
        if 0 <= job_row < self.num_project_jobs():
            job = self.project_job(job_row)
            if self.job_list_has_focus():
                current_action = job
            elif self.action_list_has_focus():
                job_row, _action_row, pos = self.get_current_action()
                if pos.actions is not None:
                    current_action = pos.action if not pos.is_sub_action else pos.sub_action
        if current_action is not None:
            self.edit_action(current_action)

    def edit_action(self, action):
        dialog = self.action_config_dialog(action)
        if dialog.exec() == QDialog.Accepted:
            self.on_job_selected(self.current_job_index())
