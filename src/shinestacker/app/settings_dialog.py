# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903
from .. gui.config_dialog import ConfigDialog


class SettingsDialog(ConfigDialog):
    def __init__(self, parent=None):
        super().__init__("Settings", parent)

    def create_form_content(self):
        pass

    def accept(self):
        super().accept()

    def reset_to_defaults(self):
        pass


def show_settings_dialog(parent):
    dialog = SettingsDialog(parent)
    dialog.exec()
