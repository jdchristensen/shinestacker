import gc
import copy
import math
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import cv2
from ..config.constants import constants
from .. core.exceptions import InvalidOptionError
from .utils import read_img, img_subsample
from .align import (AlignFrames, detect_and_compute_matches, find_transform,
                    check_affine_matrix, check_homography_distortion)


class AlignFramesParallel(AlignFrames):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(enabled=True, feature_config=None, matching_config=None,
                         alignment_config=None, **kwargs)
        self.max_threads = kwargs.get('max_threads', constants.DEFAULT_ALIGN_MAX_THREADS)
        self._img_cache = None
        self._img_locks = None
        self._good_matches = None
        self._transforms = None

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
        self._good_matches = [0] * n_frames
        self._transforms = [None] * n_frames
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
                        ret_message = future.result()
                        message = f": found matches, image {idx}: {self._good_matches[idx]}"
                        color=constants.LOG_COLOR_LEVEL_3
                        if ret_message != '':
                            message += f", {ret_message}"
                            color=constants.LOG_COLOR_WARNING
                        self.sub_msg(message, color=color)
                        # if plot_path is not None:
                        #    matches_mask = msk.ravel().tolist()
                        #    img_match = cv2.cvtColor(cv2.drawMatches(
                        #        img_8bit(img_0_sub), kp_0, img_8bit(img_ref_sub),
                        #        kp_ref, good_matches, None, matchColor=(0, 255, 0),
                        #        singlePointColor=None, matchesMask=matches_mask,
                        #        flags=2), cv2.COLOR_BGR2RGB)
                        #    plt.figure(figsize=constants.PLT_FIG_SIZE)
                        #    plt.imshow(img_match, 'gray')
                        #    save_plot(plot_path)
                        #    if callbacks and 'save_plot' in callbacks:
                        #        callbacks['save_plot'](plot_path)

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

        h_ref, w_ref = img_ref.shape[:2]
        h0, w0 = img_0.shape[:2]
        subsample = self.alignment_config['subsample']
        if subsample == 0:
            img_res = (float(h0) / constants.ONE_KILO) * (float(w0) / constants.ONE_KILO)
            target_res = constants.DEFAULT_ALIGN_RES_TARGET_MPX
            subsample = int(1 + math.floor(img_res / target_res))
        fast_subsampling = self.alignment_config['fast_subsampling']
        min_good_matches = self.alignment_config['min_good_matches']
        messages = []
        while True:
            if subsample > 1:
                img_0_sub = img_subsample(img_0, subsample, fast_subsampling)
                img_ref_sub = img_subsample(img_ref, subsample, fast_subsampling)
            else:
                img_0_sub, img_ref_sub = img_0, img_ref
            kp_0, kp_ref, good_matches = detect_and_compute_matches(
                img_ref_sub, img_0_sub, self.feature_config, self.matching_config)
            n_good_matches = len(good_matches)
            if n_good_matches > min_good_matches or subsample == 1:
                break
            subsample = 1
            messages.append("no subsampling applied")

        m = None
        min_matches = 4 if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3

        if n_good_matches >= min_matches:
            transform = self.alignment_config['transform']
            src_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            m, msk = find_transform(src_pts, dst_pts, transform, self.alignment_config['align_method'],
                                    *(self.alignment_config[k]
                                      for k in ['rans_threshold', 'max_iters',
                                                'align_confidence', 'refine_iters']))

            h_sub, w_sub = img_0_sub.shape[:2]
            if subsample > 1:
                if transform == constants.ALIGN_HOMOGRAPHY:
                    low_size = np.float32([[0, 0], [0, h_sub], [w_sub, h_sub], [w_sub, 0]])
                    high_size = np.float32([[0, 0], [0, h0], [w0, h0], [w0, 0]])
                    scale_up = cv2.getPerspectiveTransform(low_size, high_size)
                    scale_down = cv2.getPerspectiveTransform(high_size, low_size)
                    m = scale_up @ m @ scale_down
                elif transform == constants.ALIGN_RIGID:
                    rotation = m[:2, :2]
                    translation = m[:, 2]
                    translation_fullres = translation * subsample
                    m = np.empty((2, 3), dtype=np.float32)
                    m[:2, :2] = rotation
                    m[:, 2] = translation_fullres
                else:
                    messages.append("invalid transform")
                    return None, None, None, ",".join(messages)

            transform_type = self.alignment_config['transform']
            is_valid = True
            reason = ""
            if self.alignment_config['abort_abnormal']:
                affine_thresholds = _AFFINE_THRESHOLDS
                homography_thresholds = _HOMOGRAPHY_THRESHOLDS
            else:
                affine_thresholds = None
                homography_thresholds = None
            if transform_type == constants.ALIGN_RIGID:
                is_valid, reason = check_affine_matrix(
                    m, img_0.shape, affine_thresholds)
            elif transform_type == constants.ALIGN_HOMOGRAPHY:
                is_valid, reason = check_homography_distortion(
                    m, img_0.shape, homography_thresholds)
            if not is_valid:
                messages.appen("invalid transform")
                return None, None, None, ",".join(messages)
        self._good_matches[idx] = len(good_matches)
        self._transforms[idx] = m
        return ",".join(messages)
