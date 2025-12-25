# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=R1716
import os
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea, QDialog, QMessageBox
from .. config.constants import constants
from .. gui.project_model import ActionConfig
from .. gui.project_view import ProjectView
from .. gui.gui_logging import QTextEditLogger
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.run_worker import JobLogWorker, ProjectLogWorker
from .job_widget import JobWidget


class ModernProjectView(ProjectView):
    update_delete_action_state_requested = Signal()
    show_status_message_requested = Signal(str, int)

    def __init__(self, project_holder, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, dark_theme, parent)
        self.job_widgets = []
        self.scroll_area = None
        self.scroll_content = None
        self.project_layout = None
        self.selected_widget = None
        self.selected_widget_type = None
        self.selected_job_index = -1
        self.selected_action_index = -1
        self.selected_subaction_index = -1
        self.show_status_message = None
        self._worker = None
        self._setup_ui()
        self.change_theme(dark_theme)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFocusPolicy(Qt.NoFocus)
        self.scroll_content = QWidget()
        self.scroll_content.setFocusPolicy(Qt.NoFocus)
        self.scroll_content.setContentsMargins(2, 2, 2, 2)
        self.project_layout = QVBoxLayout(self.scroll_content)
        self.project_layout.setSpacing(2)
        self.project_layout.setContentsMargins(2, 2, 2, 2)
        self.project_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        main_splitter.addWidget(self.scroll_area)
        self.console_area = QTextEditLogger(self)
        self.add_gui_logger(self.console_area)
        console_layout = QVBoxLayout(self.console_area)
        self.console_area.text_edit.setFocusPolicy(Qt.ClickFocus)
        self.console_area.text_edit.installEventFilter(self)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.addWidget(self.console_area.text_edit)
        main_splitter.addWidget(self.console_area)
        main_splitter.setSizes([600, 200])
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
        ico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "gui", "ico", "shinestacker.png")
        self.console_area.handle_html_message(
            f"<img width=100 src='{ico_path}'><hr><br>")

    def connect_signals(self, update_delete_action_state, show_status_message):
        self.update_delete_action_state_requested.connect(update_delete_action_state)
        self.show_status_message_requested.connect(show_status_message)

    # pylint: disable=C0103
    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()

    def eventFilter(self, obj, event):
        if obj == self.console_area.text_edit and event.type() == event.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
                self.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if not self.job_widgets:
            return
        key = event.key()
        if key == Qt.Key_Up:
            self._select_previous_widget()
            event.accept()
        elif key == Qt.Key_Down:
            self._select_next_widget()
            event.accept()
        elif key == Qt.Key_Left:
            self._select_previous_widget()
            event.accept()
        elif key == Qt.Key_Right:
            self._select_next_widget()
            event.accept()
        elif key == Qt.Key_Home:
            self._select_first_job()
            event.accept()
        elif key == Qt.Key_End:
            self._select_last_job()
            event.accept()
        elif key in [Qt.Key_Return, Qt.Key_Enter]:
            if self.selected_widget_type == 'job':
                self._on_job_double_clicked(self.selected_job_index)
            elif self.selected_widget_type == 'action':
                self._on_action_double_clicked(self.selected_job_index, self.selected_action_index)
            elif self.selected_widget_type == 'subaction':
                self._on_subaction_double_clicked(
                    self.selected_job_index, self.selected_action_index,
                    self.selected_subaction_index)
            event.accept()
        elif key == Qt.Key_Tab:
            super().keyPressEvent(event)
        elif key == Qt.Key_Backtab:
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        pos = self.mapFromGlobal(QCursor.pos())
        widget = self.childAt(pos)
        current_action = None
        if widget:
            while widget and widget != self:
                if hasattr(widget, 'data_object'):
                    current_action = widget.data_object
                    break
                widget = widget.parentWidget()
        if not current_action and self.selected_widget:
            if hasattr(self.selected_widget, 'data_object'):
                current_action = self.selected_widget.data_object
        if current_action:
            menu = self.create_common_context_menu(current_action)
            menu.exec(event.globalPos())
    # pylint: enable=C0103

    def get_current_selected_action(self):
        if self.selected_widget_type == 'job':
            if 0 <= self.selected_job_index < len(self.project().jobs):
                return self.project().jobs[self.selected_job_index]
        elif self.selected_widget_type == 'action':
            if (0 <= self.selected_job_index < len(self.project().jobs) and
                0 <= self.selected_action_index < len(self.project().jobs[
                    self.selected_job_index].sub_actions)):
                return self.project().jobs[
                    self.selected_job_index].sub_actions[self.selected_action_index]
        elif self.selected_widget_type == 'subaction':
            if (0 <= self.selected_job_index < len(self.project().jobs) and
                0 <= self.selected_action_index < len(self.project().jobs[
                    self.selected_job_index].sub_actions)):
                action = self.project().jobs[
                    self.selected_job_index].sub_actions[self.selected_action_index]
                if (hasattr(action, 'sub_actions') and
                        0 <= self.selected_subaction_index < len(action.sub_actions)):
                    return action.sub_actions[self.selected_subaction_index]
        return None

    def has_selection(self):
        return self.selected_job_index >= 0

    def has_selected_sub_action(self):
        if self.selected_widget_type == 'subaction':
            return True
        if self.selected_widget_type == 'action' and self.selected_widget is not None:
            return self.selected_widget.data_object.type_name == constants.ACTION_COMBO
        return False

    def _select_next_widget(self):
        if self.selected_widget_type == 'job':
            if self._has_actions_in_job(self.selected_job_index):
                self._select_first_action_in_job(self.selected_job_index)
        elif self.selected_widget_type == 'action':
            if self._has_subactions_in_action(self.selected_job_index, self.selected_action_index):
                self._select_first_subaction_in_action(
                    self.selected_job_index, self.selected_action_index)
            else:
                self._select_next_action_or_job()
        elif self.selected_widget_type == 'subaction':
            self._select_next_subaction_or_action_or_job()

    def _select_previous_widget(self):
        if self.selected_widget_type == 'subaction':
            if self.selected_subaction_index > 0:
                self._select_subaction(
                    self.selected_job_index, self.selected_action_index,
                    self.selected_subaction_index - 1
                )
            else:
                self._select_action(self.selected_job_index, self.selected_action_index)
        elif self.selected_widget_type == 'action':
            if self.selected_action_index > 0:
                prev_action_index = self.selected_action_index - 1
                job_widget = self.job_widgets[self.selected_job_index]
                prev_action_widget = job_widget.child_widgets[prev_action_index]
                if prev_action_widget.num_child_widgets() > 0:
                    last_subaction_index = prev_action_widget.num_child_widgets() - 1
                    self._select_subaction(
                        self.selected_job_index, prev_action_index, last_subaction_index
                    )
                else:
                    self._select_action(self.selected_job_index, prev_action_index)
            else:
                self._select_job(self.selected_job_index)
        elif self.selected_widget_type == 'job':
            if self.selected_job_index > 0:
                self._select_job(self.selected_job_index - 1)

    def _select_job(self, job_index):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            self._on_widget_clicked(job_widget, 'job', job_index)
            self._ensure_selected_visible()

    def _select_action(self, job_index, action_index):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                self._on_widget_clicked(action_widget, 'action', job_index, action_index)
                self._ensure_selected_visible()

    def _select_subaction(self, job_index, action_index, subaction_index):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                if 0 <= subaction_index < action_widget.num_child_widgets():
                    subaction_widget = action_widget.child_widgets[subaction_index]
                    self._on_widget_clicked(
                        subaction_widget, 'subaction', job_index, action_index, subaction_index)
                    self._ensure_selected_visible()

    def _select_first_job(self):
        if self.job_widgets:
            self._select_job(0)

    def _select_last_job(self):
        if self.job_widgets:
            self._select_job(len(self.job_widgets) - 1)

    def _select_first_action_in_job(self, job_index):
        self._select_action(job_index, 0)

    def _select_first_subaction_in_action(self, job_index, action_index):
        self._select_subaction(job_index, action_index, 0)

    def _has_actions_in_job(self, job_index):
        return self.job_widgets[job_index].num_child_widgets() > 0

    def _has_subactions_in_action(self, job_index, action_index):
        job_widget = self.job_widgets[job_index]
        action_widget = job_widget.child_widgets[action_index]
        return action_widget.num_child_widgets() > 0

    def _select_next_action_or_job(self):
        job_index = self.selected_job_index
        action_index = self.selected_action_index
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            next_action_index = action_index + 1
            if next_action_index < job_widget.num_child_widgets():
                self._select_action(job_index, next_action_index)
            else:
                self._select_next_job()

    def _select_next_subaction_or_action_or_job(self):
        job_index = self.selected_job_index
        action_index = self.selected_action_index
        subaction_index = self.selected_subaction_index
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                next_subaction_index = subaction_index + 1
                if next_subaction_index < action_widget.num_child_widgets():
                    self._select_subaction(job_index, action_index, next_subaction_index)
                else:
                    self._select_next_action_or_job()

    def _select_previous_job_last_widget(self):
        prev_job_index = self.selected_job_index - 1
        if prev_job_index >= 0:
            prev_job_widget = self.job_widgets[prev_job_index]
            if prev_job_widget.num_child_widgets() > 0:
                last_action_index = prev_job_widget.num_child_widgets() - 1
                last_action_widget = prev_job_widget.child_widgets[last_action_index]
                if last_action_widget.num_child_widgets() > 0:
                    last_subaction_index = last_action_widget.num_child_widgets() - 1
                    self._select_subaction(prev_job_index, last_action_index, last_subaction_index)
                else:
                    self._select_action(prev_job_index, last_action_index)
            else:
                self._select_job(prev_job_index)

    def _select_next_job(self):
        if not self.job_widgets:
            return
        new_index = self.selected_job_index + 1
        if new_index < len(self.job_widgets):
            self._select_job(new_index)

    def _select_previous_job(self):
        if not self.job_widgets:
            return
        new_index = self.selected_job_index - 1
        if new_index >= 0:
            self._select_job(new_index)

    def _reset_selection(self):
        self.selected_widget = None
        self.selected_widget_type = None
        self.selected_job_index = -1
        self.selected_action_index = -1
        self.selected_subaction_index = -1

    def clear_job_list(self):
        for widget in self.job_widgets:
            widget.clicked.disconnect()
            widget.deleteLater()
        self.job_widgets.clear()
        if self.project_layout:
            while self.project_layout.count():
                item = self.project_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        self.selected_job_index = 0

    def clear_project(self):
        self.clear_job_list()
        self._reset_selection()
        self.update_delete_action_state_requested.emit()

    def add_job_widget(self, job):
        job_widget = JobWidget(job, self.dark_theme)
        job_widget.setFocusPolicy(Qt.NoFocus)
        job_index = len(self.job_widgets)
        job_widget.clicked.connect(
            lambda checked=False, w=job_widget, idx=job_index:
                self._on_widget_clicked(w, 'job', idx)
        )
        job_widget.double_clicked.connect(
            lambda checked=False, idx=job_index: self._on_job_double_clicked(idx)
        )
        self.job_widgets.append(job_widget)
        self.project_layout.addWidget(job_widget)
        for action_idx, action_widget in enumerate(job_widget.child_widgets):
            def make_action_click_handler(j_idx, a_idx, widget):
                def handler():
                    self._on_widget_clicked(widget, 'action', j_idx, a_idx)
                return handler
            action_widget.clicked.connect(
                make_action_click_handler(job_index, action_idx, action_widget))
            action_widget.double_clicked.connect(
                lambda checked=False, j_idx=job_index, a_idx=action_idx:
                self._on_action_double_clicked(j_idx, a_idx)
            )
            for subaction_idx, subaction_widget in enumerate(action_widget.child_widgets):
                def make_subaction_click_handler(j_idx, a_idx, s_idx, widget):
                    def handler():
                        self._on_widget_clicked(widget, 'subaction', j_idx, a_idx, s_idx)
                    return handler
                subaction_widget.clicked.connect(
                    make_subaction_click_handler(
                        job_index, action_idx, subaction_idx, subaction_widget)
                )
                subaction_widget.double_clicked.connect(
                    lambda checked=False, j_idx=job_index, a_idx=action_idx, s_idx=subaction_idx:
                    self._on_subaction_double_clicked(j_idx, a_idx, s_idx)
                )
        if len(self.job_widgets) == 1:
            self._on_widget_clicked(job_widget, 'job', 0)

    def _on_widget_clicked(self, widget, widget_type,
                           job_index, action_index=None, subaction_index=None):
        if self.selected_widget:
            self.selected_widget.set_selected(False)
        widget.set_selected(True)
        self.selected_widget = widget
        self.selected_widget_type = widget_type
        self.selected_job_index = job_index
        if widget_type == 'job':
            self.selected_action_index = -1
            self.selected_subaction_index = -1
        elif widget_type == 'action':
            self.selected_action_index = action_index if action_index is not None else -1
            self.selected_subaction_index = -1
        elif widget_type == 'subaction':
            self.selected_action_index = action_index if action_index is not None else -1
            self.selected_subaction_index = subaction_index if subaction_index is not None else -1
        self.update_delete_action_state_requested.emit()
        self.setFocus()

    def _on_job_double_clicked(self, job_index):
        job_widget = self.job_widgets[job_index]
        self._on_widget_clicked(job_widget, 'job', job_index)
        job = self.project_job(job_index)
        if job:
            self.action_dialog = ActionConfigDialog(
                job, self.current_file_directory(), self.parent())
            if self.action_dialog.exec() == QDialog.Accepted:
                self._update_job_widget(job_index, job)

    def _on_action_double_clicked(self, job_index, action_index):
        job_widget = self.job_widgets[job_index]
        action_widget = job_widget.child_widgets[action_index]
        self._on_widget_clicked(action_widget, 'action', job_index, action_index)
        job = self.project_job(job_index)
        action = job.sub_actions[action_index] if hasattr(job, 'sub_actions') else None
        if action:
            self.action_dialog = ActionConfigDialog(
                action, self.current_file_directory(), self.parent())
            if self.action_dialog.exec() == QDialog.Accepted:
                self._update_action_widget(job_index, action_index, action)

    def _on_subaction_double_clicked(self, job_index, action_index, subaction_index):
        job_widget = self.job_widgets[job_index]
        action_widget = job_widget.child_widgets[action_index]
        subaction_widget = action_widget.child_widgets[subaction_index]
        self._on_widget_clicked(
            subaction_widget, 'subaction', job_index, action_index, subaction_index)
        job = self.project_job(job_index)
        action = job.sub_actions[action_index] if hasattr(job, 'sub_actions') else None
        subaction = action.sub_actions[subaction_index] \
            if action and hasattr(action, 'sub_actions') else None
        if subaction:
            self.action_dialog = ActionConfigDialog(
                subaction, self.current_file_directory(), self.parent())
            if self.action_dialog.exec() == QDialog.Accepted:
                self._update_subaction_widget(job_index, action_index, subaction_index, subaction)

    def _update_job_widget(self, job_index, job):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            job_widget.update(job)

    def _update_action_widget(self, job_index, action_index, action):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                action_widget.update(action)

    def _update_subaction_widget(self, job_index, action_index, subaction_index, subaction):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                if 0 <= subaction_index < action_widget.num_child_widgets():
                    subaction_widget = action_widget.child_widgets[subaction_index]
                    subaction_widget.update(subaction)

    def _select_job_widget(self, widget):
        for i, job_widget in enumerate(self.job_widgets):
            if job_widget == widget:
                job_widget.set_selected(True)
                self.selected_job_index = i
            else:
                job_widget.set_selected(False)

    def delete_element(self, confirm=True):
        job_index = self.selected_job_index
        action_index = self.selected_action_index
        subaction_index = self.selected_subaction_index
        if job_index < 0:
            return None
        if action_index < 0 and subaction_index < 0:
            return self._delete_job(job_index, confirm)
        if action_index >= 0 and subaction_index < 0:
            return self._delete_action(job_index, action_index, confirm)
        if subaction_index >= 0:
            return self._delete_subaction(job_index, action_index, subaction_index, confirm)
        return None

    def _delete_job(self, job_index, confirm=True):
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            if confirm:
                reply = QMessageBox.question(
                    self.parent(), "Confirm Delete",
                    f"Are you sure you want to delete job '{job.params.get('name', '')}'?",
                    QMessageBox.Yes | QMessageBox.No
                )
            else:
                reply = None
            if not confirm or reply == QMessageBox.Yes:
                self.mark_as_modified(True, "Delete Job")
                deleted_job = self.project().jobs.pop(job_index)
                self._select_previous_widget()
                self.refresh_ui()
                return deleted_job
        return None

    def _delete_action(self, job_index, action_index, confirm=True):
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if confirm:
                    reply = QMessageBox.question(
                        self.parent(), "Confirm Delete",
                        "Are you sure you want to delete action "
                        f"'{action.params.get('name', '')}'?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                else:
                    reply = None
                if not confirm or reply == QMessageBox.Yes:
                    self.mark_as_modified(True, "Delete Action")
                    deleted_action = job.pop_sub_action(action_index)
                    self._select_previous_widget()
                    self.refresh_ui()
                    return deleted_action
        return None

    def _delete_subaction(self, job_index, action_index, subaction_index, confirm=True):
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if 0 <= subaction_index < len(action.sub_actions):
                    subaction = action.sub_actions[subaction_index]
                    if confirm:
                        reply = QMessageBox.question(
                            self.parent(), "Confirm Delete",
                            "Are you sure you want to delete sub-action "
                            f"'{subaction.params.get('name', '')}'?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                    else:
                        reply = None
                    if not confirm or reply == QMessageBox.Yes:
                        self.mark_as_modified(True, "Delete Sub-action")
                        deleted_subaction = action.pop_sub_action(subaction_index)
                        self._select_previous_widget()
                        self.refresh_ui()
                        return deleted_subaction
        return None

    def copy_job(self):
        if 0 <= self.selected_job_index < len(self.project().jobs):
            job = self.project().jobs[self.selected_job_index]
            self.set_copy_buffer(job.clone())

    def copy_action(self):
        if (0 <= self.selected_job_index < len(self.project().jobs) and
                self.selected_action_index >= 0):
            job = self.project().jobs[self.selected_job_index]
            if 0 <= self.selected_action_index < len(job.sub_actions):
                action = job.sub_actions[self.selected_action_index]
                self.set_copy_buffer(action.clone())

    def copy_subaction(self):
        if (0 <= self.selected_job_index < len(self.project().jobs) and
                self.selected_action_index >= 0 and self.selected_subaction_index >= 0):
            job = self.project().jobs[self.selected_job_index]
            if 0 <= self.selected_action_index < len(job.sub_actions):
                action = job.sub_actions[self.selected_action_index]
                if 0 <= self.selected_subaction_index < len(action.sub_actions):
                    subaction = action.sub_actions[self.selected_subaction_index]
                    self.set_copy_buffer(subaction.clone())

    def copy_element(self):
        if self.selected_widget_type == 'job':
            self.copy_job()
        elif self.selected_widget_type == 'action':
            self.copy_action()
        elif self.selected_widget_type == 'subaction':
            self.copy_subaction()

    def paste_job(self):
        if not self.has_copy_buffer():
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name != constants.ACTION_JOB:
            if len(self.project().jobs) == 0:
                return
            if copy_buffer.type_name not in constants.ACTION_TYPES:
                return
            current_job = self.project().jobs[self.selected_job_index]
            new_action_index = len(current_job.sub_actions)
            current_job.sub_actions.insert(new_action_index, copy_buffer.clone())
            self.mark_as_modified(True, "Paste Action")
            self.selected_action_index = new_action_index
            self.selected_subaction_index = -1
            self.refresh_ui()
            self._ensure_selected_visible()
            return
        if len(self.project().jobs) == 0:
            new_job_index = 0
        else:
            new_job_index = min(max(self.selected_job_index + 1, 0), len(self.project().jobs))
        self.mark_as_modified(True, "Paste Job")
        self.project().jobs.insert(new_job_index, copy_buffer.clone())
        self.selected_job_index = new_job_index
        self.selected_action_index = -1
        self.selected_subaction_index = -1
        self.refresh_ui()
        self._ensure_selected_visible()

    def paste_action(self):
        if not self.has_copy_buffer():
            return
        if self.selected_job_index < 0:
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name not in constants.ACTION_TYPES:
            return
        job = self.project().jobs[self.selected_job_index]
        if self.selected_action_index >= 0:
            new_action_index = self.selected_action_index + 1
        else:
            new_action_index = len(job.sub_actions)
        job.sub_actions.insert(new_action_index, copy_buffer.clone())
        self.mark_as_modified(True, "Paste Action")
        self.selected_action_index = new_action_index
        self.selected_subaction_index = -1
        self.refresh_ui()
        self._ensure_selected_visible()

    def paste_subaction(self):
        if not self.has_copy_buffer():
            return
        if self.selected_job_index < 0 or self.selected_action_index < 0:
            return
        copy_buffer = self.copy_buffer()
        job = self.project().jobs[self.selected_job_index]
        if self.selected_action_index >= len(job.sub_actions):
            return
        action = job.sub_actions[self.selected_action_index]
        if action.type_name != constants.ACTION_COMBO:
            return
        if copy_buffer.type_name not in constants.SUB_ACTION_TYPES:
            return
        if self.selected_subaction_index >= 0:
            new_subaction_index = self.selected_subaction_index + 1
        else:
            new_subaction_index = 0
        action.sub_actions.insert(new_subaction_index, copy_buffer.clone())
        self.mark_as_modified(True, "Paste Sub-action")
        self.selected_subaction_index = new_subaction_index
        self.refresh_ui()
        self._ensure_selected_visible()

    def paste_element(self):
        if not self.has_copy_buffer():
            return
        copy_buffer = self.copy_buffer()
        if copy_buffer.type_name in constants.SUB_ACTION_TYPES:
            self.paste_subaction()
        elif self.selected_widget_type == 'job':
            self.paste_job()
        elif self.selected_widget_type == 'action':
            self.paste_action()
        elif self.selected_widget_type == 'subaction':
            self.paste_action()

    def cut_element(self):
        element = self.delete_element(False)
        self.set_copy_buffer(element)

    def clone_job(self):
        job_index = self.selected_job_index
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            job_clone = job.clone(name_postfix=self.CLONE_POSTFIX)
            new_job_index = job_index + 1
            self.mark_as_modified(True, "Duplicate Job")
            self.project().jobs.insert(new_job_index, job_clone)
            self.selected_job_index = new_job_index
            self.selected_action_index = -1
            self.selected_subaction_index = -1
            self.selected_widget_type = 'job'
            self.refresh_ui()

    def clone_action(self):
        if self.selected_widget_type == 'action':
            job_index = self.selected_job_index
            action_index = self.selected_action_index
            if (0 <= job_index < len(self.project().jobs) and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                action_clone = action.clone(name_postfix=self.CLONE_POSTFIX)
                new_action_index = action_index + 1
                self.mark_as_modified(True, "Duplicate Action")
                job.sub_actions.insert(new_action_index, action_clone)
                self.selected_action_index = new_action_index
                self.selected_subaction_index = -1
                self.selected_widget_type = 'action'
                self.refresh_ui()
        elif self.selected_widget_type == 'subaction':
            job_index = self.selected_job_index
            action_index = self.selected_action_index
            subaction_index = self.selected_subaction_index
            if (0 <= job_index < len(self.project().jobs) and
                    0 <= action_index < len(self.project().jobs[job_index].sub_actions)):
                job = self.project().jobs[job_index]
                action = job.sub_actions[action_index]
                if (action.type_name == constants.ACTION_COMBO and
                        0 <= subaction_index < len(action.sub_actions)):
                    subaction = action.sub_actions[subaction_index]
                    subaction_clone = subaction.clone(name_postfix=self.CLONE_POSTFIX)
                    new_subaction_index = subaction_index + 1
                    self.mark_as_modified(True, "Duplicate Sub-action")
                    action.sub_actions.insert(new_subaction_index, subaction_clone)
                    self.selected_subaction_index = new_subaction_index
                    self.selected_widget_type = 'subaction'
                    self.refresh_ui()

    def clone_element(self):
        if self.selected_widget_type == 'job':
            self.clone_job()
        elif self.selected_widget_type == 'action':
            self.clone_action()
        elif self.selected_widget_type == 'subaction':
            self.clone_action()

    def disable(self):
        self.set_enabled(False)

    def enable(self):
        self.set_enabled(True)

    def disable_all(self):
        self.set_enabled_all(False)

    def enable_all(self):
        self.set_enabled_all(True)

    def set_enabled(self, enabled):
        self._set_enabled(self.selected_job_index, self.selected_action_index,
                          self.selected_subaction_index, enabled)

    def set_enabled_all(self, enabled):
        for job in self.project().jobs:
            job.set_enabled_all(enabled)
        self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} All")
        self.refresh_ui()

    def _set_enabled(self, job_idx, action_idx, subaction_idx, enabled):
        if job_idx < 0:
            return
        if subaction_idx >= 0:
            if (0 <= job_idx < len(self.project().jobs) and
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions)):
                action = self.project().jobs[job_idx].sub_actions[action_idx]
                if 0 <= subaction_idx < len(action.sub_actions):
                    action.sub_actions[subaction_idx].set_enabled(enabled)
                    self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Sub-action")
        elif action_idx >= 0:
            if 0 <= job_idx < len(self.project().jobs) and \
                    0 <= action_idx < len(self.project().jobs[job_idx].sub_actions):
                self.project().jobs[job_idx].sub_actions[action_idx].set_enabled(enabled)
                self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Action")
        else:
            if 0 <= job_idx < len(self.project().jobs):
                self.project().jobs[job_idx].set_enabled(enabled)
                self.mark_as_modified(True, f"{'Enable' if enabled else 'Disable'} Job")
        self.refresh_ui()

    def _ensure_selected_visible(self):
        if not self.selected_widget or not self.scroll_area:
            return
        if not self.selected_widget.isVisible() or self.selected_widget.height() == 0:
            QTimer.singleShot(10, self._ensure_selected_visible)
            return
        viewport_height = self.scroll_area.viewport().height()
        widget_height = self.selected_widget.height()
        if widget_height <= viewport_height:
            y_margin = (viewport_height - widget_height) // 2
        else:
            y_margin = 0
        self.scroll_area.ensureWidgetVisible(self.selected_widget, 0, y_margin)

    def move_element_up(self):
        if self.selected_widget_type == 'job':
            self._shift_job(-1)
        elif self.selected_widget_type == 'action':
            self._shift_action(-1)
        elif self.selected_widget_type == 'subaction':
            self._shift_subaction(-1)

    def move_element_down(self):
        if self.selected_widget_type == 'job':
            self._shift_job(+1)
        elif self.selected_widget_type == 'action':
            self._shift_action(+1)
        elif self.selected_widget_type == 'subaction':
            self._shift_subaction(+1)

    def _shift_job(self, delta):
        job_index = self.selected_job_index
        if job_index < 0:
            return
        new_index = job_index + delta
        if 0 <= new_index < len(self.project().jobs):
            self.mark_as_modified(True, "Shift Job")
            jobs = self.project().jobs
            jobs.insert(new_index, jobs.pop(job_index))
            self.selected_job_index = new_index
            self.selected_action_index = -1
            self.selected_subaction_index = -1
            self.refresh_ui()

    def _shift_action(self, delta):
        job_index = self.selected_job_index
        action_index = self.selected_action_index
        if job_index < 0 or action_index < 0:
            return
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            new_index = action_index + delta
            if 0 <= new_index < len(job.sub_actions):
                self.mark_as_modified(True, "Shift Action")
                job.sub_actions.insert(new_index, job.sub_actions.pop(action_index))
                self.selected_action_index = new_index
                self.selected_subaction_index = -1
                self.refresh_ui()

    def _shift_subaction(self, delta):
        job_index = self.selected_job_index
        action_index = self.selected_action_index
        subaction_index = self.selected_subaction_index
        if job_index < 0 or action_index < 0 or subaction_index < 0:
            return
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if action.type_name == constants.ACTION_COMBO:
                    new_index = subaction_index + delta
                    if 0 <= new_index < len(action.sub_actions):
                        self.mark_as_modified(True, "Shift Sub-action")
                        action.sub_actions.insert(
                            new_index, action.sub_actions.pop(subaction_index))
                        self.selected_subaction_index = new_index
                        self.refresh_ui()

    def add_action(self, type_name):
        job_index = self.selected_job_index
        if job_index < 0:
            if len(self.project().jobs) > 0:
                QMessageBox.warning(self.parent(),
                                    "No Job Selected", "Please select a job first.")
            else:
                QMessageBox.warning(self.parent(),
                                    "No Job Added", "Please add a job first.")
            return
        action = ActionConfig(type_name)
        action.parent = self.project().jobs[job_index]
        self.action_dialog = ActionConfigDialog(
            action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            self.mark_as_modified(True, "Add Action")
            self.project().jobs[job_index].add_sub_action(action)
            self.selected_action_index = len(self.project().jobs[job_index].sub_actions) - 1
            self.selected_subaction_index = -1
            self.selected_widget_type = 'action'
            self.refresh_ui()

    def add_sub_action(self, type_name):
        job_index = self.selected_job_index
        action_index = self.selected_action_index
        if job_index < 0 or action_index < 0:
            return
        if 0 <= job_index < len(self.project().jobs):
            job = self.project().jobs[job_index]
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if action.type_name != constants.ACTION_COMBO:
                    return
                sub_action = ActionConfig(type_name)
                self.action_dialog = ActionConfigDialog(
                    sub_action, self.current_file_directory(), self.parent())
                if self.action_dialog.exec() == QDialog.Accepted:
                    self.mark_as_modified(True, "Add Sub-action")
                    action.add_sub_action(sub_action)
                    self.selected_subaction_index = len(action.sub_actions) - 1
                    self.selected_widget_type = 'subaction'
                    self.refresh_ui()

    def refresh_ui(self):
        old_job_index = self.selected_job_index
        old_action_index = self.selected_action_index
        old_subaction_index = self.selected_subaction_index
        old_widget_type = self.selected_widget_type
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)
        if old_widget_type == 'job' and 0 <= old_job_index < len(self.job_widgets):
            self._select_job(old_job_index)
        elif old_widget_type == 'action' and 0 <= old_job_index < len(self.job_widgets):
            job_widget = self.job_widgets[old_job_index]
            if 0 <= old_action_index < job_widget.num_child_widgets():
                self._select_action(old_job_index, old_action_index)
            elif job_widget.num_child_widgets() > 0:
                self._select_action(old_job_index, 0)
            else:
                self._select_job(old_job_index)
        elif old_widget_type == 'subaction' and 0 <= old_job_index < len(self.job_widgets):
            job_widget = self.job_widgets[old_job_index]
            if 0 <= old_action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[old_action_index]
                if 0 <= old_subaction_index < action_widget.num_child_widgets():
                    self._select_subaction(old_job_index, old_action_index, old_subaction_index)
                elif action_widget.num_child_widgets() > 0:
                    self._select_subaction(old_job_index, old_action_index, 0)
                else:
                    self._select_action(old_job_index, old_action_index)
            elif job_widget.num_child_widgets() > 0:
                self._select_action(old_job_index, 0)
            else:
                self._select_job(old_job_index)
        elif len(self.job_widgets) > 0:
            self._select_job(0)
        else:
            self._reset_selection()

    def get_console_area(self):
        return self.console_area

    def run_job(self):
        current_index = self.selected_job_index
        if current_index < 0:
            QMessageBox.warning(
                self.parent(), "No Job Selected", "Please select a job first.")
            return
        job = self.project_job(current_index)
        if not job.enabled():
            QMessageBox.warning(
                self.parent(), "Can't run Job", f"Job {job.params['name']} is disabled.")
            return
        self._worker = JobLogWorker(job, self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.start_thread(self._worker)

    def run_all_jobs(self):
        project = self.project()
        self._worker = ProjectLogWorker(project, self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.start_thread(self._worker)

    def stop(self):
        if self._worker:
            self._worker.stop()

    def _connect_worker_signals(self, worker):
        worker.status_signal.connect(self._handle_status_signal, Qt.ConnectionType.UniqueConnection)
        worker.end_signal.connect(self._handle_worker_end, Qt.ConnectionType.UniqueConnection)

    def _handle_status_signal(self, message, _status, _error_message, timeout):
        self.show_status_message_requested.emit(message, timeout)

    def _handle_status_update(self, message, _status, _error_message, _progress):
        self.console_area.handle_html_message(f"<b>{message}</b>")

    def _handle_worker_end(self, _status, _id_str, _message):
        self.console_area.handle_html_message("-" * 80)
        # if status == constants.RUN_COMPLETED:
        #     self.console_area.handle_html_message(
        #         f"<b style='color:green'>✓ Completed: {message}</b>")
        # elif status == constants.RUN_STOPPED:
        #     self.console_area.handle_html_message(
        #         f"<b style='color:orange'>⏹ Stopped: {message}</b>")
        # elif status == constants.RUN_FAILED:
        #     self.console_area.handle_html_message(
        #         f"<b style='color:red'>✗ Failed: {message}</b>")
        self._worker = None

    def quit(self):
        return True

    def change_theme(self, dark_theme):
        self.dark_theme = dark_theme
        for job_widget in self.job_widgets:
            job_widget.set_dark_theme(dark_theme)

    def current_job_index(self):
        return self.selected_job_index

    def refresh_and_set_status(self, _status):
        self.refresh_ui()

    def refresh_and_select_job(self, _job_idx):
        self.refresh_ui()

    def select_first_job(self):
        if self.job_widgets:
            self._select_job_widget(self.job_widgets[0])
