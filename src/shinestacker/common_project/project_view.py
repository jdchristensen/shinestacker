# pylint: disable=C0114, C0115, C0116, E0611, R0902, E1101, W0718, R0904
import os
import subprocess
import traceback
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QDialog, QMenu, QMessageBox
from .. core.core_utils import running_under_windows, running_under_macos
from .. config.constants import constants
from .. gui.gui_logging import LogManager
from .. gui.action_config_dialog import ActionConfigDialog
from .. gui.project_model import (
    get_action_working_path, get_action_input_path, get_action_output_path)
from .project_handler import ProjectHandler


class ProjectView(QWidget, LogManager, ProjectHandler):
    refresh_ui_signal = Signal()
    enable_sub_actions_requested = Signal(bool)
    widget_deleted_signal = Signal(tuple)
    widget_cloned_signal = Signal(tuple)
    widget_pasted_signal = Signal(tuple)
    widget_moved_up_signal = Signal(tuple)
    widget_moved_down_signal = Signal(tuple)
    widget_added_signal = Signal(tuple)
    widget_enable_signal = Signal(tuple, bool)
    widget_enable_all_signal = Signal(bool)
    widget_updated_signal = Signal(tuple)
    run_finished_signal = Signal()
    fill_context_menu_signal = Signal(object, bool)
    current_action_working_path = None
    current_action_input_path = None
    current_action_output_path = None
    browse_working_path_action = None
    browse_input_path_action = None
    browse_output_path_action = None
    job_retouch_path_action = None
    action_dialog = None

    def __init__(self, project_holder, dark_theme, parent=None):
        ProjectHandler.__init__(self, project_holder)
        QWidget.__init__(self, parent)
        LogManager.__init__(self)
        self.dark_theme = dark_theme
        self._setup_common_menu_actions()

    def _setup_common_menu_actions(self):
        pass

    def edit_current_action(self):
        current_action = self.get_current_selected_action()
        if current_action is not None:
            self.edit_action(current_action)

    def get_current_selected_action(self):
        raise NotImplementedError

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
        if self.current_action_working_path:
            self.browse_path(self.current_action_working_path)

    def browse_input_path(self):
        if self.current_action_input_path:
            self.browse_path(self.current_action_input_path)

    def browse_output_path(self):
        if self.current_action_output_path:
            self.browse_path(self.current_action_output_path)

    def run_retouch_path(self, _job, retouch_path):
        def find_parent(widget, class_name):
            current = widget
            while current is not None:
                if current.objectName() == class_name:
                    return current
                current = current.parent()
            return None
        parent = find_parent(self, "mainWindow")
        if parent:
            if hasattr(parent, 'retouch_callback'):
                parent.retouch_callback(retouch_path)
            else:
                self._show_retouch_error(
                    "Main window found but has no retouch_callback")
        else:
            self._show_retouch_error(
                "Cannot find main window. "
                "Ensure MainWindow has objectName='mainWindow'")

    def _show_retouch_error(self, message):
        QMessageBox.warning(self, "Retouch Error",
                            f"{message}\n\nRetouch functionality may not be available.")

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

    def create_common_context_menu(self, current_action):
        menu = QMenu(self)
        edit_config_action = QAction("Edit configuration", self)
        edit_config_action.triggered.connect(self.edit_current_action)
        menu.addAction(edit_config_action)
        self.fill_context_menu_signal.emit(menu, current_action.enabled())
        try:
            self._add_path_browsing_actions(menu, current_action)
        except Exception:
            traceback.print_exc()
            QMessageBox.warning(
                self, "Missing Configuration",
                f"Job '{current_action.params.get('name', 'Unnamed')}' "
                "has no working path specified.\n"
                "Please edit the job configuration to set a working path."
            )
        return menu

    def _add_path_browsing_actions(self, menu, current_action):
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
                    lambda: self.run_retouch_path(current_action, retouch_path))
                menu.addAction(self.job_retouch_path_action)

    def edit_action(self, action):
        self.action_dialog = ActionConfigDialog(
            action, self.current_file_directory(), self.parent())
        if self.action_dialog.exec() == QDialog.Accepted:
            self.mark_as_modified(True, "Edit Action")
            self.refresh_ui()

    def refresh_ui(self):
        self.refresh_ui_signal.emit()

    def validate_output_paths_for_job(self, job):
        path_counter = {}
        duplicates = []
        for action_idx, action in enumerate(job.sub_actions):
            output_path = get_action_output_path(action)[0]
            if output_path:
                norm_path = os.path.normpath(output_path)
                if norm_path in path_counter:
                    path_counter[norm_path].append(action_idx)
                else:
                    path_counter[norm_path] = [action_idx]
        for path, indices in path_counter.items():
            if len(indices) > 1:
                action_names = [job.sub_actions[idx].params.get(
                    'name', f'Action {idx}') for idx in indices]
                duplicates.append({
                    'path': path,
                    'indices': indices,
                    'action_names': action_names
                })
        return {
            'valid': len(duplicates) == 0,
            'job_name': job.params.get('name', 'Unnamed Job'),
            'duplicates': duplicates
        }

    def validate_output_paths_for_project(self):
        all_duplicates = []
        for job_idx, job in enumerate(self.project().jobs):
            job_result = self.validate_output_paths_for_job(job)
            for dup in job_result['duplicates']:
                dup['job_idx'] = job_idx
                dup['job_name'] = job_result['job_name']
                all_duplicates.append(dup)
        return {'valid': len(all_duplicates) == 0, 'duplicates': all_duplicates}

    def show_validation_warning(self, validation_result, is_single_job=True):
        msg_box = QMessageBox(self.parent() if self.parent() else self)
        msg_box.setIcon(QMessageBox.Warning)
        if is_single_job:
            msg_box.setWindowTitle(
                f"Duplicate Output Paths in '{validation_result['job_name']}'")
            msg_text = f"Job '{validation_result['job_name']}' has " \
                       f"{len(validation_result['duplicates'])} duplicate output path(s)."
        else:
            msg_box.setWindowTitle("Duplicate Output Paths in Project")
            msg_text = f"Project has {len(validation_result['duplicates'])} " \
                       "duplicate output path(s)."
        msg_box.setText(msg_text + "\n\nThis may cause data overwrites "
                        "and progress tracking issues.\n\nDo you want to continue anyway?")
        details = "Duplicate output paths:\n"
        for dup in validation_result['duplicates']:
            if is_single_job:
                details += f"\n• Path: {dup['path']}\n"
                for idx, name in zip(dup['indices'], dup['action_names']):
                    details += f"  - Action {idx + 1}: {name}\n"
            else:
                details += f"\n• Path: {dup['path']}\n"
                details += f"  - {dup['job_name']} > "
                for idx, name in zip(dup['indices'], dup['action_names']):
                    details += f"{name} (Action {idx}), "
                details = details.rstrip(", ") + "\n"
        msg_box.setDetailedText(details)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        result = msg_box.exec()
        return result == QMessageBox.Yes

    def save_current_selection(self):
        raise NotImplementedError

    def restore_saved_selection(self):
        raise NotImplementedError

    def refresh_and_restore_selection(self):
        raise NotImplementedError

    def move_element_up(self, selection=None, update_project=True):
        self.shift_element(-1, "Up", selection, update_project)

    def move_element_down(self, selection=None, update_project=True):
        self.shift_element(+1, "Down", selection, update_project)

    def _get_current_position_tuple(self):
        if self.selection_state.is_job_selected():
            return (self.selection_state.job_index, -1, -1)
        if self.selection_state.is_action_selected():
            return (self.selection_state.job_index, self.selection_state.action_index, -1)
        if self.selection_state.is_subaction_selected():
            return (self.selection_state.job_index, self.selection_state.action_index,
                    self.selection_state.subaction_index)
        return (-1, -1, -1)

    def enforce_stop_run(self):
        pass
