# pylint: disable=C0114, C0115, C0116, E0611
from PySide6.QtCore import QObject, Signal


class ProjectUndoManager(QObject):
    set_enabled_undo_action_requested = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo_buffer = []

    def add(self, item, description):
        self._undo_buffer.append((item, description))
        self.set_enabled_undo_action_requested.emit(True, description)

    def pop(self):
        last = self._undo_buffer.pop()
        if len(self._undo_buffer) == 0:
            self.set_enabled_undo_action_requested.emit(False, '')
        else:
            self.set_enabled_undo_action_requested.emit(True, self._undo_buffer[-1][1])
        return last[0]

    def filled(self):
        return len(self._undo_buffer) != 0

    def reset(self):
        self._undo_buffer = []
        self.set_enabled_undo_action_requested.emit(False, '')
