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
from .align import (AlignFramesBase, detect_and_compute_matches, find_transform,
                    check_affine_matrix, check_homography_distortion, _cv2_border_mode_map)


def compose_transforms(T1, T2, transform_type):
    T1 = T1.astype(np.float64)
    T2 = T2.astype(np.float64)
    
    if transform_type == constants.ALIGN_RIGID:
        # Convert affine matrices to homogeneous coordinates
        T1_homo = np.vstack([T1, [0, 0, 1]])
        T2_homo = np.vstack([T2, [0, 0, 1]])
        
        # Compose transformations: T2 after T1
        result_homo = T2_homo @ T1_homo
        
        # Convert back to affine
        return result_homo[:2, :].astype(np.float32)
    else:
        # For homography, direct matrix multiplication
        return (T2 @ T1).astype(np.float32)


class AlignFramesParallel(AlignFramesBase):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(enabled=True, feature_config=None, matching_config=None,
                         alignment_config=None, **kwargs)
        self.max_threads = kwargs.get('max_threads', constants.DEFAULT_ALIGN_MAX_THREADS)
        self._img_cache = None
        self._img_locks = None
        self._transforms = None
        self._cumulative_transforms = None

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
        self._n_good_matches = [0] * n_frames
        self._transforms = [None] * n_frames
        self._cumulative_transforms = [None] * n_frames
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
                        info_messages, warning_messages = future.result()
                        message = f": found matches, image {idx}: {self._n_good_matches[idx]}"
                        if len(info_messages) > 0:
                            message += ", ".join(info_messages) 
                        color=constants.LOG_COLOR_LEVEL_3
                        if len(warning_messages) > 0:
                            message += ", ".join(warning_message) 
                            color=constants.LOG_COLOR_WARNING
                        self.sub_msg(message, color=color)
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
        self.sub_msg(": combining transformations")
        transform_type = self.alignment_config['transform']
        # Set identity for reference frame
        if transform_type == constants.ALIGN_RIGID:
            identity = np.array([[1.0, 0.0, 0.0], 
                                 [0.0, 1.0, 0.0]], dtype=np.float32)
        else:
            identity = np.eye(3, dtype=np.float32)

        self._cumulative_transforms[ref_idx] = identity
        # Forward pass for indices less than reference
        for i in range(ref_idx - 1, -1, -1):
            if self._transforms[i] is not None and self._cumulative_transforms[i + 1] is not None:
                self._cumulative_transforms[i] = compose_transforms(
                    self._transforms[i], self._cumulative_transforms[i + 1], transform_type)
            else:
                self._cumulative_transforms[i] = None
                self.sub_msg(f": warning: no transform for frame {i}")

        # Backward pass for indices greater than reference
        for i in range(ref_idx + 1, n_frames):
            if self._transforms[i] is not None and self._cumulative_transforms[i - 1] is not None:
                self._cumulative_transforms[i] = compose_transforms(
                    self._transforms[i], self._cumulative_transforms[i - 1], transform_type)
            else:
                self._cumulative_transforms[i] = None
                self.sub_msg(f": warning: no transform for frame {i}")
        self.sub_msg(": feature extaction completed")

    def extract_features(self, idx):
        ref_idx = self.process.ref_idx
        if ref_idx > idx:
            delta_idx = +1
        elif ref_idx < idx:
            delta_idx = -1
        else:
            return ''
        info_messages = []
        warning_messages = []
        ref_idx = idx
        ref_idx += delta_idx
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
            info_messages.append("no subsampling applied")
        self._n_good_matches[idx] = n_good_matches
        m = None
        min_matches = 4 if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
        if n_good_matches < min_matches:
            warning_messages.append("too few matches")
            return ",".join(warning_messages)
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
                warning_messages.append("invalid transform type specified")
                return ",".join(warning_messages)
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
            warning_messages.appen("invalid transform found")
        else:
            self._transforms[idx] = m
        return info_messages, warning_messages

    def align_images(self, idx, img_ref, img_0):
        if self._cumulative_transforms[idx] is None:
            self.sub_msg(f": no transformation for frame {idx}, skipping alignment")
            return img_0
        m = self._cumulative_transforms[idx]
        transform_type = self.alignment_config['transform']
        
        # Validate matrix dimensions
        if transform_type == constants.ALIGN_RIGID and m.shape != (2, 3):
            self.sub_msg(f": invalid matrix shape for rigid transform: {m.shape}")
            return img_0
        elif transform_type == constants.ALIGN_HOMOGRAPHY and m.shape != (3, 3):
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

