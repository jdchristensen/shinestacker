# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=R1716
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea, QDialog, QMessageBox
from PySide6.QtCore import Qt
from .. gui.project_view import ProjectView
from .. gui.gui_logging import QTextEditLogger
from .. gui.action_config_dialog import ActionConfigDialog
from .job_widget import JobWidget


class ModernProjectView(ProjectView):
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
        self._setup_ui()
        self.change_theme(dark_theme)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.action_dialog = None

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
            "<h3>ShineStacker console</h3>"
            f"<p><img width=100 src='{ico_path}'></p>"
            "<hr>")

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
    # pylint: enable=C0103

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

    def _select_action(self, job_index, action_index):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                self._on_widget_clicked(action_widget, 'action', job_index, action_index)

    def _select_subaction(self, job_index, action_index, subaction_index):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            if 0 <= action_index < job_widget.num_child_widgets():
                action_widget = job_widget.child_widgets[action_index]
                if 0 <= subaction_index < action_widget.num_child_widgets():
                    subaction_widget = action_widget.child_widgets[subaction_index]
                    self._on_widget_clicked(
                        subaction_widget, 'subaction', job_index, action_index, subaction_index)

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
            self._ensure_job_visible(new_index)

    def _select_previous_job(self):
        if not self.job_widgets:
            return
        new_index = self.selected_job_index - 1
        if new_index >= 0:
            self._select_job(new_index)
            self._ensure_job_visible(new_index)

    def _reset_selection(self):
        self.selected_widget = None
        self.selected_widget_type = None
        self.selected_job_index = -1
        self.selected_action_index = -1
        self.selected_subaction_index = -1

    def _ensure_job_visible(self, job_index):
        if not self.job_widgets or job_index < 0 or job_index >= len(self.job_widgets):
            return
        job_widget = self.job_widgets[job_index]
        widget_rect = job_widget.geometry()
        widget_top = widget_rect.top()
        widget_bottom = widget_rect.bottom()
        viewport = self.scroll_area.viewport()
        viewport_height = viewport.height()
        scroll_bar = self.scroll_area.verticalScrollBar()
        current_scroll = scroll_bar.value()
        visible_top = current_scroll
        visible_bottom = current_scroll + viewport_height
        if widget_top < visible_top:
            scroll_bar.setValue(widget_top)
        elif widget_bottom > visible_bottom:
            scroll_bar.setValue(widget_bottom - viewport_height)

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
        if action_index is not None:
            self.selected_action_index = action_index
        if subaction_index is not None:
            self.selected_subaction_index = subaction_index
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
                self.refresh_ui()
                self._reset_selection()
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
                        f"Are you sure you want to delete action "
                        f"'{action.params.get('name', '')}'?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                else:
                    reply = None
                if not confirm or reply == QMessageBox.Yes:
                    self.mark_as_modified(True, "Delete Action")
                    deleted_action = job.pop_sub_action(action_index)
                    self.refresh_ui()
                    self._reset_selection()
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
                            f"Are you sure you want to delete sub-action "
                            f"'{subaction.params.get('name', '')}'?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                    else:
                        reply = None
                    if not confirm or reply == QMessageBox.Yes:
                        self.mark_as_modified(True, "Delete Sub-action")
                        deleted_subaction = action.pop_sub_action(subaction_index)
                        self.refresh_ui()
                        self._reset_selection()
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

    def refresh_ui(self):
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)
        if len(self.job_widgets) > 0:
            self._select_job(0)
        else:
            self._reset_selection()

    def get_console_area(self):
        return self.console_area

    def run_job(self):
        pass

    def run_all_jobs(self):
        pass

    def stop(self):
        pass

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
