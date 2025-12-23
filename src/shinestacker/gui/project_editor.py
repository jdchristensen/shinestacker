# pylint: disable=C0114, C0115, C0116, E0611
from PySide6.QtCore import QObject, Signal
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.project_handler import ProjectHandler


class ProjectEditor(ProjectHandler, QObject):
    mark_as_modified_signal = Signal(bool, str)

    def __init__(self, project_holder, parent=None):
        ProjectHandler.__init__(self, project_holder)
        QObject.__init__(self, parent)
        self._dialog = None

    def mark_as_modified(self, modified=True, description=''):
        ProjectHandler.mark_as_modified(self, modified, description)
        self.mark_as_modified_signal.emit(modified, description)

    def action_config_dialog(self, action):
        self._dialog = ActionConfigDialog(action, self.current_file_directory(), self.parent())
        return self._dialog

    def post_undo(self, status):
        pass
