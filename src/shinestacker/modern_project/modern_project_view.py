# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea
from PySide6.QtCore import Qt
from .. gui.project_view import ProjectView
from .. gui.gui_logging import QTextEditLogger
from .job_widget import JobWidget


class ModernProjectView(ProjectView):
    def __init__(self, project_holder, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, dark_theme, parent)
        self.job_widgets = []
        self.scroll_content = None
        self.project_layout = None
        self._setup_ui()

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.project_layout = QVBoxLayout(self.scroll_content)
        self.project_layout.setAlignment(Qt.AlignTop)
        scroll_area.setWidget(self.scroll_content)
        main_splitter.addWidget(scroll_area)
        self.console_area = QTextEditLogger(self)
        self.add_gui_logger(self.console_area)
        console_layout = QVBoxLayout(self.console_area)
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

    def clear_job_list(self):
        for widget in self.job_widgets:
            widget.deleteLater()
        self.job_widgets.clear()
        if self.project_layout:
            while self.project_layout.count():
                item = self.project_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def add_job_widget(self, job):
        job_name = job.params['name']
        job_widget = JobWidget(job_name)
        self.job_widgets.append(job_widget)
        self.project_layout.addWidget(job_widget)

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

    def current_job_index(self):
        return 0

    def refresh_ui(self):
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)

    def refresh_and_set_status(self, _status):
        self.refresh_ui()

    def refresh_and_select_job(self, _job_idx):
        self.refresh_ui()

    def select_first_job(self):
        pass
