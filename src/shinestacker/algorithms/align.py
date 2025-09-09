# pylint: disable=C0114, C0115, C0116, E1101, R0914, R0913, R0917, R0912, R0915, R0902, E1121, W0102
import os
import math
import logging
import numpy as np
import cv2
import matplotlib.pyplot as plt
from .. config.constants import constants
from .. core.exceptions import InvalidOptionError
from .. core.colors import color_str
from .. core.core_utils import setup_matplotlib_mode
from .utils import img_8bit, img_bw_8bit, save_plot, img_subsample
from .stack_framework import SubAction
setup_matplotlib_mode()

_DEFAULT_FEATURE_CONFIG = {
    'detector': constants.DEFAULT_DETECTOR,
    'descriptor': constants.DEFAULT_DESCRIPTOR
}

_DEFAULT_MATCHING_CONFIG = {
    'match_method': constants.DEFAULT_MATCHING_METHOD,
    'flann_idx_kdtree': constants.DEFAULT_FLANN_IDX_KDTREE,
    'flann_trees': constants.DEFAULT_FLANN_TREES,
    'flann_checks': constants.DEFAULT_FLANN_CHECKS,
    'threshold': constants.DEFAULT_ALIGN_THRESHOLD,
}

_DEFAULT_ALIGNMENT_CONFIG = {
    'transform': constants.DEFAULT_TRANSFORM,
    'align_method': constants.DEFAULT_ALIGN_METHOD,
    'rans_threshold': constants.DEFAULT_RANS_THRESHOLD,
    'refine_iters': constants.DEFAULT_REFINE_ITERS,
    'align_confidence': constants.DEFAULT_ALIGN_CONFIDENCE,
    'max_iters': constants.DEFAULT_ALIGN_MAX_ITERS,
    'abort_abnormal': constants.DEFAULT_ALIGN_ABORT_ABNORMAL,
    'border_mode': constants.DEFAULT_BORDER_MODE,
    'border_value': constants.DEFAULT_BORDER_VALUE,
    'border_blur': constants.DEFAULT_BORDER_BLUR,
    'subsample': constants.DEFAULT_ALIGN_SUBSAMPLE,
    'fast_subsampling': constants.DEFAULT_ALIGN_FAST_SUBSAMPLING,
    'min_good_matches': constants.DEFAULT_ALIGN_MIN_GOOD_MATCHES
}


_cv2_border_mode_map = {
    constants.BORDER_CONSTANT: cv2.BORDER_CONSTANT,
    constants.BORDER_REPLICATE: cv2.BORDER_REPLICATE,
    constants.BORDER_REPLICATE_BLUR: cv2.BORDER_REPLICATE
}

_AFFINE_THRESHOLDS = {
    'max_rotation': 10.0,  # degrees
    'min_scale': 0.9,
    'max_scale': 1.1,
    'max_shear': 5.0,  # degrees
    'max_translation_ratio': 0.1,  # 10% of image dimension
}

_HOMOGRAPHY_THRESHOLDS = {
    'max_skew': 10.0,  # degrees
    'max_scale_change': 1.5,  # max area change ratio
    'max_aspect_ratio': 2.0,  # max aspect ratio change
}


def decompose_affine_matrix(m):
    a, b, tx = m[0, 0], m[0, 1], m[0, 2]
    c, d, ty = m[1, 0], m[1, 1], m[1, 2]
    scale_x = math.sqrt(a**2 + b**2)
    scale_y = math.sqrt(c**2 + d**2)
    rotation = math.degrees(math.atan2(b, a))
    shear = math.degrees(math.atan2(-c, d)) - rotation
    shear = (shear + 180) % 360 - 180
    return (scale_x, scale_y), rotation, shear, (tx, ty)


def check_affine_matrix(m, img_shape, affine_thresholds=_AFFINE_THRESHOLDS):
    if affine_thresholds is None:
        return True, "No thresholds provided", None
    (scale_x, scale_y), rotation, shear, (tx, ty) = decompose_affine_matrix(m)
    h, w = img_shape[:2]
    reasons = []
    if abs(rotation) > affine_thresholds['max_rotation']:
        reasons.append(f"rotation too large ({rotation:.1f}°)")
    if scale_x < affine_thresholds['min_scale'] or scale_x > affine_thresholds['max_scale']:
        reasons.append(f"x-scale out of range ({scale_x:.2f})")
    if scale_y < affine_thresholds['min_scale'] or scale_y > affine_thresholds['max_scale']:
        reasons.append(f"y-scale out of range ({scale_y:.2f})")
    if abs(shear) > affine_thresholds['max_shear']:
        reasons.append(f"shear too large ({shear:.1f}°)")
    max_tx = w * affine_thresholds['max_translation_ratio']
    max_ty = h * affine_thresholds['max_translation_ratio']
    if abs(tx) > max_tx:
        reasons.append(f"x-translation too large (|{tx:.1f}| > {max_tx:.1f})")
    if abs(ty) > max_ty:
        reasons.append(f"y-translation too large (|{ty:.1f}| > {max_ty:.1f})")
    if reasons:
        return False, "; ".join(reasons), None
    return True, "Transformation within acceptable limits", \
        (scale_x, scale_y, tx, ty, rotation, shear)


def check_homography_distortion(m, img_shape, homography_thresholds=_HOMOGRAPHY_THRESHOLDS):
    if homography_thresholds is None:
        return True, "No thresholds provided", None
    h, w = img_shape[:2]
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(corners.reshape(1, -1, 2), m).reshape(-1, 2)
    reasons = []
    area_orig = w * h
    area_new = cv2.contourArea(transformed)
    area_ratio = area_new / area_orig
    if area_ratio > homography_thresholds['max_scale_change'] or \
       area_ratio < 1.0 / homography_thresholds['max_scale_change']:
        reasons.append(f"area change too large ({area_ratio:.2f})")
    rect = cv2.minAreaRect(transformed.astype(np.float32))
    (w_rect, h_rect) = rect[1]
    aspect_ratio = max(w_rect, h_rect) / min(w_rect, h_rect)
    if aspect_ratio > homography_thresholds['max_aspect_ratio']:
        reasons.append(f"aspect ratio change too large ({aspect_ratio:.2f})")
    angles = []
    for i in range(4):
        vec1 = transformed[(i + 1) % 4] - transformed[i]
        vec2 = transformed[(i - 1) % 4] - transformed[i]
        angle = np.degrees(np.arccos(np.dot(vec1, vec2) /
                           (np.linalg.norm(vec1) * np.linalg.norm(vec2))))
        angles.append(angle)
    max_angle_dev = max(abs(angle - 90) for angle in angles)
    if max_angle_dev > homography_thresholds['max_skew']:
        reasons.append(f"angle distortion too large ({max_angle_dev:.1f}°)")
    if reasons:
        return False, "; ".join(reasons), None
    return True, "Transformation within acceptable limits", \
        (area_ratio, aspect_ratio, max_angle_dev)


def check_transform(m, img_shape, transform_type,
                    affine_thresholds, homography_thresholds):
    if transform_type == constants.ALIGN_RIGID:
        return check_affine_matrix(
            m, img_shape, affine_thresholds)
    if transform_type == constants.ALIGN_HOMOGRAPHY:
        return check_homography_distortion(
            m, img_shape, homography_thresholds)
    return False, f'invalid transfrom option {transform_type}', None


def get_good_matches(des_0, des_ref, matching_config=None):
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    match_method = matching_config['match_method']
    good_matches = []
    if match_method == constants.MATCHING_KNN:
        flann = cv2.FlannBasedMatcher(
            {'algorithm': matching_config['flann_idx_kdtree'],
             'trees': matching_config['flann_trees']},
            {'checks': matching_config['flann_checks']})
        matches = flann.knnMatch(des_0, des_ref, k=2)
        good_matches = [m for m, n in matches
                        if m.distance < matching_config['threshold'] * n.distance]
    elif match_method == constants.MATCHING_NORM_HAMMING:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        good_matches = sorted(bf.match(des_0, des_ref), key=lambda x: x.distance)
    else:
        raise InvalidOptionError(
            'match_method', match_method,
            f". Valid options are: {constants.MATCHING_KNN}, {constants.MATCHING_NORM_HAMMING}"
        )
    return good_matches


def validate_align_config(detector, descriptor, match_method):
    if descriptor == constants.DESCRIPTOR_SIFT and match_method == constants.MATCHING_NORM_HAMMING:
        raise ValueError("Descriptor SIFT requires matching method KNN")
    if detector == constants.DETECTOR_ORB and descriptor == constants.DESCRIPTOR_AKAZE and \
            match_method == constants.MATCHING_NORM_HAMMING:
        raise ValueError("Detector ORB and descriptor AKAZE require matching method KNN")
    if detector == constants.DETECTOR_BRISK and descriptor == constants.DESCRIPTOR_AKAZE:
        raise ValueError("Detector BRISK is incompatible with descriptor AKAZE")
    if detector == constants.DETECTOR_SURF and descriptor == constants.DESCRIPTOR_AKAZE:
        raise ValueError("Detector SURF is incompatible with descriptor AKAZE")
    if detector == constants.DETECTOR_SIFT and descriptor != constants.DESCRIPTOR_SIFT:
        raise ValueError("Detector SIFT requires descriptor SIFT")
    if detector in constants.NOKNN_METHODS['detectors'] and \
       descriptor in constants.NOKNN_METHODS['descriptors'] and \
       match_method != constants.MATCHING_NORM_HAMMING:
        raise ValueError(f"Detector {detector} and descriptor {descriptor}"
                         " require matching method Hamming distance")


detector_map = {
    constants.DETECTOR_SIFT: cv2.SIFT_create,
    constants.DETECTOR_ORB: cv2.ORB_create,
    constants.DETECTOR_SURF: cv2.FastFeatureDetector_create,
    constants.DETECTOR_AKAZE: cv2.AKAZE_create,
    constants.DETECTOR_BRISK: cv2.BRISK_create
}

descriptor_map = {
    constants.DESCRIPTOR_SIFT: cv2.SIFT_create,
    constants.DESCRIPTOR_ORB: cv2.ORB_create,
    constants.DESCRIPTOR_AKAZE: cv2.AKAZE_create,
    constants.DETECTOR_BRISK: cv2.BRISK_create
}


def detect_and_compute_matches(img_ref, img_0, feature_config=None, matching_config=None):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
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
        kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
        kp_ref, des_ref = detector.detectAndCompute(img_bw_ref, None)
    else:
        descriptor = descriptor_map[feature_config_descriptor]()
        kp_0, des_0 = descriptor.compute(img_bw_0, detector.detect(img_bw_0, None))
        kp_ref, des_ref = descriptor.compute(img_bw_ref, detector.detect(img_bw_ref, None))
    return kp_0, kp_ref, get_good_matches(des_0, des_ref, matching_config)


def find_transform(src_pts, dst_pts, transform=constants.DEFAULT_TRANSFORM,
                   method=constants.DEFAULT_ALIGN_METHOD,
                   rans_threshold=constants.DEFAULT_RANS_THRESHOLD,
                   max_iters=constants.DEFAULT_ALIGN_MAX_ITERS,
                   align_confidence=constants.DEFAULT_ALIGN_CONFIDENCE,
                   refine_iters=constants.DEFAULT_REFINE_ITERS):
    if method == 'RANSAC':
        cv2_method = cv2.RANSAC
    elif method == 'LMEDS':
        cv2_method = cv2.LMEDS
    else:
        raise InvalidOptionError(
            'align_method', method,
            f". Valid options are: {constants.ALIGN_RANSAC}, {constants.ALIGN_LMEDS}"
        )
    if transform == constants.ALIGN_HOMOGRAPHY:
        result = cv2.findHomography(src_pts, dst_pts, method=cv2_method,
                                    ransacReprojThreshold=rans_threshold,
                                    maxIters=max_iters)
    elif transform == constants.ALIGN_RIGID:
        result = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2_method,
                                             ransacReprojThreshold=rans_threshold,
                                             confidence=align_confidence / 100.0,
                                             refineIters=refine_iters)
    else:
        raise InvalidOptionError(
            'transform', method,
            f". Valid options are: {constants.ALIGN_HOMOGRAPHY}, {constants.ALIGN_RIGID}"
        )
    return result


def rescale_trasnsform(m, w0, h0, w_sub, h_sub, subsample, transform):
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
        return 0
    return m


def plot_matches(msk, img_ref_sub, img_0_sub, kp_ref, kp_0, good_matches, plot_path):
    matches_mask = msk.ravel().tolist()
    img_match = cv2.cvtColor(cv2.drawMatches(
        img_8bit(img_0_sub), kp_0, img_8bit(img_ref_sub),
        kp_ref, good_matches, None, matchColor=(0, 255, 0),
        singlePointColor=None, matchesMask=matches_mask,
        flags=2), cv2.COLOR_BGR2RGB)
    plt.figure(figsize=constants.PLT_FIG_SIZE)
    plt.imshow(img_match, 'gray')
    save_plot(plot_path)


def align_images(img_ref, img_0, feature_config=None, matching_config=None, alignment_config=None,
                 plot_path=None, callbacks=None,
                 affine_thresholds=_AFFINE_THRESHOLDS,
                 homography_thresholds=_HOMOGRAPHY_THRESHOLDS):
    feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
    try:
        cv2_border_mode = _cv2_border_mode_map[alignment_config['border_mode']]
    except KeyError as e:
        raise InvalidOptionError("border_mode", alignment_config['border_mode']) from e
    min_matches = 4 if alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
    if callbacks and 'message' in callbacks:
        callbacks['message']()
    h_ref, w_ref = img_ref.shape[:2]
    h0, w0 = img_0.shape[:2]
    subsample = alignment_config['subsample']
    if subsample == 0:
        img_res = (float(h0) / constants.ONE_KILO) * (float(w0) / constants.ONE_KILO)
        target_res = constants.DEFAULT_ALIGN_RES_TARGET_MPX
        subsample = int(1 + math.floor(img_res / target_res))
    fast_subsampling = alignment_config['fast_subsampling']
    min_good_matches = alignment_config['min_good_matches']
    while True:
        if subsample > 1:
            img_0_sub = img_subsample(img_0, subsample, fast_subsampling)
            img_ref_sub = img_subsample(img_ref, subsample, fast_subsampling)
        else:
            img_0_sub, img_ref_sub = img_0, img_ref
        kp_0, kp_ref, good_matches = detect_and_compute_matches(
            img_ref_sub, img_0_sub, feature_config, matching_config)
        n_good_matches = len(good_matches)
        if n_good_matches > min_good_matches or subsample == 1:
            break
        subsample = 1
        if callbacks and 'warning' in callbacks:
            callbacks['warning'](
                f"only {n_good_matches} < {min_good_matches} matches found, "
                "retrying without subsampling")
    if callbacks and 'matches_message' in callbacks:
        callbacks['matches_message'](n_good_matches)
    img_warp = None
    m = None
    if n_good_matches >= min_matches:
        transform = alignment_config['transform']
        src_pts = np.float32(
            [kp_0[match.queryIdx].pt for match in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32(
            [kp_ref[match.trainIdx].pt for match in good_matches]).reshape(-1, 1, 2)
        m, msk = find_transform(src_pts, dst_pts, transform, alignment_config['align_method'],
                                *(alignment_config[k]
                                  for k in ['rans_threshold', 'max_iters',
                                            'align_confidence', 'refine_iters']))
        if plot_path is not None:
            plot_matches(msk, img_ref_sub, img_0_sub, kp_ref, kp_0, good_matches, plot_path)
            if callbacks and 'save_plot' in callbacks:
                callbacks['save_plot'](plot_path)
        h_sub, w_sub = img_0_sub.shape[:2]
        if subsample > 1:
            m = rescale_trasnsform(m, w0, h0, w_sub, h_sub, subsample, transform)
            if m is None:
                raise InvalidOptionError("transform", transform)
        transform_type = alignment_config['transform']
        is_valid, reason, result = check_transform(
            m, img_0.shape, transform_type,
            affine_thresholds, homography_thresholds)
        if callbacks and 'save_transform_result' in callbacks:
            callbacks['save_transform_result'](result)
        if not is_valid:
            if callbacks and 'warning' in callbacks:
                callbacks['warning'](f"invalid transformation: {reason}")
            if alignment_config['abort_abnormal']:
                raise RuntimeError("invalid transformation: {reason}")
            return n_good_matches, None, None
        if callbacks and 'align_message' in callbacks:
            callbacks['align_message']()
        img_mask = np.ones_like(img_0, dtype=np.uint8)
        if alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY:
            img_warp = cv2.warpPerspective(
                img_0, m, (w_ref, h_ref),
                borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpPerspective(img_mask, m, (w_ref, h_ref),
                                           borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        elif alignment_config['transform'] == constants.ALIGN_RIGID:
            img_warp = cv2.warpAffine(
                img_0, m, (w_ref, h_ref),
                borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
            if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
                mask = cv2.warpAffine(img_mask, m, (w_ref, h_ref),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
            if callbacks and 'blur_message' in callbacks:
                callbacks['blur_message']()
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            blurred_warp = cv2.GaussianBlur(
                img_warp, (21, 21), sigmaX=alignment_config['border_blur'])
            img_warp[mask == 0] = blurred_warp[mask == 0]
    return n_good_matches, m, img_warp


class AlignFramesBase(SubAction):
    def __init__(self, enabled=True, feature_config=None, matching_config=None,
                 alignment_config=None, **kwargs):
        super().__init__(enabled)
        self.process = None
        self._n_good_matches = None
        self.feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.alignment_config = {**_DEFAULT_ALIGNMENT_CONFIG, **(alignment_config or {})}
        self.min_matches = 4 \
            if self.alignment_config['transform'] == constants.ALIGN_HOMOGRAPHY else 3
        self.plot_summary = kwargs.get('plot_summary', False)
        self.plot_matches = kwargs.get('plot_matches', False)
        for k in self.feature_config:
            if k in kwargs:
                self.feature_config[k] = kwargs[k]
        for k in self.matching_config:
            if k in kwargs:
                self.matching_config[k] = kwargs[k]
        for k in self.alignment_config:
            if k in kwargs:
                self.alignment_config[k] = kwargs[k]
        self._area_ratio = None
        self._aspect_ratio = None
        self._max_angle_dev = None
        self._scale_x = None
        self._scale_y = None
        self._translation_x = None
        self._translation_y = None
        self._rotation = None
        self._shear = None

    def relative_transformation(self):
        return None

    def align_images(self, idx, img_ref, img_0):
        pass

    def print_message(self, msg, color=constants.LOG_COLOR_LEVEL_3, level=logging.INFO):
        self.process.print_message(color_str(msg, color), level=level)

    def begin(self, process):
        self.process = process
        self._n_good_matches = np.zeros(process.total_action_counts)
        self._area_ratio = np.ones(process.total_action_counts)
        self._aspect_ratio = np.ones(process.total_action_counts)
        self._max_angle_dev = np.zeros(process.total_action_counts)
        self._scale_x = np.ones(process.total_action_counts)
        self._scale_y = np.ones(process.total_action_counts)
        self._translation_x = np.zeros(process.total_action_counts)
        self._translation_y = np.zeros(process.total_action_counts)
        self._rotation = np.zeros(process.total_action_counts)
        self._shear = np.zeros(process.total_action_counts)

    def run_frame(self, idx, ref_idx, img_0):
        if idx == self.process.ref_idx:
            return img_0
        img_ref = self.process.img_ref(ref_idx)
        return self.align_images(idx, img_ref, img_0)

    def get_transform_thresholds(self):
        return _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS

    def image_str(self, idx):
        return f"image: {self.process.idx_tot_str(idx)}, " \
               f"{os.path.basename(self.process.input_filepath(idx))}"

    def end(self):

        def get_coordinates(items):
            x = np.arange(1, len(items) + 1, dtype=int)
            no_ref = x != self.process.ref_idx + 1
            x = x[no_ref]
            y = np.array(items)[no_ref]
            if self.process.ref_idx == 0:
                y_ref = y[1]
            elif self.process.ref_idx >= len(y):
                y_ref = y[-1]
            else:
                y_ref = (y[self.process.ref_idx - 1] + y[self.process.ref_idx]) / 2
            return x, y, y_ref

        if self.plot_summary:
            plt.figure(figsize=constants.PLT_FIG_SIZE)
            x, y, y_ref = get_coordinates(self._n_good_matches)
            plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                     [0, y_ref], color='cornflowerblue', linestyle='--', label='reference frame')
            plt.plot([x[0], x[-1]], [self.min_matches, self.min_matches], color='lightgray',
                     linestyle='--', label='min. matches')
            plt.plot(x, y, color='navy', label='matches')
            plt.title("Number of matches")
            plt.xlabel('frame')
            plt.ylabel('# of matches')
            plt.legend()
            plt.ylim(0)
            plt.xlim(x[0], x[-1])
            plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                        f"{self.process.name}-matches.pdf"
            save_plot(plot_path)
            self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                  f"{self.process.name}: matches", plot_path)
            transform = self.alignment_config['transform']
            title = "Transformation parameters rel. to reference frame"
            if transform == constants.ALIGN_RIGID:
                plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._rotation)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='rotation (°)')
                y_lim = max(abs(y.min()), abs(y.max())) * 1.1
                plt.ylim(-y_lim, y_lim)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('rotation angle (degrees)')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-rotation.pdf"
                save_plot(plot_path)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      f"{self.process.name}: rotation", plot_path)
                plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y_x, y_x_ref = get_coordinates(self._translation_x)
                x, y_y, y_y_ref = get_coordinates(self._translation_y)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [y_x_ref, y_y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y_x, color='blue', label='translation, x (px)')
                plt.plot(x, y_y, color='red', label='translation, y (px)')
                y_lim = max(abs(y_x.min()), abs(y_x.max()), abs(y_y.min()), abs(y_y.max())) * 1.1
                plt.ylim(-y_lim, y_lim)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('translation (pixels)')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-translation.pdf"
                save_plot(plot_path)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      f"{self.process.name}: translation", plot_path)

                plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._scale_x)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [1, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [1, 1], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='blue', label='scale factor')
                d_max = max(abs(y.min() - 1), abs(y.max() - 1)) * 1.1
                plt.ylim(1.0 - d_max, 1.0 + d_max)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('scale factor')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-scale.pdf"
                save_plot(plot_path)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      f"{self.process.name}: scale", plot_path)
            elif transform == constants.ALIGN_HOMOGRAPHY:
                plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._area_ratio)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='area ratio')
                d_max = max(abs(y.min() - 1), abs(y.max() - 1)) * 1.1
                plt.ylim(1.0 - d_max, 1.0 + d_max)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('warped area ratio')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-area-ratio.pdf"
                save_plot(plot_path)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      f"{self.process.name}: area ratio", plot_path)
                plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._aspect_ratio)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='aspect ratio')
                y_min, y_max = y.min(), y.max()
                delta = y_max - y_min
                plt.ylim(y_min - 0.05 * delta, y_max + 0.05 * delta)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('aspect ratio')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-aspect-ratio.pdf"
                save_plot(plot_path)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      f"{self.process.name}: aspect ratio", plot_path)
                plt.figure(figsize=constants.PLT_FIG_SIZE)
                x, y, y_ref = get_coordinates(self._max_angle_dev)
                plt.plot([self.process.ref_idx + 1, self.process.ref_idx + 1],
                         [0, y_ref], color='cornflowerblue',
                         linestyle='--', label='reference frame')
                plt.plot([x[0], x[-1]], [0, 0], color='cornflowerblue', linestyle='--')
                plt.plot(x, y, color='navy', label='max. dev. ang. (°)')
                y_lim = max(abs(y.min()), abs(y.max())) * 1.1
                plt.ylim(-y_lim, y_lim)
                plt.title(title)
                plt.xlabel('frame')
                plt.ylabel('max deviation angle (degrees)')
                plt.legend()
                plt.xlim(x[0], x[-1])
                plot_path = f"{self.process.working_path}/{self.process.plot_path}/" \
                            f"{self.process.name}-rotation.pdf"
                save_plot(plot_path)
                self.process.callback(constants.CALLBACK_SAVE_PLOT, self.process.id,
                                      f"{self.process.name}: rotation", plot_path)

    def save_transform_result(self, idx, result):
        if result is None:
            return
        transform = self.alignment_config['transform']
        if transform == constants.ALIGN_HOMOGRAPHY:
            area_ratio, aspect_ratio, max_angle_dev = result
            self._area_ratio[idx] = area_ratio
            self._aspect_ratio[idx] = aspect_ratio
            self._max_angle_dev[idx] = max_angle_dev
        elif transform == constants.ALIGN_RIGID:
            scale_x, scale_y, translation_x, translation_y, rotation, shear = result
            self._scale_x[idx] = scale_x
            self._scale_y[idx] = scale_y
            self._translation_x[idx] = translation_x
            self._translation_y[idx] = translation_y
            self._rotation[idx] = rotation
            self._shear[idx] = shear
        else:
            raise InvalidOptionError(
                'transform', transform,
                f". Valid options are: {constants.ALIGN_HOMOGRAPHY}, {constants.ALIGN_RIGID}"
            )


class AlignFrames(AlignFramesBase):
    def align_images(self, idx, img_ref, img_0):
        idx_str = f"{idx:04d}"
        idx_tot_str = self.process.idx_tot_str(idx)

        callbacks = {
            'message': lambda: self.print_message(f'{idx_tot_str}: find matches'),
            'matches_message': lambda n: self.print_message(f'{idx_tot_str}: good matches: {n}'),
            'align_message': lambda: self.print_message(f'{idx_tot_str}: align images'),
            'blur_message': lambda: self.print_message(f'{idx_tot_str}: blur borders'),
            'warning': lambda msg: self.print_message(
                f': {msg}', constants.LOG_COLOR_WARNING),
            'save_plot': lambda plot_path: self.process.callback(
                constants.CALLBACK_SAVE_PLOT, self.process.id,
                f"{self.process.name}: matches\nframe {idx_str}", plot_path),
            'save_transform_result': lambda result: self.save_transform_result(idx, result)
        }
        if self.plot_matches:
            plot_path = os.path.join(
                self.process.working_path,
                self.process.plot_path,
                f"{self.process.name}-matches-{idx_str}.pdf")
        else:
            plot_path = None
        affine_thresholds, homography_thresholds = self.get_transform_thresholds()
        n_good_matches, _m, img = align_images(
            img_ref, img_0,
            feature_config=self.feature_config,
            matching_config=self.matching_config,
            alignment_config=self.alignment_config,
            plot_path=plot_path,
            callbacks=callbacks,
            affine_thresholds=affine_thresholds,
            homography_thresholds=homography_thresholds
        )
        self._n_good_matches[idx] = n_good_matches
        if n_good_matches < self.min_matches:
            self.process.print_message(
                f"{self.image_str(idx)} not aligned, too few matches found: "
                f"{n_good_matches}")
            return None
        return img

    def relative_transformation(self):
        return False

    def sequential_processing(self):
        return True
