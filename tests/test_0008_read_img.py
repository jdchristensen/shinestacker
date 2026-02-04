import unittest
from unittest.mock import patch
import numpy as np
from shinestacker.algorithms.utils import read_img

test_path_tif = 'examples/input/img-tif/0000.tif'
test_path_png = 'examples/input/img-png-8/0000.png'


class TestReadImgFallback(unittest.TestCase):
    @patch('cv2.imread')
    @patch('tifffile.imread')
    def test_tiff_fallback_on_opencv_none(self, mock_tifffile, mock_cv2):
        mock_cv2.return_value = None
        fake_rgb_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        mock_tifffile.return_value = fake_rgb_image
        img = read_img(test_path_tif)
        mock_cv2.assert_called_once()
        mock_tifffile.assert_called_once_with(test_path_tif)
        assert img is not None
        assert img.shape == (100, 100, 3)

    @patch('cv2.imread')
    @patch('tifffile.imread')
    def test_tiff_fallback_on_opencv_exception(self, mock_tifffile, mock_cv2):
        mock_cv2.side_effect = Exception("OpenCV error")
        fake_rgb_image = np.random.randint(0, 65535, (100, 100, 3), dtype=np.uint16)
        mock_tifffile.return_value = fake_rgb_image
        img = read_img(test_path_tif)
        mock_tifffile.assert_called_once()
        assert img is not None

    @patch('cv2.imread')
    @patch('tifffile.imread')
    def test_tiff_opencv_success_no_fallback(self, mock_tifffile, mock_cv2):
        fake_bgr_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        mock_cv2.return_value = fake_bgr_image
        img = read_img(test_path_tif)
        mock_cv2.assert_called_once()
        mock_tifffile.assert_not_called()
        assert img is not None

    @patch('cv2.imread')
    @patch('tifffile.imread')
    def test_tiff_multipage_fallback(self, mock_tifffile, mock_cv2):
        mock_cv2.return_value = None
        fake_multipage = np.random.randint(0, 255, (5, 100, 100, 3), dtype=np.uint8)
        mock_tifffile.return_value = fake_multipage
        img = read_img(test_path_tif)
        assert img.shape == (100, 100, 3)

    @patch('cv2.imread')
    @patch('tifffile.imread')
    def test_tiff_rgba_fallback(self, mock_tifffile, mock_cv2):
        mock_cv2.return_value = None
        fake_rgba = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)
        mock_tifffile.return_value = fake_rgba
        img = read_img(test_path_tif)
        assert img.shape == (100, 100, 4)

    @patch('cv2.imread')
    def test_png_no_fallback(self, mock_cv2):
        mock_cv2.return_value = None
        img = read_img(test_path_png)
        assert img is None


if __name__ == '__main__':
    unittest.main()
