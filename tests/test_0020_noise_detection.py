import os
import matplotlib
matplotlib.use('Agg')
import logging
from PIL import Image
from shinestacker.config.constants import constants
from shinestacker.core.logging import setup_logging
from shinestacker.core.exceptions import ShapeError, BitDepthError
from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.noise_detection import mean_image, NoiseDetection, MaskNoise


def check_fail_size(extension, directory, ExepctionType, files):
    logger = logging.getLogger()
    shape_err = False
    try:
        mean_image(["output/" + directory + f"/image{i}." + extension for i in files],
                   message_callback=lambda i, path: logger.info(path))
    except ExepctionType:
        shape_err = True
    assert shape_err


def rm_dir(path):
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)
    os.rmdir(path)


def test_detect_fail_1():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file=f"logs/{constants.APP_STRING.lower()}.log"
    )
    os.makedirs('output/img-jpg-wrong-size', exist_ok=True)
    img1 = Image.new('RGB', (400, 600), color='black')
    img2 = Image.new('RGB', (600, 400), color='black')
    img1.save('output/img-jpg-wrong-size/image1.jpg', 'JPEG', quality=100)
    img2.save('output/img-jpg-wrong-size/image2.jpg', 'JPEG', quality=100)
    check_fail_size("jpg", "img-jpg-wrong-size", ShapeError, (1, 2))
    rm_dir('output/img-jpg-wrong-size')


def test_detect_fail_2():
    os.makedirs('output/img-tif-wrong-size', exist_ok=True)
    img1 = Image.new('RGB', (400, 600), color='black')
    img2 = Image.new('RGB', (600, 400), color='black')
    img1_16bit = img1.convert('I;16')
    img2_16bit = img2.convert('I;16')
    img1_16bit.save('output/img-tif-wrong-size/image1.tif', 'TIFF')
    img2_16bit.save('output/img-tif-wrong-size/image2.tif', 'TIFF')
    check_fail_size("tif", "img-tif-wrong-size", ShapeError, (1, 2))
    rm_dir('output/img-tif-wrong-size')


def test_detect_fail_3():
    os.makedirs('output/img-tif-wrong-type', exist_ok=True)
    img1 = Image.new('RGB', (400, 600), color='black')
    img1.save('output/img-tif-wrong-type/image_8bit.tif', 'TIFF')
    img1_16bit = img1.convert('I;16')
    img1_16bit.save('output/img-tif-wrong-type/image_16bit.tif', 'TIFF')
    check_fail_size("tif", "img-tif-wrong-type", BitDepthError, ("_8bit", "_16bit"))
    rm_dir('output/img-tif-wrong-type')


def test_detect_rgb():
    try:
        job = StackJob("job", "examples", input_path="input/img-noise", callbacks='tqdm')
        job.add_action(NoiseDetection(method='rgb', plot_histograms=True))
        job.run()
    except Exception:
        assert False


def test_detect_norm_lab():
    try:
        job = StackJob("job", "examples", input_path="input/img-noise", callbacks='tqdm')
        job.add_action(NoiseDetection(method='norm_lab', plot_histograms=True))
        job.run()
    except Exception:
        assert False


def test_detect_norm_rgb():
    try:
        job = StackJob("job", "examples", input_path="input/img-noise", callbacks='tqdm')
        job.add_action(NoiseDetection(method='norm_rgb', plot_histograms=True))
        job.run()
    except Exception:
        assert False


def test_correct():
    try:
        job = StackJob("job", "examples/", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("noise",
                                       [MaskNoise(noise_mask='noise-map/hot_pixels.png')],
                                       output_path="output/img-noise-corr"))
        job.run()
    except Exception:
        assert False


def test_invalid_input():
    try:
        job = StackJob("job", "examples/", input_path="input/xxx", callbacks='tqdm')
        job.add_action(CombinedActions("noise",
                                       [MaskNoise(noise_mask='noise-map/hot_pixels.png')],
                                       output_path="output/img-noise-corr"))
        job.run()
        assert False
    except Exception as e:
        assert str(e) == 'Path does not exist: examples/input/xxx'


def test_invalid_input_2():
    try:
        job = StackJob("job", "examples/", input_path="input/xxx", callbacks='tqdm')
        job.add_action(NoiseDetection(plot_histograms=True))
        job.run()
        assert False
    except Exception as e:
        print(f"exception: {str(e)}")
        assert str(e) == 'Path does not exist: examples/input/xxx'


def test_empty_input():
    try:
        os.makedirs('output/empty', exist_ok=True)
        job = StackJob("job", "output/", input_path="empty", callbacks='tqdm')
        job.add_action(NoiseDetection(plot_histograms=True))
        job.run()
        assert False
    except Exception as e:
        print(f"exception: {str(e)}")
        assert str(e) == 'No image files found in the selected path'
    rm_dir('output/empty')


if __name__ == '__main__':
    test_detect_fail_1()
    test_detect_fail_2()
    test_detect_fail_3()
    test_detect_norm_lab()
    test_detect_norm_rgb()
    test_correct()
    test_invalid_input()
    test_invalid_input_2()
    test_empty_input()
