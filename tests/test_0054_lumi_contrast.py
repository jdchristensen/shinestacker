
import os
import math
import cv2
from shinestacker.algorithms.corrections import gamma_correction, contrast_correction
from shinestacker.algorithms.utils import read_img, write_img, bgr_to_hls, hls_to_bgr

out_path = "tests/output/corrections"


def test_lumi_gamma():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        wb = gamma_correction(img, 1.2)
        write_img(f"{out_path}/test-gamma-lumi.jpg", wb)
        assert True
    except Exception:
        assert False


def test_contrast():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        wb = contrast_correction(img, 1.2)
        write_img(f"{out_path}/test-contrast.jpg", wb)
        assert True
    except Exception:
        assert False


def test_vibrance():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        img_corr = bgr_to_hls(img)
        h, l, s = cv2.split(img_corr)
        s_corr = contrast_correction(s, - 0.5)
        img_corr = cv2.merge([h, l, s_corr])
        img_corr = hls_to_bgr(img_corr)
        write_img(f"{out_path}/test-vibrance.jpg", img_corr)
        assert True
    except Exception:
        assert False


def test_saturation():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        img_corr = bgr_to_hls(img)
        h, l, s = cv2.split(img_corr)
        s_corr = gamma_correction(s, math.exp(0.5 * 1.2))
        img_corr = cv2.merge([h, l, s_corr])
        img_corr = hls_to_bgr(img_corr)
        write_img(f"{out_path}/test-saturation.jpg", img_corr)
        assert True
    except Exception:
        assert False


def test_lumi_gamma_16():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        wb = gamma_correction(img, 1.2)
        write_img(f"{out_path}/test-gamma-lumi.tif", wb)
        assert True
    except Exception:
        assert False


def test_contrast_16():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        wb = contrast_correction(img, 1.2)
        write_img(f"{out_path}/test-contrast.tif", wb)
        assert True
    except Exception:
        assert False


def test_vibrance_16():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        img_corr = bgr_to_hls(img)
        h, l, s = cv2.split(img_corr)
        s_corr = contrast_correction(s, - 0.5)
        img_corr = cv2.merge([h, l, s_corr])
        img_corr = hls_to_bgr(img_corr)
        write_img(f"{out_path}/test-vibrance.tif", img_corr)
        assert True
    except Exception:
        assert False


def test_saturation_16():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        img_corr = bgr_to_hls(img)
        h, l, s = cv2.split(img_corr)
        s_corr = gamma_correction(s, math.exp(0.5 * 1.2))
        img_corr = cv2.merge([h, l, s_corr])
        img_corr = hls_to_bgr(img_corr)
        write_img(f"{out_path}/test-saturation.tif", img_corr)
        assert True
    except Exception:
        assert False


if __name__ == '__main__':
    test_lumi_gamma()
    test_contrast()
    test_lumi_gamma_16()
    test_contrast_16()
    test_vibrance()
    test_vibrance_16()
    test_saturation()
    test_saturation_16()
