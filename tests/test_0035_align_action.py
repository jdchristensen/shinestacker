# pylint: disable= C0116, C0114, W0212, E1101
import numpy as np
import math
from shinestacker.algorithms.align import (
    decompose_affine_matrix, check_affine_matrix, check_homography_distortion, check_transform,
    _AFFINE_THRESHOLDS, _HOMOGRAPHY_THRESHOLDS
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
    m = np.array([[0.95 * cos_a, 0.95 * sin_a, 4.0], [-0.95 * sin_a, 1.05 * cos_a, -3.0]], dtype=np.float64)
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


if __name__ == "__main__":
    test_identity_matrix()
    test_translation_only()
    test_rotation_only()
    test_scale_only()
