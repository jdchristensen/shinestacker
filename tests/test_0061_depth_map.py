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


def test_sobel_map_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    sobel_map = dms.get_sobel_map(gray_img)
    assert sobel_map.shape == gray_img.shape
    assert sobel_map.dtype == np.float32
    assert np.all(sobel_map >= 0)


def test_laplacian_map_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    laplacian_map = dms.get_laplacian_map(gray_img)
    assert laplacian_map.shape == gray_img.shape
    assert laplacian_map.dtype == np.float32
    assert np.all(laplacian_map >= 0)


def test_modified_laplacian_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    modified_laplacian_map = dms.get_modified_laplacian(gray_img)
    assert modified_laplacian_map.shape == gray_img.shape
    assert modified_laplacian_map.dtype == np.float32
    assert np.all(modified_laplacian_map >= 0)


def test_focus_stack_with_examples(example_images):
    dms = DepthMapStack()
    dms.process = MagicMock()
    dms.process.callback.return_value = True
    dms.print_message = MagicMock()
    dms.init(example_images[:3])
    result = dms.focus_stack()
    assert len(result.shape) == 3
    assert result.dtype == np.uint8
    first_input = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    assert not np.array_equal(result, first_input)


def test_variance_map_single_image(example_images):
    dms = DepthMapStack()
    img = cv2.imread(example_images[0], cv2.IMREAD_GRAYSCALE)
    gray_img = img.astype(np.float32)
    variance_map = dms.get_variance_map(gray_img)
    assert variance_map.shape == gray_img.shape
    assert variance_map.dtype == np.float32
    assert np.all(variance_map >= 0)


def test_focus_map_with_examples(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.process = MagicMock()
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    focus_map = dms.get_focus_map(energies)
    assert focus_map.shape == energies.shape
    assert focus_map.dtype == np.float32
    assert np.all(np.isfinite(focus_map))
    valid_mask = np.isfinite(focus_map)
    assert np.all(focus_map[valid_mask] >= 0)
    assert np.all(focus_map[valid_mask] <= 1)


def test_weighted_pyramid_blend(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    dms.process = MagicMock()
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    weights = dms.get_focus_map(energies)
    result = dms._weighted_pyramid_blend(weights, 3)
    assert result.shape == (dms.shape[0], dms.shape[1], 3)
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


def test_focus_map_max_type(example_images):
    dms = DepthMapStack(map_type='max')
    dms.init(example_images[:3])
    dms.print_message = MagicMock()
    dms.after_step = MagicMock()
    dms.check_running = MagicMock()
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    focus_map = dms.get_focus_map(energies)
    assert focus_map.shape == energies.shape
    assert focus_map.dtype == np.float32
    assert np.all(np.isfinite(focus_map))
    sum_weights = np.sum(focus_map, axis=0)
    assert np.allclose(sum_weights, 1.0, atol=1e-6)


def test_focus_map_invalid_type(example_images):
    dms = DepthMapStack()
    dms.init(example_images[:3])
    dms.map_type = 'invalid_type'
    energies = np.empty((3, *dms.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms.get_sobel_map(gray_img)
    with pytest.raises(InvalidOptionError):
        dms.get_focus_map(energies)


def test_focus_map_max_with_temperature(example_images):
    dms_high_temp = DepthMapStack(map_type='max', temperature=1.0)
    dms_high_temp.init(example_images[:3])
    dms_high_temp.print_message = MagicMock()
    dms_high_temp.after_step = MagicMock()
    dms_high_temp.check_running = MagicMock()
    dms_low_temp = DepthMapStack(map_type='max', temperature=0.01)
    dms_low_temp.init(example_images[:3])
    dms_low_temp.print_message = MagicMock()
    dms_low_temp.after_step = MagicMock()
    dms_low_temp.check_running = MagicMock()
    energies = np.empty((3, *dms_high_temp.shape), dtype=np.float32)
    for i, img_path in enumerate(example_images[:3]):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        gray_img = img.astype(np.float32)
        energies[i] = dms_high_temp.get_sobel_map(gray_img)
    focus_map_high_temp = dms_high_temp.get_focus_map(energies)
    focus_map_low_temp = dms_low_temp.get_focus_map(energies)

    def weight_entropy(weights):
        epsilon = 1e-10
        return -np.sum(weights * np.log(weights + epsilon), axis=0)

    avg_entropy_high = np.mean(weight_entropy(focus_map_high_temp))
    avg_entropy_low = np.mean(weight_entropy(focus_map_low_temp))
    assert avg_entropy_low < avg_entropy_high
