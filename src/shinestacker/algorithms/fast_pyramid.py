# pylint: disable=C0114, C0115, C0116, E1101, R0914, R1702, R1732, R0913, R0917, R0912
import os
import tempfile
import numpy as np
from .. config.constants import constants
from .. core.exceptions import RunStopException
from .utils import read_img
from .pyramid import PyramidBase


class FastPyramidStack(PyramidBase):
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE,
                 kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL,
                 float_type=constants.DEFAULT_PY_FLOAT,
                 tile_size=constants.DEFAULT_PY_TILE_SIZE):
        super().__init__("fast_pyramid", min_size, kernel_size, gen_kernel, float_type)
        self.offset = np.arange(-self.pad_amount, self.pad_amount + 1)
        self.dtype = None
        self.num_pixel_values = None
        self.max_pixel_value = None
        self.tile_size = tile_size
        self.temp_dir = tempfile.TemporaryDirectory()

    def process_single_image(self, img, levels, img_index):
        laplacian = self.single_image_laplacian(img, levels)
        for i, level_data in enumerate(laplacian[::-1]):
            np.save(os.path.join(self.temp_dir.name, f'img_{img_index}_level_{i}.npy'), level_data)
        return len(laplacian)

    def load_level(self, img_index, level):
        return np.load(os.path.join(self.temp_dir.name, f'img_{img_index}_level_{level}.npy'))

    def cleanup_temp_files(self):
        self.temp_dir.cleanup()

    def fuse_pyramids(self, all_level_counts, num_images):
        max_levels = max(all_level_counts)
        fused = []
        for level in range(max_levels - 1, -1, -1):
            self.print_message(f': fusing pyramids, layer: {level + 1}')
            if level == 0:
                sample_level = self.load_level(0, 0)
                h, w = sample_level.shape[:2]
                del sample_level
                fused_level = np.zeros((h, w, 3), dtype=self.float_type)
                for y in range(0, h, self.tile_size):
                    for x in range(0, w, self.tile_size):
                        y_end = min(y + self.tile_size, h)
                        x_end = min(x + self.tile_size, w)
                        self.print_message(f': fusing tile [{x}, {x_end - 1}]×[{y}, {y_end - 1}]')
                        laplacians = []
                        for img_index in range(num_images):
                            if level < all_level_counts[img_index]:
                                full_laplacian = self.load_level(img_index, level)
                                tile = full_laplacian[y:y_end, x:x_end]
                                laplacians.append(tile)
                                del full_laplacian
                        stacked = np.stack(laplacians, axis=0)
                        fused_tile = self.fuse_laplacian(stacked)
                        fused_level[y:y_end, x:x_end] = fused_tile
                        del laplacians, stacked, fused_tile
                        if self.process.callback(
                                'check_running', self.process.id, self.process.name) is False:
                            self.cleanup_temp_files()
                            raise RunStopException(self.name)
            else:
                laplacians = []
                for img_index in range(num_images):
                    if level < all_level_counts[img_index]:
                        laplacian = self.load_level(img_index, level)
                        laplacians.append(laplacian)
                if level == max_levels - 1:
                    stacked = np.stack(laplacians, axis=0)
                    fused_level = self.get_fused_base(stacked)
                else:
                    stacked = np.stack(laplacians, axis=0)
                    fused_level = self.fuse_laplacian(stacked)
                    if self.process.callback(
                            'check_running', self.process.id, self.process.name) is False:
                        self.cleanup_temp_files()
                        raise RunStopException(self.name)
            fused.append(fused_level)
        self.print_message(': pyramids fusion completed')
        return fused[::-1]

    def focus_stack(self, filenames):
        n = len(filenames)
        levels = self.focus_stack_validate(filenames, self.cleanup_temp_files)
        all_level_counts = []
        for i, img_path in enumerate(filenames):
            self.print_message(f": processing file {img_path.split('/')[-1]}")
            img = read_img(img_path)
            level_count = self.process_single_image(img, levels, i)
            all_level_counts.append(level_count)
            if self.do_step_callback:
                self.process.callback('after_step', self.process.id, self.process.name, i + n)
            if self.process.callback('check_running', self.process.id, self.process.name) is False:
                self.cleanup_temp_files()
                raise RunStopException(self.name)
        fused_pyramid = self.fuse_pyramids(all_level_counts, n)
        stacked_image = self.collapse(fused_pyramid)
        self.cleanup_temp_files()
        return stacked_image.astype(self.dtype)
