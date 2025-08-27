# pylint: disable=C0114, C0116, E1101
import os
import logging
import numpy as np
import cv2
import matplotlib.pyplot as plt
from .. config.config import config
from .. core.exceptions import ShapeError, BitDepthError


def get_path_extension(path):
    return os.path.splitext(path)[1].lstrip('.')


EXTENSIONS_TIF = ['tif', 'tiff']
EXTENSIONS_JPG = ['jpg', 'jpeg']
EXTENSIONS_PNG = ['png']
EXTENSIONS_PDF = ['pdf']


def extension_in(path, exts):
    return get_path_extension(path).lower() in exts


def extension_tif(path):
    return extension_in(path, EXTENSIONS_TIF)


def extension_jpg(path):
    return extension_in(path, EXTENSIONS_JPG)


def extension_png(path):
    return extension_in(path, EXTENSIONS_PNG)


def extension_pdf(path):
    return extension_in(path, EXTENSIONS_PDF)


def extension_tif_jpg(path):
    return extension_in(path, EXTENSIONS_TIF + EXTENSIONS_JPG)


def extension_tif_png(path):
    return extension_in(path, EXTENSIONS_TIF + EXTENSIONS_PNG)


def extension_jpg_png(path):
    return extension_in(path, EXTENSIONS_JPG + EXTENSIONS_PNG)


def read_img(file_path):
    if not os.path.isfile(file_path):
        raise RuntimeError("File does not exist: " + file_path)
    img = None
    if extension_jpg(file_path):
        img = cv2.imread(file_path)
    elif extension_tif_png(file_path):
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    return img


def write_img(file_path, img):
    if extension_jpg(file_path):
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    elif extension_tif(file_path):
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    elif extension_png(file_path):
        cv2.imwrite(file_path, img)


def img_8bit(img):
    return (img >> 8).astype('uint8') if img.dtype == np.uint16 else img


def img_bw_8bit(img):
    img = img_8bit(img)
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if len(img.shape) == 2:
        return img
    raise ValueError(f"Unsupported image format: {img.shape}")


def img_bw(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def get_img_file_shape(file_path):
    img = read_img(file_path)
    return img.shape[:2]


def get_img_metadata(img):
    if img is None:
        return None, None
    return img.shape[:2], img.dtype


def validate_image(img, expected_shape=None, expected_dtype=None):
    if img is None:
        raise RuntimeError("Image is None")
    shape, dtype = get_img_metadata(img)
    if expected_shape and shape[:2] != expected_shape[:2]:
        raise ShapeError(expected_shape, shape)
    if expected_dtype and dtype != expected_dtype:
        raise BitDepthError(expected_dtype, dtype)


def save_plot(filename):
    logging.getLogger(__name__).debug(msg=f"save plot file: {filename}")
    dir_path = os.path.dirname(filename)
    if not dir_path:
        dir_path = '.'
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    plt.savefig(filename, dpi=150)
    if config.JUPYTER_NOTEBOOK:
        plt.show()
    plt.close('all')


def img_subsample(img, subsample, fast=True):
    if fast:
        img_sub = img[::subsample, ::subsample]
    else:
        img_sub = cv2.resize(img, (0, 0),
                             fx=1 / subsample, fy=1 / subsample,
                             interpolation=cv2.INTER_AREA)
    return img_sub
