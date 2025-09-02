# pylint: disable=C0114, C0115, C0116, W0102, R0902, R0903
# pylint: disable=R0917, R0913, R1702, R0912, E1111, E1121, W0613
import logging
import os
from .. config.constants import constants
from .. core.colors import color_str
from .. core.framework import Job, ActionList
from .. core.core_utils import check_path_exists
from .. core.exceptions import RunStopException
from .utils import read_img, write_img, extension_tif_jpg, get_img_metadata, validate_image


class StackJob(Job):
    def __init__(self, name, working_path, input_path='', **kwargs):
        check_path_exists(working_path)
        self.working_path = working_path
        if input_path == '':
            self.paths = []
        else:
            self.paths = [input_path]
        Job.__init__(self, name, **kwargs)

    def init(self, a):
        a.init(self)


class FramePaths:
    def __init__(self, name, input_path='', output_path='', working_path='',
                 plot_path=constants.DEFAULT_PLOTS_PATH,
                 scratch_output_dir=True, resample=1,
                 reverse_order=constants.DEFAULT_FILE_REVERSE_ORDER, **_kwargs):
        self.name = name
        self.working_path = working_path
        self.plot_path = plot_path
        self.input_path = input_path
        self.output_path = self.name if output_path == '' else output_path
        self.resample = resample
        self.reverse_order = reverse_order
        self.scratch_output_dir = scratch_output_dir
        self.enabled = None
        self.base_message = ''
        self._input_full_path = None
        self._output_full_path = None
        self._input_filepaths = None

    def output_full_path(self):
        if self._output_full_path is None:
            self._output_full_path = os.path.join(self.working_path, self.output_path)
        return self._output_full_path

    def input_full_path(self):
        if self._input_full_path is None:
            if isinstance(self.input_path, str):
                self._input_full_path = os.path.join(self.working_path, self.input_path)
                check_path_exists(self._input_full_path)
            elif hasattr(self.input_path, "__len__"):
                self._input_full_path = [os.path.join(self.working_path, path)
                                         for path in self.input_path]
                for path in self._input_full_path:
                    check_path_exists(path)
        return self._input_full_path

    def input_filepaths(self):
        if self._input_filepaths is None:
            if isinstance(self.input_full_path(), str):
                dirs = [self.input_full_path()]
            elif hasattr(self.input_full_path(), "__len__"):
                dirs = self.input_full_path()
            else:
                raise RuntimeError("input_full_path option must contain "
                                   "a path or an array of paths")
            files = []
            for d in dirs:
                filelist = []
                for _dirpath, _, filenames in os.walk(d):
                    filelist = [os.path.join(_dirpath, name)
                                for name in filenames if extension_tif_jpg(name)]
                    filelist.sort()
                    if self.reverse_order:
                        filelist.reverse()
                    if self.resample > 1:
                        filelist = filelist[0::self.resample]
                    files += filelist
                if len(files) == 0:
                    self.print_message(color_str(f"input folder {d} does not contain any image",
                                                 constants.LOG_COLOR_WARNING),
                                       level=logging.WARNING)
            self._input_filepaths = files
        return self._input_filepaths

    def input_filepath(self, index):
        return self.input_filepaths()[index]

    def num_input_filepaths(self):
        return len(self.input_filepaths())

    def print_message(self, msg='', level=logging.INFO, end=None, begin='', tqdm=False):
        assert False, "this method should be overwritten"

    def set_filelist(self):
        file_folder = self.input_full_path().replace(self.working_path, '').lstrip('/')
        self.print_message(color_str(f"{self.num_input_filepaths()} files in folder: {file_folder}",
                                     constants.LOG_COLOR_LEVEL_2))
        self.base_message = color_str(self.name, constants.LOG_COLOR_LEVEL_1, "bold")

    def init(self, job):
        if self.working_path == '':
            self.working_path = job.working_path
        check_path_exists(self.working_path)
        output_dir = self.output_full_path()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            list_dir = os.listdir(output_dir)
            if len(list_dir) > 0:
                if self.scratch_output_dir:
                    if self.enabled:
                        for filename in list_dir:
                            file_path = os.path.join(output_dir, filename)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        self.print_message(
                            color_str(f": output directory {self.output_path} content erased",
                                      'yellow'))
                    else:
                        self.print_message(
                            color_str(f": module disabled, output directory {self.output_path}"
                                      " not scratched", 'yellow'))
                else:
                    self.print_message(
                        color_str(
                            f": output directory {self.output_path} not empty, "
                            "files may be overwritten or merged with existing ones.", 'yellow'
                        ), level=logging.WARNING)
        if self.plot_path == '':
            self.plot_path = self.working_path + \
                ('' if self.working_path[-1] == '/' else '/') + self.plot_path
            if not os.path.exists(self.plot_path):
                os.makedirs(self.plot_path)
        if self.input_path in ['', []]:
            if len(job.paths) == 0:
                raise RuntimeError(f"Job {job.name} does not have any configured path")
            self.input_path = job.paths[-1]
        job.paths.append(self.output_path)

    def folder_list_str(self):
        if isinstance(self.input_full_path(), list):
            file_list = ", ".join(
                [path.replace(self.working_path, '').lstrip('/')
                 for path in self.input_full_path()])
            return "folder" + ('s' if len(self.input_full_path()) > 1 else '') + f": {file_list}"
        return "folder: " + self.input_full_path().replace(self.working_path, '').lstrip('/')


class FramesRefActions(ActionList, FramePaths):
    def __init__(self, name, enabled=True, reference_index=0, step_process=False, **kwargs):
        FramePaths.__init__(self, name, **kwargs)
        ActionList.__init__(self, name, enabled)
        self.ref_idx = reference_index
        self.step_process = step_process
        self.current_idx = None
        self.current_ref_idx = None
        self.current_idx_step = None

    def begin(self):
        ActionList.begin(self)
        self.set_filelist()
        n = self.num_input_filepaths()
        self.set_counts(n)
        if self.ref_idx == 0:
            self.ref_idx = n // 2
        elif self.ref_idx == -1:
            self.ref_idx = n - 1
        else:
            self.ref_idx -= 1
            if not 0 <= self.ref_idx < n:
                msg = f"reference index {self.ref_idx} out of range [1, {n}]"
                self.print_message_r(color_str(msg, constants.LOG_COLOR_LEVEL_2))
                raise IndexError(msg)

    def end(self):
        ActionList.end(self)

    def run_frame(self, _idx, _ref_idx):
        return None

    def run_step(self):
        if self.current_action_count == 0:
            self.current_idx = self.ref_idx if self.step_process else 0
            self.current_ref_idx = self.ref_idx
            self.current_idx_step = +1
        ll = self.num_input_filepaths()
        self.print_message_r(
            color_str(f"step {self.current_action_count + 1}/{ll}: process file: "
                      f"{os.path.basename(self.input_filepath(self.current_idx))}, "
                      f"reference: {os.path.basename(self.input_filepath(self.current_ref_idx))}",
                      constants.LOG_COLOR_LEVEL_2))
        self.base_message = color_str(self.name, constants.LOG_COLOR_LEVEL_1, "bold")
        success = self.run_frame(self.current_idx, self.current_ref_idx) is not None
        if self.current_idx < ll:
            if self.step_process and success:
                self.current_ref_idx = self.current_idx
            self.current_idx += self.current_idx_step
        if self.current_idx == ll:
            self.current_idx = self.ref_idx - 1
            if self.step_process:
                self.current_ref_idx = self.ref_idx
            self.current_idx_step = -1


class SubAction:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def begin(self, process):
        pass

    def end(self):
        pass


class CombinedActions(FramesRefActions):
    def __init__(self, name, actions=[], enabled=True, **kwargs):
        FramesRefActions.__init__(self, name, enabled, **kwargs)
        self._actions = actions
        self._metadata = (None, None)

    def begin(self):
        FramesRefActions.begin(self)
        for a in self._actions:
            if a.enabled:
                a.begin(self)

    def img_ref(self, idx):
        input_path = self.input_filepath(idx)
        img = read_img(input_path)
        if img is None:
            raise RuntimeError(f"Invalid file: {os.path.basename(input_path)}")
        self._metadata = get_img_metadata(img)
        return img

    def run_frame(self, idx, ref_idx):
        input_path = self.input_filepath(idx)
        self.sub_message_r(color_str(': read input image', constants.LOG_COLOR_LEVEL_3))
        img = read_img(input_path)
        validate_image(img, *(self._metadata))
        if img is None:
            raise RuntimeError(f"Invalid file:  {os.path.basename(input_path)}")
        if len(self._actions) == 0:
            self.sub_message(color_str(": no actions specified", constants.LOG_COLOR_ALERT),
                             level=logging.WARNING)
        for a in self._actions:
            if not a.enabled:
                self.get_logger().warning(color_str(f"{self.base_message}: sub-action disabled",
                                                    constants.LOG_COLOR_ALERT))
            else:
                if self.callback('check_running', self.id, self.name) is False:
                    raise RunStopException(self.name)
                if img is not None:
                    img = a.run_frame(idx, ref_idx, img)
                else:
                    self.sub_message(
                        color_str(": null input received, action skipped",
                                  constants.LOG_COLOR_ALERT),
                        level=logging.WARNING)
        if img is not None:
            self.sub_message_r(color_str(': write output image', constants.LOG_COLOR_LEVEL_3))
            output_path = os.path.join(self.output_full_path(), os.path.basename(input_path))
            write_img(output_path, img)
            return img
        self.print_message(color_str(
            f"no output file resulted from processing input file: {os.path.basename(input_path)}",
            constants.LOG_COLOR_ALERT), level=logging.WARNING)
        return None

    def end(self):
        for a in self._actions:
            if a.enabled:
                a.end()
