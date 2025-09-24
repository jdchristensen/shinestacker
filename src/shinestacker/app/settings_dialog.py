# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903
from PySide6.QtWidgets import QLabel
from .. gui.config_dialog import ConfigDialog


class SettingsDialog(ConfigDialog):
    def __init__(self, parent=None, project_settings=True, retouch_settings=True):
        self.project_settings = project_settings
        self.retouch_settings = retouch_settings
        super().__init__("Settings", parent)

    def create_form_content(self):
        if self.project_settings:
            self.create_project_settings()
        if self.retouch_settings:
            self.create_retouch_settings()

    def create_project_settings(self):
        label = QLabel("Project settings")
        label.setStyleSheet("font-weight: bold")
        self.container_layout.addRow(label)

    def create_retouch_settings(self):
        label = QLabel("Retouch settings")
        label.setStyleSheet("font-weight: bold")
        self.container_layout.addRow(label)

    def accept(self):
        super().accept()

    def reset_to_defaults(self):
        pass


def show_settings_dialog(parent=None, project_settings=True, retouch_settings=True):
    dialog = SettingsDialog(parent, project_settings, retouch_settings)
    dialog.exec()
