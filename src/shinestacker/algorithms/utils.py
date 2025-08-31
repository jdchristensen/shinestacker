# pylint: disable=C0114, C0116, E1101, R0914
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


def bgr_to_hsv(bgr_img):
    if bgr_img.dtype == np.uint8:
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HLS)
    if len(bgr_img.shape) == 2:
        bgr_img = cv2.merge([bgr_img, bgr_img, bgr_img])
    bgr_normalized = bgr_img.astype(np.float32) / 65535.0
    b, g, r = cv2.split(bgr_normalized)
    v = np.max(bgr_normalized, axis=2)
    m = np.min(bgr_normalized, axis=2)
    delta = v - m
    s = np.zeros_like(v)
    nonzero_delta = delta != 0
    s[nonzero_delta] = delta[nonzero_delta] / v[nonzero_delta]
    h = np.zeros_like(v)
    r_is_max = (v == r) & nonzero_delta
    h[r_is_max] = (60 * (g[r_is_max] - b[r_is_max]) / delta[r_is_max]) % 360
    g_is_max = (v == g) & nonzero_delta
    h[g_is_max] = (60 * (b[g_is_max] - r[g_is_max]) / delta[g_is_max] + 120) % 360
    b_is_max = (v == b) & nonzero_delta
    h[b_is_max] = (60 * (r[b_is_max] - g[b_is_max]) / delta[b_is_max] + 240) % 360
    h[h < 0] += 360
    h_16bit = (h / 360 * 65535).astype(np.uint16)
    s_16bit = (s * 65535).astype(np.uint16)
    v_16bit = (v * 65535).astype(np.uint16)
    return cv2.merge([h_16bit, s_16bit, v_16bit])


def hsv_to_bgr(hsv_img):
    if hsv_img.dtype == np.uint8:
        return cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR)
    h, s, v = cv2.split(hsv_img)
    h_normalized = h.astype(np.float32) / 65535.0 * 360
    s_normalized = s.astype(np.float32) / 65535.0
    v_normalized = v.astype(np.float32) / 65535.0
    c = v_normalized * s_normalized
    x = c * (1 - np.abs((h_normalized / 60) % 2 - 1))
    m = v_normalized - c
    r = np.zeros_like(h, dtype=np.float32)
    g = np.zeros_like(h, dtype=np.float32)
    b = np.zeros_like(h, dtype=np.float32)
    mask = (h_normalized >= 0) & (h_normalized < 60)
    r[mask], g[mask], b[mask] = c[mask], x[mask], 0
    mask = (h_normalized >= 60) & (h_normalized < 120)
    r[mask], g[mask], b[mask] = x[mask], c[mask], 0
    mask = (h_normalized >= 120) & (h_normalized < 180)
    r[mask], g[mask], b[mask] = 0, c[mask], x[mask]
    mask = (h_normalized >= 180) & (h_normalized < 240)
    r[mask], g[mask], b[mask] = 0, x[mask], c[mask]
    mask = (h_normalized >= 240) & (h_normalized < 300)
    r[mask], g[mask], b[mask] = x[mask], 0, c[mask]
    mask = (h_normalized >= 300) & (h_normalized < 360)
    r[mask], g[mask], b[mask] = c[mask], 0, x[mask]
    r = np.clip((r + m) * 65535, 0, 65535).astype(np.uint16)
    g = np.clip((g + m) * 65535, 0, 65535).astype(np.uint16)
    b = np.clip((b + m) * 65535, 0, 65535).astype(np.uint16)
    return cv2.merge([b, g, r])


def bgr_to_hls(bgr_img):
    if bgr_img.dtype == np.uint8:
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HLS)
    if len(bgr_img.shape) == 2:
        bgr_img = cv2.merge([bgr_img, bgr_img, bgr_img])
    bgr_normalized = bgr_img.astype(np.float32) / 65535.0
    b, g, r = cv2.split(bgr_normalized)
    max_val = np.max(bgr_normalized, axis=2)
    min_val = np.min(bgr_normalized, axis=2)
    delta = max_val - min_val
    l = (max_val + min_val) / 2  # noqa
    s = np.zeros_like(l)
    mask = delta != 0
    s[mask] = delta[mask] / (1 - np.abs(2 * l[mask] - 1))
    h = np.zeros_like(l)
    r_is_max = (max_val == r) & mask
    h[r_is_max] = (60 * (g[r_is_max] - b[r_is_max]) / delta[r_is_max]) % 360
    g_is_max = (max_val == g) & mask
    h[g_is_max] = (60 * (b[g_is_max] - r[g_is_max]) / delta[g_is_max] + 120) % 360
    b_is_max = (max_val == b) & mask
    h[b_is_max] = (60 * (r[b_is_max] - g[b_is_max]) / delta[b_is_max] + 240) % 360
    h[h < 0] += 360
    h_16bit = (h / 360 * 65535).astype(np.uint16)
    l_16bit = (l * 65535).astype(np.uint16)
    s_16bit = (s * 65535).astype(np.uint16)
    return cv2.merge([h_16bit, l_16bit, s_16bit])


def hls_to_bgr(hls_img):
    if hls_img.dtype == np.uint8:
        return cv2.cvtColor(hls_img, cv2.COLOR_HLS2BGR)
    h, l, s = cv2.split(hls_img)
    h_normalized = h.astype(np.float32) / 65535.0 * 360
    l_normalized = l.astype(np.float32) / 65535.0
    s_normalized = s.astype(np.float32) / 65535.0
    c = (1 - np.abs(2 * l_normalized - 1)) * s_normalized
    x = c * (1 - np.abs((h_normalized / 60) % 2 - 1))
    m = l_normalized - c / 2
    r = np.zeros_like(h, dtype=np.float32)
    g = np.zeros_like(h, dtype=np.float32)
    b = np.zeros_like(h, dtype=np.float32)
    mask = (h_normalized >= 0) & (h_normalized < 60)
    r[mask], g[mask], b[mask] = c[mask], x[mask], 0
    mask = (h_normalized >= 60) & (h_normalized < 120)
    r[mask], g[mask], b[mask] = x[mask], c[mask], 0
    mask = (h_normalized >= 120) & (h_normalized < 180)
    r[mask], g[mask], b[mask] = 0, c[mask], x[mask]
    mask = (h_normalized >= 180) & (h_normalized < 240)
    r[mask], g[mask], b[mask] = 0, x[mask], c[mask]
    mask = (h_normalized >= 240) & (h_normalized < 300)
    r[mask], g[mask], b[mask] = x[mask], 0, c[mask]
    mask = (h_normalized >= 300) & (h_normalized < 360)
    r[mask], g[mask], b[mask] = c[mask], 0, x[mask]
    r = np.clip((r + m) * 65535, 0, 65535).astype(np.uint16)
    g = np.clip((g + m) * 65535, 0, 65535).astype(np.uint16)
    b = np.clip((b + m) * 65535, 0, 65535).astype(np.uint16)
    return cv2.merge([b, g, r])


def bgr_to_lab(bgr_img):
    if bgr_img.dtype == np.uint8:
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)
    if len(bgr_img.shape) == 2:
        bgr_img = cv2.merge([bgr_img, bgr_img, bgr_img])
    bgr_normalized = bgr_img.astype(np.float32) / 65535.0
    b, g, r = cv2.split(bgr_normalized)
    r_linear = np.where(r > 0.04045, ((r + 0.055) / 1.055) ** 2.4, r / 12.92)
    g_linear = np.where(g > 0.04045, ((g + 0.055) / 1.055) ** 2.4, g / 12.92)
    b_linear = np.where(b > 0.04045, ((b + 0.055) / 1.055) ** 2.4, b / 12.92)
    x = r_linear * 0.4124564 + g_linear * 0.3575761 + b_linear * 0.1804375
    y = r_linear * 0.2126729 + g_linear * 0.7151522 + b_linear * 0.0721750
    z = r_linear * 0.0193339 + g_linear * 0.1191920 + b_linear * 0.9503041
    x /= 0.950456
    z /= 1.088754
    x = np.where(x > 0.008856, x ** (1 / 3), (7.787 * x) + (16 / 116))
    y = np.where(y > 0.008856, y ** (1 / 3), (7.787 * y) + (16 / 116))
    z = np.where(z > 0.008856, z ** (1 / 3), (7.787 * z) + (16 / 116))
    l = (116 * y) - 16  # noqa
    a = 500 * (x - y)
    b_val = 200 * (y - z)
    l_16bit = np.clip(l * 65535 / 100, 0, 65535).astype(np.uint16)
    a_16bit = np.clip((a + 128) * 65535 / 255, 0, 65535).astype(np.uint16)
    b_16bit = np.clip((b_val + 128) * 65535 / 255, 0, 65535).astype(np.uint16)
    return cv2.merge([l_16bit, a_16bit, b_16bit])


def lab_to_bgr(lab_img):
    if lab_img.dtype == np.uint8:
        return cv2.cvtColor(lab_img, cv2.COLOR_LAB2BGR)
    l, a, b = cv2.split(lab_img)
    l_normalized = l.astype(np.float32) * 100 / 65535.0
    a_normalized = a.astype(np.float32) * 255 / 65535.0 - 128
    b_normalized = b.astype(np.float32) * 255 / 65535.0 - 128
    y = (l_normalized + 16) / 116
    x = a_normalized / 500 + y
    z = y - b_normalized / 200
    x = np.where(x > 0.206893, x ** 3, (x - 16 / 116) / 7.787)
    y = np.where(y > 0.206893, y ** 3, (y - 16 / 116) / 7.787)
    z = np.where(z > 0.206893, z ** 3, (z - 16 / 116) / 7.787)
    x *= 0.950456
    z *= 1.088754
    r_linear = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    g_linear = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    b_linear = x * 0.0556434 + y * -0.2040259 + z * 1.0572252
    r_linear = np.clip(r_linear, 0, 1)
    g_linear = np.clip(g_linear, 0, 1)
    b_linear = np.clip(b_linear, 0, 1)
    r = np.where(r_linear > 0.0031308, 1.055 * (r_linear ** (1 / 2.4)) - 0.055, 12.92 * r_linear)
    g = np.where(g_linear > 0.0031308, 1.055 * (g_linear ** (1 / 2.4)) - 0.055, 12.92 * g_linear)
    b = np.where(b_linear > 0.0031308, 1.055 * (b_linear ** (1 / 2.4)) - 0.055, 12.92 * b_linear)
    r = np.clip(r * 65535, 0, 65535).astype(np.uint16)
    g = np.clip(g * 65535, 0, 65535).astype(np.uint16)
    b = np.clip(b * 65535, 0, 65535).astype(np.uint16)
    return cv2.merge([b, g, r])
