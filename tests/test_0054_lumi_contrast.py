
import os
from shinestacker.algorithms.corrections import gamma_correction, contrast_correction
from shinestacker.algorithms.utils import read_img, write_img

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
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        wb = contrast_correction(img, 1.2)
        write_img(f"{out_path}/test-contrast.tif", wb)
        assert True
    except Exception:
        assert False


if __name__ == '__main__':
    test_lumi_gamma()
    test_contrast()
