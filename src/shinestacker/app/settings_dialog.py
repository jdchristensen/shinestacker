# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903, E0611
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QCheckBox
from .. gui.config_dialog import ConfigDialog
from .. config.settings import Settings
from .. config.constants import constants
from .. config.app_config import AppConfig


class SettingsDialog(ConfigDialog):
    update_project_config_requested = Signal()

    def __init__(self, parent=None, project_settings=True, retouch_settings=True):
        self.project_settings = project_settings
        self.retouch_settings = retouch_settings
        self.settings = Settings()
        self.expert_options = None
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
        self.expert_options = QCheckBox()
        self.expert_options.setChecked(
            self.settings.settings.get('expert_options',
                                       constants.DEFAULT_EXPERT_OPTIONS))
        self.container_layout.addRow("Expert options:", self.expert_options)

    def create_retouch_settings(self):
        label = QLabel("Retouch settings")
        label.setStyleSheet("font-weight: bold")
        self.container_layout.addRow(label)

    def accept(self):
        self.settings.settings['expert_options'] = self.expert_options.isChecked()
        self.settings.save()
        AppConfig.instance().load_defaults()
        self.update_project_config_requested.emit()
        super().accept()

    def reset_to_defaults(self):
        self.expert_options.setChecked(constants.DEFAULT_EXPERT_OPTIONS)


def show_settings_dialog(parent, project_settings, retouch_settings,
                         handle_project_config):
    dialog = SettingsDialog(parent, project_settings, retouch_settings)
    dialog.update_project_config_requested.connect(handle_project_config)
    dialog.exec()
