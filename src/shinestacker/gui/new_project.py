# pylint: disable=C0114, C0115, C0116, E0611, R0915, R0902, R0914, R0911, R0912, R0904
import os
import numpy as np
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QLabel, QCheckBox, QSpinBox,
                               QMessageBox, QGroupBox, QVBoxLayout, QFormLayout, QSizePolicy)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from .. config.gui_constants import gui_constants
from .. config.constants import constants
from .. config.app_config import AppConfig
from .. algorithms.utils import read_img, extension_tif_jpg
from .. algorithms.stack import get_bunches
from .folder_file_selection import FolderFileSelectionWidget
from .base_form_dialog import BaseFormDialog

DEFAULT_NO_COUNT_LABEL = " - "


class NewProjectDialog(BaseFormDialog):
    def __init__(self, parent=None):
        super().__init__("New Project", 600, parent)
        self.create_form()
        button_box = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(self.ok_button)
        button_box.addWidget(cancel_button)
        self.add_row_to_layout(button_box)
        self.ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.n_image_files = 0
        self.selected_filenames = []

    def expert(self):
        return AppConfig.get('expert_options')

    def add_bold_label(self, label):
        label = QLabel(label)
        label.setStyleSheet("font-weight: bold")
        self.form_layout.addRow(label)

    def add_label(self, label):
        label = QLabel(label)
        self.form_layout.addRow(label)

    def create_form(self):
        self.input_widget = FolderFileSelectionWidget()
        self.input_widget.text_changed_connect(self.input_submitted)
        self.noise_detection = QCheckBox()
        self.noise_detection.setChecked(gui_constants.NEW_PROJECT_NOISE_DETECTION)
        self.vignetting_correction = QCheckBox()
        self.vignetting_correction.setChecked(gui_constants.NEW_PROJECT_VIGNETTING_CORRECTION)
        self.align_frames = QCheckBox()
        self.align_frames.setChecked(gui_constants.NEW_PROJECT_ALIGN_FRAMES)
        self.balance_frames = QCheckBox()
        self.balance_frames.setChecked(gui_constants.NEW_PROJECT_BALANCE_FRAMES)
        self.bunch_stack = QCheckBox()
        self.bunch_stack.setChecked(gui_constants.NEW_PROJECT_BUNCH_STACK)
        self.bunch_frames = QSpinBox()
        bunch_frames_range = gui_constants.NEW_PROJECT_BUNCH_FRAMES
        self.bunch_frames.setRange(bunch_frames_range['min'], bunch_frames_range['max'])
        self.bunch_frames.setValue(constants.DEFAULT_FRAMES)
        self.bunch_overlap = QSpinBox()
        bunch_overlap_range = gui_constants.NEW_PROJECT_BUNCH_OVERLAP
        self.bunch_overlap.setRange(bunch_overlap_range['min'], bunch_overlap_range['max'])
        self.bunch_overlap.setValue(constants.DEFAULT_OVERLAP)
        self.bunches_label = QLabel(DEFAULT_NO_COUNT_LABEL)
        self.frames_label = QLabel(DEFAULT_NO_COUNT_LABEL)
        self.update_bunch_options(gui_constants.NEW_PROJECT_BUNCH_STACK)
        self.bunch_stack.toggled.connect(self.update_bunch_options)
        self.bunch_frames.valueChanged.connect(self.update_bunches_label)
        self.bunch_overlap.valueChanged.connect(self.update_bunches_label)
        self.focus_stack_pyramid = QCheckBox()
        self.focus_stack_pyramid.setChecked(gui_constants.NEW_PROJECT_FOCUS_STACK_PYRAMID)
        self.focus_stack_depth_map = QCheckBox()
        self.focus_stack_depth_map.setChecked(gui_constants.NEW_PROJECT_FOCUS_STACK_DEPTH_MAP)
        self.multi_layer = QCheckBox()
        self.multi_layer.setChecked(gui_constants.NEW_PROJECT_MULTI_LAYER)
        step1_group = QGroupBox("1) Select Input")
        step1_layout = QVBoxLayout()
        step1_layout.setContentsMargins(15, 0, 15, 15)
        step1_layout.addWidget(
            QLabel("Select a folder containing "
                   "all your images, or specific image files."))
        input_form = QFormLayout()
        input_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        input_form.setFormAlignment(Qt.AlignLeft)
        input_form.setLabelAlignment(Qt.AlignLeft)
        self.input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.frames_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        input_form.addRow("Input:", self.input_widget)
        input_form.addRow("Number of frames: ", self.frames_label)
        step1_layout.addLayout(input_form)
        step1_group.setLayout(step1_layout)
        self.form_layout.addRow(step1_group)
        step2_group = QGroupBox("2) Basic Options")
        step2_layout = QFormLayout()
        step2_layout.setContentsMargins(15, 0, 15, 15)
        step2_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        step2_layout.setFormAlignment(Qt.AlignLeft)
        step2_layout.setLabelAlignment(Qt.AlignLeft)
        for widget in [self.noise_detection, self.vignetting_correction, self.align_frames,
                       self.balance_frames, self.bunch_stack, self.bunch_frames,
                       self.bunch_overlap, self.focus_stack_pyramid,
                       self.focus_stack_depth_map, self.multi_layer]:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if self.expert():
            step2_layout.addRow("Automatic noise detection:", self.noise_detection)
            step2_layout.addRow("Vignetting correction:", self.vignetting_correction)
        step2_layout.addRow(
            # f" {constants.ACTION_ICONS[constants.ACTION_ALIGNFRAMES]} "
            "Align frames:", self.align_frames)
        step2_layout.addRow(
            # f" {constants.ACTION_ICONS[constants.ACTION_BALANCEFRAMES]} "
            "Balance frames:", self.balance_frames)
        step2_layout.addRow(
            # f" {constants.ACTION_ICONS[constants.ACTION_FOCUSSTACKBUNCH]} "
            "Create bunches:", self.bunch_stack)
        self.bunch_stack.setToolTip("Combine multiple frames into fewer, high-quality "
                                    "composite frames for easier retouching")
        step2_layout.addRow("Frames per bunch:", self.bunch_frames)
        step2_layout.addRow("Overlap between bunches:", self.bunch_overlap)
        self.bunches_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        step2_layout.addRow("Number of resulting bunches: ", self.bunches_label)
        if self.expert():
            step2_layout.addRow(
                f" {constants.ACTION_ICONS[constants.ACTION_FOCUSSTACK]} "
                "Focus stack (pyramid):", self.focus_stack_pyramid)
            step2_layout.addRow(
                f" {constants.ACTION_ICONS[constants.ACTION_FOCUSSTACK]} "
                "Focus stack (depth map):", self.focus_stack_depth_map)
        else:
            step2_layout.addRow(
                f" {constants.ACTION_ICONS[constants.ACTION_FOCUSSTACK]} "
                "Focus stack:", self.focus_stack_pyramid)
        if self.expert():
            step2_layout.addRow(
                f" {constants.ACTION_ICONS[constants.ACTION_MULTILAYER]} "
                "Export as multilayer TIFF:", self.multi_layer)
        step2_group.setLayout(step2_layout)
        self.form_layout.addRow(step2_group)
        step3_group = QGroupBox("3) Confirm")
        step3_layout = QVBoxLayout()
        step3_layout.setContentsMargins(15, 0, 15, 15)
        step3_layout.addWidget(
            QLabel("Click 🆗 to create project with these settings."))
        step3_layout.addWidget(
            QLabel("Select: <b>View</b> > <b>Expert options</b> for advanced configuration."))
        step3_group.setLayout(step3_layout)
        self.form_layout.addRow(step3_group)
        step4_group = QGroupBox("4) Execute")
        step4_layout = QHBoxLayout()
        step4_layout.setContentsMargins(15, 0, 15, 15)
        step4_layout.addWidget(QLabel("Press ▶️ to run your job."))
        step4_layout.addStretch()
        icon_path = f"{os.path.dirname(__file__)}/ico/shinestacker.png"
        app_icon = QIcon(icon_path)
        icon_pixmap = app_icon.pixmap(80, 80)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignRight)
        step4_layout.addWidget(icon_label)
        step4_group.setLayout(step4_layout)
        self.form_layout.addRow(step4_group)
        group_style = """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #f8f8f8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f8f8f8;
            }
        """
        for group in [step1_group, step2_group, step3_group, step4_group]:
            group.setStyleSheet(group_style)
            group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.form_layout.setFormAlignment(Qt.AlignLeft)
        self.form_layout.setLabelAlignment(Qt.AlignLeft)

    def update_bunch_options(self, checked):
        self.bunch_frames.setEnabled(checked)
        self.bunch_overlap.setEnabled(checked)
        self.update_bunches_label()

    def update_bunches_label(self):
        if not self.input_widget.get_path():
            return

        def count_image_files(path):
            if path == '' or not os.path.isdir(path):
                return 0
            count = 0
            for filename in os.listdir(path):
                if extension_tif_jpg(filename):
                    count += 1
            return count
        if self.input_widget.get_selection_mode() == 'files' and \
                self.input_widget.get_selected_files():
            self.n_image_files = self.input_widget.num_selected_files()
            self.selected_filenames = self.input_widget.get_selected_filenames()
        else:
            self.n_image_files = count_image_files(self.input_widget.get_path())
            self.selected_filenames = []
        if self.n_image_files == 0:
            self.bunches_label.setText(DEFAULT_NO_COUNT_LABEL)
            self.frames_label.setText(DEFAULT_NO_COUNT_LABEL)
            return
        self.frames_label.setText(f"{self.n_image_files}")
        if self.bunch_stack.isChecked():
            bunches = get_bunches(list(range(self.n_image_files)),
                                  self.bunch_frames.value(),
                                  self.bunch_overlap.value())
            self.bunches_label.setText(f"{max(1, len(bunches))}")
        else:
            self.bunches_label.setText(DEFAULT_NO_COUNT_LABEL)

    def input_submitted(self):
        self.update_bunches_label()
        self.ok_button.setFocus()

    def accept(self):
        input_path = self.input_widget.get_path()
        selection_mode = self.input_widget.get_selection_mode()
        selected_files = self.input_widget.get_selected_files()
        if not input_path:
            QMessageBox.warning(self, "Input Required", "Please select an input folder or files")
            return
        if selection_mode == 'files':
            if not selected_files:
                QMessageBox.warning(self, "Invalid Selection", "No files selected")
                return
            for file_path in selected_files:
                if not os.path.exists(file_path):
                    QMessageBox.warning(self, "Invalid Path",
                                        f"The file {file_path} does not exist")
                    return
        else:
            if not os.path.exists(input_path):
                QMessageBox.warning(self, "Invalid Path", "The specified folder does not exist")
                return
            if not os.path.isdir(input_path):
                QMessageBox.warning(self, "Invalid Path", "The specified path is not a folder")
                return
        parent_dir = os.path.dirname(input_path)
        if not parent_dir:
            parent_dir = input_path
        if len(parent_dir.split('/')) < 2:
            QMessageBox.warning(self, "Invalid Path", "The path must have a parent folder")
            return
        if self.n_image_files > 0 and not self.bunch_stack.isChecked():
            if selection_mode == 'files' and selected_files:
                file_path = selected_files[0]
            else:
                path = self.input_widget.get_path()
                files = os.listdir(path)
                file_path = None
                for filename in files:
                    full_path = os.path.join(path, filename)
                    if extension_tif_jpg(full_path):
                        file_path = full_path
                        break
            if file_path is None:
                QMessageBox.warning(
                    self, "Invalid input", "Could not find images in the selected path")
                return
            img = read_img(file_path)
            height, width = img.shape[:2]
            n_bytes = 1 if img.dtype == np.uint8 else 2
            n_bits = 8 if img.dtype == np.uint8 else 16
            n_gbytes = float(n_bytes * height * width * self.n_image_files) / constants.ONE_GIGA
            if n_gbytes > 1 and not self.bunch_stack.isChecked():
                msg = QMessageBox()
                msg.setStyleSheet("""
                    QMessageBox {
                        min-width: 600px;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    QMessageBox QLabel#qt_msgbox_informativelabel {
                        font-weight: normal;
                        font-size: 14px;
                        color: #555555;
                    }
                """)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Too many frames")
                msg.setText(f"You selected {self.n_image_files} images "
                            f"with resolution {width}×{height} pixels, {n_bits} bits depth. "
                            "Processing may require a significant amount "
                            "of memory or I/O buffering.\n\n"
                            "Continue anyway?")
                msg.setInformativeText('You may consider creating "bunches" to reduce '
                                       "the number of frames for retouching.\n\n"
                                       '✅ Check "Create bunches" to combine frames '
                                       "into manageable composites.\n\n"
                                       "➡️ Check expert options for the stacking algorithm.\n\n"
                                       'Go to "View" > "Expert Options".')
                msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                msg.setDefaultButton(QMessageBox.Cancel)
                if msg.exec_() != QMessageBox.Ok:
                    return
        super().accept()

    def get_input_folder(self):
        return self.input_widget.get_path()

    def get_selected_files(self):
        return self.input_widget.get_selected_files()

    def get_selected_filenames(self):
        return self.input_widget.get_selected_filenames()

    def get_selection_mode(self):
        return self.input_widget.get_selection_mode()

    def get_noise_detection(self):
        return self.noise_detection.isChecked()

    def get_vignetting_correction(self):
        return self.vignetting_correction.isChecked()

    def get_align_frames(self):
        return self.align_frames.isChecked()

    def get_balance_frames(self):
        return self.balance_frames.isChecked()

    def get_bunch_stack(self):
        return self.bunch_stack.isChecked()

    def get_bunch_frames(self):
        return self.bunch_frames.value()

    def get_bunch_overlap(self):
        return self.bunch_overlap.value()

    def get_focus_stack_pyramid(self):
        return self.focus_stack_pyramid.isChecked()

    def get_focus_stack_depth_map(self):
        return self.focus_stack_depth_map.isChecked()

    def get_multi_layer(self):
        return self.multi_layer.isChecked()
