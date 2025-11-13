# pylint: disable=C0114, C0115, C0116, E1101
import numpy as np
import cv2
from .. config.constants import constants
from .. core.exceptions import InvalidOptionError

_cv2_border_mode_map = {
    constants.BORDER_CONSTANT: cv2.BORDER_CONSTANT,
    constants.BORDER_REPLICATE: cv2.BORDER_REPLICATE,
    constants.BORDER_REPLICATE_BLUR: cv2.BORDER_REPLICATE
}


def apply_alignment_transform(img_0, img_ref, m, alignment_config, callbacks=None):
    try:
        cv2_border_mode = _cv2_border_mode_map[alignment_config['border_mode']]
    except KeyError as e:
        raise InvalidOptionError("border_mode", alignment_config['border_mode']) from e
    if callbacks and 'estimation_message' in callbacks:
        callbacks['estimation_message']()
    transform_type = alignment_config['transform']
    if transform_type == constants.ALIGN_RIGID and m.shape != (2, 3):
        if callbacks and 'warning' in callbacks:
            callbacks['warning'](f"invalid matrix shape for rigid transform: {m.shape}")
        return None
    if transform_type == constants.ALIGN_HOMOGRAPHY and m.shape != (3, 3):
        if callbacks and 'warning' in callbacks:
            callbacks['warning'](f"invalid matrix shape for homography: {m.shape}")
        return None
    img_mask = np.ones_like(img_0, dtype=np.uint8)
    h_ref, w_ref = img_ref.shape[:2]
    img_warp = None
    if transform_type == constants.ALIGN_HOMOGRAPHY:
        img_warp = cv2.warpPerspective(
            img_0, m, (w_ref, h_ref),
            borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
        if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
            mask = cv2.warpPerspective(img_mask, m, (w_ref, h_ref),
                                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    elif transform_type == constants.ALIGN_RIGID:
        img_warp = cv2.warpAffine(
            img_0, m, (w_ref, h_ref),
            borderMode=cv2_border_mode, borderValue=alignment_config['border_value'])
        if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
            mask = cv2.warpAffine(img_mask, m, (w_ref, h_ref),
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if alignment_config['border_mode'] == constants.BORDER_REPLICATE_BLUR:
        if callbacks and 'blur_message' in callbacks:
            callbacks['blur_message']()
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        blurred_warp = cv2.GaussianBlur(
            img_warp, (21, 21), sigmaX=alignment_config['border_blur'])
        img_warp[mask == 0] = blurred_warp[mask == 0]
    return img_warp
