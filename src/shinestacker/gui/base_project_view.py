# pylint: disable=C0114, C0115, C0116, E0611
from PySide6.QtWidgets import QWidget
from .. gui.gui_logging import LogManager


class BaseProjectView(QWidget, LogManager):
    def __init__(self, project_editor, project_controller, parent=None):
        QWidget.__init__(self, parent)
        LogManager.__init__(self)
        self.project_editor = project_editor
        self.project_controller = project_controller
        self.menu_manager = None

    def set_menu_manager(self, menu_manager):
        self.menu_manager = menu_manager
