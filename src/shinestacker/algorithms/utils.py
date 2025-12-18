# pylint: disable=C0114, C0116, E1101, R0914, W0718
import os
import sys
import numpy as np
import cv2
from .. core.exceptions import ShapeError, BitDepthError, PathTooLong, InvalidWinPath


def get_path_extension(path):
    return os.path.splitext(path)[1].lstrip('.')


def check_windows_path(path):
    if not sys.platform.startswith('win'):
        return
    try:
        path.encode('ascii')
    except UnicodeEncodeError as e:
        raise InvalidWinPath(path) from e
    abs_path = os.path.abspath(path)
    if len(abs_path) > 260:
        try:
            # pylint: disable=C0415, E0401
            import winreg  # Windows only
            # pylint: enable=C0415, E0401
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
                if winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 0:
                    raise PathTooLong(abs_path)
        except Exception as e:
            raise PathTooLong(abs_path) from e


EXTENSIONS_TIF = ['tif', 'tiff']
EXTENSIONS_JPG = ['jpg', 'jpeg']
EXTENSIONS_PNG = ['png']
EXTENSIONS_PDF = ['pdf']
EXTENSIONS_SUPPORTED = EXTENSIONS_TIF + EXTENSIONS_JPG + EXTENSIONS_PNG
EXTENSIONS_GUI_STR = " ".join([f"*.{ext}" for ext in EXTENSIONS_SUPPORTED])
EXTENSION_GUI_TIF = " ".join([f"*.{ext}" for ext in EXTENSIONS_TIF])
EXTENSION_GUI_JPG = " ".join([f"*.{ext}" for ext in EXTENSIONS_JPG])
EXTENSION_GUI_PNG = " ".join([f"*.{ext}" for ext in EXTENSIONS_PNG])
EXTENSIONS_GUI_SAVE_STR = f"TIFF Files ({EXTENSION_GUI_TIF});;" \
                          f"JPEG Files ({EXTENSION_GUI_JPG});;" \
                          f"PNG Files ({EXTENSION_GUI_PNG});;" \
                          "All Files (*)"


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


def extension_jpg_tif_png(path):
    return extension_in(path, EXTENSIONS_JPG + EXTENSIONS_TIF + EXTENSIONS_PNG)


def extension_supported(path):
    return extension_in(path, EXTENSIONS_SUPPORTED)


def read_img(file_path):
    check_windows_path(file_path)
    if not os.path.isfile(file_path):
        raise RuntimeError("File does not exist: " + file_path)
    img = None
    if extension_jpg(file_path):
        img = cv2.imread(file_path)
    elif extension_tif_png(file_path):
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    return img


def write_img(file_path, img):
    check_windows_path(file_path)
    if extension_jpg(file_path):
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    elif extension_tif(file_path):
        cv2.imwrite(file_path, img, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1])
    elif extension_png(file_path):
        cv2.imwrite(file_path, img, [
            int(cv2.IMWRITE_PNG_COMPRESSION), 9,
            int(cv2.IMWRITE_PNG_STRATEGY), cv2.IMWRITE_PNG_STRATEGY_HUFFMAN_ONLY
        ])


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


def get_first_image_file(filenames):
    if len(filenames) == 0:
        raise ValueError("No valid image files found in the selected path")
    first_img_file = None
    for filename in filenames:
        if os.path.isfile(filename) and extension_supported(filename):
            first_img_file = filename
            break
    if first_img_file is None:
        paths = ", ".join(filenames)
        raise ValueError(f"No image files found in paths: {paths}")
    return first_img_file


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
    return img


def read_and_validate_img(filename, expected_shape=None, expected_dtype=None):
    return validate_image(read_img(filename), expected_shape, expected_dtype)


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
        return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
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
    bgr_8bit = (bgr_img.astype(np.float32) / 65535 * 255).astype(np.uint8)
    lab_8bit = cv2.cvtColor(bgr_8bit, cv2.COLOR_BGR2LAB)
    lab_16bit = (lab_8bit.astype(np.float32) / 255 * 65535).astype(np.uint16)
    return lab_16bit


def lab_to_bgr(lab_img):
    if lab_img.dtype == np.uint8:
        return cv2.cvtColor(lab_img, cv2.COLOR_LAB2BGR)
    lab_8bit = (lab_img.astype(np.float32) / 65535 * 255).astype(np.uint8)
    bgr_8bit = cv2.cvtColor(lab_8bit, cv2.COLOR_LAB2BGR)
    bgr_16bit = (bgr_8bit.astype(np.float32) / 255 * 65535).astype(np.uint16)
    return bgr_16bit
