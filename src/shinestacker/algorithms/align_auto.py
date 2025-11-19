# pylint: disable=C0114, C0115, C0116, W0718, R0912, R0915, E1101, R0914, R0911, E0606, R0801, R0902
import os
import numpy as np
from ..config.constants import constants
from ..config.defaults import DEFAULTS
from .align import AlignFramesBase, AlignFrames
from .align_parallel import AlignFramesParallel
from .utils import get_first_image_file, get_img_metadata, read_img


class AlignFramesAuto(AlignFramesBase):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        self.mode = kwargs.pop(
            'mode', DEFAULTS['align_frames_params']['align_mode'])
        self.memory_limit = kwargs.pop(
            'memory_limit', DEFAULTS['align_frames_params']['memory_limit'])
        self.max_threads = kwargs.pop(
            'max_threads', DEFAULTS['align_frames_params']['max_threads'])
        self.chunk_submit = kwargs.pop(
            'chunk_submit', DEFAULTS['align_frames_params']['chunk_submit'])
        self.bw_matching = kwargs.pop(
            'bw_matching', DEFAULTS['align_frames_params']['bw_matching'])
        self.kwargs = kwargs
        super().__init__(enabled=enabled, feature_config=None, matching_config=None,
                         alignment_config=None, **kwargs)
        available_cores = os.cpu_count() or 1
        self.num_threads = min(self.max_threads, available_cores)
        self._implementation = None
        self.overhead = 30.0
        self.mem_per_gpx_sift = 0.1

    def begin(self, process):
        if not self.enabled:
            return
        if self.mode == 'sequential' or self.num_threads == 1:
            num_threads = 1
        else:
            if self.mode == 'parallel':
                num_threads = self.num_threads
                chunk_submit = self.chunk_submit
            else:
                default_detector = DEFAULTS['align_frames_params']['detector']
                default_descriptor = DEFAULTS['align_frames_params']['descriptor']
                if self.feature_config is not None:
                    detector = self.feature_config.get('detector', default_detector)
                    descriptor = self.feature_config.get('descriptor', default_descriptor)
                else:
                    detector = default_detector
                    descriptor = default_descriptor
                if detector in (constants.DETECTOR_SIFT, constants.DETECTOR_AKAZE) or \
                        descriptor in (constants.DESCRIPTOR_SIFT, constants.DESCRIPTOR_AKAZE):
                    shape, dtype = get_img_metadata(read_img(
                        get_first_image_file(process.input_filepaths())))
                    img_pxls = shape[0] * shape[1]
                    mem_gb = img_pxls / constants.ONE_MEGA * self.mem_per_gpx_sift * \
                        np.dtype(dtype).itemsize
                    num_threads = min(self.num_threads, int(self.memory_limit / mem_gb))
                    num_threads = min(num_threads, self.num_threads)
                    chunk_submit = True
                else:
                    num_threads = self.num_threads
                    chunk_submit = self.chunk_submit
        if num_threads > 1:
            self._implementation = AlignFramesParallel(
                self.enabled, self.feature_config, self.matching_config, self.alignment_config,
                max_threads=num_threads, chunk_submit=chunk_submit,
                bw_matching=self.bw_matching,
                **self.kwargs)
        else:
            self._implementation = AlignFrames(
                self.enabled, self.feature_config, self.matching_config, self.alignment_config,
                **self.kwargs)
        self._implementation.begin(process)

    def align_images(self, idx, img_ref, img_0):
        return self._implementation.align_images(idx, img_ref, img_0)

    def run_frame(self, idx, ref_idx, img_0):
        return self._implementation.run_frame(idx, ref_idx, img_0)

    def sequential_processing(self):
        if self.enabled:
            return self._implementation.sequential_processing()
        return False

    def end(self):
        self._implementation.end()
