# pylint: disable=C0114, C0115, C0116, E0611, R0902, R0904, R0913, R0914, R0917, R0912, R0915, E1101
# pylint: disable=R1716, C0302, R0911, R0903, W0718, W0613, R0801, R1702
import os
from functools import partial
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea
from .. gui.gui_logging import QTextEditLogger
from .. config.constants import constants
from .. common_project.run_worker import JobLogWorker, ProjectLogWorker
from .. common_project.project_view import ProjectView
from .. common_project.selection_state import SelectionState
from .. common_project.element_action_manager import CLONE_POSTFIX
from .job_widget import JobWidget
from .progress_mapper import ProgressMapper
from .progress_signal_handler import ProgressSignalHandler, SignalConnector
from .selection_navigation_manager import SelectionNavigationManager
from .action_widget import ActionWidget
from .sub_action_widget import SubActionWidget


class ModernProjectView(ProjectView):
    update_delete_action_state_requested = Signal()
    show_status_message_requested = Signal(str, int)

    def __init__(self, project_holder, selection_state, dark_theme, parent=None):
        ProjectView.__init__(self, project_holder, selection_state, dark_theme, parent)
        self.job_widgets = []
        self.scroll_area = None
        self.scroll_content = None
        self.project_layout = None
        self.selected_widget = None
        self.show_status_message = None
        self._worker = None
        self.progress_mapper = ProgressMapper()
        self.actions_layout_horizontal = False
        self.subactions_layout_vertical = False
        self.progress_handler = ProgressSignalHandler(
            self.progress_mapper,
            self._find_widget,
            self._scroll_to_widget
        )
        self.selection_nav = SelectionNavigationManager(
            self.project_holder,
            self.selection_state,
            self._selection_callback
        )
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

    def _select_widget(self, state):
        if not state or not state.is_valid():
            return
        widget = self._find_widget(state)
        if not widget:
            return
        if self.selected_widget:
            self.selected_widget.set_selected(False)
        widget.set_selected(True)
        self.selected_widget = widget
        self.selection_state.copy_from(state)
        self.update_delete_action_state_requested.emit()
        self._ensure_selected_visible()

    def _selection_callback(self, widget_type, job_index, action_index=-1, subaction_index=-1):
        state = SelectionState(job_index, action_index, subaction_index)
        self._select_widget(state)

    def connect_signals(self, update_delete_action_state, show_status_message, enable_sub_actions):
        self.update_delete_action_state_requested.connect(update_delete_action_state)
        self.show_status_message_requested.connect(show_status_message)
        self.enable_sub_actions_requested.connect(enable_sub_actions)

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
        key_map = {
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Home: "home",
            Qt.Key_End: "end"
        }
        if key in key_map:
            if self.selection_nav.handle_key_navigation(key_map[key]):
                event.accept()
                return
        if key in [Qt.Key_Return, Qt.Key_Enter]:
            self.edit_element_signal.emit()
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

    def _build_progress_mapping(self, job_indices=None):
        self.progress_mapper.build_mapping(self.project(), job_indices)

    def _find_widget(self, state):
        if not state or not state.is_valid():
            return None
        if not 0 <= state.job_index < len(self.job_widgets):
            return None
        job_widget = self.job_widgets[state.job_index]
        if state.is_job_selected():
            return job_widget
        if not 0 <= state.action_index < len(job_widget.child_widgets):
            return None
        action_widget = job_widget.child_widgets[state.action_index]
        if state.is_action_selected():
            return action_widget
        if not 0 <= state.subaction_index < len(action_widget.child_widgets):
            return None
        return action_widget.child_widgets[state.subaction_index]

    def _scroll_to_widget(self, widget):
        if not widget or not self.scroll_area:
            return
        if not widget.isVisible() or widget.height() == 0:
            QTimer.singleShot(10, lambda: self._scroll_to_widget(widget))
            return
        viewport_height = self.scroll_area.viewport().height()
        widget_height = widget.height()
        if widget_height <= viewport_height:
            y_margin = (viewport_height - widget_height) // 2
        else:
            y_margin = 0
        self.scroll_area.ensureWidgetVisible(widget, 0, y_margin)

    def _reset_selection(self):
        self.selected_widget = None
        self.selection_state.reset()

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
        self.selection_state.job_index = 0
        self.selected_widget = None

    def clear_project(self):
        self.clear_job_list()
        self._reset_selection()
        self.update_delete_action_state_requested.emit()

    def add_job_widget(self, job):
        job_widget = JobWidget(job, self.dark_theme,
                               self.actions_layout_horizontal,
                               self.subactions_layout_vertical)
        job_widget.setFocusPolicy(Qt.NoFocus)
        job_index = len(self.job_widgets)
        job_widget.clicked.connect(
            lambda checked=False, w=job_widget, idx=job_index:
                self._on_widget_clicked(w, idx)
        )
        job_widget.double_clicked.connect(self.edit_element_signal.emit)
        job_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
        self.job_widgets.append(job_widget)
        self.project_layout.addWidget(job_widget)
        for action_idx, action_widget in enumerate(job_widget.child_widgets):
            def make_action_click_handler(j_idx, a_idx, widget):
                def handler():
                    self._on_widget_clicked(widget, j_idx, a_idx)
                return handler
            action_widget.clicked.connect(
                make_action_click_handler(job_index, action_idx, action_widget))
            action_widget.double_clicked.connect(self.edit_element_signal.emit)
            action_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
            for subaction_idx, subaction_widget in enumerate(action_widget.child_widgets):
                def make_subaction_click_handler(j_idx, a_idx, s_idx, widget):
                    def handler():
                        self._on_widget_clicked(widget, j_idx, a_idx, s_idx)
                    return handler
                subaction_widget.clicked.connect(
                    make_subaction_click_handler(
                        job_index, action_idx, subaction_idx, subaction_widget)
                )
                subaction_widget.double_clicked.connect(self.edit_element_signal.emit)
                subaction_widget.enabled_toggled.connect(self._on_widget_enabled_toggled)
        if len(self.job_widgets) == 1:
            self._on_widget_clicked(job_widget, 0)

    def _safe_disconnect(self, signal, slot):
        try:
            signal.disconnect(slot)
        except TypeError:
            pass

    # pylint: disable=W0212
    def _refresh_job_widget_signals(self):
        signal_types = ["clicked", "double_clicked", "enabled_toggled"]

        def disconnect_signals(widget):
            for signal in signal_types:
                try:
                    signal_obj = getattr(widget, signal)
                    if signal_obj:
                        try:
                            signal_obj.disconnect()
                        except TypeError:
                            pass
                except AttributeError:
                    pass

        def connect_widget_signals(widget, widget_type, indices):
            widget._slots = {}
            if widget_type == "job":
                j_idx = indices[0]
                widget._slots["clicked"] = partial(self._on_widget_clicked, widget, j_idx)
                widget._slots["double_clicked"] = self.edit_element_signal.emit
            elif widget_type == "action":
                j_idx, a_idx = indices
                widget._slots["clicked"] = partial(
                    self._on_widget_clicked, widget, j_idx, a_idx)
                widget._slots["double_clicked"] = self.edit_element_signal.emit
            else:
                j_idx, a_idx, s_idx = indices
                widget._slots["clicked"] = partial(
                    self._on_widget_clicked, widget, j_idx, a_idx, s_idx)
                widget._slots["double_clicked"] = self.edit_element_signal.emit
            widget._slots["enabled_toggled"] = self._on_widget_enabled_toggled
            for signal in signal_types:
                getattr(widget, signal).connect(widget._slots[signal])
            widget._signals_connected = True

        for j_idx, job_widget in enumerate(self.job_widgets):
            disconnect_signals(job_widget)
            for action_widget in job_widget.child_widgets:
                disconnect_signals(action_widget)
                for subaction_widget in action_widget.child_widgets:
                    disconnect_signals(subaction_widget)
            connect_widget_signals(job_widget, "job", (j_idx,))
            for a_idx, action_widget in enumerate(job_widget.child_widgets):
                connect_widget_signals(action_widget, "action", (j_idx, a_idx))
                for s_idx, subaction_widget in enumerate(action_widget.child_widgets):
                    connect_widget_signals(subaction_widget, "subaction", (j_idx, a_idx, s_idx))
    # pylint: enable=W0212

    def _refresh_after_structure_change(self):
        self._refresh_job_widget_signals()

    def _on_widget_clicked(self, widget, job_index, action_index=-1, subaction_index=-1):
        if self.selected_widget:
            self.selected_widget.set_selected(False)
        widget.set_selected(True)
        self.selected_widget = widget
        self.selection_state.from_tuple((job_index, action_index, subaction_index))
        self.update_delete_action_state_requested.emit()
        element = self.project_element(job_index, action_index, subaction_index)
        self.enable_sub_actions_requested.emit(element.type_name == constants.ACTION_COMBO)
        self.setFocus()

    def _update_widget(self, selection, element):
        if not selection.is_valid():
            return
        widget = self._find_widget(selection)
        widget.update(element)

    def _select_job_widget(self, widget):
        for i, job_widget in enumerate(self.job_widgets):
            if job_widget == widget:
                job_widget.set_selected(True)
                self.selection_state.job_index = i
            else:
                job_widget.set_selected(False)

    def delete_element(self, old_selection, new_selection):
        widget_state = None
        if old_selection and old_selection.is_valid():
            widget = self._find_widget(old_selection)
            if widget:
                widget_state = widget.capture_widget_state()
        if old_selection:
            self._remove_widget(old_selection)
        if new_selection:
            self.selection_state.copy_from(new_selection)
            self.selection_nav.restore_selection(new_selection)
            self._ensure_selected_visible()
        else:
            self._reset_selection()
        if widget_state and self.undo_manager():
            self.undo_manager().add_extra_data_to_last_entry(
                'modern_widget_state', widget_state)

    def paste_element(self, old_selection, new_selection):
        try:
            job_idx = old_selection.job_index
            if not 0 <= job_idx < self.num_project_jobs():
                return
            if not self.copy_buffer():
                return
            element = self.copy_buffer().clone()
            new_widget = self._insert_widget(new_selection, element)
            if new_widget:
                if self.selected_widget:
                    self.selected_widget.set_selected(False)
                new_widget.set_selected(True)
                self.selected_widget = new_widget
                self._ensure_selected_visible()
                self.selection_state.copy_from(new_selection)
                self.update_delete_action_state_requested.emit()
        except Exception:
            self.refresh_ui()

    def clone_element(self, old_selection, new_selection):
        if not old_selection or not old_selection.is_valid():
            return
        try:
            job_idx = old_selection.job_index
            if not 0 <= job_idx < self.num_project_jobs():
                return
            job = self.project().jobs[job_idx]
            if old_selection.is_job_selected():
                element = self.project_job(job_idx)
            elif old_selection.is_action_selected():
                action_idx = old_selection.action_index
                if not 0 <= action_idx < len(job.sub_actions):
                    return
                element = job.sub_actions[action_idx]
            elif old_selection.is_subaction_selected():
                action_idx = old_selection.action_index
                subaction_idx = old_selection.subaction_index
                if not 0 <= action_idx < len(job.sub_actions):
                    return
                action = job.sub_actions[action_idx]
                if not 0 <= subaction_idx < len(action.sub_actions):
                    return
                element = action.sub_actions[subaction_idx]
            else:
                return
            new_widget = self._insert_widget(
                new_selection, element.clone(name_postfix=CLONE_POSTFIX))
            if new_widget:
                if self.selected_widget:
                    self.selected_widget.set_selected(False)
                new_widget.set_selected(True)
                self.selected_widget = new_widget
                self._ensure_selected_visible()
                self.selection_state.copy_from(new_selection)
                self.update_delete_action_state_requested.emit()
        except Exception:
            self.refresh_ui()

    def _after_set_enabled(self, selection, enabled):
        self.refresh_ui(selection)

    def _update_widget_enable_state(self, selection, enabled):
        widget = self._find_widget(selection)
        if widget:
            widget.set_enabled_and_update(enabled)

    def set_enabled_all(self, enabled):
        for job_widget in self.job_widgets:
            job_widget.set_enabled_and_update(enabled)
            for action_widget in job_widget.child_widgets:
                action_widget.set_enabled_and_update(enabled)
                for subaction_widget in action_widget.child_widgets:
                    subaction_widget.set_enabled_and_update(enabled)

    def _move_widgets(self, from_state, to_state):
        try:
            if from_state.is_job_selected() and to_state.is_job_selected():
                if not (0 <= from_state.job_index < len(self.job_widgets) and
                        0 <= to_state.job_index < len(self.job_widgets)):
                    self.refresh_ui()
                    return
                job_widgets = self.job_widgets
                project_layout = self.project_layout
                project_layout.removeWidget(job_widgets[from_state.job_index])
                project_layout.removeWidget(job_widgets[to_state.job_index])
                a, b = from_state.job_index, to_state.job_index
                job_widgets[a], job_widgets[b] = job_widgets[b], job_widgets[a]
                insert_first = min(a, b)
                insert_second = max(a, b)
                project_layout.insertWidget(insert_first, job_widgets[insert_first])
                project_layout.insertWidget(insert_second, job_widgets[insert_second])
            elif from_state.is_action_selected() and to_state.is_action_selected() and \
                    from_state.job_index == to_state.job_index:
                if not 0 <= from_state.job_index < len(self.job_widgets):
                    self.refresh_ui()
                    return
                job_widget = self.job_widgets[from_state.job_index]
                child_widgets = job_widget.child_widgets
                if not (0 <= from_state.action_index < len(child_widgets) and
                        0 <= to_state.action_index < len(child_widgets)):
                    self.refresh_ui()
                    return
                job_widget.child_container_layout.removeWidget(
                    child_widgets[from_state.action_index])
                job_widget.child_container_layout.removeWidget(
                    child_widgets[to_state.action_index])
                a, b = from_state.action_index, to_state.action_index
                child_widgets[a], child_widgets[b] = child_widgets[b], child_widgets[a]
                insert_first = min(a, b)
                insert_second = max(a, b)
                job_widget.child_container_layout.insertWidget(
                    insert_first, child_widgets[insert_first])
                job_widget.child_container_layout.insertWidget(
                    insert_second, child_widgets[insert_second])
            elif from_state.is_subaction_selected() and to_state.is_subaction_selected() and \
                    from_state.job_index == to_state.job_index and \
                    from_state.action_index == to_state.action_index:
                if not 0 <= from_state.job_index < len(self.job_widgets):
                    self.refresh_ui()
                    return
                job_widget = self.job_widgets[from_state.job_index]
                if not 0 <= from_state.action_index < len(job_widget.child_widgets):
                    self.refresh_ui()
                    return
                action_widget = job_widget.child_widgets[from_state.action_index]
                child_widgets = action_widget.child_widgets
                if not (0 <= from_state.subaction_index < len(child_widgets) and
                        0 <= to_state.subaction_index < len(child_widgets)):
                    self.refresh_ui()
                    return
                action_widget.child_container_layout.removeWidget(
                    child_widgets[from_state.subaction_index])
                action_widget.child_container_layout.removeWidget(
                    child_widgets[to_state.subaction_index])
                a, b = from_state.subaction_index, to_state.subaction_index
                child_widgets[a], child_widgets[b] = child_widgets[b], child_widgets[a]
                insert_first = min(a, b)
                insert_second = max(a, b)
                action_widget.child_container_layout.insertWidget(
                    insert_first, child_widgets[insert_first])
                action_widget.child_container_layout.insertWidget(
                    insert_second, child_widgets[insert_second])
            else:
                self.refresh_ui()
        except Exception:
            self.refresh_ui()

    def _before_shift_element(self):
        return self.enforce_stop_run()

    def shift_element(self, old_selection, new_selection):
        self._move_widgets(old_selection, new_selection)
        self.selection_nav.restore_selection(new_selection)
        self._ensure_selected_visible()
        self._refresh_job_widget_signals()

    def set_style_sheet(self, dark_theme):
        pass

    def _on_widget_enabled_toggled(self, enabled):
        widget = self.sender()
        if not widget:
            return
        self.widget_enable_signal.emit(enabled)

    def set_enabled(self, enabled, selection):
        widget = self._find_widget(selection)
        if widget:
            widget.set_enabled_and_update(enabled)

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

    def current_job_index(self):
        return self.selection_state.job_index

    def _before_add_sub_action(self):
        return self.enforce_stop_run()

    def _update_ui_after_add_sub_action(self, sub_action, position):
        job_index, action_index, insert_index = position
        new_state = SelectionState(job_index, action_index, insert_index)
        subaction_widget = self._insert_widget(new_state, sub_action)
        if subaction_widget:
            self.selection_state.copy_from(new_state)
            if self.selected_widget:
                self.selected_widget.set_selected(False)
            subaction_widget.set_selected(True)
            self.selected_widget = subaction_widget
            self._ensure_selected_visible()
            self._refresh_job_widget_signals()

    def update_added_element(self, indices_tuple):
        job_idx, action_idx, subaction_idx = indices_tuple
        try:
            if not 0 <= job_idx < self.num_project_jobs():
                return False
            job = self.project().jobs[job_idx]
            if subaction_idx != -1:
                if not 0 <= action_idx < len(job.sub_actions):
                    return False
                action = job.sub_actions[action_idx]
                if not 0 <= subaction_idx < len(action.sub_actions):
                    return False
                subaction = action.sub_actions[subaction_idx]
                self._insert_widget(SelectionState(
                    job_idx, action_idx, subaction_idx), subaction)
            elif action_idx != -1:
                if not 0 <= action_idx < len(job.sub_actions):
                    return False
                action = job.sub_actions[action_idx]
                self._insert_widget(SelectionState(job_idx, action_idx), action)
            else:
                self._insert_widget(SelectionState(job_idx), job)
            self.selection_state.copy_from(SelectionState(*indices_tuple))
            self._select_widget(self.selection_state)
            return True
        except Exception:
            pass
        return False

    def update_widget(self, selection):
        if not selection.is_valid():
            return
        widget = self._find_widget(selection)
        if widget is None:
            return
        widget.update()

    def horizontal_actions_layout(self, horizontal=True):
        if self.actions_layout_horizontal != horizontal:
            self.actions_layout_horizontal = horizontal
            for job_widget in self.job_widgets:
                job_widget.set_horizontal_layout(horizontal)
            self.progress_handler.set_horizontal_layout(horizontal)
            txt = "horizontal" if horizontal else "vertical"
            self.vertical_subactions_layout(vertical=horizontal)
            self.show_status_message_requested.emit(f"Actions layout set to {txt}", 2000)

    def vertical_subactions_layout(self, vertical=True):
        if self.subactions_layout_vertical != vertical:
            self.subactions_layout_vertical = vertical
            for job_widget in self.job_widgets:
                for action_widget in job_widget.child_widgets:
                    action_widget.set_horizontal_layout(not vertical)
                    image_horizontal = vertical
                    for subaction_widget in action_widget.child_widgets:
                        subaction_widget.set_image_orientation(image_horizontal)
                    if vertical:
                        action_widget.child_container_layout.setSpacing(5)
                    else:
                        action_widget.child_container_layout.setSpacing(2)

    def refresh_ui(self, restore_state=None):
        old_state = restore_state if restore_state else self.selection_state.copy()
        self.clear_job_list()
        for job in self.project_jobs():
            self.add_job_widget(job)
        ProjectView.refresh_ui(self)
        if old_state:
            self.selection_nav.restore_selection(old_state)
            self._ensure_selected_visible()

    def _safe_disconnect_all(self, widget):
        try:
            if hasattr(widget, 'clicked'):
                widget.clicked.disconnect()
        except Exception:
            pass
        try:
            if hasattr(widget, 'double_clicked'):
                widget.double_clicked.disconnect()
        except Exception:
            pass

    def _remove_widget(self, state):
        if not state.is_valid():
            return False
        try:
            if state.is_job_selected():
                if 0 <= state.job_index < len(self.job_widgets):
                    widget = self.job_widgets.pop(state.job_index)
                    self.project_layout.removeWidget(widget)
                    self._safe_disconnect_all(widget)
                    widget.deleteLater()
                    self._refresh_job_widget_signals()
                    return True
            elif state.is_action_selected():
                if 0 <= state.job_index < len(self.job_widgets) and \
                        0 <= state.action_index < len(
                            self.job_widgets[state.job_index].child_widgets):
                    job_widget = self.job_widgets[state.job_index]
                    action_widget = job_widget.child_widgets.pop(state.action_index)
                    job_widget.child_container_layout.removeWidget(action_widget)
                    self._safe_disconnect_all(action_widget)
                    action_widget.deleteLater()
                    self._refresh_job_widget_signals()
                    return True
            elif state.is_subaction_selected():
                if 0 <= state.job_index < len(self.job_widgets) and \
                        0 <= state.action_index < len(
                            self.job_widgets[state.job_index].child_widgets):
                    job_widget = self.job_widgets[state.job_index]
                    action_widget = job_widget.child_widgets[state.action_index]
                    if 0 <= state.subaction_index < len(action_widget.child_widgets):
                        subaction_widget = action_widget.child_widgets.pop(state.subaction_index)
                        action_widget.child_container_layout.removeWidget(subaction_widget)
                        self._safe_disconnect_all(subaction_widget)
                        subaction_widget.deleteLater()
                        self._refresh_job_widget_signals()
                        return True
        except Exception:
            pass
        return False

    def _insert_widget(self, state, element):
        if not state.is_valid():
            return None
        if state.is_job_selected():
            if 0 <= state.job_index <= len(self.job_widgets):
                job_widget = JobWidget(
                    element, self.dark_theme,
                    self.actions_layout_horizontal,
                    self.subactions_layout_vertical)
                job_widget.setFocusPolicy(Qt.NoFocus)
                job_widget.clicked.connect(
                    lambda: self._on_widget_clicked(job_widget, state.job_index))
                job_widget.double_clicked.connect(self.edit_element_signal.emit)
                self.job_widgets.insert(state.job_index, job_widget)
                self.project_layout.insertWidget(state.job_index, job_widget)
                return job_widget
        elif state.is_action_selected():
            if 0 <= state.job_index < len(self.job_widgets) and \
                    0 <= state.action_index <= len(self.job_widgets[state.job_index].child_widgets):
                job_widget = self.job_widgets[state.job_index]
                action_widget = ActionWidget(
                    element, self.dark_theme, self.subactions_layout_vertical)
                action_widget.clicked.connect(
                    lambda: self._on_widget_clicked(
                        action_widget, state.job_index, state.action_index))
                action_widget.double_clicked.connect(self.edit_element_signal.emit)
                job_widget.child_widgets.insert(state.action_index, action_widget)
                job_widget.child_container_layout.insertWidget(state.action_index, action_widget)
                return action_widget
        elif state.is_subaction_selected():
            if 0 <= state.job_index < len(self.job_widgets) and \
                    0 <= state.action_index < len(self.job_widgets[state.job_index].child_widgets):
                job_widget = self.job_widgets[state.job_index]
                action_widget = job_widget.child_widgets[state.action_index]
                if 0 <= state.subaction_index <= len(action_widget.child_widgets):
                    subaction_widget = SubActionWidget(
                        element, self.dark_theme,
                        horizontal_images=not self.subactions_layout_vertical)
                    subaction_widget.clicked.connect(lambda: self._on_widget_clicked(
                        subaction_widget, state.job_index, state.action_index,
                        state.subaction_index))
                    subaction_widget.double_clicked.connect(self.edit_element_signal.emit())
                    action_widget.child_widgets.insert(state.subaction_index, subaction_widget)
                    action_widget.child_container_layout.insertWidget(
                        state.subaction_index, subaction_widget)
                    return subaction_widget
        return None

    def run_job(self):
        if self.selection_state.is_job_selected():
            self.save_undo_state(self.project().clone(), "Run Job", "run",
                                 (self.selection_state.job_index, -1, -1))
        return self.execute_run_job()

    def run_all_jobs(self):
        self.save_undo_state(self.project().clone(), "Run All Jobs", "run_all")
        return self.execute_run_all_jobs()

    def _start_job_worker(self, job_index, job):
        self._prepare_job_run_ui(job_index, job)
        self._worker = JobLogWorker(job, self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.start_thread(self._worker)
        return True

    def _start_project_worker(self):
        self._prepare_project_run_ui()
        self._worker = ProjectLogWorker(self.project(), self.last_id_str())
        self._connect_worker_signals(self._worker)
        self.start_thread(self._worker)
        return True

    def _prepare_job_run_ui(self, job_index, job):
        self.job_widgets[job_index].clear_all()
        self._build_progress_mapping([job_index])

    def _prepare_project_run_ui(self):
        for job_widget in self.job_widgets:
            job_widget.clear_all()
        self._build_progress_mapping()

    def stop(self):
        if self._worker:
            self._worker.stop()
            return True
        return False

    def is_running(self):
        return self._worker is not None and self._worker.isRunning()

    def _connect_worker_signals(self, worker):
        SignalConnector.connect_worker_signals(worker, self, self.progress_handler)

    def clear_run_metadata(self):
        self.save_undo_state(self.project().clone(), "Clear Run Information", "clear_run_info")
        for job_widget in self.job_widgets:
            self._clear_widget_metadata(job_widget)

    def _clear_widget_metadata(self, widget):
        if widget.data_object and 'widget_state' in widget.data_object.metadata:
            widget.data_object.metadata.pop('widget_state', None)
        if hasattr(widget, 'clear_all'):
            widget.clear_all()
        if hasattr(widget, 'clear_images'):
            widget.clear_images()
        if hasattr(widget, 'clear_frames_status'):
            widget.clear_frames_status()
        if hasattr(widget, 'hide_progress'):
            widget.hide_progress()
        for child in widget.child_widgets:
            self._clear_widget_metadata(child)

    @Slot(str, int, str, int)
    def handle_status_signal(self, message, _status, _error_message, timeout):
        self.show_status_message_requested.emit(message, timeout)

    @Slot(str, int, str, int)
    def handle_status_update(self, message, _status, _error_message, _progress):
        self.console_area.handle_html_message(f"<b>{message}</b>")

    @Slot(int, str, str)
    def handle_worker_end(self, _status, _id_str, _message):
        self.console_area.handle_html_message("-" * 80)
        self._worker = None

    @Slot(int, str)
    def handle_run_completed(self, _run_id, _name):
        self.run_finished_signal.emit()

    def quit(self):
        if self._worker:
            self._worker.stop()
        self.close()
        return True

    def change_theme(self, dark_theme):
        self.dark_theme = dark_theme
        for job_widget in self.job_widgets:
            job_widget.set_dark_theme(dark_theme)

    def refresh_and_select_job(self, job_idx):
        if job_idx < 0 or job_idx >= self.num_project_jobs():
            self.refresh_ui()
            return
        old_job_count = len(self.job_widgets)
        new_job_count = self.num_project_jobs()
        if new_job_count == old_job_count + 1:
            job = self.project_job(job_idx)
            if job:
                self._insert_widget(SelectionState(job_idx), job)
                if 0 <= job_idx < len(self.job_widgets):
                    job_widget = self.job_widgets[job_idx]
                    if self.selected_widget:
                        self.selected_widget.set_selected(False)
                    job_widget.set_selected(True)
                    self.selected_widget = job_widget
                    self.selection_state.set_job(job_idx)
                self._refresh_job_widget_signals()
                self._ensure_selected_visible()
                self.update_delete_action_state_requested.emit()
                return
        self.refresh_ui()
        if 0 <= job_idx < len(self.job_widgets):
            self._select_widget(SelectionState(job_idx))

    def select_first_job(self):
        if self.job_widgets:
            self._select_job_widget(self.job_widgets[0])

    def perform_undo(self, entry, old_selection):
        if entry:
            self.targeted_undo(entry)
            self.selection_nav.restore_selection(
                SelectionState(*entry.get('affected_position', old_selection)[:3]))
        else:
            self.refresh_ui()

    def targeted_undo(self, entry):
        action_type = entry.get('action_type', '')
        position = entry.get('affected_position', (-1, -1, -1))
        if action_type == 'move':
            if len(position) < 6:
                self.refresh_ui()
            else:
                from_position = SelectionState(*position[:3])
                to_position = SelectionState(*position[3:])
                self._undo_move_action(from_position, to_position)
        elif action_type == 'edit_all':
            self._undo_edit_all_action()
        elif action_type in ['run', 'run_all', 'clear_run_info']:
            self.refresh_ui()
        else:
            state = SelectionState(*position)
            if action_type == 'add':
                self._undo_add_action(state)
            elif action_type == 'delete':
                self._undo_delete_action(state, entry.get('modern_widget_state'))
            elif action_type == 'edit':
                self._undo_edit_action(state)
            elif action_type == 'clone':
                self._undo_clone_action(state)
            elif action_type == 'paste':
                self._undo_paste_action(state)
            else:
                self.refresh_ui()

    def _undo_add_action(self, state):
        try:
            self._remove_widget(state)
        except Exception:
            self.refresh_ui()

    def _undo_delete_action(self, selection, widget_state):
        if not selection.is_valid():
            return
        position = selection.to_tuple()
        try:
            if not self.valid_indices(*position):
                return
            element = self.project_element(*position)
            if not element:
                return
            self._insert_widget(selection, element)
            widget = self._find_widget(selection)
            if widget:
                if widget_state:
                    widget.restore_widget_state(widget_state)
                if self.selected_widget:
                    self.selected_widget.set_selected(False)
                widget.set_selected(True)
                self.selected_widget = widget
                self.selection_state.copy_from(selection)
            self._refresh_job_widget_signals()
            self.update_delete_action_state_requested.emit()
        except Exception:
            self.refresh_ui()

    def _undo_edit_action(self, selection):
        position = selection.to_tuple()
        try:
            if not self.valid_indices(*position):
                return
            element = self.project_element(*position)
            if element:
                self._update_widget(selection, element)
        except Exception:
            self.refresh_ui()

    def _undo_move_action(self, from_position, to_position):
        self._move_widgets(from_position, to_position)

    def _undo_edit_all_action(self):
        entry = self.undo_manager().last_entry()
        if not entry or 'item' not in entry:
            self.refresh_ui()
            return
        saved_project = entry['item']
        if not saved_project or not saved_project.jobs:
            self.refresh_ui()
            return
        for job_idx, job_widget in enumerate(self.job_widgets):
            if job_idx < len(saved_project.jobs):
                saved_job = saved_project.jobs[job_idx]
                job_enabled = saved_job.params.get('enabled', True)
                job_widget.data_object.params['enabled'] = job_enabled
                job_widget.update(job_widget.data_object)
                job_widget.set_enabled_and_update(job_enabled)
                for action_idx, action_widget in enumerate(job_widget.child_widgets):
                    if action_idx < len(saved_job.sub_actions):
                        saved_action = saved_job.sub_actions[action_idx]
                        action_enabled = saved_action.params.get('enabled', True)
                        action_widget.data_object.params['enabled'] = action_enabled
                        action_widget.update(action_widget.data_object)
                        action_widget.set_enabled_and_update(action_enabled)
                        for subaction_idx, subaction_widget \
                                in enumerate(action_widget.child_widgets):
                            if subaction_idx < len(saved_action.sub_actions):
                                saved_subaction = saved_action.sub_actions[subaction_idx]
                                subaction_enabled = saved_subaction.params.get('enabled', True)
                                subaction_widget.data_object.params['enabled'] = subaction_enabled
                                subaction_widget.update(subaction_widget.data_object)
                                subaction_widget.set_enabled_and_update(subaction_enabled)

    def _undo_clone_action(self, state):
        try:
            if state.is_subaction_selected():
                cloned_state = SelectionState(
                    state.job_index, state.action_index, state.subaction_index + 1)
            elif state.is_action_selected():
                cloned_state = SelectionState(
                    state.job_index, state.action_index + 1, -1)
            elif state.is_job_selected():
                cloned_state = SelectionState(state.job_index + 1, -1, -1)
            else:
                self.refresh_ui()
                return
            self._remove_widget(cloned_state)
            self._refresh_job_widget_signals()
            self.update_delete_action_state_requested.emit()
        except Exception:
            self.refresh_ui()

    def _undo_paste_action(self, state):
        try:
            if state.is_valid():
                self._remove_widget(state)
                self._refresh_job_widget_signals()
                self.update_delete_action_state_requested.emit()
        except Exception:
            self.refresh_ui()
