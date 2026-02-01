# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917
# pylint: disable=R0912, R0915, E1101, R0911, W0613
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QApplication
from .. config.constants import constants
from .. gui.colors import ColorPalette
from .. common_project.run_worker import JobLogWorker, ProjectLogWorker
from .. common_project.project_view import ProjectView
from .. common_project.selection_state import SelectionState
from .tab_widget import TabWidgetWithPlaceholder
from .gui_run import RunWindow
from .list_container import ListContainer, get_action_row


def rows_to_state(project, job_row, action_row):
    if job_row < 0:
        return None
    if action_row < 0:
        state = SelectionState(job_row, -1, -1)
        return state
    job = project.jobs[job_row]
    current_row = -1
    for i, action in enumerate(job.sub_actions):
        current_row += 1
        if current_row == action_row:
            state = SelectionState(job_row, i, -1)
            return state
        if action.sub_actions:
            for sub_idx, _ in enumerate(action.sub_actions):
                current_row += 1
                if current_row == action_row:
                    state = SelectionState(job_row, i, sub_idx)
                    return state
    state = SelectionState(job_row, -1, -1)
    return state


class ClassicProjectView(ProjectView, ListContainer):
    def __init__(self, project_holder, selection_state, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, selection_state, dark_theme, parent)
        ListContainer.__init__(self, dark_theme)
        self.tab_widget = TabWidgetWithPlaceholder(dark_theme)
        self.tab_widget.resize(1000, 500)
        self._windows = []
        self._workers = []
        self.style_light = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.DARK_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.DARK_RED.hex()}; }}
        """
        self.style_dark = f"""
            QLabel[color-type="enabled"] {{ color: #{ColorPalette.LIGHT_BLUE.hex()}; }}
            QLabel[color-type="disabled"] {{ color: #{ColorPalette.LIGHT_RED.hex()}; }}
        """
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        self.set_style_sheet(dark_theme)
        self._setup_ui()

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
        self.job_list().itemDoubleClicked.connect(self.on_job_edit)
        self.job_list().itemDoubleClicked.connect(self._update_selection_state)
        self.action_list().itemDoubleClicked.connect(self.on_action_edit)
        self.action_list().itemDoubleClicked.connect(self._update_selection_state)
        self.job_list().itemClicked.connect(self._update_selection_state)
        self.action_list().itemClicked.connect(self._update_selection_state)
        self.job_list().currentRowChanged.connect(self.on_job_selected)
        self.job_list().itemSelectionChanged.connect(self._update_selection_state)
        self.action_list().itemSelectionChanged.connect(self._update_selection_state)
        self.job_list().itemClicked.connect(self.check_enable_subactions)
        self.action_list().itemClicked.connect(self.check_enable_subactions)

    def connect_signals(
            self, update_delete_action_state, set_enabled_sub_actions_gui,
            edit_selected_element):
        self.job_list().itemSelectionChanged.connect(update_delete_action_state)
        self.action_list().itemSelectionChanged.connect(update_delete_action_state)
        self.enable_sub_actions_requested.connect(set_enabled_sub_actions_gui)
        self.job_list().enter_key_pressed.connect(edit_selected_element)
        self.action_list().enter_key_pressed.connect(edit_selected_element)

    def update_focus_styles(self):
        ListContainer.update_focus_styles(self)

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

    def clear_project(self):
        self.clear_job_list()
        self.clear_action_list()

    def refresh_ui(self, restore_state=None):
        job_row = -1
        action_row = -1
        if restore_state is not None:
            restore_state = restore_state.copy()
            if restore_state.is_job_selected():
                job_row = restore_state.job_index
                action_row = -1
            elif restore_state.is_action_selected() or restore_state.is_subaction_selected():
                job_row = restore_state.job_index
                actions = None
                if job_row >= 0:
                    job = self.project_job(job_row)
                    actions = job.sub_actions if job else None
                action_row = get_action_row(restore_state, actions)
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_list_item(self.job_list(), job, False)
        if self.project_jobs():
            if 0 <= job_row < self.num_project_jobs():
                self.set_current_job(job_row)
                if action_row >= 0:
                    self.set_current_action(action_row)
            else:
                self.set_current_job(0)
        ProjectView.refresh_ui(self)
        if restore_state is not None:
            self.selection_state.copy_from(restore_state)

    def select_first_job(self):
        self.set_current_job(0)

    def select_current(self):
        if self.selection_state.job_index < 0:
            return
        if self.selection_state.action_index >= 0:
            self._action_list.setFocus()
        else:
            self._job_list.setFocus()
        self.update_focus_styles()

    def get_current_action_at(self, job, action_index):
        action_counter = -1
        current_action = None
        is_sub_action = False
        for action in job.sub_actions:
            action_counter += 1
            if action_counter == action_index:
                current_action = action
                break
            if len(action.sub_actions) > 0:
                for sub_action in action.sub_actions:
                    action_counter += 1
                    if action_counter == action_index:
                        current_action = sub_action
                        is_sub_action = True
                        break
                if current_action:
                    break
        return current_action, is_sub_action

    def create_new_window(self, title, labels, retouch_paths):
        new_window = RunWindow(labels,
                               lambda id_str: self.close_window(self.get_tab_position(id_str)),
                               retouch_paths, self)
        self.tab_widget.addTab(new_window, title)
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        if title is not None:
            new_window.setWindowTitle(title)
        new_window.show()
        self.add_gui_logger(new_window)
        self._windows.append(new_window)
        return new_window, new_window.id_str()

    def close_window(self, index):
        if 0 <= index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)
            self.tab_widget.removeTab(index)
            if widget in self._windows:
                self._windows.remove(widget)
            widget.deleteLater()

    def stop_worker(self, index):
        if 0 <= index < len(self._workers):
            worker = self._workers[index]
            worker.stop()
            return True
        return False

    def is_running(self):
        return len(self._workers) > 0 and any(w.is_running() for w in self._workers)

    def _start_job_worker(self, job_index, job):
        self._prepare_job_run_ui(job_index, job)
        id_str = f"job-{job_index}"
        labels = [[(self.action_text(a), a.enabled()) for a in job.sub_actions]]
        new_window, id_str = self.create_new_window(job.params['name'], labels, [])
        worker = JobLogWorker(job, id_str)
        self.connect_worker_signals(worker, new_window)
        self.start_thread(worker)
        self._workers.append(worker)
        return True

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
            lambda run_id: self.handle_run_completed())
        worker.run_stopped_signal.connect(window.handle_run_stopped)
        worker.run_failed_signal.connect(window.handle_run_failed)
        worker.add_status_box_signal.connect(window.handle_add_status_box)
        worker.add_frame_signal.connect(window.handle_add_frame)
        worker.set_total_actions_signal.connect(window.handle_set_total_actions)
        worker.update_frame_status_signal.connect(window.handle_update_frame_status)
        worker.plot_manager.save_plot_signal.connect(window.handle_save_plot_via_manager)

    def start_thread(self, worker):
        worker.start()

    def _start_project_worker(self):
        self._prepare_project_run_ui()
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
        return True

    def _prepare_job_run_ui(self, job_index, job):
        pass

    def _prepare_project_run_ui(self):
        pass

    def stop(self):
        tab_position = self.tab_widget.count()
        if tab_position > 0:
            self.stop_worker(tab_position - 1)
            return True
        return False

    def handle_end_message(self, status, id_str, message):
        tab = self.get_tab_at_position(id_str)
        tab.close_button.setEnabled(True)
        if hasattr(tab, 'retouch_widget') and tab.retouch_widget is not None:
            tab.retouch_widget.setEnabled(True)
        self.run_finished_signal.emit()

    def delete_element(self, old_selection, new_selection):
        self.refresh_ui(new_selection)

    def paste_element(self, old_selection, new_selection):
        self.refresh_ui(new_selection)

    def clone_element(self, old_selection, new_selection):
        self.refresh_ui(new_selection)

    def set_enabled_all(self):
        self.refresh_ui(self.selection_state)

    def set_enabled(self, selection):
        self.refresh_ui(selection)

    def shift_element(self, old_selection, new_selection):
        self.refresh_ui(new_selection)

    def _get_current_subaction_index(self):
        if not self.selection_state.is_subaction_selected():
            return -1
        return self.selection_state.subaction_index

    def current_job_index(self):
        return ListContainer.current_job_index(self)

    def update_added_element(self, new_selection):
        self.refresh_ui(new_selection)

    def update_widget(self, selection):
        self.refresh_ui(selection)

    # pylint: disable=C0103
    def contextMenuEvent(self, event):
        item = self.job_list().itemAt(self.job_list().viewport().mapFrom(self, event.pos()))
        current_action = None
        if item:
            index = self.job_list().row(item)
            current_action = self.get_job_at(index)
            self.set_current_job(index)
        item = self.action_list().itemAt(self.action_list().viewport().mapFrom(self, event.pos()))
        if item:
            index = self.action_list().row(item)
            self.set_current_action(index)
            _job_row, _action_row, pos = self.get_action_at(index)
            current_action = pos.action if not pos.is_sub_action else pos.sub_action
        if current_action:
            menu = self.create_common_context_menu(current_action)
            menu.exec(event.globalPos())
    # pylint: enable=C0103

    def get_job_at(self, index):
        return None if index < 0 else self.project_job(index)

    def check_enable_subactions(self):
        element = self.project_element(*self.selection_state.to_tuple())
        self.enable_sub_actions_requested.emit(
            self.selection_state.is_subaction_selected() or
            element.type_name == constants.ACTION_COMBO)

    def on_job_edit(self, item):
        self.edit_element_signal.emit()

    def on_action_edit(self, item):
        self.edit_element_signal.emit()

    def on_job_selected(self, index):
        self.clear_action_list()
        if 0 <= index < self.num_project_jobs():
            job = self.project_job(index)
            for action in job.sub_actions:
                self.add_list_item(self.action_list(), action, False)
                if len(action.sub_actions) > 0:
                    for sub_action in action.sub_actions:
                        self.add_list_item(self.action_list(), sub_action, True)
            self.select_signal.emit()
        self._update_selection_state()

    def _update_selection_state(self):
        if self.action_list_has_focus() and self.num_selected_actions() > 0:
            _job_row, _action_row, pos = self.get_current_action()
            if pos is not None:
                self.selection_state.set_indices(
                    pos.job_index, pos.action_index, pos.subaction_index)
        elif self.job_list_has_focus() and self.num_selected_jobs() > 0:
            job_idx = self.current_job_index()
            if 0 <= job_idx < self.num_project_jobs():
                self.selection_state.set_indices(job_idx, -1, -1)
        else:
            self.selection_state.reset()

    def _ensure_selected_visible(self):
        pass

    def handle_run_completed(self):
        self.run_finished_signal.emit()

    def quit(self):
        for worker in self._workers:
            worker.stop()
        self.close()
        return True

    def change_theme(self, dark_theme):
        self.dark_theme = dark_theme
        self.tab_widget.change_theme(dark_theme)
        QApplication.instance().setStyleSheet(
            self.style_dark if dark_theme else self.style_light)
        self.set_style_sheet(dark_theme)

    def perform_undo(self, entry, old_selection):
        if entry:
            old_position = entry.get('old_position', (-1, -1, -1))
            restore_state = SelectionState(*old_position)
            self.refresh_ui(restore_state)

    def perform_redo(self, entry, old_selection):
        if entry:
            new_position = entry.get('new_position', (-1, -1, -1))
            restore_state = SelectionState(*new_position)
            self.refresh_ui(restore_state)
