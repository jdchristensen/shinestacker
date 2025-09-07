# pylint: disable= C0116, C0114, W0212, E1101
import threading
from unittest.mock import Mock, patch
import cv2
import numpy as np
from shinestacker.config.constants import constants
from shinestacker.algorithms.align_parallel import AlignFramesParallel, compose_transforms


def test_compose_transforms():
    t1_rigid = np.array([[1, 0, 10], [0, 1, 20]], dtype=np.float64)
    t2_rigid = np.array([[0, -1, 5], [1, 0, 15]], dtype=np.float64)
    result_rigid = compose_transforms(t1_rigid, t2_rigid, constants.ALIGN_RIGID)
    assert result_rigid.shape == (2, 3)
    t1_homo = np.eye(3, dtype=np.float64)
    t1_homo[0, 2] = 10
    t2_homo = np.eye(3, dtype=np.float64)
    t2_homo[1, 2] = 20
    result_homo = compose_transforms(t1_homo, t2_homo, constants.ALIGN_HOMOGRAPHY)
    assert result_homo.shape == (3, 3)


def test_align_frames_parallel_initialization():
    aligner = AlignFramesParallel(
        max_threads=4,
        chunk_submit=False,
        bw_matching=True
    )
    assert aligner.max_threads == 4
    assert not aligner.chunk_submit
    assert aligner.bw_matching


def test_cache_img():
    aligner = AlignFramesParallel()
    aligner.process = Mock()
    aligner.process.input_filepath.return_value = "test_path.jpg"
    with patch('shinestacker.algorithms.align_parallel.read_img') as mock_read, \
         patch('shinestacker.algorithms.align_parallel.img_bw') as mock_bw:
        mock_read.return_value = np.ones((100, 100, 3), dtype=np.uint8)
        mock_bw.return_value = np.ones((100, 100), dtype=np.uint8)
        aligner._img_cache = [None]
        aligner._img_locks = [0]
        aligner._cache_locks = [threading.Lock()]
        result = aligner.cache_img(0)
        assert result is not None
        assert aligner._img_cache[0] is not None
        result2 = aligner.cache_img(0)
        assert np.array_equal(result, result2)


def create_test_images():
    img1 = np.zeros((200, 200, 3), dtype=np.uint8)
    img2 = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.rectangle(img1, (50, 50), (70, 70), (255, 255, 255), -1)
    cv2.rectangle(img2, (55, 55), (75, 75), (255, 255, 255), -1)
    return img1, img2


def test_align_images_method():
    aligner = AlignFramesParallel()
    process = Mock()
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(return_value="test.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner.alignment_config = {
        'transform': constants.ALIGN_RIGID,
        'border_mode': constants.BORDER_CONSTANT,
        'border_value': 0,
        'border_blur': 5
    }
    img_ref = np.ones((100, 100, 3), dtype=np.uint8)
    img_0 = np.ones((100, 100, 3), dtype=np.uint8)
    aligner._cumulative_transforms = [None]
    result = aligner.align_images(0, img_ref, img_0)
    assert np.array_equal(result, img_0)
    aligner._cumulative_transforms = [np.eye(2, 3, dtype=np.float32)]
    result = aligner.align_images(0, img_ref, img_0)
    assert result.shape == img_ref.shape
    aligner.alignment_config['transform'] = constants.ALIGN_HOMOGRAPHY
    aligner._cumulative_transforms = [np.eye(3, dtype=np.float32)]
    result = aligner.align_images(0, img_ref, img_0)
    assert result.shape == img_ref.shape


def test_align_images_border_modes():
    aligner = AlignFramesParallel()
    process = Mock()
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(return_value="test.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    img_ref = np.ones((100, 100, 3), dtype=np.uint8)
    img_0 = np.ones((100, 100, 3), dtype=np.uint8)
    for border_mode in [constants.BORDER_CONSTANT,
                        constants.BORDER_REPLICATE,
                        constants.BORDER_REPLICATE_BLUR]:
        aligner.alignment_config = {
            'transform': constants.ALIGN_RIGID,
            'border_mode': border_mode,
            'border_value': 0,
            'border_blur': 5
        }
        aligner._cumulative_transforms = [np.eye(2, 3, dtype=np.float32)]
        result = aligner.align_images(0, img_ref, img_0)
        assert result.shape == img_ref.shape


def test_extract_features_fallback():
    aligner = AlignFramesParallel()
    process = Mock()
    process.ref_idx = 0
    process.idx_tot_str = Mock(return_value="1/2")
    process.input_filepath = Mock(return_value="test.jpg")
    aligner.process = process
    aligner.print_message = Mock()
    aligner.alignment_config = {
        'transform': constants.ALIGN_RIGID,
        'subsample': 1,
        'fast_subsampling': False,
        'min_good_matches': 100,  # Set high to force fallback
        'align_method': 'RANSAC',
        'rans_threshold': 3.0,
        'max_iters': 2000,
        'align_confidence': 0.99,
        'refine_iters': 10,
        'abort_abnormal': False
    }
    aligner._n_good_matches = [0] * 2
    aligner._target_indices = [None] * 2
    aligner._transforms = [None] * 2
    with patch.object(aligner, 'cache_img') as mock_cache:
        mock_cache.side_effect = [
            np.ones((100, 100, 3), dtype=np.uint8),
            np.zeros((100, 100, 3), dtype=np.uint8)
        ]
        _info, warnings = aligner.extract_features(1)
        assert len(warnings) > 0


if __name__ == '__main__':
    test_compose_transforms()
    test_align_frames_parallel_initialization()
    test_cache_img()
    test_align_images_method()
    test_align_images_border_modes()
    test_extract_features_fallback()
    print("All tests passed!")
