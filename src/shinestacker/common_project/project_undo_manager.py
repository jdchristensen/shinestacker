# pylint: disable=C0114, C0115, C0116, E0611
from PySide6.QtCore import QObject, Signal


class ProjectUndoManager(QObject):
    set_enabled_undo_action_requested = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo_buffer = []

    def add(self, item, description, action_type=None, affected_position=None):
        # print(f"ADD UNDO DEBUG: action={action_type or ''}, "
        #      f"position={affected_position}, desc={description}")
        entry = {
            'item': item,
            'description': description,
            'action_type': action_type if action_type else '',
            'affected_position': affected_position if affected_position else (-1, -1, -1)
        }
        self._undo_buffer.append(entry)
        self.set_enabled_undo_action_requested.emit(True, description)

    def pop(self):
        entry = self._undo_buffer.pop()
        if len(self._undo_buffer) == 0:
            self.set_enabled_undo_action_requested.emit(False, '')
        else:
            self.set_enabled_undo_action_requested.emit(True, self._undo_buffer[-1]['description'])
        # print(f"UNDO DEBUG: action={entry['action_type']}, "
        #      f"position={entry['affected_position']}, desc={entry['description']}")
        return entry

    def peek(self):
        if self._undo_buffer:
            return self._undo_buffer[-1]
        return None

    def last_entry(self):
        return self.peek()

    def filled(self):
        return len(self._undo_buffer) != 0

    def reset(self):
        self._undo_buffer = []
        self.set_enabled_undo_action_requested.emit(False, '')

    def add_extra_data_to_last_entry(self, label, data):
        if len(self._undo_buffer) > 0:
            self._undo_buffer[-1][label] = data
