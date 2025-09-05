# pylint: disable=C0114, C0115, C0116, W0718, R0912, R0915, E1101, R0914, R0911, E0606, R0801
import gc
import copy
import math
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import cv2
from ..config.constants import constants
from .. core.exceptions import InvalidOptionError, RunStopException
from .. core.core_utils import make_chunks
from .utils import read_img, img_subsample
from .align import (AlignFramesBase, detect_and_compute_matches, find_transform,
                    check_transform, _cv2_border_mode_map, rescale_trasnsform)


def compose_transforms(t1, t2, transform_type):
    t1 = t1.astype(np.float64)
    t2 = t2.astype(np.float64)
    if transform_type == constants.ALIGN_RIGID:
        t1_homo = np.vstack([t1, [0, 0, 1]])
        t2_homo = np.vstack([t2, [0, 0, 1]])
        result_homo = t2_homo @ t1_homo
        return result_homo[:2, :]
    return t2 @ t1


class AlignFramesParallel(AlignFramesBase):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(enabled=True, feature_config=None, matching_config=None,
                         alignment_config=None, **kwargs)
        self.max_threads = kwargs.get('max_threads', constants.DEFAULT_ALIGN_MAX_THREADS)
        self.chunk_submit = kwargs.get('chunk_submit', constants.DEFAULT_ALIGN_CHUNK_SUBMIT)
        self._img_cache = None
        self._img_locks = None
        self._cache_locks = None
        self._target_indices = None
        self._transforms = None
        self._cumulative_transforms = None

    def check_running(self):
        if self.process.callback(constants.CALLBACK_CHECK_RUNNING,
                                 self.process.id, self.process.name) is False:
            raise RunStopException(self.process.name)

    def cache_img(self, idx):
        with self._cache_locks[idx]:
            self._img_locks[idx] += 1
            if self._img_cache[idx] is None:
                self._img_cache[idx] = read_img(self.process.input_filepath(idx))
            return self._img_cache[idx]

    def submit_threads(self, idxs, imgs):
        with ThreadPoolExecutor(max_workers=len(imgs)) as executor:
            future_to_index = {}
            for idx in idxs:
                self.sub_msg(f": submit image preprocessing: {idx}")
                future = executor.submit(self.extract_features, idx)
                future_to_index[future] = idx
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    info_messages, warning_messages = future.result()
                    message = f": image {idx}: found {self._n_good_matches[idx]} matches"
                    if len(info_messages) > 0:
                        message += ", " + ", ".join(info_messages)
                    color = constants.LOG_COLOR_LEVEL_3
                    if len(warning_messages) > 0:
                        message += ", " + ", ".join(warning_messages)
                        color = constants.LOG_COLOR_WARNING
                    self.sub_msg(message, color=color)
                    self.check_running()
                except Exception as e:
                    traceback.print_tb(e.__traceback__)
                    self.sub_msg(f": failed processing image: {idx}: {str(e)}")
            for i in range(self.process.num_input_filepaths()):
                if self._img_locks[i] == 2:
                    self._img_cache[i] = None
                    self._img_locks[i] = 0
        gc.collect()

    def begin(self, process):
        super().begin(process)
        n_frames = self.process.num_input_filepaths()
        self.sub_msg(f": preprocess {n_frames} images in parallel, {self.max_threads} cores")
        self._img_cache = [None] * n_frames
        self._img_locks = [0] * n_frames
        self._cache_locks = [threading.Lock() for _ in range(n_frames)]
        self._target_indices = [None] * n_frames
        self._n_good_matches = [0] * n_frames
        self._transforms = [None] * n_frames
        self._cumulative_transforms = [None] * n_frames
        max_chunck_size = self.max_threads
        input_filepaths = self.process.input_filepaths()
        ref_idx = self.process.ref_idx
        self.sub_msg(f": reference index: {ref_idx}")
        sub_indices = list(range(n_frames))
        sub_indices.remove(ref_idx)
        sub_img_filepaths = copy.deepcopy(input_filepaths)
        sub_img_filepaths.remove(input_filepaths[ref_idx])
        if self.chunk_submit:
            img_chunks = make_chunks(sub_img_filepaths, max_chunck_size)
            idx_chunks = make_chunks(sub_indices, max_chunck_size)
            for idxs, imgs in zip(idx_chunks, img_chunks):
                self.submit_threads(idxs, imgs)
        else:
            self.submit_threads(sub_indices, sub_img_filepaths)
        for i in range(n_frames):
            if self._img_cache[i] is not None:
                self._img_cache[i] = None
        gc.collect()
        self.sub_msg(": combining transformations")
        transform_type = self.alignment_config['transform']
        if transform_type == constants.ALIGN_RIGID:
            identity = np.array([[1.0, 0.0, 0.0],
                                 [0.0, 1.0, 0.0]], dtype=np.float64)
        else:
            identity = np.eye(3, dtype=np.float64)
        self._cumulative_transforms[ref_idx] = identity
        frames_to_process = []
        for i in range(n_frames):
            if i != ref_idx:
                frames_to_process.append((i, abs(i - ref_idx)))
        frames_to_process.sort(key=lambda x: x[1])
        for i, _ in frames_to_process:
            target_idx = self._target_indices[i]
            if target_idx is not None and self._cumulative_transforms[target_idx] is not None:
                self._cumulative_transforms[i] = compose_transforms(
                    self._transforms[i], self._cumulative_transforms[target_idx], transform_type)
            else:
                self._cumulative_transforms[i] = None
                self.sub_msg(f": warning: no cumulative transform for frame {i}")
        for i in range(n_frames):
            if self._cumulative_transforms[i] is not None:
                self._cumulative_transforms[i] = self._cumulative_transforms[i].astype(np.float32)
        self.sub_msg(": feature extaction completed")

    def extract_features(self, idx, delta=1):
        ref_idx = self.process.ref_idx
        pass_ref_err_msg = "cannot find path to reference frame"
        if idx < ref_idx:
            target_idx = idx + delta
            if target_idx > ref_idx:
                return [], [pass_ref_err_msg]
        elif idx > ref_idx:
            target_idx = idx - delta
            if target_idx < ref_idx:
                return [], [pass_ref_err_msg]
        else:
            return [], []
        info_messages = []
        warning_messages = []
        img_0 = self.cache_img(idx)
        img_ref = self.cache_img(target_idx)
        h0, w0 = img_0.shape[:2]
        subsample = self.alignment_config['subsample']
        if subsample == 0:
            img_res = (float(h0) / constants.ONE_KILO) * (float(w0) / constants.ONE_KILO)
            target_res = constants.DEFAULT_ALIGN_RES_TARGET_MPX
            subsample = int(1 + math.floor(img_res / target_res))
        fast_subsampling = self.alignment_config['fast_subsampling']
        min_good_matches = self.alignment_config['min_good_matches']
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
            info_messages.append("too few matches, no subsampling applied")
        self._n_good_matches[idx] = n_good_matches
        m = None
        min_matches = 4 if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
        if n_good_matches < min_matches:
            return self.extract_features(idx, delta + 1)
        transform = self.alignment_config['transform']
        src_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        m, _msk = find_transform(src_pts, dst_pts, transform, self.alignment_config['align_method'],
                                 *(self.alignment_config[k]
                                   for k in ['rans_threshold', 'max_iters',
                                             'align_confidence', 'refine_iters']))
        h_sub, w_sub = img_0_sub.shape[:2]
        if subsample > 1:
            m = rescale_trasnsform(m, w0, h0, w_sub, h_sub, subsample, transform)
            if m is None:
                warning_messages.append(f" invalid option {transform}")
                return info_messages, warning_messages
        transform_type = self.alignment_config['transform']
        is_valid = True
        affine_thresholds, homography_thresholds = self.get_transform_thresholds()
        is_valid, _reason = check_transform(
            m, img_0, transform_type,
            affine_thresholds, homography_thresholds)
        if not is_valid:
            return self.extract_features(idx, delta + 1)
        self._transforms[idx] = m
        self._target_indices[idx] = target_idx
        return info_messages, warning_messages

    def align_images(self, idx, img_ref, img_0):
        if self._cumulative_transforms[idx] is None:
            self.sub_msg(f": no transformation for frame {idx}, skipping alignment")
            return img_0
        m = self._cumulative_transforms[idx]
        transform_type = self.alignment_config['transform']
        if transform_type == constants.ALIGN_RIGID and m.shape != (2, 3):
            self.sub_msg(f": invalid matrix shape for rigid transform: {m.shape}")
            return img_0
        if transform_type == constants.ALIGN_HOMOGRAPHY and m.shape != (3, 3):
            self.sub_msg(f": invalid matrix shape for homography: {m.shape}")
            return img_0
        self.sub_msg(': apply image alignment')
        try:
            cv2_border_mode = _cv2_border_mode_map[self.alignment_config['border_mode']]
        except KeyError as e:
            raise InvalidOptionError("border_mode", self.alignment_config['border_mode']) from e
        img_mask = np.ones_like(img_0, dtype=np.uint8)
        h_ref, w_ref = img_ref.shape[:2]
        if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY:
            img_warp = cv2.warpPerspective(
                img_0, m, (w_ref, h_ref),
                borderMode=cv2_border_mode, borderValue=self.alignment_config['border_value'])
            if self.alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpPerspective(img_mask, m, (w_ref, h_ref),
                                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        elif self.alignment_config['transform'] == constants.ALIGN_RIGID:
            img_warp = cv2.warpAffine(
                img_0, m, (w_ref, h_ref),
                borderMode=cv2_border_mode, borderValue=self.alignment_config['border_value'])
            if self.alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpAffine(img_mask, m, (w_ref, h_ref),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if self.alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
            self.sub_msg(': blur borders')
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            blurred_warp = cv2.GaussianBlur(
                img_warp, (21, 21), sigmaX=self.alignment_config['border_blur'])
            img_warp[mask == 0] = blurred_warp[mask == 0]
        return img_warp
