import os
from shinestacker.algorithms.tonemapping import local_tonemapping
from shinestacker.algorithms.utils import read_img, write_img

out_path = "tests/output/sharpen"


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


if __name__ == '__main__':
    test_tonemapping_8bit()
    test_tonemapping_16bit()
