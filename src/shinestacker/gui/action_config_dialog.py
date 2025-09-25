# pylint: disable=C0114, C0115, C0116, E0611, R0913, R0917, R0915, R0912
# pylint: disable=E0606, W0718, R1702, W0102, W0221, R0914, C0302
import os
import traceback
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QLabel, QMessageBox, QStackedWidget
from .. config.constants import constants
from .. config.app_config import AppConfig
from .. algorithms.align import validate_align_config
from . action_config import (
    DefaultActionConfigurator,
    FIELD_TEXT, FIELD_ABS_PATH, FIELD_REL_PATH, FIELD_FLOAT,
    FIELD_INT, FIELD_INT_TUPLE, FIELD_BOOL, FIELD_COMBO, FIELD_REF_IDX
)
from .folder_file_selection import FolderFileSelectionWidget
from .config_dialog import ConfigDialog


class ActionConfigDialog(ConfigDialog):
    def __init__(self, action, current_wd, parent=None):
        self.action = action
        self.current_wd = current_wd
        super().__init__(f"Configure {action.type_name}", parent)

    def create_form_content(self):
        self.configurator = self.get_configurator(self.action.type_name)
        self.configurator.create_form(self.container_layout, self.action)

    def get_configurator(self, action_type):
        configurators = {
            constants.ACTION_JOB: JobConfigurator,
            constants.ACTION_COMBO: CombinedActionsConfigurator,
            constants.ACTION_NOISEDETECTION: NoiseDetectionConfigurator,
            constants.ACTION_FOCUSSTACK: FocusStackConfigurator,
            constants.ACTION_FOCUSSTACKBUNCH: FocusStackBunchConfigurator,
            constants.ACTION_MULTILAYER: MultiLayerConfigurator,
            constants.ACTION_MASKNOISE: MaskNoiseConfigurator,
            constants.ACTION_VIGNETTING: VignettingConfigurator,
            constants.ACTION_ALIGNFRAMES: AlignFramesConfigurator,
            constants.ACTION_BALANCEFRAMES: BalanceFramesConfigurator,
        }
        return configurators.get(
            action_type, DefaultActionConfigurator)(self.expert(), self.current_wd)

    def accept(self):
        if self.configurator.update_params(self.action.params):
            if hasattr(self.parent(), 'mark_as_modified'):
                self.parent().mark_as_modified(True, "Modify Configuration")
            super().accept()

    def reset_to_defaults(self):
        builder = self.configurator.get_builder()
        if builder:
            builder.reset_to_defaults()

    def expert(self):
        return AppConfig.get('expert_options')


class JobConfigurator(DefaultActionConfigurator):
    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd, expert_toggle=False)
        self.working_path_label = None
        self.input_path_label = None
        self.frames_label = None
        self.input_widget = None

    def create_form(self, layout, action):
        super().create_form(layout, action, "Job")
        self.input_widget = FolderFileSelectionWidget()
        self.frames_label = QLabel("0")
        working_path = action.params.get('working_path', '')
        input_path = action.params.get('input_path', '')
        input_filepaths = action.params.get('input_filepaths', [])
        if isinstance(input_filepaths, str) and input_filepaths:
            input_filepaths = input_filepaths.split(constants.PATH_SEPARATOR)
        self.working_path_label = QLabel(working_path or "Not set")
        self.input_path_label = QLabel(input_path or "Not set")
        self.input_widget.path_edit.setText('')
        if input_filepaths:
            self.input_widget.files_mode_radio.setChecked(True)
        else:
            self.input_widget.folder_mode_radio.setChecked(False)
        self.input_widget.text_changed_connect(self.update_paths_and_frames)
        self.input_widget.folder_mode_radio.toggled.connect(self.update_paths_and_frames)
        self.input_widget.files_mode_radio.toggled.connect(self.update_paths_and_frames)
        self.add_bold_label("Input Selection:")
        self.add_row(self.input_widget)
        self.add_labelled_row("Number of frames: ", self.frames_label)
        self.add_bold_label("Derived Paths:")
        self.add_labelled_row("Working path: ", self.working_path_label)
        self.add_labelled_row("Input path:", self.input_path_label)
        self.set_paths_and_frames(working_path, input_path, input_filepaths)

    def update_frames_count(self):
        if self.input_widget.get_selection_mode() == 'files':
            count = self.input_widget.num_selected_files()
        else:
            count = self.count_image_files(self.input_widget.get_path())
        self.frames_label.setText(str(count))

    def set_paths_and_frames(self, working_path, input_path, input_filepaths):
        self.input_path_label.setText(input_path or "Not set")
        self.working_path_label.setText(working_path or "Not set")
        self.frames_label.setText(str(len(input_filepaths)))

    def update_paths_and_frames(self, ):
        input_fullpath = self.input_widget.get_path()
        input_path = os.path.basename(os.path.normpath(input_fullpath)) if input_fullpath else ""
        working_path = os.path.dirname(input_fullpath) if input_fullpath else ""
        self.input_path_label.setText(input_path or "Not set")
        self.working_path_label.setText(working_path or "Not set")
        self.update_frames_count()

    def count_image_files(self, path):
        if not path or not os.path.isdir(path):
            return 0
        count = 0
        for filename in os.listdir(path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff')):
                count += 1
        return count

    def update_params(self, params):
        if not super().update_params(params):
            return False
        selection_mode = self.input_widget.get_selection_mode()
        selected_files = self.input_widget.get_selected_files()
        if selection_mode == 'files' and selected_files:
            input_full_path = os.path.dirname(selected_files[0])
            params['input_filepaths'] = self.input_widget.get_selected_filenames()
        else:
            input_full_path = self.input_widget.get_path()
            params['input_filepaths'] = []
        input_path = os.path.basename(os.path.normpath(input_full_path)) if input_full_path else ""
        working_path = os.path.dirname(input_full_path) if input_full_path else ""
        params['input_path'] = input_path
        params['working_path'] = working_path
        return True


class NoiseDetectionConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'working_path', FIELD_ABS_PATH, 'Working path', required=True,
            placeholder='inherit from job')
        self.add_field(
            'input_path', FIELD_REL_PATH,
            f'Input path (separate by {constants.PATH_SEPARATOR})',
            required=False, multiple_entries=True,
            placeholder='relative to working path')
        self.add_field(
            'max_frames', FIELD_INT, 'Max. num. of frames (0 = All)',
            required=False,
            default=constants.DEFAULT_NOISE_MAX_FRAMES, min_val=0, max_val=1000)
        self.add_field(
            'channel_thresholds', FIELD_INT_TUPLE, 'Noise threshold',
            required=False, size=3,
            default=constants.DEFAULT_CHANNEL_THRESHOLDS,
            labels=constants.RGB_LABELS, min_val=[1] * 3, max_val=[1000] * 3)
        self.add_field(
            'blur_size', FIELD_INT, 'Blur size (px)', required=False,
            expert=True,
            default=constants.DEFAULT_BLUR_SIZE, min_val=1, max_val=50)
        self.add_field(
            'file_name', FIELD_TEXT, 'File name', required=False,
            default=constants.DEFAULT_NOISE_MAP_FILENAME,
            placeholder=constants.DEFAULT_NOISE_MAP_FILENAME)
        self.add_bold_label("Miscellanea:")
        self.add_field(
            'plot_histograms', FIELD_BOOL, 'Plot histograms', required=False,
            default=False)
        self.add_field(
            'plot_path', FIELD_REL_PATH, 'Plots path', required=False,
            default=constants.DEFAULT_PLOTS_PATH,
            placeholder='relative to working path')
        self.add_field(
            'plot_range', FIELD_INT_TUPLE, 'Plot range', required=False,
            size=2, default=constants.DEFAULT_NOISE_PLOT_RANGE,
            labels=['min', 'max'], min_val=[0] * 2, max_val=[1000] * 2)


class FocusStackBaseConfigurator(DefaultActionConfigurator):
    ENERGY_OPTIONS = ['Laplacian', 'Sobel']
    MAP_TYPE_OPTIONS = ['Average', 'Maximum']
    FLOAT_OPTIONS = ['float 32 bits', 'float 64 bits']
    MODE_OPTIONS = ['Auto', 'All in memory', 'Tiled I/O buffered']

    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.tab_widget = None
        self.general_tab_layout = None
        self.algorithm_tab_layout = None

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.tab_widget = self.create_tab_widget(layout)
        self.general_tab_layout = self.add_tab(self.tab_widget, "General Parameters")
        self.create_general_tab(self.general_tab_layout)
        self.algorithm_tab_layout = self.add_tab(self.tab_widget, "Stacking Algorithm")
        self.create_algorithm_tab(self.algorithm_tab_layout)

    def create_general_tab(self, layout):
        self.add_field_to_layout(
            layout, 'working_path', FIELD_ABS_PATH, 'Working path', required=False,
            expert=True)
        self.add_field_to_layout(
            layout, 'input_path', FIELD_REL_PATH, 'Input path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field_to_layout(
            layout, 'output_path', FIELD_REL_PATH, 'Output path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field_to_layout(
            layout, 'scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
            required=False, default=True)

    def create_algorithm_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Stacking algorithm:")
        combo = self.add_field_to_layout(
            layout, 'stacker', FIELD_COMBO, 'Stacking algorithm', required=True,
            options=constants.STACK_ALGO_OPTIONS,
            default=constants.STACK_ALGO_DEFAULT)
        q_pyramid, q_depthmap = QWidget(), QWidget()
        for q in [q_pyramid, q_depthmap]:
            q.setLayout(self.create_tab_layout())
        stacked = QStackedWidget()
        stacked.addWidget(q_pyramid)
        stacked.addWidget(q_depthmap)

        def change():
            text = combo.currentText()
            if text == constants.STACK_ALGO_PYRAMID:
                stacked.setCurrentWidget(q_pyramid)
            elif text == constants.STACK_ALGO_DEPTH_MAP:
                stacked.setCurrentWidget(q_depthmap)

        change()
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_min_size', FIELD_INT, 'Minimum size (px)',
            expert=True,
            required=False, default=constants.DEFAULT_PY_MIN_SIZE, min_val=2, max_val=256)
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_kernel_size', FIELD_INT, 'Kernel size (px)',
            expert=True,
            required=False, default=constants.DEFAULT_PY_KERNEL_SIZE, min_val=3, max_val=21)
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_gen_kernel', FIELD_FLOAT, 'Gen. kernel',
            expert=True,
            required=False, default=constants.DEFAULT_PY_GEN_KERNEL,
            min_val=0.0, max_val=2.0)
        self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_float_type', FIELD_COMBO, 'Precision', required=False,
            expert=True,
            options=self.FLOAT_OPTIONS, values=constants.VALID_FLOATS,
            default=dict(zip(constants.VALID_FLOATS,
                             self.FLOAT_OPTIONS))[constants.DEFAULT_PY_FLOAT])
        mode = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_mode', FIELD_COMBO, 'Mode',
            expert=True,
            required=False, options=self.MODE_OPTIONS, values=constants.PY_VALID_MODES,
            default=dict(zip(constants.PY_VALID_MODES,
                             self.MODE_OPTIONS))[constants.DEFAULT_PY_MODE])
        memory_limit = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_memory_limit', FIELD_FLOAT,
            'Memory limit (approx., GBytes)',
            expert=True,
            required=False, default=constants.DEFAULT_PY_MEMORY_LIMIT_GB,
            min_val=1.0, max_val=64.0)
        max_threads = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_max_threads', FIELD_INT, 'Max num. of cores',
            expert=True,
            required=False, default=AppConfig.get('focus_stack_params')['max_threads'],
            min_val=1, max_val=64)
        tile_size = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_tile_size', FIELD_INT, 'Tile size (px)',
            expert=True,
            required=False, default=constants.DEFAULT_PY_TILE_SIZE,
            min_val=128, max_val=2048)
        n_tiled_layers = self.add_field_to_layout(
            q_pyramid.layout(), 'pyramid_n_tiled_layers', FIELD_INT, 'Num. tiled layers',
            expert=True,
            required=False, default=constants.DEFAULT_PY_N_TILED_LAYERS,
            min_val=0, max_val=6)

        def change_mode():
            text = mode.currentText()
            enabled = text == self.MODE_OPTIONS[2]
            tile_size.setEnabled(enabled)
            n_tiled_layers.setEnabled(enabled)
            memory_limit.setEnabled(text == self.MODE_OPTIONS[0])
            max_threads.setEnabled(text != self.MODE_OPTIONS[1])

        mode.currentIndexChanged.connect(change_mode)
        change_mode()

        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_energy', FIELD_COMBO, 'Energy', required=False,
            options=self.ENERGY_OPTIONS, values=constants.VALID_DM_ENERGY,
            default=dict(zip(constants.VALID_DM_ENERGY,
                             self.ENERGY_OPTIONS))[constants.DEFAULT_DM_ENERGY])
        self.add_field_to_layout(
            q_depthmap.layout(), 'map_type', FIELD_COMBO, 'Map type', required=False,
            options=self.MAP_TYPE_OPTIONS, values=constants.VALID_DM_MAP,
            default=dict(zip(constants.VALID_DM_MAP,
                             self.MAP_TYPE_OPTIONS))[constants.DEFAULT_DM_MAP])
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_kernel_size', FIELD_INT, 'Kernel size (px)',
            expert=True,
            required=False, default=constants.DEFAULT_DM_KERNEL_SIZE, min_val=3, max_val=21)
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_blur_size', FIELD_INT, 'Blurl size (px)',
            expert=True,
            required=False, default=constants.DEFAULT_DM_BLUR_SIZE, min_val=1, max_val=21)
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_smooth_size', FIELD_INT, 'Smooth size (px)',
            expert=True,
            required=False, default=constants.DEFAULT_DM_SMOOTH_SIZE, min_val=0, max_val=256)
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_temperature', FIELD_FLOAT, 'Temperature',
            expert=True,
            required=False, default=constants.DEFAULT_DM_TEMPERATURE,
            min_val=0, max_val=1, step=0.05)
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_levels', FIELD_INT, 'Levels', required=False,
            expert=True,
            default=constants.DEFAULT_DM_LEVELS, min_val=2, max_val=6)
        self.add_field_to_layout(
            q_depthmap.layout(), 'depthmap_float_type', FIELD_COMBO,
            'Precision', required=False,
            expert=True,
            options=self.FLOAT_OPTIONS, values=constants.VALID_FLOATS,
            default=dict(zip(constants.VALID_FLOATS,
                             self.FLOAT_OPTIONS))[constants.DEFAULT_DM_FLOAT])
        layout.addRow(stacked)
        combo.currentIndexChanged.connect(change)


class FocusStackConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field_to_layout(
            self.general_tab_layout, 'exif_path', FIELD_REL_PATH,
            'Exif data path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field_to_layout(
            self.general_tab_layout, 'prefix', FIELD_TEXT,
            'Output filename prefix', required=False,
            expert=True,
            default=constants.DEFAULT_STACK_PREFIX,
            placeholder=constants.DEFAULT_STACK_PREFIX)
        self.add_field_to_layout(
            self.general_tab_layout, 'plot_stack', FIELD_BOOL, 'Plot stack', required=False,
            default=constants.DEFAULT_PLOT_STACK)


class FocusStackBunchConfigurator(FocusStackBaseConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field_to_layout(
            self.general_tab_layout, 'frames', FIELD_INT, 'Frames', required=False,
            default=constants.DEFAULT_FRAMES, min_val=1, max_val=100)
        self.add_field_to_layout(
            self.general_tab_layout, 'overlap', FIELD_INT, 'Overlapping frames', required=False,
            default=constants.DEFAULT_OVERLAP, min_val=0, max_val=100)
        self.add_field_to_layout(
            self.general_tab_layout, 'plot_stack', FIELD_BOOL, 'Plot stack', required=False,
            default=constants.DEFAULT_PLOT_STACK_BUNCH)


class MultiLayerConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'working_path', FIELD_ABS_PATH, 'Working path', required=False,
            expert=True)
        self.add_field(
            'input_path', FIELD_REL_PATH,
            f'Input path (separate by {constants.PATH_SEPARATOR})',
            required=False, multiple_entries=True,
            placeholder='relative to working path')
        self.add_field(
            'output_path', FIELD_REL_PATH, 'Output path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field(
            'exif_path', FIELD_REL_PATH, 'Exif data path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field(
            'scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
            required=False, default=True)
        self.add_field(
            'reverse_order', FIELD_BOOL, 'Reverse file order', required=False,
            default=constants.DEFAULT_MULTILAYER_FILE_REVERSE_ORDER)


class CombinedActionsConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'working_path', FIELD_ABS_PATH, 'Working path', required=False,
            expert=True)
        self.add_field(
            'input_path', FIELD_REL_PATH, 'Input path', required=False,
            expert=True,
            must_exist=True, placeholder='relative to working path')
        self.add_field(
            'output_path', FIELD_REL_PATH, 'Output path', required=False,
            expert=True,
            placeholder='relative to working path')
        self.add_field(
            'scratch_output_dir', FIELD_BOOL, 'Scratch output dir.',
            required=False, default=True)
        self.add_field(
            'plot_path', FIELD_REL_PATH, 'Plots path', required=False,
            expert=True,
            default="plots", placeholder='relative to working path')
        self.add_field(
            'resample', FIELD_INT, 'Resample frame stack', required=False,
            expert=True,
            default=1, min_val=1, max_val=100)
        self.add_field(
            'reference_index', FIELD_REF_IDX, 'Reference frame', required=False,
            expert=True,
            default=0)
        self.add_field(
            'step_process', FIELD_BOOL, 'Step process', required=False,
            expert=True,
            default=True)
        self.add_field(
            'max_threads', FIELD_INT, 'Max num. of cores',
            required=False, default=AppConfig.get('combined_actions_params')['max_threads'],
            expert=True,
            min_val=1, max_val=64)
        self.add_field(
            'chunk_submit', FIELD_BOOL, 'Submit in chunks',
            expert=True,
            required=False, default=constants.DEFAULT_MAX_FWK_CHUNK_SUBMIT)


class MaskNoiseConfigurator(DefaultActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'noise_mask', FIELD_REL_PATH, 'Noise mask file', required=False,
            path_type='file', must_exist=True,
            default=constants.DEFAULT_NOISE_MAP_FILENAME,
            placeholder=constants.DEFAULT_NOISE_MAP_FILENAME)
        self.add_field(
            'kernel_size', FIELD_INT, 'Kernel size', required=False,
            expert=True,
            default=constants.DEFAULT_MN_KERNEL_SIZE, min_val=1, max_val=10)
        self.add_field(
            'method', FIELD_COMBO, 'Interpolation method', required=False,
            expert=True,
            options=['Mean', 'Median'], default='Mean')


class SubsampleActionConfigurator(DefaultActionConfigurator):
    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.subsample_field = None
        self.fast_subsampling_field = None

    def add_subsample_fields(self, add_to_layout=None):
        if add_to_layout is None:
            add_to_layout = self.builder.main_layout
        self.subsample_field = self.add_field(
            'subsample', FIELD_COMBO, 'Subsample', required=False,
            expert=True,
            options=constants.FIELD_SUBSAMPLE_OPTIONS,
            values=constants.FIELD_SUBSAMPLE_VALUES,
            default=constants.FIELD_SUBSAMPLE_DEFAULT,
            add_to_layout=add_to_layout)
        self.fast_subsampling_field = self.add_field(
            'fast_subsampling', FIELD_BOOL, 'Fast subsampling', required=False,
            expert=True,
            default=constants.DEFAULT_ALIGN_FAST_SUBSAMPLING,
            add_to_layout=add_to_layout)

        self.subsample_field.currentTextChanged.connect(self.change_subsample)
        self.change_subsample()

    def change_subsample(self):
        self.fast_subsampling_field.setEnabled(
            self.subsample_field.currentText() not in constants.FIELD_SUBSAMPLE_OPTIONS[:2])


class AlignFramesConfigurator(SubsampleActionConfigurator):
    BORDER_MODE_OPTIONS = ['Constant', 'Replicate', 'Replicate and blur']
    TRANSFORM_OPTIONS = ['Rigid', 'Homography']
    METHOD_OPTIONS = ['Random Sample Consensus (RANSAC)', 'Least Median (LMEDS)']
    MATCHING_METHOD_OPTIONS = ['K-nearest neighbors', 'Hamming distance']
    MODE_OPTIONS = ['Auto', 'Sequential', 'Parallel']

    def __init__(self, expert, current_wd):
        super().__init__(expert, current_wd)
        self.matching_method_field = None
        self.info_label = None
        self.detector_field = None
        self.descriptor_field = None
        self.matching_method_field = None
        self.tab_widget = None
        self.current_tab_layout = None

    def show_info(self, message, timeout=3000):
        self.info_label.setText(message)
        timer = QTimer(self.info_label)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self.info_label.setText(''))
        timer.start(timeout)

    def change_match_config(self):
        detector = self.detector_field.currentText()
        descriptor = self.descriptor_field.currentText()
        match_method = dict(
            zip(self.MATCHING_METHOD_OPTIONS,
                constants.VALID_MATCHING_METHODS))[self.matching_method_field.currentText()]
        try:
            validate_align_config(detector, descriptor, match_method)
        except Exception as e:
            self.show_info(str(e))
            if descriptor == constants.DETECTOR_SIFT and \
               match_method == constants.MATCHING_NORM_HAMMING:
                self.matching_method_field.setCurrentText(self.MATCHING_METHOD_OPTIONS[0])
            if detector == constants.DETECTOR_ORB and descriptor == constants.DESCRIPTOR_AKAZE and \
                    match_method == constants.MATCHING_NORM_HAMMING:
                self.matching_method_field.setCurrentText(constants.MATCHING_NORM_HAMMING)
            if detector == constants.DETECTOR_BRISK and descriptor == constants.DESCRIPTOR_AKAZE:
                self.descriptor_field.setCurrentText('BRISK')
            if detector == constants.DETECTOR_SURF and descriptor == constants.DESCRIPTOR_AKAZE:
                self.descriptor_field.setCurrentText('SIFT')
            if detector == constants.DETECTOR_SIFT and descriptor != constants.DESCRIPTOR_SIFT:
                self.descriptor_field.setCurrentText('SIFT')
            if detector in constants.NOKNN_METHODS['detectors'] and \
               descriptor in constants.NOKNN_METHODS['descriptors']:
                if match_method == constants.MATCHING_KNN:
                    self.matching_method_field.setCurrentText(self.MATCHING_METHOD_OPTIONS[1])

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.detector_field = None
        self.descriptor_field = None
        self.matching_method_field = None
        self.tab_widget = self.create_tab_widget(layout)
        feature_layout = self.add_tab(self.tab_widget, "Feature extraction")
        self.create_feature_tab(feature_layout)
        transform_layout = self.add_tab(self.tab_widget, "Transform")
        self.create_transform_tab(transform_layout)
        border_layout = self.add_tab(self.tab_widget, "Border")
        self.create_border_tab(border_layout)
        misc_layout = self.add_tab(self.tab_widget, "Miscellanea")
        self.create_miscellanea_tab(misc_layout)

    def create_feature_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Feature identification:")
        self.detector_field = self.add_field_to_layout(
            layout, 'detector', FIELD_COMBO, 'Detector', required=False,
            options=constants.VALID_DETECTORS, default=constants.DEFAULT_DETECTOR)
        self.descriptor_field = self.add_field_to_layout(
            layout, 'descriptor', FIELD_COMBO, 'Descriptor', required=False,
            options=constants.VALID_DESCRIPTORS, default=constants.DEFAULT_DESCRIPTOR)
        self.detector_field.setToolTip(
            "SIFT: Requires SIFT descriptor and K-NN matching\n"
            "ORB/AKAZE: Work best with Hamming distance"
        )
        self.descriptor_field.setToolTip(
            "SIFT: Requires K-NN matching\n"
            "ORB/AKAZE: Require Hamming distance with ORB/AKAZE detectors"
        )
        self.detector_field.currentIndexChanged.connect(self.change_match_config)
        self.descriptor_field.currentIndexChanged.connect(self.change_match_config)
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: orange; font-style: italic;")
        layout.addRow(self.info_label)
        self.add_bold_label_to_layout(layout, "Feature matching:")
        self.matching_method_field = self.add_field_to_layout(
            layout, 'match_method', FIELD_COMBO, 'Match method', required=False,
            options=self.MATCHING_METHOD_OPTIONS, values=constants.VALID_MATCHING_METHODS,
            default=constants.DEFAULT_MATCHING_METHOD)
        self.matching_method_field.setToolTip(
            "Automatically selected based on detector/descriptor combination"
        )
        self.matching_method_field.currentIndexChanged.connect(self.change_match_config)
        self.add_field_to_layout(
            layout, 'flann_idx_kdtree', FIELD_INT, 'Flann idx kdtree', required=False,
            expert=True,
            default=constants.DEFAULT_FLANN_IDX_KDTREE,
            min_val=0, max_val=10)
        self.add_field_to_layout(
            layout, 'flann_trees', FIELD_INT, 'Flann trees', required=False,
            expert=True,
            default=constants.DEFAULT_FLANN_TREES,
            min_val=0, max_val=10)
        self.add_field_to_layout(
            layout, 'flann_checks', FIELD_INT, 'Flann checks', required=False,
            expert=True,
            default=constants.DEFAULT_FLANN_CHECKS,
            min_val=0, max_val=1000)
        self.add_field_to_layout(
            layout, 'threshold', FIELD_FLOAT, 'Threshold', required=False,
            expert=True,
            default=constants.DEFAULT_ALIGN_THRESHOLD,
            min_val=0, max_val=1, step=0.05)
        self.add_subsample_fields(add_to_layout=layout)

    def create_transform_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Transform:")
        transform = self.add_field_to_layout(
            layout, 'transform', FIELD_COMBO, 'Transform', required=False,
            options=self.TRANSFORM_OPTIONS, values=constants.VALID_TRANSFORMS,
            default=constants.DEFAULT_TRANSFORM)
        method = self.add_field_to_layout(
            layout, 'align_method', FIELD_COMBO, 'Align method', required=False,
            options=self.METHOD_OPTIONS, values=constants.VALID_ALIGN_METHODS,
            default=constants.DEFAULT_ALIGN_METHOD)
        rans_threshold = self.add_field_to_layout(
            layout, 'rans_threshold', FIELD_FLOAT, 'RANSAC threshold (px)', required=False,
            expert=True,
            default=constants.DEFAULT_RANS_THRESHOLD, min_val=0, max_val=20, step=0.1)
        self.add_field_to_layout(
            layout, 'min_good_matches', FIELD_INT, "Min. good matches", required=False,
            expert=True,
            default=constants.DEFAULT_ALIGN_MIN_GOOD_MATCHES, min_val=0, max_val=500)

        def change_method():
            text = method.currentText()
            if text == self.METHOD_OPTIONS[0]:
                rans_threshold.setEnabled(True)
            elif text == self.METHOD_OPTIONS[1]:
                rans_threshold.setEnabled(False)

        method.currentIndexChanged.connect(change_method)
        change_method()
        self.add_field_to_layout(
            layout, 'align_confidence', FIELD_FLOAT, 'Confidence (%)',
            required=False, decimals=1,
            expert=True,
            default=constants.DEFAULT_ALIGN_CONFIDENCE,
            min_val=70.0, max_val=100.0, step=0.1)
        refine_iters = self.add_field_to_layout(
            layout, 'refine_iters', FIELD_INT, 'Refinement iterations (Rigid)', required=False,
            expert=True,
            default=constants.DEFAULT_REFINE_ITERS, min_val=0, max_val=1000)
        max_iters = self.add_field_to_layout(
            layout, 'max_iters', FIELD_INT, 'Max. iterations (Homography)', required=False,
            expert=True,
            default=constants.DEFAULT_ALIGN_MAX_ITERS, min_val=0, max_val=5000)

        def change_transform():
            text = transform.currentText()
            if text == self.TRANSFORM_OPTIONS[0]:
                refine_iters.setEnabled(True)
                max_iters.setEnabled(False)
            elif text == self.TRANSFORM_OPTIONS[1]:
                refine_iters.setEnabled(False)
                max_iters.setEnabled(True)

        transform.currentIndexChanged.connect(change_transform)
        change_transform()
        self.add_field_to_layout(
            layout, 'abort_abnormal', FIELD_BOOL, 'Abort on abnormal transf.',
            expert=True,
            required=False, default=constants.DEFAULT_ALIGN_ABORT_ABNORMAL)

    def create_border_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Border:")
        self.add_field_to_layout(
            layout, 'border_mode', FIELD_COMBO, 'Border mode', required=False,
            options=self.BORDER_MODE_OPTIONS,
            values=constants.VALID_BORDER_MODES,
            default=constants.DEFAULT_BORDER_MODE)
        self.add_field_to_layout(
            layout, 'border_value', FIELD_INT_TUPLE,
            'Border value (if constant)', required=False, size=4,
            expert=True,
            default=constants.DEFAULT_BORDER_VALUE,
            labels=constants.RGBA_LABELS,
            min_val=constants.DEFAULT_BORDER_VALUE, max_val=[255] * 4)
        self.add_field_to_layout(
            layout, 'border_blur', FIELD_FLOAT, 'Border blur', required=False,
            expert=True,
            default=constants.DEFAULT_BORDER_BLUR,
            min_val=0, max_val=1000, step=1)

    def create_miscellanea_tab(self, layout):
        self.add_bold_label_to_layout(layout, "Miscellanea:")
        mode = self.add_field_to_layout(
            layout, 'mode', FIELD_COMBO, 'Mode',
            required=False, options=self.MODE_OPTIONS, values=constants.ALIGN_VALID_MODES,
            default=dict(zip(constants.ALIGN_VALID_MODES,
                             self.MODE_OPTIONS))[constants.DEFAULT_ALIGN_MODE])
        memory_limit = self.add_field_to_layout(
            layout, 'memory_limit', FIELD_FLOAT, 'Memory limit (approx., GBytes)',
            required=False, default=constants.DEFAULT_ALIGN_MEMORY_LIMIT_GB,
            min_val=1.0, max_val=64.0)
        max_threads = self.add_field_to_layout(
            layout, 'max_threads', FIELD_INT, 'Max num. of cores',
            required=False, default=AppConfig.get('align_frames_params')['max_threads'],
            min_val=1, max_val=64)
        chunk_submit = self.add_field_to_layout(
            layout, 'chunk_submit', FIELD_BOOL, 'Submit in chunks',
            expert=True,
            required=False, default=constants.DEFAULT_ALIGN_CHUNK_SUBMIT)
        bw_matching = self.add_field_to_layout(
            layout, 'bw_matching', FIELD_BOOL, 'Match using black & white',
            expert=True,
            required=False, default=constants.DEFAULT_ALIGN_BW_MATCHING)

        def change_mode():
            text = mode.currentText()
            enabled = text != self.MODE_OPTIONS[1]
            memory_limit.setEnabled(enabled)
            max_threads.setEnabled(enabled)
            chunk_submit.setEnabled(enabled)
            bw_matching.setEnabled(enabled)

        mode.currentIndexChanged.connect(change_mode)

        self.add_field_to_layout(
            layout, 'plot_summary', FIELD_BOOL, 'Plot summary',
            required=False, default=False)

        self.add_field_to_layout(
            layout, 'plot_matches', FIELD_BOOL, 'Plot matches',
            required=False, default=False)

    def update_params(self, params):
        if self.detector_field and self.descriptor_field and self.matching_method_field:
            try:
                detector = self.detector_field.currentText()
                descriptor = self.descriptor_field.currentText()
                match_method = dict(
                    zip(self.MATCHING_METHOD_OPTIONS,
                        constants.VALID_MATCHING_METHODS))[
                            self.matching_method_field.currentText()]
                validate_align_config(detector, descriptor, match_method)
                return super().update_params(params)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                QMessageBox.warning(None, "Error", f"{str(e)}")
                return False
        return super().update_params(params)


class BalanceFramesConfigurator(SubsampleActionConfigurator):
    CORRECTION_MAP_OPTIONS = ['Linear', 'Gamma', 'Match histograms']
    CHANNEL_OPTIONS = ['Luminosity', 'RGB', 'HSV', 'HLS', 'LAB']

    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'mask_size', FIELD_FLOAT, 'Mask size', required=False,
            expert=True,
            default=0, min_val=0, max_val=5, step=0.1)
        self.add_field(
            'intensity_interval', FIELD_INT_TUPLE, 'Intensity range',
            required=False, size=2,
            expert=True,
            default=[v for k, v in constants.DEFAULT_INTENSITY_INTERVAL.items()],
            labels=['min', 'max'], min_val=[-1] * 2, max_val=[65536] * 2)
        self.add_subsample_fields()
        self.add_field(
            'corr_map', FIELD_COMBO, 'Correction map', required=False,
            options=self.CORRECTION_MAP_OPTIONS, values=constants.VALID_BALANCE,
            default='Linear')
        self.add_field(
            'channel', FIELD_COMBO, 'Channel', required=False,
            options=self.CHANNEL_OPTIONS, values=constants.VALID_BALANCE_CHANNELS,
            default='Luminosity')
        self.add_bold_label("Miscellanea:")
        self.add_field(
            'plot_summary', FIELD_BOOL, 'Plot summary',
            required=False, default=False)
        self.add_field(
            'plot_histograms', FIELD_BOOL, 'Plot histograms',
            required=False, default=False)


class VignettingConfigurator(SubsampleActionConfigurator):
    def create_form(self, layout, action):
        super().create_form(layout, action)
        self.add_field(
            'r_steps', FIELD_INT, 'Radial steps', required=False,
            expert=True,
            default=constants.DEFAULT_R_STEPS, min_val=1, max_val=1000)
        self.add_field(
            'black_threshold', FIELD_INT, 'Black intensity threshold',
            expert=True,
            required=False, default=constants.DEFAULT_BLACK_THRESHOLD,
            min_val=0, max_val=1000)
        self.add_subsample_fields()
        self.add_field(
            'max_correction', FIELD_FLOAT, 'Max. correction', required=False,
            default=constants.DEFAULT_MAX_CORRECTION,
            min_val=0, max_val=1, step=0.05)
        self.add_bold_label("Miscellanea:")
        self.add_field(
            'plot_correction', FIELD_BOOL, 'Plot correction', required=False,
            default=False)
        self.add_field(
            'plot_summary', FIELD_BOOL, 'Plot summary', required=False,
            default=False)
