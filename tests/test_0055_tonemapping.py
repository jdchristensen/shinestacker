import os
import numpy as np
from shinestacker.algorithms.tonemapping import local_tonemapping
from shinestacker.algorithms.utils import read_img, write_img, img_bw

out_path = "tests/output/tonemapping"


def test_tonemapping_8bit():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        sharp = local_tonemapping(img, amount=1.0, clip_limit=2.0, tile_size=4)
        write_img(f"{out_path}/test-local-tonemapping.jpg", sharp)
        assert True
    except Exception:
        assert False


def test_tonemapping_16bit():
    img = read_img("examples/input/img-tif/0002.tif")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        sharp = local_tonemapping(img, amount=1.0, clip_limit=2.0, tile_size=4)
        write_img(f"{out_path}/test-local-tonemapping.tif", sharp)
        assert True
    except Exception:
        assert False


def test_tonemapping_bw():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        sharp = local_tonemapping(img_bw(img), amount=1.0, clip_limit=2.0, tile_size=4)
        write_img(f"{out_path}/test-local-tonemapping-bw.jpg", sharp)
        assert True
    except Exception:
        assert False


def test_tonemapping_misc():
    img = read_img("examples/input/img-jpg/0002.jpg")
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    try:
        local_tonemapping(img_bw(img), amount=-1.0, clip_limit=2.0, tile_size=4)
        local_tonemapping(img_bw(img), amount=2.0, clip_limit=2.0, tile_size=4)
        try:
            local_tonemapping(
                img.astype(np.float32), amount=1.0, clip_limit=2.0, tile_size=4)
            assert False
        except Exception:
            assert True
        assert True
    except Exception:
        assert False


if __name__ == '__main__':
    test_tonemapping_8bit()
    test_tonemapping_16bit()
    test_tonemapping_bw()
    test_tonemapping_misc()
