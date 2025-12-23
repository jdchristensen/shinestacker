# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0915, R0904, R0914
# pylint: disable=R0912, E1101, W0201, E1121, R0913, R0917, W0718
import os
import traceback
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QAction, QPalette
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QToolBar, QMainWindow, QApplication, QStackedWidget, QMessageBox,
    QFileDialog)
from .. config.constants import constants
from .. config.app_config import AppConfig
from .. core.exceptions import InvalidProjectError
from .. gui.project_model import Project
from .. gui.project_handler import ProjectHolder, ProjectIOHandler
from .. gui.sys_mon import StatusBarSystemMonitor
from .. gui.new_project import fill_new_project
from .. classic_project.classic_project_view import ClassicProjectView
from .. classic_project.classic_project_editor import ClassicProjectEditor
from .. modern_project.modern_project_view import ModernProjectView
from .. core.core_utils import get_app_base_path
from .menu_manager import MenuManager


class MainWindow(ProjectIOHandler, QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        project_holder = ProjectHolder()
        ProjectIOHandler.__init__(self, project_holder)
        self.setObjectName("mainWindow")
        self.classic_project_editor = ClassicProjectEditor(self.project_holder, self)
        dark_theme = self.is_dark_theme()
        self.classic_view = ClassicProjectView(self.project_holder, dark_theme, self)
        self.classic_project_editor.set_lists(*self.classic_view.get_lists())
        self.modern_view = ModernProjectView(dark_theme, self)
        self.views = {'classic': self.classic_view, 'modern': self.modern_view}
        self.editors = {'classic': self.classic_project_editor}
        actions = {
            "&New...": self.new_project,
            "&Open...": self.open_project,
            "&Close": self.close_project,
            "&Save": self.save_project,
            "Save &As...": self.save_project_as,
            "&Undo": self.undo,
            "&Cut": self.classic_project_editor.cut_element,
            "Cop&y": self.classic_project_editor.copy_element,
            "&Paste": self.classic_project_editor.paste_element,
            "Duplicate": self.classic_project_editor.clone_element,
            "Delete": self.delete_element,
            "Move &Up": self.classic_project_editor.move_element_up,
            "Move &Down": self.classic_project_editor.move_element_down,
            "E&nable": self.classic_project_editor.enable,
            "Di&sable": self.classic_project_editor.disable,
            "Enable All": self.classic_project_editor.enable_all,
            "Disable All": self.classic_project_editor.disable_all,
            "Expert Options": self.toggle_expert_options,
            "Add Job": self.classic_project_editor.add_job,
            "Run Job": lambda: self.view_stack.currentWidget().run_job(),
            "Run All Jobs": lambda: self.view_stack.currentWidget().run_all_jobs(),
            "Stop": lambda: self.view_stack.currentWidget().stop(),
            "Classic View": self.set_classic_view,
            "Modern View": self.set_modern_view
        }
        self.menu_manager = MenuManager(
            self.menuBar(), actions, self.classic_project_editor, dark_theme, self)
        for _k, v in self.views.items():
            v.set_menu_manager(self.menu_manager)
        self.script_dir = os.path.dirname(__file__)
        self.retouch_callback = None
        self.classic_view.set_style_sheet(dark_theme)
        self.menu_manager.add_menus()
        toolbar = QToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.menu_manager.fill_toolbar(toolbar)
        self.resize(1200, 800)
        self.move(QGuiApplication.primaryScreen().geometry().center() -
                  self.rect().center())
        self.set_project(Project())

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.view_stack = QStackedWidget()
        for _k, v in self.views.items():
            self.view_stack.addWidget(v)
        self.view_stack.setCurrentIndex(0)
        layout.addWidget(self.view_stack)

        self.classic_project_editor.connect_signals()

        self.central_widget.setLayout(layout)

        self.update_title()
        self.statusBar().addPermanentWidget(StatusBarSystemMonitor(self))
        QApplication.instance().paletteChanged.connect(self.on_theme_changed)
        self.classic_project_editor.mark_as_modified_signal.connect(self.mark_as_modified)
        self.classic_project_editor.select_signal.connect(
            self.update_delete_action_state)
        self.classic_project_editor.refresh_ui_signal.connect(self.classic_view.refresh_ui)
        self.classic_view.refresh_ui_signal.connect(self.refresh_ui)
        self.modern_view.refresh_ui_signal.connect(self.refresh_ui)
        self.classic_project_editor.enable_delete_action_signal.connect(
            self.menu_manager.delete_element_action.setEnabled)
        self.undo_manager().set_enabled_undo_action_requested.connect(
            self.menu_manager.set_enabled_undo_action)
        self.classic_project_editor.enable_sub_actions_requested.connect(
            self.menu_manager.set_enabled_sub_actions_gui)
        self.menu_manager.open_file_requested.connect(self.open_project)
        self.set_enabled_file_open_close_actions(False)
        self.show_status_message("Shine Stacker ready.", 4000)

    def show_status_message(self, message, timeout=4000):
        self.statusBar().showMessage(message, timeout)

    def mark_as_modified(self, modified=True, description=''):
        ProjectIOHandler.mark_as_modified(self, modified, description)
        self.menu_manager.save_actions_set_enabled(modified)
        self.update_title()

    def clear_action_list(self):
        self.classic_project_editor.clear_action_list()

    def get_current_action_at(self, job, action_index):
        return self.classic_project_editor.get_current_action_at(job, action_index)

    def action_config_dialog(self, action):
        return self.classic_project_editor.action_config_dialog(action)

    def set_retouch_callback(self, callback):
        self.retouch_callback = callback

    def update_title(self):
        title = constants.APP_TITLE
        file_name = self.current_file_name()
        if file_name:
            title += f" - {file_name}"
            if self.modified():
                title += " *"
        self.window().setWindowTitle(title)

    def refresh_ui(self):
        self.update_title()
        if self.num_project_jobs() == 0:
            self.menu_manager.add_action_entry_action.setEnabled(False)
            self.menu_manager.action_selector.setEnabled(False)
            self.menu_manager.run_job_action.setEnabled(False)
        else:
            self.menu_manager.add_action_entry_action.setEnabled(True)
            self.menu_manager.action_selector.setEnabled(True)
            self.menu_manager.delete_element_action.setEnabled(True)
            self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.set_enabled_run_all_jobs(self.num_project_jobs() > 1)

    def set_classic_view(self):
        self.view_stack.setCurrentIndex(0)

    def set_modern_view(self):
        self.view_stack.setCurrentIndex(1)

    def quit(self):
        if self.check_unsaved_changes():
            q = True
            for _k, v in self.views.items():
                q = q and v.quit()
            return q
        return False

    def refresh_ui_and_select_first_job(self):
        for _k, v in self.views.items():
            v.refresh_ui()
            v.select_first_job()

    def check_unsaved_changes(self):
        if self.modified():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "The project has unsaved changes. Do you want to continue?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if reply == QMessageBox.Save:
                self.save_project()
                return True
            return reply == QMessageBox.Discard
        return True

    def open_project_base(self, file_path):
        if not self.check_unsaved_changes():
            return False, '', ''
        if file_path is False:
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent, "Open Project", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            try:
                ProjectIOHandler.open_project(self, file_path)
                return True, file_path, ''
            except InvalidProjectError as e:
                QMessageBox.critical(self.parent, "Error", str(e))
                return False, file_path, str(e)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                msg = f"Cannot open file {file_path}:\n{str(e)}"
                QMessageBox.critical(self.parent, "Error", msg)
                return False, file_path, msg
        return False, '', ''

    def open_project(self, file_path=False):
        opened, file_path, msg = self.open_project_base(file_path)
        if opened:
            self.refresh_ui_and_select_first_job()
            self.menu_manager.save_actions_set_enabled(True)
            self.show_status_message(f"Project file {os.path.basename(file_path)} loaded.")
            self.menu_manager.add_recent_file(os.path.abspath(file_path))
            self.set_enabled_file_open_close_actions(True)
            if self.num_project_jobs() > 0:
                self.classic_project_editor.set_current_job(0)
                self.activateWindow()
            for job in self.project_jobs():
                if 'working_path' in job.params.keys():
                    working_path = job.params['working_path']
                    if not os.path.isdir(working_path):
                        msg = "Working path not found"
                        QMessageBox.warning(
                            self, msg,
                            f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                        self.classic_project_editor.edit_action(job)
                for action in job.sub_actions:
                    if 'working_path' in job.params.keys():
                        working_path = job.params['working_path']
                        if working_path != '' and not os.path.isdir(working_path):
                            msg = "Working path not found"
                            QMessageBox.warning(
                                self, msg,
                                f'''The working path specified in the project file for the job:
                                "{job.params['name']}"
                                was not found.\n
                                Please, select a valid working path.''')
                            self.classic_project_editor.edit_action(action)
                self.refresh_ui_and_select_first_job()
        elif msg != '':
            self.show_status_message(msg)

    def new_project(self):
        if self.check_unsaved_changes():
            os.chdir(get_app_base_path())
            self.reset_project()
            self.update_title()
            if fill_new_project(self.project(), self):
                self.set_modified(True)
                self.classic_project_editor.clear_job_list()
                self.classic_project_editor.clear_action_list()
            self.refresh_ui_and_select_first_job()
            self.menu_manager.save_actions_set_enabled(False)
            self.set_enabled_file_open_close_actions(True)
            self.show_status_message("New project created.")

    def close_project(self):
        if self.check_unsaved_changes():
            self.reset_project()
            self.update_title()
            self.classic_project_editor.clear_job_list()
            self.classic_project_editor.clear_action_list()
            self.set_enabled_file_open_close_actions(False)
            self.show_status_message("Project closed.")

    def do_save(self, file_path):
        try:
            ProjectIOHandler.do_save(self, file_path)
            self.update_title()
            self.show_status_message(f"Project file {os.path.basename(file_path)} saved.")
            self.menu_manager.add_recent_file(file_path)
        except Exception as e:
            msg = f"Cannot save file:\n{str(e)}"
            self.show_status_message(msg)
            QMessageBox.critical(self, "Error", msg)

    def save_project(self):
        path = self.current_file_path()
        if path:
            self.do_save(path)
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "Project Files (*.fsp);;All Files (*)")
        if file_path:
            if not file_path.endswith('.fsp'):
                file_path += '.fsp'
            self.do_save(file_path)
            self.set_current_file_path(file_path)
            os.chdir(os.path.dirname(file_path))

    def handle_config(self):
        self.menu_manager.expert_options_action.setChecked(
            AppConfig.get('expert_options'))

    def toggle_expert_options(self):
        AppConfig.set('expert_options', self.menu_manager.expert_options_action.isChecked())

    def before_thread_begins(self):
        self.menu_manager.run_job_action.setEnabled(False)
        self.menu_manager.run_all_jobs_action.setEnabled(False)

    def undo(self):
        # ProjectIOHandler.undo(self)
        self.classic_project_editor.undo()

    def delete_element(self):
        self.classic_project_editor.delete_element()
        if self.num_project_jobs() > 0:
            self.menu_manager.delete_element_action.setEnabled(True)

    def update_delete_action_state(self):
        self.menu_manager.delete_element_action.setEnabled(
            self.classic_project_editor.has_selection())
        self.menu_manager.set_enabled_sub_actions_gui(
            self.classic_project_editor.has_selected_sub_action())

    def set_enabled_file_open_close_actions(self, enabled):
        for action in self.findChildren(QAction):
            if action.property("requires_file"):
                action.setEnabled(enabled)
        self.menu_manager.stop_action.setEnabled(False)

    def is_dark_theme(self):
        palette = QApplication.palette()
        window_color = palette.color(QPalette.Window)
        brightness = (window_color.red() * 0.299 +
                      window_color.green() * 0.587 +
                      window_color.blue() * 0.114)
        return brightness < 128

    def on_theme_changed(self):
        dark_theme = self.is_dark_theme()
        for _k, v in self.views.items():
            v.change_theme(dark_theme)
