# pylint: disable=C0114, C0115, C0116, W0718, R0912, R0915, E1101, R0914, R0911, E0606, R0801, R0902
import gc
import os
import copy
import math
import traceback
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from ..config.constants import constants
from .. core.exceptions import RunStopException
from .. core.colors import color_str
from .. core.core_utils import make_chunks
from .utils import read_img, img_subsample, img_bw
from .align import (
    AlignFramesBase, find_transform, find_transform_phase_correlation,
    check_transform, rescale_transform, apply_alignment_transform)
from .feature_match import FeatureMatcher


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
        self.delta_max = kwargs.get('delta_max', constants.DEFAULT_ALIGN_DELTA_MAX)
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
        self.feature_matcher = FeatureMatcher(feature_config, matching_config)

    def relative_transformation(self):
        return True

    def get_img_ref(self, ref_idx):
        return self.process.img_ref(ref_idx)

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
                future = executor.submit(self.find_transform, idx)
                future_to_index[future] = idx
                filename = os.path.basename(self.process.input_filepath(idx))
                self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                      self.process.name, filename, 100)
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                filename = os.path.basename(self.process.input_filepath(idx))
                try:
                    info_messages, warning_messages = future.result()
                    message = f"{self.image_str(idx)}: " \
                              f"matches found: {self._n_good_matches[idx]}"
                    if len(info_messages) > 0:
                        message += ", " + ", ".join(info_messages)
                    color = constants.LOG_COLOR_LEVEL_3
                    level = logging.INFO
                    if len(warning_messages) > 0:
                        message += "; " + color_str("; ".join(warning_messages), 'yellow')
                        color = constants.LOG_COLOR_WARNING
                        level = logging.WARNING
                    self.print_message(message, color=color, level=level)
                    self.step_counter += 1
                    self.process.after_step(self.step_counter)
                    self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                          self.process.name, filename, 101)
                    self.process.check_running()
                except RunStopException as e:
                    self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                          self.process.name, filename, 1001)
                    raise e
                except Exception as e:
                    traceback.print_tb(e.__traceback__)
                    self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                          self.process.name, filename, 1001)
                    self.print_message(
                        f"failed processing {self.image_str(idx)}: {str(e)}")
            cached_images = 0
            for i in range(self.process.num_input_filepaths()):
                if self._img_locks[i] >= 2:
                    self._img_cache[i] = None
                    self._img_locks[i] = 0
                elif self._img_cache[i] is not None:
                    cached_images += 1
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
        ref_filepath = input_filepaths[ref_idx]
        sub_img_filepaths.remove(ref_filepath)
        filename = os.path.basename(ref_filepath)
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.name, filename, 101)
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
        thresholds = self.get_transform_thresholds_large()
        for i in range(n_frames):
            if self._cumulative_transforms[i] is not None:
                self._cumulative_transforms[i] = self._cumulative_transforms[i].astype(np.float32)
                is_valid, reason, result = check_transform(
                    self._cumulative_transforms[i], self._img_shapes[i],
                    transform_type, *thresholds)
                if is_valid:
                    self.save_transform_result(i, result)
                else:
                    self.print_message(
                        f"invalid cumulative transform for {self.image_str(i)}",
                        color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
                if self.alignment_config['abort_abnormal']:
                    self._cumulative_transforms[i] = None
                    raise RuntimeError(f"invalid cumulative transformation: {reason}")
            else:
                missing_transforms += 1
        msg = "feature extaction completed"
        if missing_transforms > 0:
            msg += ", " + color_str(f"images not matched: {missing_transforms}",
                                    constants.LOG_COLOR_WARNING)
        self.print_message(msg)
        self.process.add_begin_steps(n_frames)

    def find_transform(self, idx, delta=1):
        ref_idx = self.process.ref_idx
        if delta > self.delta_max:
            if self.delta_max > 1:
                msg = f"next {self.delta_max} frames not matched, frame skipped"
            else:
                msg = "next frame not matched, frame skipped"
            return [], [msg]
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
            match_result = self.feature_matcher.match_images(img_ref_sub, img_0_sub)
            n_good_matches = match_result.n_good_matches()
            if n_good_matches >= min_good_matches or subsample == 1:
                break
            subsample = 1
            s_str = 'es' if n_good_matches != 1 else ''
            msg = f"{self.image_str(idx)}: only {n_good_matches} < {min_good_matches} " \
                f"match{s_str} found with {self.image_str(target_idx)}, " \
                "retrying without subsampling"
            self.print_message(msg, color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            warning_messages.append("no subsampling applied")
        self._n_good_matches[idx] = n_good_matches
        m = None
        min_matches = 4 if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
        if n_good_matches < min_matches:
            if self.alignment_config['phase_corr_fallback']:
                s_str = 'es' if n_good_matches != 1 else ''
                msg = f"{self.image_str(idx)}: only {n_good_matches} good matches found " \
                    f" with {self.image_str(target_idx)}, using phase correlation as fallback"
                self.print_message(msg, color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
                warning_messages.append("used phase correlation as fallback")
                n_good_matches = 0
                m = find_transform_phase_correlation(img_ref_sub, img_0_sub)
                self._transforms[idx] = m
                self._target_indices[idx] = target_idx
                return info_messages, warning_messages
            s_str = 'es' if n_good_matches != 1 else ''
            msg = f"{self.image_str(idx)}: only {n_good_matches} good match{s_str} found, " \
                  f" with {self.image_str(target_idx)}, trying next frame"
            self.print_message(msg, color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            warning_messages.append(msg)
            return self.find_transform(idx, delta + 1)
        transform = self.alignment_config['transform']
        src_pts = match_result.get_src_points()
        dst_pts = match_result.get_dst_points()
        m, _msk = find_transform(
            src_pts, dst_pts, transform, self.alignment_config['align_method'],
            *(self.alignment_config[k]
              for k in ['rans_threshold', 'max_iters',
                        'align_confidence', 'refine_iters']))
        h_sub, w_sub = img_0_sub.shape[:2]
        if subsample > 1:
            m = rescale_transform(m, w0, h0, w_sub, h_sub, subsample, transform)
            if m is None:
                self.print_message(
                    f"invalid option {transform} "
                    f"for {self.image_str(idx)}, trying next frame",
                    color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
                return self.find_transform(idx, delta + 1)
        transform_type = self.alignment_config['transform']
        thresholds = self.get_transform_thresholds()
        is_valid, _reason, _result = check_transform(m, img_0.shape, transform_type, *thresholds)
        if not is_valid:
            msg = f"invalid transformation for {self.image_str(idx)}"
            do_abort = self.alignment_config['abort_abnormal']
            if not do_abort:
                msg += ", trying next frame"
            self.print_message(
                msg, color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            if do_abort:
                raise RuntimeError("invalid transformation: {reason}")
            return self.find_transform(idx, delta + 1)
        self._transforms[idx] = m
        self._target_indices[idx] = target_idx
        return info_messages, warning_messages

    def align_images(self, idx, img_ref, img_0):
        m = self._cumulative_transforms[idx]
        if m is None:
            self.print_message(
                f"no transformation for {self.image_str(idx)}, image skipped",
                color=constants.LOG_COLOR_WARNING, level=logging.WARNING)
            return None
        callbacks = {
            'estimation_message':
                lambda: self.print_message(f'{self.image_str(idx)}: apply image alignment'),
            'blur_message':
                lambda: self.print_message(f'{self.image_str(idx)}: blur borders'),
            'warning':
                lambda msg: self.print_message(msg, constants.LOG_COLOR_WARNING)
        }
        return apply_alignment_transform(img_0, img_ref, m, self.alignment_config, callbacks)
