# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel
from PySide6.QtCore import Qt
from .. gui.base_project_view import BaseProjectView
from .. gui.gui_logging import QTextEditLogger


class ModernProjectView(BaseProjectView):
    def __init__(self, dark_theme, parent=None):
        super().__init__(dark_theme, parent)
        self._setup_ui()

    def _setup_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        project_area = QWidget()
        project_layout = QVBoxLayout(project_area)
        project_layout.addWidget(QLabel("Modern Project Area"))
        main_splitter.addWidget(project_area)
        self.console_area = QTextEditLogger(self)
        self.add_gui_logger(self.console_area)
        console_layout = QVBoxLayout(self.console_area)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.addWidget(self.console_area.text_edit)
        main_splitter.addWidget(self.console_area)
        main_splitter.setSizes([600, 200])
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(main_splitter)
        ico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "gui", "ico", "shinestacker.png")
        self.console_area.handle_html_message(
            "<h3>ShineStacker console</h3>"
            f"<p><img width=100 src='{ico_path}'></p>"
            "<hr>")

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

    def refresh_ui(self):
        BaseProjectView.refresh_ui(self)
