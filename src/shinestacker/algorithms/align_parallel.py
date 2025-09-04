import os
import gc
import copy
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..config.constants import constants
from .utils import read_img
from .align import AlignFrames, detect_and_compute_matches


class AlignFramesParallel(AlignFrames):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(enabled=True, feature_config=None, matching_config=None,
                         alignment_config=None, **kwargs)
        self.max_threads = kwargs.get('max_threads', constants.DEFAULT_ALIGN_MAX_THREADS)
        self._img_cache = None
        self._img_locks = None
        self._matches = None

    def cache_img(self, idx):
        self._img_locks[idx] += 1
        if self._img_cache[idx] is None:
            self._img_cache[idx] = read_img(self.process.input_filepath(idx))
        return self._img_cache[idx]

    def begin(self, process):
        super().begin(process)
        n_frames = self.process.num_input_filepaths()
        self.sub_msg(f": preprocess {n_frames} images in parallel, {self.max_threads} cores")
        self._img_cache = [None] * n_frames
        self._img_locks = [0] * n_frames
        self._matches = [(None, None, 0)] * n_frames
        max_chunck_size = self.max_threads
        input_filepaths = self.process.input_filepaths()

        def make_chunks(ll, max_size):
            return [ll[i:i + max_size] for i in range(0, len(ll), max_size)]

        ref_idx = self.process.ref_idx
        self.sub_msg(f": reference index: {ref_idx}")
        sub_indices = list(range(n_frames))
        sub_indices.remove(ref_idx)
        sub_img_filepaths = copy.deepcopy(input_filepaths)
        sub_img_filepaths.remove(input_filepaths[ref_idx])
        img_chunks = make_chunks(sub_img_filepaths, max_chunck_size)
        idx_chunks = make_chunks(sub_indices, max_chunck_size)
        for idxs, imgs in zip(idx_chunks, img_chunks):
            with ThreadPoolExecutor(max_workers=len(imgs)) as executor:
                future_to_index = {}
                for idx in idxs:
                    self.sub_msg(f": submit processing image: {idx}")
                    future = executor.submit(self.extract_features, idx)
                    future_to_index[future] = idx
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        kp_0, kp_ref, good_matches = future.result()
                        self._matches[idx] = (kp_0, kp_ref, good_matches)
                        self.sub_msg(f": found matches, image {idx}: {len(good_matches)}")
                    except Exception as e:
                        traceback.print_tb(e.__traceback__)
                        self.sub_msg(f": failed processing image: {idx}: {str(e)}")
                for i in range(n_frames):
                    if self._img_locks[i] == 2:
                        self._img_cache[i] = None
                        self._img_locks[i] = 0
                        self.sub_msg(f": clear cache: {i}")
            gc.collect()
        for i in range(n_frames):
            if self._img_cache[i] is not None:
                self._img_cache[i] = None
                self.sub_msg(f": clear cache: {i}")      
        gc.collect()

    def extract_features(self, idx):
        ref_idx = self.process.ref_idx
        if ref_idx > idx:
            ref_idx = idx + 1
        elif ref_idx < idx:
            ref_idx = idx - 1
        else:
            return None
        img_0 = self.cache_img(idx)
        img_ref = self.cache_img(ref_idx)
        kp_0, kp_ref, good_matches = detect_and_compute_matches(
            img_ref, img_0, self.feature_config, self.matching_config)
        return kp_0, kp_ref, good_matches

