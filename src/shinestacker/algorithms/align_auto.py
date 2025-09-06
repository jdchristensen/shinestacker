# pylint: disable=C0114, C0115, C0116, W0718, R0912, R0915, E1101, R0914, R0911, E0606, R0801, R0902
import os
from ..config.constants import constants
from .align import AlignFramesBase, AlignFrames
from .align_parallel import AlignFramesParallel


class AlignFramesAuto(AlignFramesBase):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(enabled=True, feature_config=None, matching_config=None,
                         alignment_config=None, **kwargs)
        self.mode = kwargs.pop('mode', constants.DEFAULT_ALIGN_MODE)
        self.max_threads = kwargs.pop('max_threads', constants.DEFAULT_ALIGN_MAX_THREADS)
        self.chunk_submit = kwargs.pop('chunk_submit', constants.DEFAULT_ALIGN_CHUNK_SUBMIT)
        self.bw_matching = kwargs.pop('bw_matching', constants.DEFAULT_ALIGN_BW_MATCHING)
        self.kwargs = kwargs
        available_cores = os.cpu_count() or 1
        self.num_threads = min(self.max_threads, available_cores)
        self._implementation = None

    def begin(self, process):
        if self.mode == 'sequential' or self.num_threads == 1:
            self._implementation = AlignFrames(
                self.enabled, self.feature_config, self.matching_config, self.alignment_config,
                **self.kwargs)
        else:
            if self.mode == 'parallel':
                num_threads = self.num_threads
                chunk_submit = self.chunk_submit
            else:
                if self.feature_config is not None:
                    detector = self.feature_config.get(
                        'detector', constants.DEFAULT_DETECTOR)
                    descriptor = self.feature_config.get(
                        'descriptor', constants.DEFAULT_DESCRIPTOR)
                else:
                    detector = constants.DEFAULT_DETECTOR
                    descriptor = constants.DEFAULT_DESCRIPTOR
                if detector in (constants.DETECTOR_SIFT, constants.DETECTOR_AKAZE) or \
                        descriptor in (constants.DESCRIPTOR_SIFT, constants.DESCRIPTOR_AKAZE):
                    num_threads = min(3, self.num_threads)
                    chunk_submit = True
                else:
                    num_threads = self.num_threads
                    chunk_submit = self.chunk_submit
            self._implementation = AlignFramesParallel(
                self.enabled, self.feature_config, self.matching_config, self.alignment_config,
                max_threads=num_threads, chunk_submit=chunk_submit,
                bw_matching=self.bw_matching,
                **self.kwargs)
        self._implementation.begin(process)

    def align_images(self, idx, img_ref, img_0):
        return self._implementation.align_images(idx, img_ref, img_0)

    def run_frame(self, idx, ref_idx, img_0):
        return self._implementation.run_frame(idx, ref_idx, img_0)

    def sequential_processing(self):
        return self._implementation.sequential_processing()

    def end(self):
        self._implementation.end()
