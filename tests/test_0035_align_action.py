# pylint: disable= C0116, C0114, W0212, E1101
import numpy as np
import math
from shinestacker.config import constants
from shinestacker.algorithms.align import (
    decompose_affine_matrix, check_affine_matrix, check_homography_distortion, check_transform,
    _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS, _DEFAULT_FEATURE_CONFIG, _DEFAULT_MATCHING_CONFIG,
    _DEFAULT_ALIGNMENT_CONFIG, AlignFramesBase
)


def test_identity_matrix():
    identity = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(identity)
    assert math.isclose(scales[0], 1.0, abs_tol=1e-10)
    assert math.isclose(scales[1], 1.0, abs_tol=1e-10)
    assert math.isclose(rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_translation_only():
    tx, ty = 50.0, -30.0
    translation_matrix = np.array([[1, 0, tx], [0, 1, ty]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(translation_matrix)
    assert math.isclose(scales[0], 1.0, abs_tol=1e-10)
    assert math.isclose(scales[1], 1.0, abs_tol=1e-10)
    assert math.isclose(rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], tx, abs_tol=1e-10)
    assert math.isclose(translation[1], ty, abs_tol=1e-10)


def test_scale_only():
    scale_x, scale_y = 2.0, 0.5
    scale_matrix = np.array([[scale_x, 0, 0], [0, scale_y, 0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(scale_matrix)
    assert math.isclose(scales[0], scale_x, abs_tol=1e-10)
    assert math.isclose(scales[1], scale_y, abs_tol=1e-10)
    assert math.isclose(rotation, 0.0, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_rotation_only():
    angle_deg = 45.0
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rotation_matrix = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(rotation_matrix)
    assert math.isclose(scales[0], 1.0, abs_tol=1e-10)
    assert math.isclose(scales[1], 1.0, abs_tol=1e-10)
    assert math.isclose(rotation, angle_deg, abs_tol=1e-10)
    assert math.isclose(shear, 0.0, abs_tol=1e-10)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_check_affine_matrix_valid():
    m = np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 5.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_invalid_rotation():
    angle_rad = math.radians(25.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert not is_valid
    assert "rotation too large" in reason


def test_check_affine_matrix_invalid_scale():
    m = np.array([[0.8, 0.0, 0.0], [0.0, 1.2, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert not is_valid
    assert "x-scale out of range" in reason


def test_check_affine_matrix_invalid_translation():
    m = np.array([[1.0, 0.0, 20.0], [0.0, 1.0, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert not is_valid
    assert "translation too large" in reason


def test_check_homography_distortion_valid():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_invalid_area():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert not is_valid
    assert "area change too large" in reason


def test_check_homography_distortion_invalid_aspect():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert not is_valid
    assert "aspect ratio change too large" in reason


def test_check_homography_distortion_skew():
    m = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert not is_valid
    assert "angle distortion too large" in reason


def test_check_affine_matrix_valid_rotation():
    angle_rad = math.radians(5.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_valid_scale():
    m = np.array([[0.95, 0.0, 0.0], [0.0, 1.05, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_valid_translation():
    m = np.array([[1.0, 0.0, 5.0], [0.0, 1.0, 5.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_valid_shear():
    m = np.array([[1.0, 0.0, 0.0], [0.0857, 1.0, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_combined_valid():
    angle_rad = math.radians(3.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[0.95 * cos_a, 0.95 * sin_a, 4.0],
                  [-0.95 * sin_a, 1.05 * cos_a, -3.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_valid_scale():
    m = np.array([[1.2, 0.0, 0.0], [0.0, 1.2, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_valid_aspect():
    m = np.array([[1.5, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_homography_distortion_valid_skew():
    m = np.array([[1.0, 0.1, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_affine_matrix_combined_invalid():
    angle_rad = math.radians(15.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[0.8 * cos_a, 0.8 * sin_a, 20.0],
                  [-0.8 * sin_a, 1.2 * cos_a, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert not is_valid
    assert "rotation too large" in reason
    assert "x-scale out of range" in reason
    assert "y-scale out of range" in reason
    assert "translation too large" in reason


def test_check_transform_rigid_valid():
    m = np.array([[1.0, 0.0, 5.0], [0.0, 1.0, 5.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_transform_homography_valid():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert is_valid
    assert "within acceptable limits" in reason


def test_check_transform_homography_invalid_area():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "area change too large" in reason


def test_check_transform_homography_invalid_aspect():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "aspect ratio change too large" in reason


def test_check_transform_invalid_type():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, 'invalid_type', _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "invalid transfrom option" in reason


def test_check_transform_rigid_invalid_rotation():
    angle_rad = math.radians(25.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[cos_a, sin_a, 0], [-sin_a, cos_a, 0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "rotation too large" in reason


def test_check_transform_rigid_invalid_translation():
    m = np.array([[1.0, 0.0, 20.0], [0.0, 1.0, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "translation too large" in reason


def test_check_transform_rigid_invalid_scale():
    m = np.array([[0.8, 0.0, 0.0], [0.0, 1.2, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "x-scale out of range" in reason


def test_check_transform_homography_invalid_skew():
    m = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_HOMOGRAPHY, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "angle distortion too large" in reason


def test_check_transform_rigid_combined_invalid():
    angle_rad = math.radians(15.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[0.8 * cos_a, 0.8 * sin_a, 20.0],
                  [-0.8 * sin_a, 1.2 * cos_a, 15.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(
        m, img_shape, constants.ALIGN_RIGID, _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS)
    assert not is_valid
    assert "rotation too large" in reason
    assert "x-scale out of range" in reason
    assert "y-scale out of range" in reason
    assert "translation too large" in reason


def test_check_transform_none_thresholds():
    m = np.array([[2.0, 0.0, 100.0], [0.0, 2.0, 100.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(m, img_shape, constants.ALIGN_RIGID, None, None)
    assert is_valid
    assert "No thresholds provided" in reason


def test_check_transform_homography_none_thresholds():
    m = np.array([[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_transform(m, img_shape, constants.ALIGN_HOMOGRAPHY, None, None)
    assert is_valid
    assert "No thresholds provided" in reason


def test_decompose_affine_matrix_shear():
    m = np.array([[1.0, 0.2, 0.0], [0.1, 1.0, 0.0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(m)
    assert math.isclose(scales[0], 1.0198039, abs_tol=1e-6)
    assert math.isclose(scales[1], 1.0049875, abs_tol=1e-6)
    assert math.isclose(rotation, 11.309932, abs_tol=1e-6)
    assert math.isclose(shear, -17.020525, abs_tol=1e-6)
    assert math.isclose(translation[0], 0.0, abs_tol=1e-10)
    assert math.isclose(translation[1], 0.0, abs_tol=1e-10)


def test_decompose_affine_matrix_combined():
    angle_rad = math.radians(30.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([[1.5 * cos_a, 1.5 * sin_a, 25.0],
                  [-0.8 * sin_a, 0.8 * cos_a, -15.0]], dtype=np.float64)
    scales, rotation, shear, translation = decompose_affine_matrix(m)
    assert math.isclose(scales[0], 1.5, abs_tol=1e-6)
    assert math.isclose(scales[1], 0.8, abs_tol=1e-6)
    assert math.isclose(rotation, 30.0, abs_tol=1e-6)
    assert math.isclose(shear, 0.0, abs_tol=1e-6)
    assert math.isclose(translation[0], 25.0, abs_tol=1e-10)
    assert math.isclose(translation[1], -15.0, abs_tol=1e-10)


def test_check_affine_matrix_zero_matrix():
    m = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_affine_matrix(m, img_shape)
    assert not is_valid
    assert "x-scale out of range" in reason
    assert "y-scale out of range" in reason


def test_check_homography_distortion_identity():
    m = np.eye(3, dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason
    area_ratio, aspect_ratio, max_angle_dev = result
    assert math.isclose(area_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(aspect_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(max_angle_dev, 0.0, abs_tol=1e-10)


def test_check_homography_distortion_translation():
    m = np.array([[1.0, 0.0, 10.0], [0.0, 1.0, 5.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason
    area_ratio, aspect_ratio, max_angle_dev = result
    assert math.isclose(area_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(aspect_ratio, 1.0, abs_tol=1e-10)
    assert math.isclose(max_angle_dev, 0.0, abs_tol=1e-10)


def test_check_homography_distortion_rotation_scale():
    angle = 5.0
    scale = 1.2
    angle_rad = math.radians(angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    m = np.array([
        [scale * cos_a, -scale * sin_a, 0],
        [scale * sin_a, scale * cos_a, 0],
        [0, 0, 1]
    ], dtype=np.float64)
    img_shape = (100, 100)
    is_valid, reason, result = check_homography_distortion(m, img_shape)
    assert is_valid
    assert "within acceptable limits" in reason
    area_ratio, aspect_ratio, max_angle_dev = result
    assert math.isclose(area_ratio, scale * scale, abs_tol=1e-6)
    assert math.isclose(aspect_ratio, 1.0, abs_tol=1e-6)
    assert math.isclose(max_angle_dev, 0.0, abs_tol=1e-5)


def test_align_frames_base_initialization():
    align_base = AlignFramesBase()
    assert align_base.enabled
    assert align_base.feature_config == _DEFAULT_FEATURE_CONFIG
    assert align_base.matching_config == _DEFAULT_MATCHING_CONFIG
    assert align_base.alignment_config == _DEFAULT_ALIGNMENT_CONFIG
    assert align_base.min_matches == 3


def test_align_frames_base_custom_initialization():
    custom_feature = {'detector': 'ORB', 'descriptor': 'ORB'}
    custom_matching = {'match_method': 'NORM_HAMMING', 'threshold': 0.8}
    custom_alignment = {'transform': 'rigid', 'align_method': 'RANSAC'}
    align_base = AlignFramesBase(
        enabled=False,
        feature_config=custom_feature,
        matching_config=custom_matching,
        alignment_config=custom_alignment
    )
    assert not align_base.enabled
    assert align_base.feature_config['detector'] == 'ORB'
    assert align_base.feature_config['descriptor'] == 'ORB'
    assert align_base.matching_config['match_method'] == 'NORM_HAMMING'
    assert align_base.matching_config['threshold'] == 0.8
    assert align_base.alignment_config['transform'] == 'rigid'
    assert align_base.alignment_config['align_method'] == 'RANSAC'
    assert align_base.min_matches == 3


def test_align_frames_base_homography_initialization():
    custom_alignment = {'transform': constants.ALIGN_HOMOGRAPHY}
    align_base = AlignFramesBase(alignment_config=custom_alignment)
    assert align_base.min_matches == 4


def test_align_frames_base_relative_transformation():
    align_base = AlignFramesBase()
    result = align_base.relative_transformation()
    assert result is None


def test_align_frames_base_get_transform_thresholds():
    align_base = AlignFramesBase()
    affine_thresholds, homography_thresholds = align_base.get_transform_thresholds()
    assert affine_thresholds == _AFFINE_THRESHOLDS
    assert homography_thresholds == _HOMOGRAPHY_THRESHOLDS


if __name__ == "__main__":
    test_identity_matrix()
    test_translation_only()
    test_rotation_only()
    test_scale_only()
