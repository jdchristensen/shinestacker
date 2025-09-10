# pylint: disable=C0114, C0115, C0116, W0718, R0912, R0915, E1101, R0914, R0911, E0606, R0801, R0902
import gc
import copy
import math
import traceback
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import cv2
from ..config.constants import constants
from .. core.exceptions import InvalidOptionError, RunStopException
from .. core.colors import color_str
from .. core.core_utils import make_chunks
from .utils import read_img, img_subsample, img_bw, img_bw_8bit
from .align import (AlignFramesBase, find_transform,
                    check_transform, _cv2_border_mode_map, rescale_trasnsform,
                    validate_align_config, detector_map, descriptor_map,
                    get_good_matches)


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
        super().__init__(enabled, feature_config, matching_config,
                         alignment_config, **kwargs)
        self.max_threads = kwargs.get('max_threads', constants.DEFAULT_ALIGN_MAX_THREADS)
        self.chunk_submit = kwargs.get('chunk_submit', constants.DEFAULT_ALIGN_CHUNK_SUBMIT)
        self.bw_matching = kwargs.get('bw_matching', constants.DEFAULT_ALIGN_BW_MATCHING)
        self._img_cache = None
        self._img_shapes = None
        self._img_locks = None
        self._cache_locks = None
        self._target_indices = None
        self._transforms = None
        self._cumulative_transforms = None
        self.step_counter = 0
        self._kp = None
        self._des = None

    def relative_transformation(self):
        return True

    def cache_img(self, idx):
        with self._cache_locks[idx]:
            self._img_locks[idx] += 1
            if self._img_cache[idx] is None:
                img = read_img(self.process.input_filepath(idx))
                if self.bw_matching:
                    img = img_bw(img)
                self._img_cache[idx] = img
                if img is not None:
                    self._img_shapes[idx] = img.shape
            return self._img_cache[idx]

    def submit_threads(self, idxs, imgs):
        with ThreadPoolExecutor(max_workers=len(imgs)) as executor:
            future_to_index = {}
            for idx in idxs:
                self.print_message(
                    f"submit alignment matches, {self.image_str(idx)}")
                future = executor.submit(self.extract_features, idx)
                future_to_index[future] = idx
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    info_messages, warning_messages = future.result()
                    message = f"{self.image_str(idx)}: " \
                              f"matches found: {self._n_good_matches[idx]}"
                    if len(info_messages) > 0:
                        message += ", " + ", ".join(info_messages)
                    color = constants.LOG_COLOR_LEVEL_3
                    level = logging.INFO
                    if len(warning_messages) > 0:
                        message += ", " + color_str(", ".join(warning_messages), 'yellow')
                        color = constants.LOG_COLOR_WARNING
                        level = logging.WARNING
                    self.print_message(message, color=color, level=level)
                    self.step_counter += 1
                    self.process.after_step(self.step_counter)
                    self.process.check_running()
                except RunStopException as e:
                    raise e
                except Exception as e:
                    traceback.print_tb(e.__traceback__)
                    self.print_message(
                        f"failed processing {self.image_str(idx)}: {str(e)}")
            cached_images = 0
            for i in range(self.process.num_input_filepaths()):
                if self._img_locks[i] >= 2:
                    self._img_cache[i] = None
                    self._img_locks[i] = 0
                elif self._img_cache[i] is not None:
                    cached_images += 1
            # self.print_message(f"cached images: {cached_images}")
        gc.collect()

    def begin(self, process):
        super().begin(process)
        if self.plot_matches:
            self.print_message(
                "requested plot matches is not supported with parallel processing",
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
        n_frames = self.process.num_input_filepaths()
        self.print_message(f"preprocess {n_frames} images in parallel, cores: {self.max_threads}")
        self.process.callback(constants.CALLBACK_STEP_COUNTS,
                              self.process.id, self.process.name, 2 * n_frames)
        input_filepaths = self.process.input_filepaths()
        self._img_cache = [None] * n_frames
        self._img_shapes = [None] * n_frames
        self._img_locks = [0] * n_frames
        self._cache_locks = [threading.Lock() for _ in range(n_frames)]
        self._target_indices = [None] * n_frames
        self._n_good_matches = [0] * n_frames
        self._transforms = [None] * n_frames
        self._cumulative_transforms = [None] * n_frames
        self._kp = [None] * n_frames
        self._des = [None] * n_frames
        max_chunck_size = self.max_threads
        ref_idx = self.process.ref_idx
        self.print_message(f"reference: {self.image_str(ref_idx)}")
        sub_indices = list(range(n_frames))
        sub_indices.remove(ref_idx)
        sub_img_filepaths = copy.deepcopy(input_filepaths)
        sub_img_filepaths.remove(input_filepaths[ref_idx])
        self.step_counter = 0
        if self.chunk_submit:
            img_chunks = make_chunks(sub_img_filepaths, max_chunck_size)
            idx_chunks = make_chunks(sub_indices, max_chunck_size)
            for idxs, imgs in zip(idx_chunks, img_chunks):
                self.submit_threads(idxs, imgs)
        else:
            self.submit_threads(sub_indices, sub_img_filepaths)
        for idx in range(n_frames):
            if self._img_cache[idx] is not None:
                self._img_cache[idx] = None
                self._kp[idx] = None
                self._des[idx] = None
        gc.collect()
        self.print_message("combining transformations")
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
                self.print_message(
                    f"warning: no cumulative transform for {self.image_str(i)}",
                    color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
        for idx in range(n_frames):
            self._transforms[idx] = None
        gc.collect()
        missing_transforms = 0
        thresholds = self.get_transform_thresholds()
        for i in range(n_frames):
            if self._cumulative_transforms[i] is not None:
                self._cumulative_transforms[i] = self._cumulative_transforms[i].astype(np.float32)
                is_valid, _reason, result = check_transform(
                    self._cumulative_transforms[i], self._img_shapes[i],
                    transform_type, *thresholds)
                if is_valid:
                    self.save_transform_result(i, result)
                else:
                    self._cumulative_transforms[i] = None
            else:
                missing_transforms += 1
        msg = "feature extaction completed"
        if missing_transforms > 0:
            msg += ", " + color_str(f"images not matched: {missing_transforms}",
                                    constants.LOG_COLOR_WARNING)
        self.print_message(msg)
        self.process.add_begin_steps(n_frames)

    def detect_and_compute_matches(self, img_ref, ref_idx, img_0, idx):
        feature_config, matching_config = self.feature_config, self.matching_config
        feature_config_detector = feature_config['detector']
        feature_config_descriptor = feature_config['descriptor']
        match_method = matching_config['match_method']
        validate_align_config(feature_config_detector, feature_config_descriptor, match_method)
        img_bw_0, img_bw_ref = img_bw_8bit(img_0), img_bw_8bit(img_ref)
        detector = detector_map[feature_config_detector]()
        if feature_config_detector == feature_config_descriptor and \
           feature_config_detector in (constants.DETECTOR_SIFT,
                                       constants.DETECTOR_AKAZE,
                                       constants.DETECTOR_BRISK):
            if self._kp[idx] is None or self._des[idx] is None:
                kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
            else:
                kp_0, des_0 = self._kp[idx], self._des[idx]
            if self._kp[ref_idx] is None or self._des[ref_idx] is None:
                kp_ref, des_ref = detector.detectAndCompute(img_bw_ref, None)
            else:
                kp_ref, des_ref = self._kp[ref_idx], self._des[ref_idx]
        else:
            descriptor = descriptor_map[feature_config_descriptor]()
            kp_0, des_0 = descriptor.compute(img_bw_0, detector.detect(img_bw_0, None))
            kp_ref, des_ref = descriptor.compute(img_bw_ref, detector.detect(img_bw_ref, None))
        return kp_0, kp_ref, get_good_matches(des_0, des_ref, matching_config)

    def extract_features(self, idx, delta=1):
        ref_idx = self.process.ref_idx
        pass_ref_err_msg = "cannot find path to reference frame"
        if idx < ref_idx:
            target_idx = idx + delta
            if target_idx > ref_idx:
                self._target_indices[idx] = None
                self._transforms[idx] = None
                return [], [pass_ref_err_msg]
        elif idx > ref_idx:
            target_idx = idx - delta
            if target_idx < ref_idx:
                self._target_indices[idx] = None
                self._transforms[idx] = None
                return [], [pass_ref_err_msg]
        else:
            self._target_indices[idx] = None
            self._transforms[idx] = None
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
            kp_0, kp_ref, good_matches = self.detect_and_compute_matches(
                img_ref_sub, ref_idx, img_0_sub, idx)
            n_good_matches = len(good_matches)
            if n_good_matches > min_good_matches or subsample == 1:
                break
            subsample = 1
            warning_messages.append("too few matches, no subsampling applied")
        self._n_good_matches[idx] = n_good_matches
        m = None
        min_matches = 4 if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
        if n_good_matches < min_matches:
            self.print_message(
                f"warning: only {n_good_matches} found for "
                f"{self.image_str(idx)}, trying next frame",
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
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
                self.print_message(
                    f"invalid option {transform} "
                    f"for {self.image_str(idx)}, trying next frame",
                    color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
                return self.extract_features(idx, delta + 1)
        transform_type = self.alignment_config['transform']
        thresholds = self.get_transform_thresholds()
        is_valid, _reason, _result = check_transform(m, img_0.shape, transform_type, *thresholds)
        # self.save_transform_result(idx, result)
        if not is_valid:
            msg = f"invalid transformation for {self.image_str(idx)}"
            do_abort = self.alignment_config['abort_abnormal']
            if not do_abort:
                msg += ", trying next frame"
            self.print_message(
                msg, color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            if do_abort:
                raise RuntimeError("invalid transformation: {reason}")
            return self.extract_features(idx, delta + 1)
        self._transforms[idx] = m
        self._target_indices[idx] = target_idx
        return info_messages, warning_messages

    def align_images(self, idx, img_ref, img_0):
        m = self._cumulative_transforms[idx]
        if m is None:
            self.print_message(
                f"no transformation for {self.image_str(idx)}, skipping alignment",
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            return img_0
        transform_type = self.alignment_config['transform']
        if transform_type == constants.ALIGN_RIGID and m.shape != (2, 3):
            self.print_message(f"invalid matrix shape for rigid transform: {m.shape}")
            return img_0
        if transform_type == constants.ALIGN_HOMOGRAPHY and m.shape != (3, 3):
            self.print_message(f"invalid matrix shape for homography: {m.shape}")
            return img_0
        self.print_message(f'{self.image_str(idx)}: apply image alignment')
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
            self.print_message(f'{self.image_str(idx)}: blur borders')
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            blurred_warp = cv2.GaussianBlur(
                img_warp, (21, 21), sigmaX=self.alignment_config['border_blur'])
            img_warp[mask == 0] = blurred_warp[mask == 0]
        return img_warp
