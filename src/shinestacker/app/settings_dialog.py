# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, E1121
from abc import ABC, abstractmethod
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox
from .. config.settings import Settings
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .. gui.config_dialog import ConfigDialog
from .. gui.action_config import add_tab, create_tab_widget
from .. gui.action_config_dialog import AlignFramesConfigBase


class BaseParameter(ABC):
    def __init__(self, key, label, tooltip=""):
        self.key = key
        self.label = label
        self.tooltip = tooltip
        self.widget = None

    @abstractmethod
    def create_widget(self, parent):
        pass

    @abstractmethod
    def get_value(self):
        pass

    @abstractmethod
    def set_value(self, value):
        pass

    @abstractmethod
    def set_default(self):
        pass


class NestedParameter(BaseParameter):
    def __init__(self, parent_key, key, label, tooltip=""):
        super().__init__(key, label, tooltip)
        self.parent_key = parent_key

    def get_nested_value(self, settings):
        return settings.get(self.parent_key).get(self.key)

    def set_nested_value(self, settings, value):
        nested_dict = settings.get(self.parent_key).copy()
        nested_dict[self.key] = value
        settings.set(self.parent_key, nested_dict)


class CheckBoxParameter(BaseParameter):
    def __init__(self, key, label, default_value, tooltip=""):
        super().__init__(key, label, tooltip)
        self.default_value = default_value

    def create_widget(self, parent):
        self.widget = QCheckBox(parent)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget

    def get_value(self):
        return self.widget.isChecked()

    def set_value(self, value):
        self.widget.setChecked(value)

    def set_default(self):
        self.widget.setChecked(self.default_value)


class SpinBoxParameter(BaseParameter):
    def __init__(self, key, label, default_value, min_val, max_val, step=1, tooltip=""):
        super().__init__(key, label, tooltip)
        self.default_value = default_value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step

    def create_widget(self, parent):
        self.widget = QSpinBox(parent)
        self.widget.setRange(self.min_val, self.max_val)
        self.widget.setSingleStep(self.step)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget

    def get_value(self):
        return self.widget.value()

    def set_value(self, value):
        self.widget.setValue(value)

    def set_default(self):
        self.widget.setValue(self.default_value)


class DoubleSpinBoxParameter(SpinBoxParameter):
    def create_widget(self, parent):
        self.widget = QDoubleSpinBox(parent)
        self.widget.setRange(self.min_val, self.max_val)
        self.widget.setSingleStep(self.step)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget


class ComboBoxParameter(BaseParameter):
    def __init__(self, key, label, default_value, options, tooltip=""):
        super().__init__(key, label, tooltip)
        self.default_value = default_value
        self.options = options

    def create_widget(self, parent):
        self.widget = QComboBox(parent)
        for display_text, data in self.options:
            self.widget.addItem(display_text, data)
        if self.tooltip:
            self.widget.setToolTip(self.tooltip)
        return self.widget

    def get_value(self):
        return self.widget.itemData(self.widget.currentIndex())

    def set_value(self, value):
        idx = self.widget.findData(value)
        if idx >= 0:
            self.widget.setCurrentIndex(idx)

    def set_default(self):
        idx = self.widget.findData(self.default_value)
        if idx >= 0:
            self.widget.setCurrentIndex(idx)


class CallbackComboBoxParameter(ComboBoxParameter):
    def __init__(self, key, label, default_value, options, tooltip="", on_change=None):
        super().__init__(key, label, default_value, options, tooltip)
        self.on_change = on_change

    def create_widget(self, parent):
        widget = super().create_widget(parent)
        if self.on_change:
            widget.currentIndexChanged.connect(self.on_change)
        return widget


class NestedSpinBoxParameter(SpinBoxParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value, min_val, max_val, step=1, tooltip=""):
        SpinBoxParameter.__init__(
            self, key, label, default_value, min_val, max_val, step, tooltip)
        NestedParameter.__init__(
            self, parent_key, key, label, tooltip)


class NestedDoubleSpinBoxParameter(DoubleSpinBoxParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value, min_val, max_val, step=1, tooltip=""):
        DoubleSpinBoxParameter.__init__(
            self, key, label, default_value, min_val, max_val, step, tooltip)
        NestedParameter.__init__(
            self, parent_key, key, label, tooltip)


class NestedCallbackComboBoxParameter(CallbackComboBoxParameter, NestedParameter):
    def __init__(self, parent_key, key, label, default_value,
                 options, tooltip="", on_change=None):
        CallbackComboBoxParameter.__init__(
            self, key, label, default_value, options, tooltip, on_change)
        NestedParameter.__init__(self, parent_key, key, label, tooltip)


class SettingsDialog(ConfigDialog, AlignFramesConfigBase):
    update_project_config_requested = Signal()
    update_retouch_config_requested = Signal()

    def __init__(self, parent=None, project_settings=True, retouch_settings=True):
        AlignFramesConfigBase.__init__(self)
        self.project_settings = project_settings
        self.retouch_settings = retouch_settings
        self.settings = Settings.instance()
        self.project_parameters = []
        self.retouch_parameters = []
        self._init_parameters()
        super().__init__("Settings", parent)

    def _init_parameters(self):
        if self.project_settings:
            self.project_parameters = [
                CheckBoxParameter(
                    'expert_options', 'Expert options:',
                    constants.DEFAULT_EXPERT_OPTIONS),
                NestedSpinBoxParameter(
                    'combined_actions_params', 'max_threads',
                    'Combined actions, max num. of cores:',
                    constants.DEFAULT_FWK_MAX_THREADS, 0, 64),
                NestedDoubleSpinBoxParameter(
                    'align_frames_params', 'memory_limit',
                    'Align frames, mem. limit (approx., GBytes):',
                    constants.DEFAULT_ALIGN_MEMORY_LIMIT_GB, 1.0, 64.0, 1.0),
                NestedSpinBoxParameter(
                    'align_frames_params', 'max_threads',
                    'Align frames, max num. of cores:',
                    constants.DEFAULT_ALIGN_MAX_THREADS, 0, 64),
                NestedCallbackComboBoxParameter(
                    'align_frames_params', 'detector', 'Detector:',
                    constants.DEFAULT_DETECTOR, [(d, d) for d in constants.VALID_DETECTORS],
                    tooltip=self.DETECTOR_DESCRIPTOR_TOOLTIPS['detector'],
                    on_change=self.change_match_config_settings),
                NestedCallbackComboBoxParameter(
                    'align_frames_params', 'descriptor', 'Descriptor:',
                    constants.DEFAULT_DESCRIPTOR, [(d, d) for d in constants.VALID_DESCRIPTORS],
                    tooltip=self.DETECTOR_DESCRIPTOR_TOOLTIPS['descriptor'],
                    on_change=self.change_match_config_settings),
                NestedCallbackComboBoxParameter(
                    'align_frames_params', 'match_method', 'Match method:',
                    constants.DEFAULT_MATCHING_METHOD,
                    list(zip(self.MATCHING_METHOD_OPTIONS, constants.VALID_MATCHING_METHODS)),
                    tooltip=self.DETECTOR_DESCRIPTOR_TOOLTIPS['match_method'],
                    on_change=self.change_match_config_settings),
                NestedDoubleSpinBoxParameter(
                    'focus_stack_params', 'memory_limit',
                    'Focus stacking, mem. limit (approx., GBytes):',
                    constants.DEFAULT_PY_MEMORY_LIMIT_GB, 1.0, 64.0, 1.0),
                NestedSpinBoxParameter(
                    'focus_stack_params', 'max_threads', 'Focus stacking, max. num. of cores:',
                    constants.DEFAULT_PY_MAX_THREADS, 0, 64),
            ]
        if self.retouch_settings:
            self.retouch_parameters = [
                ComboBoxParameter(
                    'view_strategy', 'View strategy:',
                    constants.DEFAULT_VIEW_STRATEGY,
                    [
                        ("Overlaid", "overlaid"),
                        ("Side by side", "sidebyside"),
                        ("Top-Bottom", "topbottom")
                    ]),
                DoubleSpinBoxParameter(
                    'min_mouse_step_brush_fraction', 'Min. mouse step in brush units:',
                    gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION, 0, 1, 0.02),
                SpinBoxParameter(
                    'paint_refresh_time', 'Paint refresh time:',
                    gui_constants.DEFAULT_PAINT_REFRESH_TIME, 0, 1000),
                SpinBoxParameter(
                    'display_refresh_time', 'Display refresh time:',
                    gui_constants.DEFAULT_DISPLAY_REFRESH_TIME, 0, 200),
                SpinBoxParameter(
                    'cursor_update_time', 'Cursor refresh time:',
                    gui_constants.DEFAULT_CURSOR_UPDATE_TIME, 0, 50),
            ]

    def create_form_content(self):
        self.tab_widget = create_tab_widget(self.container_layout)
        if self.project_settings:
            project_tab_layout = add_tab(self.tab_widget, "Project Settings")
            self.create_project_settings(project_tab_layout)
        if self.retouch_settings:
            retouch_tab_layout = add_tab(self.tab_widget, "Retouch Settings")
            self.create_retouch_settings(retouch_tab_layout)

    def create_project_settings(self, layout=None):
        if layout is None:
            layout = self.container_layout
        label = QLabel("Project settings:")
        label.setStyleSheet("font-weight: bold")
        layout.addRow(label)
        for param in self.project_parameters:
            widget = param.create_widget(self)
            param.set_value(self._get_current_value(param))
            layout.addRow(param.label, widget)
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: orange; font-style: italic;")
        layout.addRow(self.info_label)

    def create_retouch_settings(self, layout=None):
        if layout is None:
            layout = self.container_layout
        label = QLabel("Retouch settings:")
        label.setStyleSheet("font-weight: bold")
        layout.addRow(label)
        for param in self.retouch_parameters:
            widget = param.create_widget(self)
            param.set_value(self._get_current_value(param))
            layout.addRow(param.label, widget)

    def _get_current_value(self, param):
        if isinstance(param, NestedParameter):
            return param.get_nested_value(self.settings)
        return self.settings.get(param.key)

    def _set_current_value(self, param, value):
        if isinstance(param, NestedParameter):
            param.set_nested_value(self.settings, value)
        else:
            self.settings.set(param.key, value)

    def change_match_config_settings(self):
        detector_widget = None
        descriptor_widget = None
        matching_method_widget = None
        for param in self.project_parameters:
            if (isinstance(param, NestedParameter) and
                    param.parent_key == 'align_frames_params'):
                if param.key == 'detector':
                    detector_widget = param.widget
                elif param.key == 'descriptor':
                    descriptor_widget = param.widget
                elif param.key == 'match_method':
                    matching_method_widget = param.widget
        if detector_widget and descriptor_widget and matching_method_widget:
            self.change_match_config(
                detector_widget, descriptor_widget, matching_method_widget, self.show_info)

    def accept(self):
        for param in self.project_parameters:
            self._set_current_value(param, param.get_value())
        for param in self.retouch_parameters:
            self._set_current_value(param, param.get_value())
        self.settings.update()
        if self.project_settings:
            self.update_project_config_requested.emit()
        if self.retouch_settings:
            self.update_retouch_config_requested.emit()
        super().accept()

    def reset_to_defaults(self):
        for param in self.project_parameters:
            param.set_default()
        for param in self.retouch_parameters:
            param.set_default()


def show_settings_dialog(
        parent, project_settings, retouch_settings, handle_project_config, handle_retouch_config):
    dialog = SettingsDialog(parent, project_settings, retouch_settings)
    dialog.update_project_config_requested.connect(handle_project_config)
    dialog.update_retouch_config_requested.connect(handle_retouch_config)
    dialog.exec()
