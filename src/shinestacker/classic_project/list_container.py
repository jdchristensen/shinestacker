# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0904, R0913, R0917, E1101, R0911
import os
from PySide6.QtCore import Qt, QEvent, QSize, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel, QSizePolicy
from .. config.constants import constants
from .. gui.project_model import get_action_input_path, get_action_output_path
from .classic_selection_state import ClassicSelectionState


class HandCursorListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setWordWrap(False)

    def event(self, event):
        if event.type() == QEvent.HoverMove:
            pos = event.position().toPoint()
            item = self.itemAt(pos)
            if item:
                self.viewport().setCursor(Qt.PointingHandCursor)
            else:
                self.viewport().setCursor(Qt.ArrowCursor)
        elif event.type() == QEvent.Leave:
            self.viewport().setCursor(Qt.ArrowCursor)
        return super().event(event)


class ListContainer:
    INDENT_SPACE = "&nbsp;&nbsp;&nbsp;↪&nbsp;&nbsp;&nbsp;"

    select_signal = Signal()

    def __init__(self, job_list=False, action_list=False):
        if job_list is False:
            self._job_list = HandCursorListWidget()
        else:
            self._job_list = job_list
        if action_list is False:
            self._action_list = HandCursorListWidget()
        else:
            self._action_list = action_list

    def get_lists(self):
        return self._job_list, self._action_list

    def set_lists(self, job_list, action_list):
        self._job_list = job_list
        self._action_list = action_list

    def job_list(self):
        return self._job_list

    def action_list(self):
        return self._action_list

    def current_job_index(self):
        return self._job_list.currentRow()

    def current_action_index(self):
        return self._action_list.currentRow()

    def set_current_job(self, index):
        self._job_list.setCurrentRow(index)

    def set_current_action(self, index):
        self._action_list.setCurrentRow(index)

    def job_list_count(self):
        return self._job_list.count()

    def action_list_count(self):
        return self._action_list.count()

    def job_list_item(self, index):
        return self._job_list.item(index)

    def action_list_item(self, index):
        return self._action_list.item(index)

    def job_list_has_focus(self):
        return self._job_list.hasFocus()

    def action_list_has_focus(self):
        return self._action_list.hasFocus()

    def take_job(self, index):
        return self._job_list.takeItem(index)

    def clear_job_list(self):
        self._job_list.clear()

    def clear_action_list(self):
        self._action_list.clear()

    def clear_project(self):
        self._job_list.clear()
        self._action_list.clear()

    def num_selected_jobs(self):
        return len(self._job_list.selectedItems())

    def num_selected_actions(self):
        return len(self._action_list.selectedItems())

    def get_current_job(self):
        return self.project_job(self.current_job_index())

    def get_current_status(self):
        return self.get_current_action()

    def get_current_action(self):
        return self.get_action_at(self.current_action_index())

    def find_action_position(self, job_index, ui_index):
        if not 0 <= job_index < self.num_project_jobs():
            return (None, None, -1)
        actions = self.project_job(job_index).sub_actions
        counter = -1
        for action in actions:
            counter += 1
            if counter == ui_index:
                return (action, None, -1)
            for subaction_index, sub_action in enumerate(action.sub_actions):
                counter += 1
                if counter == ui_index:
                    return (action, sub_action, subaction_index)
        return (None, None, -1)

    def job_text(self, job, long_name=False, html=False):
        txt = f"{job.params.get('name', '(job)')}"
        if html:
            txt = f"<b>{txt}</b>"
        in_path = get_action_input_path(job)[0]
        if os.path.isabs(in_path):
            in_path = ".../" + os.path.basename(in_path)
        ico = constants.ACTION_ICONS[constants.ACTION_JOB]
        return txt + (f" [{ico}Job] - 📁 {in_path} → 📂 ..." if long_name else "")

    def action_text(self, action, is_sub_action=False, indent=True, long_name=False, html=False):
        ico = constants.ACTION_ICONS.get(action.type_name, '')
        if is_sub_action and indent:
            txt = self.INDENT_SPACE
        else:
            txt = ''
        if action.params.get('name', '') != '':
            txt += f"{action.params['name']}"
            if html:
                txt = f"<b>{txt}</b>"
        in_path, out_path = get_action_input_path(action)[0], get_action_output_path(action)[0]
        if os.path.isabs(in_path):
            in_path = ".../" + os.path.basename(in_path)
        if os.path.isabs(out_path):
            out_path = ".../" + os.path.basename(out_path)
        return f"{txt} [{ico}{action.type_name}]" + \
               (f" - 📁 <i>{in_path}</i> → 📂 <i>{out_path}</i>"
                if long_name and not is_sub_action else "")

    def get_insertion_position(self, selection_state):
        if not selection_state or not selection_state.is_valid():
            return self.action_list_count(), False
        if selection_state.is_job_selected():
            return 0, False
        current_row = selection_state.get_action_row()
        if current_row < 0:
            return self.action_list_count(), False
        if selection_state.is_action_selected():
            selected_action = selection_state.action
            if selected_action and selected_action.sub_actions:
                return current_row + len(selected_action.sub_actions) + 1, False
            return current_row + 1, False
        if selection_state.is_subaction_selected():
            parent_action = selection_state.action
            sub_action_idx = selection_state.subaction_index
            if sub_action_idx == len(parent_action.sub_actions) - 1:
                return current_row + 1, False
            return current_row + 1, True
        return self.action_list_count(), False

    def add_list_item(self, widget_list, action, is_sub_action, position=None):
        if action.type_name == constants.ACTION_JOB:
            text = self.job_text(action, long_name=True, html=True)
        else:
            text = self.action_text(action, long_name=True, html=True, is_sub_action=is_sub_action)
        item = QListWidgetItem()
        item.setText('')
        item.setToolTip(
            "<b>Double-click:</b> configure parameters<br>"
            "<b>Right-click:</b> show menu")
        item.setData(Qt.ItemDataRole.UserRole, True)
        if position is None:
            widget_list.addItem(item)
        else:
            widget_list.insertItem(position, item)
        html_text = ("✅ " if action.enabled() else "🚫 ") + text
        label = QLabel(html_text)
        label.setProperty("color-type", "enabled" if action.enabled() else "disabled")
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(False)
        label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        label.adjustSize()
        ideal_width = label.sizeHint().width()
        widget_list.setItemWidget(item, label)
        item.setSizeHint(QSize(ideal_width, label.sizeHint().height()))
        widget_list.setItemWidget(item, label)

    def on_job_selected(self, index):
        self.clear_action_list()
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            position = 0
            for action in job.sub_actions:
                self.add_list_item(self.action_list(), action, False, position)
                position += 1
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.add_list_item(self.action_list(), sub_action, True, position)
                        position += 1
            self.select_signal.emit()

    def get_action_at(self, action_row):
        job_row = self.current_job_index()
        if job_row < 0 or action_row < 0:
            return (job_row, action_row, None)
        action, sub_action, subaction_index = self.find_action_position(job_row, action_row)
        if not action:
            return (job_row, action_row, None)
        job = self.project_job(job_row)
        if sub_action:
            return (job_row, action_row,
                    ClassicSelectionState(
                        job.sub_actions,
                        action.sub_actions,
                        job.sub_actions.index(action),
                        subaction_index,
                        job_index=job_row,
                        widget_type='subaction'
                    ))
        return (job_row, action_row,
                ClassicSelectionState(
                    job.sub_actions,
                    None,
                    job.sub_actions.index(action),
                    job_index=job_row,
                    widget_type='action'
                ))
