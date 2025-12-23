# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
import os
import subprocess
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QMessageBox, QMenu, QApplication)
from PySide6.QtCore import Qt
from .. config.constants import constants
from .. core.core_utils import running_under_windows, running_under_macos
from .. gui.project_model import (
    get_action_working_path, get_action_input_path, get_action_output_path)
from .. gui.project_converter import ProjectConverter
from .. gui.base_project_view import BaseProjectView
from .. gui.colors import ColorPalette
from .tab_widget import TabWidgetWithPlaceholder
from .gui_run import RunWindow, RunWorker


class JobLogWorker(RunWorker):
    def __init__(self, job, id_str):
        super().__init__(id_str)
        self.job = job
        self.tag = "Job"

    def do_run(self):
        converter = ProjectConverter(self.plot_manager)
        return converter.run_job(self.job, self.id_str, self.callbacks)


class ProjectLogWorker(RunWorker):
    def __init__(self, project, id_str):
        super().__init__(id_str)
        self.project = project
        self.tag = "Project"

    def do_run(self):
        converter = ProjectConverter(self.plot_manager)
        return converter.run_project(self.project, self.id_str, self.callbacks)


class ClassicProjectView(BaseProjectView):
    def __init__(self, project_editor, project_controller, dark_theme, parent=None):
        super().__init__(dark_theme, parent)
        self.project_editor = project_editor
        self.project_controller = project_controller
        self.tab_widget = TabWidgetWithPlaceholder(dark_theme)
        self.tab_widget.resize(1000, 500)
        self._windows = []
        self._workers = []
        self.current_action_working_path = None
        self.current_action_input_path = None
        self.current_action_output_path = None
        self.browse_working_path_action = None
        self.browse_input_path_action = None
        self.browse_output_path_action = None
        self.job_retouch_path_action = None
        self.style_light = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.DARK_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.DARK_RED.hex()}; }}
        """
        self.style_dark = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.LIGHT_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.LIGHT_RED.hex()}; }}
        """
        self.list_style_sheet_light = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.LIGHT_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #F0F0F0;
            }}
        """
        self.list_style_sheet_dark = f"""
            QListWidget::item:selected {{
                background-color: #{ColorPalette.DARK_BLUE.hex()};
            }}
            QListWidget::item:hover {{
                background-color: #303030;
            }}
        """
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        h_splitter = QSplitter(Qt.Orientation.Vertical)
        top_widget = QWidget()
        h_layout = QHBoxLayout(top_widget)
        h_layout.setContentsMargins(10, 0, 10, 10)
        vbox_left = QVBoxLayout()
        vbox_left.setSpacing(4)
        vbox_left.addWidget(QLabel("Jobs"))
        vbox_left.addWidget(self.job_list())
        vbox_right = QVBoxLayout()
        vbox_right.setSpacing(4)
        vbox_right.addWidget(QLabel("Actions"))
        vbox_right.addWidget(self.action_list())
        h_layout.addLayout(vbox_left)
        h_layout.addLayout(vbox_right)
        h_splitter.addWidget(top_widget)
        h_splitter.addWidget(self.tab_widget)
        self.setLayout(layout)
        layout.addWidget(h_splitter)

    def _connect_signals(self):
        self.job_list().currentRowChanged.connect(
            self.project_editor.on_job_selected)
        self.job_list().itemSelectionChanged.connect(
            self.parent().update_delete_action_state)
        self.action_list().itemSelectionChanged.connect(
            self.parent().update_delete_action_state)

    def job_list(self):
        return self.project_editor.job_list()

    def action_list(self):
        return self.project_editor.action_list()

    def current_job_index(self):
        return self.project_editor.current_job_index()

    def project_jobs(self):
        return self.project_editor.project_jobs()

    def project_job(self, i):
        return self.project_editor.project_job(i)

    def num_project_jobs(self):
        return self.project_editor.num_project_jobs()

    def get_action_at(self, action_row):
        return self.project_editor.get_action_at(action_row)

    def edit_current_action(self):
        self.project_controller.edit_current_action()

    def set_current_job(self, index):
        return self.project_editor.set_current_job(index)

    def set_current_action(self, index):
        return self.project_editor.set_current_action(index)

    def action_text(self, action, is_sub_action=False, indent=True, long_name=False, html=False):
        return self.project_editor.action_text(action, is_sub_action, indent, long_name, html)

    def job_text(self, job, long_name=False, html=False):
        return self.project_editor.job_text(job, long_name, html)

    def get_tab_widget(self):
        return self.tab_widget

    def get_tab_and_position(self, id_str):
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if w.id_str() == id_str:
                return i, w
        return None, None

    def get_tab_at_position(self, id_str):
        _i, w = self.get_tab_and_position(id_str)
        return w

    def get_tab_position(self, id_str):
        i, _w = self.get_tab_and_position(id_str)
        return i

    def set_style_sheet(self, dark_theme):
        list_style_sheet = self.list_style_sheet_dark \
            if dark_theme else self.list_style_sheet_light
        self.job_list().setStyleSheet(list_style_sheet)
        self.action_list().setStyleSheet(list_style_sheet)

    def refresh_ui(self, job_row=-1, action_row=-1):
        self.project_editor.clear_job_list()
        for job in self.project_editor.project_jobs():
            self.project_editor.add_list_item(self.job_list(), job, False)
        if self.project_editor.project_jobs():
            self.project_editor.set_current_job(0)
        if job_row >= 0:
            self.project_editor.set_current_job(job_row)
        if action_row >= 0:
            self.project_editor.set_current_action(action_row)

    def create_new_window(self, title, labels, retouch_paths):
        new_window = RunWindow(labels,
                               lambda id_str: self.stop_worker(self.get_tab_position(id_str)),
                               lambda id_str: self.close_window(self.get_tab_position(id_str)),
                               retouch_paths, self)
        self.tab_widget.addTab(new_window, title)
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        if title is not None:
            new_window.setWindowTitle(title)
        new_window.show()
        self.add_gui_logger(new_window)
        self._windows.append(new_window)
        return new_window, self.last_id_str()

    def close_window(self, tab_position):
        self._windows.pop(tab_position)
        self._workers.pop(tab_position)
        self.tab_widget.removeTab(tab_position)

    def stop_worker(self, tab_position):
        worker = self._workers[tab_position]
        worker.stop()

    def connect_worker_signals(self, worker, window):
        worker.before_action_signal.connect(window.handle_before_action)
        worker.after_action_signal.connect(window.handle_after_action)
        worker.step_counts_signal.connect(window.handle_step_counts)
        worker.begin_steps_signal.connect(window.handle_begin_steps)
        worker.end_steps_signal.connect(window.handle_end_steps)
        worker.after_step_signal.connect(window.handle_after_step)
        worker.save_plot_signal.connect(window.handle_save_plot)
        worker.open_app_signal.connect(window.handle_open_app)
        worker.run_completed_signal.connect(
            lambda run_id: self.handle_run_completed(window, run_id))
        worker.run_stopped_signal.connect(window.handle_run_stopped)
        worker.run_failed_signal.connect(window.handle_run_failed)
        worker.add_status_box_signal.connect(window.handle_add_status_box)
        worker.add_frame_signal.connect(window.handle_add_frame)
        worker.set_total_actions_signal.connect(window.handle_set_total_actions)
        worker.update_frame_status_signal.connect(window.handle_update_frame_status)
        worker.plot_manager.save_plot_signal.connect(window.handle_save_plot_via_manager)

    def run_job(self):
        current_index = self.current_job_index()
        if current_index < 0:
            msg = "No Job Selected" if self.num_project_jobs() > 0 else "No Job Added"
            QMessageBox.warning(self, msg, "Please select a job first.")
            return
        if current_index >= 0:
            job = self.project_job(current_index)
            if job.enabled():
                job_name = job.params["name"]
                labels = [[(self.action_text(a), a.enabled()) for a in job.sub_actions]]
                r = self.get_retouch_path(job)
                retouch_paths = [] if len(r) == 0 else [(job_name, r)]
                new_window, id_str = self.create_new_window(f"{job_name} [⚙️ Job]",
                                                            labels, retouch_paths)
                worker = JobLogWorker(job, id_str)
                self.connect_worker_signals(worker, new_window)
                self.start_thread(worker)
                self._workers.append(worker)
            else:
                QMessageBox.warning(self, "Can't run Job",
                                    "Job " + job.params["name"] + " is disabled.")
                return
        self.menu_manager.stop_action.setEnabled(True)

    def run_all_jobs(self):
        labels = [[(self.action_text(a), a.enabled() and
                    job.enabled()) for a in job.sub_actions] for job in self.project_jobs()]
        project_name = ".".join(self.current_file_name().split(".")[:-1])
        if project_name == '':
            project_name = '[new]'
        retouch_paths = []
        for job in self.project_jobs():
            r = self.get_retouch_path(job)
            if len(r) > 0:
                retouch_paths.append((job.params["name"], r))
        new_window, id_str = self.create_new_window(f"{project_name} [Project]",
                                                    labels, retouch_paths)
        worker = ProjectLogWorker(self.project(), id_str)
        self.connect_worker_signals(worker, new_window)
        self.start_thread(worker)
        self._workers.append(worker)
        self.menu_manager.stop_action.setEnabled(True)

    def stop(self):
        tab_position = self.tab_widget.count()
        self.stop_worker(tab_position - 1)
        self.menu_manager.stop_action.setEnabled(False)

    def do_handle_end_message(self, status, id_str, message):
        self.menu_manager.run_job_action.setEnabled(True)
        self.menu_manager.run_all_jobs_action.setEnabled(True)
        tab = self.get_tab_at_position(id_str)
        tab.close_button.setEnabled(True)
        tab.stop_button.setEnabled(False)
        if hasattr(tab, 'retouch_widget') and tab.retouch_widget is not None:
            tab.retouch_widget.setEnabled(True)

    # pylint: disable=C0103
    def contextMenuEvent(self, event):
        item = self.job_list().itemAt(self.job_list().viewport().mapFrom(self, event.pos()))
        current_action = None
        if item:
            index = self.job_list().row(item)
            current_action = self.project_editor.get_job_at(index)
            self.set_current_job(index)
        item = self.action_list().itemAt(self.action_list().viewport().mapFrom(self, event.pos()))
        if item:
            index = self.action_list().row(item)
            self.set_current_action(index)
            _job_row, _action_row, pos = self.get_action_at(index)
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
        if current_action:
            menu = QMenu(self)
            if current_action.enabled():
                menu.addAction(self.menu_manager.disable_action)
            else:
                menu.addAction(self.menu_manager.enable_action)
            edit_config_action = QAction("Edit configuration")
            edit_config_action.triggered.connect(self.edit_current_action)
            menu.addAction(edit_config_action)
            menu.addSeparator()
            menu.addAction(self.menu_manager.cut_action)
            menu.addAction(self.menu_manager.copy_action)
            menu.addAction(self.menu_manager.paste_action)
            menu.addAction(self.menu_manager.duplicate_action)
            menu.addAction(self.menu_manager.delete_element_action)
            menu.addSeparator()
            menu.addAction(self.menu_manager.run_job_action)
            menu.addAction(self.menu_manager.run_all_jobs_action)
            menu.addSeparator()
            self.current_action_working_path, name = get_action_working_path(current_action)
            if self.current_action_working_path != '' and \
                    os.path.exists(self.current_action_working_path):
                action_name = "Browse Working Path" + (f" > {name}" if name != '' else '')
                self.browse_working_path_action = QAction(action_name)
                self.browse_working_path_action.triggered.connect(self.browse_working_path)
                menu.addAction(self.browse_working_path_action)
            ip, name = get_action_input_path(current_action)
            if ip != '':
                ips = ip.split(constants.PATH_SEPARATOR)
                self.current_action_input_path = constants.PATH_SEPARATOR.join(
                    [f"{self.current_action_working_path}/{ip}" for ip in ips])
                p_exists = False
                for p in self.current_action_input_path.split(constants.PATH_SEPARATOR):
                    if os.path.exists(p):
                        p_exists = True
                        break
                if p_exists:
                    action_name = "Browse Input Path" + (f" > {name}" if name != '' else '')
                    n_files = [f"{len(next(os.walk(p))[2])}"
                               for p in
                               self.current_action_input_path.split(constants.PATH_SEPARATOR)]
                    s = "" if len(n_files) == 1 and n_files[0] == 1 else "s"
                    action_name += " (" + ", ".join(n_files) + f" file{s})"
                    self.browse_input_path_action = QAction(action_name)
                    self.browse_input_path_action.triggered.connect(self.browse_input_path)
                    menu.addAction(self.browse_input_path_action)
            op, name = get_action_output_path(current_action)
            if op != '':
                self.current_action_output_path = f"{self.current_action_working_path}/{op}"
                if os.path.exists(self.current_action_output_path):
                    action_name = "Browse Output Path" + (f" > {name}" if name != '' else '')
                    n_files = len(next(os.walk(self.current_action_output_path))[2])
                    s = "" if n_files == 1 else "s"
                    action_name += f" ({n_files} file{s})"
                    self.browse_output_path_action = QAction(action_name)
                    self.browse_output_path_action.triggered.connect(self.browse_output_path)
                    menu.addAction(self.browse_output_path_action)
            if current_action.type_name == constants.ACTION_JOB:
                retouch_path = self.get_retouch_path(current_action)
                if len(retouch_path) > 0:
                    menu.addSeparator()
                    self.job_retouch_path_action = QAction("Retouch path")
                    self.job_retouch_path_action.triggered.connect(
                        lambda job: self.run_retouch_path(current_action, retouch_path))
                    menu.addAction(self.job_retouch_path_action)
            menu.exec(event.globalPos())
    # pylint: enable=C0103

    def run_retouch_path(self, _job, retouch_path):
        self.retouch_callback(retouch_path)

    def get_retouch_path(self, job):
        frames_path = [get_action_output_path(action)[0]
                       for action in job.sub_actions
                       if action.type_name == constants.ACTION_COMBO]
        bunches_path = [get_action_output_path(action)[0]
                        for action in job.sub_actions
                        if action.type_name == constants.ACTION_FOCUSSTACKBUNCH]
        stack_path = [get_action_output_path(action)[0]
                      for action in job.sub_actions
                      if action.type_name == constants.ACTION_FOCUSSTACK]
        if len(bunches_path) > 0:
            stack_path += [bunches_path[0]]
        elif len(frames_path) > 0:
            stack_path += [frames_path[0]]
        wp = get_action_working_path(job)[0]
        if wp == '':
            raise ValueError("Job has no working path specified.")
        stack_path = [f"{wp}/{s}" for s in stack_path]
        return stack_path

    def handle_run_completed(self, window, run_id):
        window.handle_run_completed(run_id)
        self.menu_manager.stop_action.setEnabled(False)

    def browse_path(self, path):
        ps = path.split(constants.PATH_SEPARATOR)
        for p in ps:
            if os.path.exists(p):
                if running_under_windows():
                    os.startfile(os.path.normpath(p))
                else:
                    cmd = 'open' if running_under_macos() else 'xdg-open'
                    subprocess.run([cmd, p], check=True)

    def browse_working_path(self):
        self.browse_path(self.current_action_working_path)

    def browse_input_path(self):
        self.browse_path(self.current_action_input_path)

    def browse_output_path(self):
        self.browse_path(self.current_action_output_path)

    def quit(self):
        for worker in self._workers:
            worker.stop()
        self.close()
        return True

    def change_theme(self, dark_theme):
        self.dark_theme = dark_theme
        self.menu_manager.change_theme(dark_theme)
        self.tab_widget.change_theme(dark_theme)
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        list_style_sheet = self.list_style_sheet_dark \
            if dark_theme else self.list_style_sheet_light
        self.job_list().setStyleSheet(list_style_sheet)
        self.action_list().setStyleSheet(list_style_sheet)
