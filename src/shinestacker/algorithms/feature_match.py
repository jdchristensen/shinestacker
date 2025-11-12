# pylint: disable=C0114, C0115, C0116, R0913, R0903, E1101, W0718, R0914, R0917
import numpy as np
import cv2
from .. config.constants import constants
from .. core.exceptions import InvalidOptionError
from .utils import img_bw_8bit

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


class MatchResult:
    def __init__(self, kp_0, kp_ref, good_matches, n_good_matches):
        self.kp_0 = kp_0
        self.kp_ref = kp_ref
        self.good_matches = good_matches
        self.n_good_matches = n_good_matches

    def has_sufficient_matches(self, min_matches):
        return self.n_good_matches >= min_matches

    def get_src_points(self):
        return np.float32(
            [self.kp_0[match.queryIdx].pt for match in self.good_matches]
        ).reshape(-1, 1, 2)

    def get_dst_points(self):
        return np.float32(
            [self.kp_ref[match.trainIdx].pt for match in self.good_matches]
        ).reshape(-1, 1, 2)


class FeatureMatcher:
    def __init__(self, feature_config=None, matching_config=None, callbacks=None):
        self.feature_config = {**_DEFAULT_FEATURE_CONFIG, **(feature_config or {})}
        self.matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
        self.callbacks = callbacks or {}
        detector = self.feature_config['detector']
        descriptor = self.feature_config['descriptor']
        match_method = self.matching_config['match_method']
        validate_align_config(detector, descriptor, match_method)
        self.detector = {
            constants.DETECTOR_SIFT: cv2.SIFT_create,
            constants.DETECTOR_ORB: cv2.ORB_create,
            constants.DETECTOR_SURF: cv2.FastFeatureDetector_create,
            constants.DETECTOR_AKAZE: cv2.AKAZE_create,
            constants.DETECTOR_BRISK: cv2.BRISK_create
        }[detector]()
        if detector == descriptor and detector in (
            constants.DETECTOR_SIFT, constants.DETECTOR_AKAZE, constants.DETECTOR_BRISK
        ):
            self.descriptor = self.detector
        else:
            self.descriptor = {
                constants.DESCRIPTOR_SIFT: cv2.SIFT_create,
                constants.DESCRIPTOR_ORB: cv2.ORB_create,
                constants.DESCRIPTOR_AKAZE: cv2.AKAZE_create,
                constants.DETECTOR_BRISK: cv2.BRISK_create
            }[descriptor]()

    def detect_and_compute(self, image):
        img_bw = img_bw_8bit(image)
        detector_name = self.feature_config['detector']
        descriptor_name = self.feature_config['descriptor']
        if (detector_name == descriptor_name and detector_name in
                (constants.DETECTOR_SIFT, constants.DETECTOR_AKAZE, constants.DETECTOR_BRISK)):
            kp, des = self.detector.detectAndCompute(img_bw, None)
        else:
            kp = self.detector.detect(img_bw, None)
            if kp:
                kp, des = self.descriptor.compute(img_bw, kp)
            else:
                des = None
        return kp, des

    def match_images(self, img_ref, img_0):
        kp_0, des_0 = self.detect_and_compute(img_0)
        kp_ref, des_ref = self.detect_and_compute(img_ref)
        if des_0 is None or des_ref is None or len(des_0) == 0 or len(des_ref) == 0:
            return MatchResult(kp_0, kp_ref, [], 0)
        good_matches = self.match_features(des_0, des_ref)
        n_good_matches = len(good_matches)
        return MatchResult(kp_0, kp_ref, good_matches, n_good_matches)

    def match_features(self, des_0, des_ref):
        return get_good_matches(des_0, des_ref, self.matching_config, self.callbacks)


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


def get_good_matches(des_0, des_ref, matching_config=None, callbacks=None):
    matching_config = {**_DEFAULT_MATCHING_CONFIG, **(matching_config or {})}
    match_method = matching_config['match_method']
    good_matches = []
    invalid_option = False
    try:
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
            invalid_option = True
    except Exception:
        if callbacks and 'warning' in callbacks:
            callbacks['warning']("failed to compute matches")
    if invalid_option:
        raise InvalidOptionError(
            'match_method', match_method,
            f". Valid options are: {constants.MATCHING_KNN}, {constants.MATCHING_NORM_HAMMING}"
        )
    return good_matches
