import unittest
import os
import tempfile
import numpy as np
from shinestacker.algorithms.utils import (
    get_path_extension, extension_tif, extension_jpg, extension_png,
    extension_tif_jpg, extension_tif_png, extension_jpg_png, extension_jpg_tif_png,
    read_img, write_img, img_8bit, img_bw_8bit, img_bw,
    get_first_image_file, get_img_file_shape, get_img_metadata,
    validate_image, read_and_validate_img, img_subsample,
    bgr_to_hsv, hsv_to_bgr, bgr_to_hls, hls_to_bgr, bgr_to_lab, lab_to_bgr
)


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_files = {
            'jpg': 'examples/input/img-jpg/0000.jpg',
            'tif': 'examples/input/img-tif/0000.tif',
            'png': 'examples/input/img-png/0000.png'
        }
        self.test_color_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        self.test_color_img_16bit = np.random.randint(0, 65535, (100, 100, 3), dtype=np.uint16)

    def test_get_path_extension(self):
        self.assertEqual(get_path_extension('image.jpg'), 'jpg')
        self.assertEqual(get_path_extension('image.tif'), 'tif')
        self.assertEqual(get_path_extension('image.png'), 'png')
        self.assertEqual(get_path_extension('image.JPEG'), 'JPEG')
        self.assertEqual(get_path_extension('no_extension'), '')

    def test_extension_functions(self):
        test_cases = [
            ('test.jpg', {
                'jpg': True, 'tif': False, 'png': False,
                'tif_jpg': True, 'tif_png': False, 'jpg_png': True, 'jpg_tif_png': True
            }),
            ('test.tif', {
                'jpg': False, 'tif': True, 'png': False,
                'tif_jpg': True, 'tif_png': True, 'jpg_png': False, 'jpg_tif_png': True
            }),
            ('test.png', {
                'jpg': False, 'tif': False, 'png': True,
                'tif_jpg': False, 'tif_png': True, 'jpg_png': True, 'jpg_tif_png': True
            })
        ]
        for filename, expected in test_cases:
            self.assertEqual(extension_jpg(filename), expected['jpg'])
            self.assertEqual(extension_tif(filename), expected['tif'])
            self.assertEqual(extension_png(filename), expected['png'])
            self.assertEqual(extension_tif_jpg(filename), expected['tif_jpg'])
            self.assertEqual(extension_tif_png(filename), expected['tif_png'])
            self.assertEqual(extension_jpg_png(filename), expected['jpg_png'])
            self.assertEqual(extension_jpg_tif_png(filename), expected['jpg_tif_png'])

    def test_read_img(self):
        for img_type, file_path in self.test_files.items():
            if os.path.exists(file_path):
                img = read_img(file_path)
                self.assertIsNotNone(img, f"Failed to read {img_type} image")
                self.assertIsInstance(img, np.ndarray)
                self.assertTrue(len(img.shape) in [2, 3])

    def test_read_img_nonexistent(self):
        with self.assertRaises(RuntimeError):
            read_img('nonexistent_file.jpg')

    def test_write_img(self):
        test_img = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as temp_dir:
            jpg_path = os.path.join(temp_dir, 'test.jpg')
            write_img(jpg_path, test_img)
            self.assertTrue(os.path.exists(jpg_path))
            tif_path = os.path.join(temp_dir, 'test.tif')
            write_img(tif_path, test_img)
            self.assertTrue(os.path.exists(tif_path))
            png_path = os.path.join(temp_dir, 'test.png')
            write_img(png_path, test_img)
            self.assertTrue(os.path.exists(png_path))

    def test_img_8bit(self):
        img_16bit = np.random.randint(0, 65535, (50, 50), dtype=np.uint16)
        img_8bit_result = img_8bit(img_16bit)
        self.assertEqual(img_8bit_result.dtype, np.uint8)
        img_8bit_input = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
        img_8bit_result = img_8bit(img_8bit_input)
        self.assertEqual(img_8bit_result.dtype, np.uint8)
        np.testing.assert_array_equal(img_8bit_input, img_8bit_result)

    def test_img_bw_conversions(self):
        color_img = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        bw_8bit = img_bw_8bit(color_img)
        self.assertEqual(len(bw_8bit.shape), 2)
        self.assertEqual(bw_8bit.dtype, np.uint8)
        bw = img_bw(color_img)
        self.assertEqual(len(bw.shape), 2)

    def test_get_first_image_file(self):
        test_files = ['not_an_image.txt', self.test_files['jpg'], 'another_file.xml']
        first_img = get_first_image_file(test_files)
        self.assertEqual(first_img, self.test_files['jpg'])

    def test_get_first_image_file_no_valid(self):
        with self.assertRaises(ValueError):
            get_first_image_file(['file1.txt', 'file2.xml'])

    def test_get_img_file_shape(self):
        for img_type, file_path in self.test_files.items():
            if os.path.exists(file_path):
                shape = get_img_file_shape(file_path)
                self.assertEqual(len(shape), 2)
                self.assertIsInstance(shape[0], int)
                self.assertIsInstance(shape[1], int)

    def test_get_img_metadata(self):
        test_img = np.random.randint(0, 255, (30, 40, 3), dtype=np.uint8)
        shape, dtype = get_img_metadata(test_img)
        self.assertEqual(shape, (30, 40))
        self.assertEqual(dtype, np.uint8)
        shape, dtype = get_img_metadata(None)
        self.assertIsNone(shape)
        self.assertIsNone(dtype)

    def test_validate_image(self):
        valid_img = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
        result = validate_image(valid_img)
        np.testing.assert_array_equal(result, valid_img)
        with self.assertRaises(RuntimeError):
            validate_image(None)
        with self.assertRaises(Exception):
            validate_image(valid_img, expected_shape=(60, 60))
        with self.assertRaises(Exception):
            validate_image(valid_img, expected_dtype=np.uint16)

    def test_read_and_validate_img(self):
        for img_type, file_path in self.test_files.items():
            if os.path.exists(file_path):
                img = read_and_validate_img(file_path)
                self.assertIsNotNone(img)
                self.assertIsInstance(img, np.ndarray)

    def test_img_subsample(self):
        test_img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        subsampled_fast = img_subsample(test_img, 2, fast=True)
        self.assertEqual(subsampled_fast.shape, (50, 50))
        subsampled_slow = img_subsample(test_img, 2, fast=False)
        self.assertEqual(subsampled_slow.shape, (50, 50))

    def test_color_conversions_8bit(self):
        hsv = bgr_to_hsv(self.test_color_img)
        bgr_back = hsv_to_bgr(hsv)
        self.assertEqual(bgr_back.shape, self.test_color_img.shape)
        hls = bgr_to_hls(self.test_color_img)
        bgr_back = hls_to_bgr(hls)
        self.assertEqual(bgr_back.shape, self.test_color_img.shape)
        lab = bgr_to_lab(self.test_color_img)
        bgr_back = lab_to_bgr(lab)
        self.assertEqual(bgr_back.shape, self.test_color_img.shape)

    def test_color_conversions_16bit(self):
        hsv = bgr_to_hsv(self.test_color_img_16bit)
        bgr_back = hsv_to_bgr(hsv)
        self.assertEqual(bgr_back.shape, self.test_color_img_16bit.shape)
        self.assertEqual(bgr_back.dtype, np.uint16)
        hls = bgr_to_hls(self.test_color_img_16bit)
        bgr_back = hls_to_bgr(hls)
        self.assertEqual(bgr_back.shape, self.test_color_img_16bit.shape)
        self.assertEqual(bgr_back.dtype, np.uint16)
        lab = bgr_to_lab(self.test_color_img_16bit)
        bgr_back = lab_to_bgr(lab)
        self.assertEqual(bgr_back.shape, self.test_color_img_16bit.shape)
        self.assertEqual(bgr_back.dtype, np.uint16)

    def test_grayscale_color_conversions(self):
        gray_img = np.random.randint(0, 65535, (50, 50), dtype=np.uint16)
        hsv = bgr_to_hsv(gray_img)
        self.assertEqual(len(hsv.shape), 3)
        self.assertEqual(hsv.shape[2], 3)
        hls = bgr_to_hls(gray_img)
        self.assertEqual(len(hls.shape), 3)
        self.assertEqual(hls.shape[2], 3)
        lab = bgr_to_lab(gray_img)
        self.assertEqual(len(lab.shape), 3)
        self.assertEqual(lab.shape[2], 3)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestUtils)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
