# pylint: disable=C0114, C0115, C0116, R0913, R0917, W0718, R0902
import os
import traceback
import logging
import numpy as np
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.framework import TaskBase
from .. core.colors import color_str
from .. core.exceptions import InvalidOptionError
from .utils import write_img, extension_supported
from .stack_framework import ImageSequenceManager, SequentialTask
from .exif import copy_exif_from_file_to_file
from .denoise import denoise
from .sharpen import unsharp_mask


class FocusStackBase(TaskBase, ImageSequenceManager):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        ImageSequenceManager.__init__(self, name, **kwargs)
        TaskBase.__init__(self, name, enabled)
        default_params = DEFAULTS['focus_stack_params']
        self.stack_algo = stack_algo
        self.exif_path = kwargs.pop('exif_path', '')
        self.prefix = kwargs.pop('prefix', default_params['prefix'])
        self.denoise_amount = kwargs.pop(
            'denoise_amount', default_params['denoise_amount'])
        self.sharpen_amount = kwargs.pop(
            'sharpen_amount_percent', default_params['sharpen_amount_percent']) / 100.0
        self.sharpen_radius = kwargs.pop(
            'sharpen_radius', default_params['sharpen_radius'])
        self.sharpen_threshold = kwargs.pop(
            'sharpen_threshold', default_params['sharpen_threshold'])
        self.plot_stack = kwargs.pop(
            'plot_stack', DEFAULTS['focus_stack_params']['plot_stack'])
        self.stack_algo.set_process(self)
        self.frame_count = -1

    def focus_stack(self, filenames):
        self.sub_message_r(color_str(': reading input files', constants.LOG_COLOR_LEVEL_3))
        in_filename = os.path.basename(filenames[0]).split(".")
        out_filename = os.path.join(
            self.output_full_path(),
            f"{self.prefix}{in_filename[0]}." + '.'.join(in_filename[1:]))
        filename = os.path.basename(out_filename)
        self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS, self.name, filename, 0)
        self.stack_algo.set_output_filename(filename)
        stacked_img = self.stack_algo.focus_stack()
        if self.denoise_amount > 0.0:
            self.sub_message_r(color_str(': denoise image', constants.LOG_COLOR_LEVEL_3))
            stacked_img = denoise(
                stacked_img, self.denoise_amount)
        if self.sharpen_amount > 0.0:
            self.sub_message_r(color_str(': sharpen image', constants.LOG_COLOR_LEVEL_3))
            stacked_img = unsharp_mask(
                stacked_img, self.sharpen_amount, self.sharpen_radius, self.sharpen_threshold)
        write_img(out_filename, stacked_img)
        if self.exif_path != '':
            if stacked_img.dtype == np.uint16 and \
               os.path.splitext(out_filename)[-1].lower() == '.png':
                self.sub_message_r(color_str(': exif not supported for 16-bit PNG format',
                                             constants.LOG_COLOR_WARNING),
                                   level=logging.WARNING)
            else:
                self.sub_message_r(color_str(': copy exif data', constants.LOG_COLOR_LEVEL_3))
                if not os.path.exists(self.exif_path):
                    raise RuntimeError(f"path {self.exif_path} does not exist.")
                try:
                    _dirpath, _, fnames = next(os.walk(self.exif_path))
                    fnames = [name for name in fnames if extension_supported(name)]
                    if len(fnames) == 0:
                        raise RuntimeError(f"path {self.exif_path} does not contain image files.")
                    exif_filename = os.path.join(self.exif_path, fnames[0])
                    copy_exif_from_file_to_file(exif_filename, out_filename)
                    self.sub_message_r(' ' * 60)
                except Exception as e:
                    traceback.print_tb(e.__traceback__)
                    self.sub_message_r(color_str(f': failed to copy EXIF data: {str(e)}',
                                                 constants.LOG_COLOR_WARNING),
                                       level=logging.WARNING)
        self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS, self.name, filename, 1000)
        if self.plot_stack:
            idx_str = f"{self.frame_count + 1:04d}" if self.frame_count >= 0 else ''
            name = f"{self.name}: {self.stack_algo.name()}"
            if idx_str != '':
                name += f"\nbunch: {idx_str}"
            self.callback(constants.CALLBACK_SAVE_PLOT, self.id, name, out_filename)
        if self.frame_count >= 0:
            self.frame_count += 1

    def init(self, job, working_path=''):
        if working_path == '':
            working_path = job.working_path
        ImageSequenceManager.init(self, job)
        if self.exif_path is None:
            self.exif_path = job.action_path(0)
        if self.exif_path != '':
            self.exif_path = os.path.join(working_path, self.exif_path)

    def end_job(self):
        ImageSequenceManager.end_job(self)


def get_bunches(collection, n_frames, n_overlap):
    if n_frames == n_overlap:
        raise RuntimeError(
            f"Can't get bunch collection, total number of frames ({n_frames}) "
            "is equal to the number of overlapping grames")
    bunches = [collection[x:x + n_frames]
               for x in range(0, len(collection) - n_overlap, n_frames - n_overlap)]
    return bunches


class FocusStackBunch(SequentialTask, FocusStackBase):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        SequentialTask.__init__(self, name, enabled)
        FocusStackBase.__init__(self, name, stack_algo, enabled, **kwargs)
        self._chunks = None
        self.frame_count = 0
        self.frames = kwargs.get('frames', DEFAULTS['focus_stack_bunch_params']['frames'])
        self.overlap = kwargs.get('overlap', DEFAULTS['focus_stack_bunch_params']['overlap'])
        self.denoise_amount = kwargs.get('denoise_amount', 0)
        self.stack_algo.set_do_step_callback(False)
        if self.overlap >= self.frames:
            raise InvalidOptionError("overlap", self.overlap,
                                     "overlap must be smaller than batch size")

    def sequential_processing(self):
        return True

    def init(self, job, _working_path=''):
        FocusStackBase.init(self, job, self.working_path)

    def begin(self):
        SequentialTask.begin(self)
        self._chunks = get_bunches(sorted(self.input_filepaths()), self.frames, self.overlap)
        self.callback(constants.CALLBACK_ADD_STATUS_BOX, self.output_path)
        for chunk in self._chunks:
            filename = chunk[0]
            file_path = self.output_full_path()
            filename = os.path.join(file_path, self.prefix + os.path.basename(filename))
            self.callback(constants.CALLBACK_ADD_FRAME, self.output_path, filename, 1)
        self.set_counts(len(self._chunks))

    def end(self):
        SequentialTask.end(self)

    def end_job(self):
        FocusStackBase.end_job(self)

    def run_step(self, action_count=-1):
        self.print_message(
            color_str(f"fusing bunch: {action_count + 1}/{self.total_action_counts}",
                      constants.LOG_COLOR_LEVEL_2))
        img_files = self._chunks[action_count]
        filename = self.prefix + os.path.basename(img_files[0])
        self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS, self.output_path, filename, 0)
        self.stack_algo.init(img_files)
        self.focus_stack(self._chunks[action_count])
        self.callback(constants.CALLBACK_UPDATE_FRAME_STATUS, self.output_path, filename, 1000)
        return True


class FocusStack(FocusStackBase):
    def __init__(self, name, stack_algo, enabled=True, **kwargs):
        super().__init__(name, stack_algo, enabled, **kwargs)
        self.stack_algo.set_do_step_callback(True)
        self.shape = None

    def run_core(self):
        self.set_filelist()
        img_files = sorted(self.input_filepaths())
        self.stack_algo.init(img_files)
        self.callback('step_counts', self.id, self.name,
                      self.stack_algo.total_steps(self.num_input_filepaths()))
        self.callback(constants.CALLBACK_ADD_STATUS_BOX, self.output_path)
        filename = img_files[0]
        file_path = self.output_full_path()
        filename = os.path.join(file_path, self.prefix + os.path.basename(filename))
        self.callback(constants.CALLBACK_ADD_FRAME, self.output_path, filename, 1)
        self.focus_stack(img_files)
        return True

    def init(self, job, _working_path=''):
        FocusStackBase.init(self, job, self.working_path)

    def end_job(self):
        FocusStackBase.end_job(self)
