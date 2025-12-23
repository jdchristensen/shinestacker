# pylint: disable=C0114, C0115, C0116, E0611
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from .. gui.gui_logging import LogManager


class ProjectView(QWidget, LogManager):
    refresh_ui_signal = Signal()

    def __init__(self, dark_theme, parent=None):
        QWidget.__init__(self, parent)
        LogManager.__init__(self)
        self.menu_manager = None
        self.dark_theme = dark_theme

    def set_menu_manager(self, menu_manager):
        self.menu_manager = menu_manager

    def refresh_ui(self):
        self.refresh_ui_signal.emit()
