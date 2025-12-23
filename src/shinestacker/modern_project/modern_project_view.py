# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea, QDialog
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
        self.selected_job_index = 0
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
            self._select_previous_job()
            event.accept()
        elif key == Qt.Key_Down:
            self._select_next_job()
            event.accept()
        elif key == Qt.Key_Home:
            self._select_first_job()
            event.accept()
        elif key == Qt.Key_End:
            self._select_last_job()
            event.accept()
        elif key == Qt.Key_Tab:
            super().keyPressEvent(event)
        elif key == Qt.Key_Backtab:  # Shift+Tab
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
    # pylint: enable=C0103

    def _select_previous_job(self):
        if not self.job_widgets:
            return
        new_index = self.selected_job_index - 1
        if new_index >= 0:
            self._select_job_widget(self.job_widgets[new_index])
            self._ensure_job_visible(new_index)

    def _select_next_job(self):
        if not self.job_widgets:
            return
        new_index = self.selected_job_index + 1
        if new_index < len(self.job_widgets):
            self._select_job_widget(self.job_widgets[new_index])
            self._ensure_job_visible(new_index)

    def _select_first_job(self):
        if self.job_widgets:
            self._select_job_widget(self.job_widgets[0])
            self._ensure_job_visible(0)

    def _select_last_job(self):
        if self.job_widgets:
            last_index = len(self.job_widgets) - 1
            self._select_job_widget(self.job_widgets[last_index])
            self._ensure_job_visible(last_index)

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
        job_name = job.params['name']
        job_widget = JobWidget(job_name, self.dark_theme)
        job_widget.setFocusPolicy(Qt.StrongFocus)
        job_widget.clicked.connect(lambda w=job_widget: self._on_job_clicked(w))
        job_index = len(self.job_widgets)
        job_widget.double_clicked.connect(
            lambda idx=job_index: self._on_job_double_clicked(idx)
        )
        self.job_widgets.append(job_widget)
        self.project_layout.addWidget(job_widget)
        if len(self.job_widgets) == 1:
            self._select_job_widget(job_widget)

    def _on_job_clicked(self, clicked_widget):
        self._select_job_widget(clicked_widget)
        self.setFocus()

    def _on_job_double_clicked(self, job_index):
        job = self.project_job(job_index)
        self.action_dialog = ActionConfigDialog(job, self.current_file_directory(), self)
        if self.action_dialog.exec() == QDialog.Accepted:
            self._update_job_widget(job_index, job)
        self.setFocus()

    def _update_job_widget(self, job_index, job):
        if 0 <= job_index < len(self.job_widgets):
            job_widget = self.job_widgets[job_index]
            job_widget.set_job_name(job.params['name'])

    def _select_job_widget(self, widget):
        for i, job_widget in enumerate(self.job_widgets):
            if job_widget == widget:
                job_widget.set_selected(True)
                self.selected_job_index = i
            else:
                job_widget.set_selected(False)

    def refresh_ui(self):
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)

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
