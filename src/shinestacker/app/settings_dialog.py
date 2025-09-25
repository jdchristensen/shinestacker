# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903, E0611
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox
from .. gui.config_dialog import ConfigDialog
from .. config.settings import Settings
from .. config.constants import constants
from .. config.gui_constants import gui_constants
from .. config.app_config import AppConfig


class SettingsDialog(ConfigDialog):
    update_project_config_requested = Signal()
    update_retouch_config_requested = Signal()

    def __init__(self, parent=None, project_settings=True, retouch_settings=True):
        self.project_settings = project_settings
        self.retouch_settings = retouch_settings
        self.settings = Settings()
        self.expert_options = None
        self.view_strategy = None
        self.min_mouse_step_brush_fraction = None
        self.paint_refresh_time = None
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

    def accept(self):
        if self.project_settings:
            self.settings.set(
                'expert_options', self.expert_options.isChecked())
        if self.retouch_settings:
            self.settings.set(
                'view_strategy', self.view_strategy.itemData(self.view_strategy.currentIndex()))
            self.settings.set(
                'min_mouse_step_brush_fraction', self.min_mouse_step_brush_fraction.value())
            self.settings.set(
                'paint_refresh_time', self.paint_refresh_time.value())
        self.settings.save()
        AppConfig.instance().load_defaults()
        if self.project_settings:
            self.update_project_config_requested.emit()
        if self.retouch_settings:
            self.update_retouch_config_requested.emit()
        super().accept()

    def reset_to_defaults(self):
        if self.project_settings:
            self.expert_options.setChecked(constants.DEFAULT_EXPERT_OPTIONS)
        if self.retouch_settings:
            idx = self.view_strategy.findData(constants.DEFAULT_VIEW_STRATEGY)
            if idx >= 0:
                self.view_strategy.setCurrentIndex(idx)
            self.min_mouse_step_brush_fraction.setValue(
                gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION)
            self.paint_refresh_time.setValue(
                gui_constants.DEFAULT_PAINT_REFRESH_TIME)


def show_settings_dialog(parent, project_settings, retouch_settings,
                         handle_project_config, handle_retouch_config):
    dialog = SettingsDialog(parent, project_settings, retouch_settings)
    dialog.update_project_config_requested.connect(handle_project_config)
    dialog.update_retouch_config_requested.connect(handle_retouch_config)
    dialog.exec()
