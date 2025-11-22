import pytest
import numpy as np
import cv2
import os
from unittest.mock import MagicMock
from shinestacker.config.defaults import DEFAULTS
from shinestacker.core.exceptions import InvalidOptionError
from shinestacker.algorithms.depth_map import DepthMapStack

n_images = 6


@pytest.fixture
def example_images():
    image_dir = "examples/input/img-jpg/"
    filenames = [os.path.join(image_dir, f"000{i}.jpg") for i in range(6)]
    for f in filenames:
        if not os.path.exists(f):
            pytest.skip(f"Test image {f} not found")
    return filenames


def test_initialization():
    dms = DepthMapStack()
    assert dms.map_type == DEFAULTS['depth_map_params']['map_type']
    assert dms.energy == DEFAULTS['depth_map_params']['energy']


def test_sobel_map_with_examples(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    sobel_map = dms.get_sobel_map(gray_images)
    assert sobel_map.shape == gray_images.shape
    assert sobel_map.dtype == np.float32
    assert np.all(sobel_map >= 0)  # Energy should always be positive


def test_laplacian_map_with_examples(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    laplacian_map = dms.get_laplacian_map(gray_images)
    assert laplacian_map.shape == gray_images.shape
    assert laplacian_map.dtype == np.float32
    assert np.all(laplacian_map >= 0)


def test_modified_laplacian_with_examples(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    modified_laplacian_map = dms.get_modified_laplacian(gray_images)
    assert modified_laplacian_map.shape == gray_images.shape
    assert modified_laplacian_map.dtype == np.float32
    assert np.all(modified_laplacian_map >= 0)


def test_focus_stack_with_examples(example_images):
    dms = DepthMapStack()
    dms.process = MagicMock()
    dms.process.callback.return_value = True  # Keep running
    dms.print_message = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8
    first_input = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    assert not np.array_equal(result, first_input)


def test_variance_map_with_examples(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    variance_map = dms.get_variance_map(gray_images)
    assert variance_map.shape == gray_images.shape
    assert variance_map.dtype == np.float32
    assert np.all(variance_map >= 0)


def test_focus_map_with_examples(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    sobel_map = dms.get_sobel_map(gray_images)
    focus_map = dms.get_focus_map(sobel_map)
    assert focus_map.shape == sobel_map.shape
    assert focus_map.dtype == np.float32
    assert np.all(focus_map >= 0)
    assert np.all(focus_map <= 1)


def test_weighted_pyramid_blend(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.process = MagicMock()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    sobel_map = dms.get_sobel_map(gray_images)
    weights = dms.get_focus_map(sobel_map)
    result = dms._weighted_pyramid_blend(weights, 3)
    assert result.shape == (gray_images.shape[1], gray_images.shape[2], 3)
    assert result.dtype == np.uint8


def test_best_pixel_selection(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.process = MagicMock()
    gray_images = []
    for img_path in example_images[:3]:
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_images.append(img.astype(np.float32))
    gray_images = np.array(gray_images)
    sobel_map = dms.get_sobel_map(gray_images)
    result = dms._best_pixel_selection(sobel_map, 3)
    assert result.shape == (gray_images.shape[1], gray_images.shape[2], 3)
    assert result.dtype == np.uint8


def test_performance_with_all_images(example_images):
    dms = DepthMapStack()
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    import time
    start = time.time()
    dms.init(example_images)
    result = dms.focus_stack()
    elapsed = time.time() - start
    assert result.shape[0] > 0 and result.shape[1] > 0
    print(f"\nFocus stacking {n_images} images took {elapsed:.2f} seconds")
    output_dir = "examples/output/"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "focus_stacked.jpg")
    cv2.imwrite(output_path, result)
    os.remove(output_path)


def test_focus_stack_invalid_energy(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.process = MagicMock()
    dms.print_message = MagicMock()
    dms.energy = "invalid_energy"
    with pytest.raises(InvalidOptionError):
        dms.focus_stack()


def test_focus_stack_invalid_blend_mode(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.process = MagicMock()
    dms.print_message = MagicMock()
    dms.blend_mode = "invalid_mode"
    with pytest.raises(InvalidOptionError):
        dms.focus_stack()
