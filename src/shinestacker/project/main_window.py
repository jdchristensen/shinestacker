# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0915, R0904, R0914
# pylint: disable=R0912, E1101, W0201, E1121, R0913, R0917
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QAction, QPalette
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QToolBar, QMainWindow, QApplication, QStackedWidget)
from .. config.constants import constants
from .. config.app_config import AppConfig
from .. gui.colors import ColorPalette
from .. gui.project_model import Project
from .. gui.project_controller import ProjectController
from .. gui.sys_mon import StatusBarSystemMonitor
from .. gui.project_editor import ProjectEditor
from .. classic_project.classic_project_view import ClassicProjectView
from .. modern_project.modern_project_view import ModernProjectView
from .menu_manager import MenuManager


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setObjectName("mainWindow")
        self.project_editor = ProjectEditor(self)
        self.project_controller = ProjectController(self.project_editor, self)
        self.project_controller.status_message_requested.connect(
            lambda msg: self.show_status_message(msg, 4000))
        dark_theme = self.is_dark_theme()
        self.classic_view = ClassicProjectView(
            self.project_editor, self.project_controller, dark_theme, self)
        self.modern_view = ModernProjectView(dark_theme, self)
        actions = {
            "&New...": self.project_controller.new_project,
            "&Open...": self.project_controller.open_project,
            "&Close": self.project_controller.close_project,
            "&Save": self.project_controller.save_project,
            "Save &As...": self.project_controller.save_project_as,
            "&Undo": self.project_editor.undo,
            "&Cut": self.project_editor.cut_element,
            "Cop&y": self.project_editor.copy_element,
            "&Paste": self.project_editor.paste_element,
            "Duplicate": self.project_editor.clone_element,
            "Delete": self.delete_element,
            "Move &Up": self.project_editor.move_element_up,
            "Move &Down": self.project_editor.move_element_down,
            "E&nable": self.project_editor.enable,
            "Di&sable": self.project_editor.disable,
            "Enable All": self.project_editor.enable_all,
            "Disable All": self.project_editor.disable_all,
            "Expert Options": self.toggle_expert_options,
            "Add Job": self.project_editor.add_job,
            "Run Job": lambda: self.view_stack.currentWidget().run_job(),
            "Run All Jobs": lambda: self.view_stack.currentWidget().run_all_jobs(),
            "Stop": lambda: self.view_stack.currentWidget().stop(),
            "Classic View": self.set_classic_view,
            "Modern View": self.set_modern_view
        }
        self.menu_manager = MenuManager(
            self.menuBar(), actions, self.project_editor, dark_theme, self)
        self.classic_view.set_menu_manager(self.menu_manager)
        self.modern_view.set_menu_manager(self.menu_manager)
        self.script_dir = os.path.dirname(__file__)
        self.retouch_callback = None
        self.list_style_sheet_light = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.LIGHT_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #F0F0F0;
            }}
        """
        self.list_style_sheet_dark = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.DARK_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #303030;
            }}
        """
        list_style_sheet = self.list_style_sheet_dark \
            if dark_theme else self.list_style_sheet_light
        self.job_list().setStyleSheet(list_style_sheet)
        self.action_list().setStyleSheet(list_style_sheet)
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
        self.view_stack.addWidget(self.classic_view)
        self.view_stack.addWidget(self.modern_view)
        self.view_stack.setCurrentIndex(0)
        layout.addWidget(self.view_stack)

        self.job_list().itemDoubleClicked.connect(self.on_job_edit)
        self.action_list().itemDoubleClicked.connect(self.on_action_edit)

        self.central_widget.setLayout(layout)

        self.update_title()
        self.statusBar().addPermanentWidget(StatusBarSystemMonitor(self))
        QApplication.instance().paletteChanged.connect(self.on_theme_changed)

        def handle_modified(modified):
            self.save_actions_set_enabled(modified)
            self.update_title()

        self.project_editor.modified_signal.connect(handle_modified)
        self.project_editor.select_signal.connect(
            self.update_delete_action_state)
        self.project_editor.refresh_ui_signal.connect(
            self.refresh_ui)
        self.project_editor.enable_delete_action_signal.connect(
            self.menu_manager.delete_element_action.setEnabled)
        self.project_editor.undo_manager.set_enabled_undo_action_requested.connect(
            self.menu_manager.set_enabled_undo_action)
        self.project_controller.update_title_requested.connect(
            self.update_title)
        self.project_controller.refresh_ui_requested.connect(
            self.refresh_ui)
        self.project_controller.activate_window_requested.connect(
            self.activateWindow)
        self.project_controller.enable_save_actions_requested.connect(
            self.menu_manager.save_actions_set_enabled)
        self.project_controller.enable_sub_actions_requested.connect(
            self.menu_manager.set_enabled_sub_actions_gui)
        self.project_controller.add_recent_file_requested.connect(
            self.menu_manager.add_recent_file)
        self.project_controller.set_enabled_file_open_close_actions_requested.connect(
            self.set_enabled_file_open_close_actions)
        self.menu_manager.open_file_requested.connect(
            self.project_controller.open_project)
        self.set_enabled_file_open_close_actions(False)
        self.style_light = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.DARK_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.DARK_RED.hex()}; }}
        """
        self.style_dark = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.LIGHT_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.LIGHT_RED.hex()}; }}
        """
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        self.show_status_message("Shine Stacker ready.", 4000)

    def show_status_message(self, message, timeout=0):
        self.statusBar().showMessage(message, timeout)

    def modified(self):
        return self.project_editor.modified()

    def mark_as_modified(self, modified=True, description=''):
        self.project_editor.mark_as_modified(modified, description)

    def set_project(self, project):
        self.project_editor.set_project(project)

    def project(self):
        return self.project_editor.project()

    def project_jobs(self):
        return self.project_editor.project_jobs()

    def project_job(self, i):
        return self.project_editor.project_job(i)

    def add_job_to_project(self, job):
        self.project_editor.add_job_to_project(job)

    def num_project_jobs(self):
        return self.project_editor.num_project_jobs()

    def current_file_path(self):
        return self.project_editor.current_file_path()

    def current_file_directory(self):
        return self.project_editor.current_file_directory()

    def current_file_name(self):
        return self.project_editor.current_file_name()

    def set_current_file_path(self, path):
        self.project_editor.set_current_file_path(path)

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

    def action_config_dialog(self, action):
        return self.project_editor.action_config_dialog(action)

    def on_job_selected(self, index):
        return self.project_editor.on_job_selected(index)

    def get_action_at(self, action_row):
        return self.project_editor.get_action_at(action_row)

    def on_job_edit(self, item):
        self.project_controller.on_job_edit(item)

    def on_action_edit(self, item):
        self.project_controller.on_action_edit(item)

    def edit_current_action(self):
        self.project_controller.edit_current_action()

    def edit_action(self, action):
        self.project_controller.edit_action(action)

    def set_retouch_callback(self, callback):
        self.retouch_callback = callback

    def save_actions_set_enabled(self, enabled):
        self.menu_manager.save_actions_set_enabled(enabled)

    def update_title(self):
        title = constants.APP_TITLE
        file_name = self.current_file_name()
        if file_name:
            title += f" - {file_name}"
            if self.modified():
                title += " *"
        self.window().setWindowTitle(title)

    def refresh_ui(self, job_row=-1, action_row=-1):
        self.clear_job_list()
        for job in self.project_jobs():
            self.project_editor.add_list_item(self.job_list(), job, False)
        if self.project_jobs():
            self.set_current_job(0)
        if job_row >= 0:
            self.set_current_job(job_row)
        if action_row >= 0:
            self.set_current_action(action_row)
        if self.job_list_count() == 0:
            self.menu_manager.add_action_entry_action.setEnabled(False)
            self.menu_manager.action_selector.setEnabled(False)
            self.menu_manager.run_job_action.setEnabled(False)
        else:
            self.menu_manager.add_action_entry_action.setEnabled(True)
            self.menu_manager.action_selector.setEnabled(True)
            self.menu_manager.delete_element_action.setEnabled(True)
            self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.set_enabled_run_all_jobs(self.job_list_count() > 1)

    def set_classic_view(self):
        self.view_stack.setCurrentIndex(0)

    def set_modern_view(self):
        self.view_stack.setCurrentIndex(1)

    def quit(self):
        if self.project_controller.check_unsaved_changes():
            q_classic = self.classic_view.quit()
            q_modern = self.modern_view.quit()
            return q_classic and q_modern
        return False

    def handle_config(self):
        self.menu_manager.expert_options_action.setChecked(
            AppConfig.get('expert_options'))

    def toggle_expert_options(self):
        AppConfig.set('expert_options', self.menu_manager.expert_options_action.isChecked())

    def before_thread_begins(self):
        self.menu_manager.run_job_action.setEnabled(False)
        self.menu_manager.run_all_jobs_action.setEnabled(False)

    def delete_element(self):
        self.project_editor.delete_element()
        if self.job_list_count() > 0:
            self.menu_manager.delete_element_action.setEnabled(True)

    def update_delete_action_state(self):
        has_job_selected = self.num_selected_jobs() > 0
        has_action_selected = self.num_selected_actions() > 0
        self.menu_manager.delete_element_action.setEnabled(
            has_job_selected or has_action_selected)
        if has_action_selected and has_job_selected:
            job_index = min(self.current_job_index(), self.num_project_jobs() - 1)
            action_index = self.current_action_index()
            if job_index >= 0:
                job = self.project_job(job_index)
                current_action, is_sub_action = \
                    self.get_current_action_at(job, action_index)
                enable_sub_actions = current_action is not None and \
                    not is_sub_action and current_action.type_name == constants.ACTION_COMBO
                self.menu_manager.set_enabled_sub_actions_gui(enable_sub_actions)
        else:
            self.menu_manager.set_enabled_sub_actions_gui(False)

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
        self.menu_manager.change_theme(dark_theme)
        self.tab_widget.change_theme(dark_theme)
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        list_style_sheet = self.list_style_sheet_dark \
            if dark_theme else self.list_style_sheet_light
        self.job_list().setStyleSheet(list_style_sheet)
        self.action_list().setStyleSheet(list_style_sheet)
