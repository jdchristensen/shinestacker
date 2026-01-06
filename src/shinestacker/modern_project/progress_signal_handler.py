# pylint: disable=C0114, C0115, C0116, E0611, R0903
import os
from PySide6.QtCore import Qt, QObject, Slot
from .. algorithms.utils import extension_supported, extension_pdf
from .. algorithms.plot_manager import DirectPlotManager
from .. gui.gui_images import GuiPdfView, GuiImageView, GuiOpenApp


class SignalConnector(QObject):
    @staticmethod
    def connect_worker_signals(worker, view, progress_handler):
        for attr_name in dir(worker):
            if attr_name.endswith('_signal'):
                signal = getattr(worker, attr_name)
                handler_name = f'handle_{attr_name[:-7]}'
                handler = None
                if hasattr(progress_handler, handler_name):
                    handler = getattr(progress_handler, handler_name)
                elif hasattr(view, handler_name):
                    handler = getattr(view, handler_name)
                if handler and callable(handler):
                    signal.connect(handler, Qt.ConnectionType.UniqueConnection)
        worker.plot_manager.save_plot_signal.connect(progress_handler.plot_manager.save_plot)


class ProgressSignalHandler(QObject):
    def __init__(self, progress_mapper, find_widget_callback, scroll_to_callback):
        super().__init__()
        self.progress_mapper = progress_mapper
        self.find_widget = find_widget_callback
        self.scroll_to_widget = scroll_to_callback
        self.horizontal_layout = True
        self.plot_manager = DirectPlotManager()

    def set_horizontal_layout(self, horizontal=True):
        self.horizontal_layout = horizontal

    def _call_on_widget(self, module_name, func):
        state = self.progress_mapper.get_state(module_name)
        if not state:
            return
        widget = self.find_widget(state)
        if widget:
            func(widget)

    @Slot(int, str, str)
    def handle_step_counts(self, _run_id, module_name, total_steps):
        self._call_on_widget(
            module_name, lambda w: w.show_progress(total_steps))

    @Slot(int, str, str)
    def handle_after_step(self, _run_id, module_name, current_step):
        self._call_on_widget(module_name, lambda w: w.update_progress(current_step))

    @Slot(int, str)
    def handle_end_steps(self, _run_id, module_name):
        self._call_on_widget(module_name, lambda w: w.complete_progress())

    @Slot(int, str)
    def handle_begin_steps(self, _run_id, module_name):
        def begin_func(widget):
            if hasattr(widget, 'progress_bar') and not widget.progress_bar.isVisible():
                widget.progress_bar.start(1)
                widget.progress_bar.setVisible(True)
                self.scroll_to_widget(widget)
        self._call_on_widget(module_name, begin_func)

    @Slot(int, str)
    def handle_before_action(self, _run_id, name):
        self._call_on_widget(name, lambda w: w.progress_bar.set_running_style())

    @Slot(int, str)
    def handle_after_action(self, _run_id, name):
        self._call_on_widget(name, lambda w: w.progress_bar.set_done_style())

    @Slot(int, str)
    def handle_run_stopped(self, _run_id, name):
        self._call_on_widget(name, lambda w: w.progress_bar.set_stopped_style())

    @Slot(int, str)
    def handle_run_failed(self, _run_id, name):
        self._call_on_widget(name, lambda w: w.progress_bar.set_failed_style())

    @Slot(str)
    def handle_add_status_box(self, module_name):
        def add_status_func(widget):
            if hasattr(widget, 'add_status_box'):
                widget.add_status_box(module_name)
                self.scroll_to_widget(widget)
        self._call_on_widget(module_name, add_status_func)

    @Slot(int, str, str, int)
    def handle_add_frame(self, module_name, filename, total_actions):
        def add_frame_func(widget):
            if hasattr(widget, 'add_frame'):
                widget.add_frame(module_name, filename, total_actions)
                self.scroll_to_widget(widget)
        self._call_on_widget(module_name, add_frame_func)

    @Slot(int, str, str, int)
    def handle_update_frame_status(self, module_name, filename, status_id):
        def update_frame_func(widget):
            if hasattr(widget, 'update_frame_status'):
                widget.update_frame_status(module_name, filename, status_id)
                self.scroll_to_widget(widget)
        self._call_on_widget(module_name, update_frame_func)

    @Slot(int, str, str, int)
    def handle_set_total_actions(self, module_name, filename, total_actions):
        def set_total_func(widget):
            if hasattr(widget, 'set_frame_total_actions'):
                widget.set_frame_total_actions(module_name, filename, total_actions)
        self._call_on_widget(module_name, set_total_func)

    @Slot(int, str, str, str)
    def handle_save_plot(self, _run_id, module_name, _caption, path):
        state = self.progress_mapper.get_state(module_name)
        if not state:
            return
        widget = self.find_widget(state)
        if not widget:
            return
        fixed_height = state.subaction_index == -1 and self.horizontal_layout is False
        if extension_pdf(path):
            image_view = GuiPdfView(path, widget, fixed_height=fixed_height)
        elif extension_supported(path):
            image_view = GuiImageView(path, widget, fixed_height=fixed_height)
        else:
            raise RuntimeError(f"Can't visualize file type {os.path.splitext(path)[1]}.")
        widget.add_image_view(image_view)

    @Slot(int, str, str, str)
    def handle_open_app(self, _run_id, name, app, path):
        state = self.progress_mapper.get_state(name)
        if not state:
            return
        widget = self.find_widget(state)
        if not widget:
            return
        image_view = GuiOpenApp(app, path, widget, fixed_height=state.subaction_index == -1)
        widget.add_image_view(image_view)
