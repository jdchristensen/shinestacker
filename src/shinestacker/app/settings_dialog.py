# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903, E0611, R0902
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox
from .. config.settings import Settings
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .. gui.config_dialog import ConfigDialog
from .. gui.action_config_dialog import AlignFramesConfigBase


class SettingsDialog(ConfigDialog, AlignFramesConfigBase):
    update_project_config_requested = Signal()
    update_retouch_config_requested = Signal()

    def __init__(self, parent=None, project_settings=True, retouch_settings=True):
        AlignFramesConfigBase.__init__(self)
        self.project_settings = project_settings
        self.retouch_settings = retouch_settings
        self.settings = Settings.instance()
        self.expert_options = None
        self.combined_actions_max_threads = None
        self.align_frames_max_threads = None
        self.detector = None
        self.descriptor = None
        self.matching_method = None
        self.focus_stack_max_threads = None
        self.view_strategy = None
        self.min_mouse_step_brush_fraction = None
        self.paint_refresh_time = None
        self.display_refresh_time = None
        self.cursor_update_time = None
        super().__init__("Settings", parent)

    def create_form_content(self):
        if self.project_settings:
            self.create_project_settings()
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(1)
        self.container_layout.addRow(separator)
        if self.retouch_settings:
            self.create_retouch_settings()

    def create_project_settings(self):
        label = QLabel("Project settings")
        label.setStyleSheet("font-weight: bold")
        self.container_layout.addRow(label)
        self.expert_options = QCheckBox()
        self.expert_options.setChecked(self.settings.get('expert_options'))
        self.container_layout.addRow("Expert options:", self.expert_options)
        self.combined_actions_max_threads = QSpinBox()
        self.combined_actions_max_threads.setRange(0, 64)
        self.combined_actions_max_threads.setValue(
            self.settings.get('combined_actions_params')['max_threads'])
        self.container_layout.addRow("Max num. of cores, combined actions:",
                                     self.combined_actions_max_threads)

        self.align_frames_max_threads = QSpinBox()
        self.align_frames_max_threads.setRange(0, 64)
        self.align_frames_max_threads.setValue(
            self.settings.get('align_frames_params')['max_threads'])
        self.container_layout.addRow("Max num. of cores, align frames:",
                                     self.align_frames_max_threads)

        def change_match_config():
            self.change_match_config(
                self.detector, self.descriptor,
                self. matching_method, self.show_info)

        self.detector = QComboBox()
        self.detector.addItems(constants.VALID_DETECTORS)
        self.descriptor = QComboBox()
        self.descriptor.addItems(constants.VALID_DESCRIPTORS)
        self.matching_method = QComboBox()
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: orange; font-style: italic;")
        self.matching_method = QComboBox()
        for k, v in zip(self.MATCHING_METHOD_OPTIONS, constants.VALID_MATCHING_METHODS):
            self.matching_method.addItem(k, v)
        self.detector.setToolTip(self.DETECTOR_DESCRIPTOR_TOOLTIPS['detector'])
        self.descriptor.setToolTip(self.DETECTOR_DESCRIPTOR_TOOLTIPS['descriptor'])
        self.matching_method.setToolTip(self.DETECTOR_DESCRIPTOR_TOOLTIPS['match_method'])
        self.detector.currentIndexChanged.connect(change_match_config)
        self.descriptor.currentIndexChanged.connect(change_match_config)
        self.matching_method.currentIndexChanged.connect(change_match_config)
        self.container_layout.addRow('Detector:', self.detector)
        self.container_layout.addRow('Descriptor:', self.descriptor)
        self.container_layout.addRow(self.info_label)
        self.container_layout.addRow('Match method:', self.matching_method)

        self.focus_stack_max_threads = QSpinBox()
        self.focus_stack_max_threads.setRange(0, 64)
        self.focus_stack_max_threads.setValue(
            self.settings.get('align_frames_params')['max_threads'])
        self.container_layout.addRow("Max num. of cores, focus stacking:",
                                     self.focus_stack_max_threads)

    def create_retouch_settings(self):
        label = QLabel("Retouch settings")
        label.setStyleSheet("font-weight: bold")
        self.container_layout.addRow(label)
        self.view_strategy = QComboBox()
        self.view_strategy.addItem("Overlaid", "overlaid")
        self.view_strategy.addItem("Side by side", "sidebyside")
        self.view_strategy.addItem("Top-Bottom", "topbottom")
        idx = self.view_strategy.findData(self.settings.get('view_strategy'))
        if idx >= 0:
            self.view_strategy.setCurrentIndex(idx)
        self.container_layout.addRow("View strategy:", self.view_strategy)
        self.min_mouse_step_brush_fraction = QDoubleSpinBox()
        self.min_mouse_step_brush_fraction.setValue(
            self.settings.get('min_mouse_step_brush_fraction'))
        self.min_mouse_step_brush_fraction.setRange(0, 1)
        self.min_mouse_step_brush_fraction.setDecimals(2)
        self.min_mouse_step_brush_fraction.setSingleStep(0.02)
        self.container_layout.addRow("Min. mouse step in brush units:",
                                     self.min_mouse_step_brush_fraction)
        self.paint_refresh_time = QSpinBox()
        self.paint_refresh_time.setRange(0, 1000)
        self.paint_refresh_time.setValue(
            self.settings.get('paint_refresh_time'))
        self.container_layout.addRow("Paint refresh time:",
                                     self.paint_refresh_time)
        self.display_refresh_time = QSpinBox()
        self.display_refresh_time.setRange(0, 200)
        self.display_refresh_time.setValue(
            self.settings.get('display_refresh_time'))
        self.container_layout.addRow("Display refresh time:",
                                     self.display_refresh_time)

        self.cursor_update_time = QSpinBox()
        self.cursor_update_time.setRange(0, 50)
        self.cursor_update_time.setValue(
            self.settings.get('cursor_update_time'))
        self.container_layout.addRow("Cursor refresh time:",
                                     self.cursor_update_time)

    def accept(self):
        if self.project_settings:
            self.settings.set(
                'expert_options', self.expert_options.isChecked())
            self.settings.set(
                'combined_actions_params', {
                    'max_threads': self.combined_actions_max_threads.value()
                })
            self.settings.set(
                'align_frames_params', {
                    'max_threads':
                        self.align_frames_max_threads.value(),
                    'detector':
                        self.descriptor.currentText(),
                    'descriptor':
                        self.descriptor.currentText(),
                    'match_method':
                        self.matching_method.itemData(self.matching_method.currentIndex())
                })
            self.settings.set(
                'focus_stack_params', {
                    'max_threads': self.focus_stack_max_threads.value()
                })
            self.settings.set(
                'focus_stack_bunch:params', {
                    'max_threads': self.focus_stack_max_threads.value()
                })
        if self.retouch_settings:
            self.settings.set(
                'view_strategy', self.view_strategy.itemData(self.view_strategy.currentIndex()))
            self.settings.set(
                'min_mouse_step_brush_fraction', self.min_mouse_step_brush_fraction.value())
            self.settings.set(
                'paint_refresh_time', self.paint_refresh_time.value())
            self.settings.set(
                'display_refresh_time', self.display_refresh_time.value())
            self.settings.set(
                'cursor_update_time', self.cursor_update_time.value())
        self.settings.update()
        if self.project_settings:
            self.update_project_config_requested.emit()
        if self.retouch_settings:
            self.update_retouch_config_requested.emit()
        super().accept()

    def reset_to_defaults(self):
        if self.project_settings:
            self.expert_options.setChecked(constants.DEFAULT_EXPERT_OPTIONS)
            self.combined_actions_max_threads.setValue(constants.DEFAULT_MAX_FWK_THREADS)
            self.align_frames_max_threads.setValue(constants.DEFAULT_ALIGN_MAX_THREADS)
            self.detector.setCurrentText(constants.DEFAULT_DETECTOR)
            self.descriptor.setCurrentText(constants.DEFAULT_DESCRIPTOR)
            idx = self.matching_method.findData(constants.DEFAULT_MATCHING_METHOD)
            if idx >= 0:
                self.matching_method.setCurrentIndex(idx)
            self.focus_stack_max_threads.setValue(constants.DEFAULT_PY_MAX_THREADS)
        if self.retouch_settings:
            idx = self.view_strategy.findData(constants.DEFAULT_VIEW_STRATEGY)
            if idx >= 0:
                self.view_strategy.setCurrentIndex(idx)
            self.min_mouse_step_brush_fraction.setValue(
                gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION)
            self.paint_refresh_time.setValue(
                gui_constants.DEFAULT_PAINT_REFRESH_TIME)
            self.display_refresh_time.setValue(
                gui_constants.DEFAULT_DISPLAY_REFRESH_TIME)
            self.cursor_update_time.setValue(
                gui_constants.DEFAULT_CURSOR_UPDATE_TIME)


def show_settings_dialog(parent, project_settings, retouch_settings,
                         handle_project_config, handle_retouch_config):
    dialog = SettingsDialog(parent, project_settings, retouch_settings)
    dialog.update_project_config_requested.connect(handle_project_config)
    dialog.update_retouch_config_requested.connect(handle_retouch_config)
    dialog.exec()
