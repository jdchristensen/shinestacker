# pylint: disable=C0114, C0115, C0116, E1101
import numpy as np
import cv2
from ..config.constants import constants


def gamma_correction(img, gamma):
    max_px_val = constants.MAX_UINT8 if img.dtype == np.uint8 else constants.MAX_UINT16
    ar = np.arange(0, max_px_val + 1, dtype=np.float64)
    lut = (((ar / max_px_val) ** (1.0 / gamma)) * max_px_val).astype(img.dtype)
    return cv2.LUT(img, lut) if img.dtype == np.uint8 else np.take(lut, img)


def contrast_correction(img, contrast):
    max_px_val = constants.MAX_UINT8 if img.dtype == np.uint8 else constants.MAX_UINT16
    ar = np.arange(0, max_px_val + 1, dtype=np.float64)
    normalized = 2.0 * (ar / max_px_val) - 1.0
    if contrast == 0:
        corrected = normalized
    elif contrast > 0:
        corrected = np.tanh(contrast * normalized) / np.tanh(contrast)
    else:
        contrast_abs = -contrast
        corrected = normalized / (1.0 + contrast_abs * (1.0 - abs(normalized)))
    corrected = (corrected + 1.0) * 0.5 * max_px_val
    lut = corrected.astype(img.dtype)
    return cv2.LUT(img, lut) if img.dtype == np.uint8 else np.take(lut, img)
