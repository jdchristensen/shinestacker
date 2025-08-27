# pylint: disable=C0114, C0115, C0116, E0602, R0903
import os
import numpy as np
from .. core.exceptions import InvalidOptionError, ImageLoadError, RunStopException
from .. config.constants import constants
from .. core.colors import color_str
from .utils import read_img, get_img_metadata, validate_image, get_img_file_shape, extension_tif_jpg


class BaseStackAlgo:
    def __init__(self, name, steps_per_frame, float_type=constants.DEFAULT_PY_FLOAT):
        self._name = name
        self._steps_per_frame = steps_per_frame
        self.process = None
        self.filenames = None
        self.shape = None
        self.do_step_callback = False
        if float_type == constants.FLOAT_32:
            self.float_type = np.float32
        elif float_type == constants.FLOAT_64:
            self.float_type = np.float64
        else:
            raise InvalidOptionError(
                "float_type", float_type,
                details=" valid values are FLOAT_32 and FLOAT_64"
            )

    def name(self):
        return self._name

    def init(self, filenames):
        self.filenames = filenames
        first_img_file = ''
        for filename in filenames:
            if os.path.isfile(filename) and extension_tif_jpg(filename):
                first_img_file = filename
                break
        self.shape = get_img_file_shape(first_img_file)

    def total_steps(self, n_frames):
        return self._steps_per_frame * n_frames

    def print_message(self, msg):
        self.process.sub_message_r(color_str(msg, constants.LOG_COLOR_LEVEL_3))

    def read_image_and_update_metadata(self, img_path, metadata):
        img = read_img(img_path)
        if img is None:
            raise ImageLoadError(img_path)
        updated = metadata is None
        if updated:
            metadata = get_img_metadata(img)
        else:
            validate_image(img, *metadata)
        return img, metadata, updated

    def check_running(self, cleanup_callback=None):
        if self.process.callback('check_running', self.process.id, self.process.name) is False:
            if cleanup_callback is not None:
                cleanup_callback()
            raise RunStopException(self.name)

    def after_step(self, step):
        if self.do_step_callback:
            self.process.callback('after_step', self.process.id, self.process.name, step)
