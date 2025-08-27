# pylint: disable=C0114, C0115, C0116, E1101, R0914, R1702, R1732, R0913, R0917, R0912, R0915
import os
import tempfile
import numpy as np
from .. config.constants import constants
from .utils import read_img
from .pyramid import PyramidBase


class PyramidTilesStack(PyramidBase):
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
        self.n_tiles = 0

    def init(self, filenames):
        super().init(filenames)
        self.n_tiles = (self.shape[0] // self.tile_size + 1) * (self.shape[1] // self.tile_size + 1)

    def total_steps(self, n_frames):
        n_steps = super().total_steps(n_frames)
        return n_steps + self.n_tiles

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
        count = self._steps_per_frame * self.n_frames
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
                        self.after_step(count)
                        self.check_running(self.cleanup_temp_files)
                        count += 1
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
                    self.check_running(self.cleanup_temp_files)
            fused.append(fused_level)
            count += 1
            self.after_step(count)
            self.check_running(self.cleanup_temp_files)
        self.print_message(': pyramids fusion completed')
        return fused[::-1]

    def focus_stack(self):
        n = len(self.filenames)
        self.focus_stack_validate(self.cleanup_temp_files)
        all_level_counts = []
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": processing file {img_path.split('/')[-1]}")
            img = read_img(img_path)
            level_count = self.process_single_image(img, self.n_levels, i)
            all_level_counts.append(level_count)
            self.after_step(i + n + 1)
            self.check_running(self.cleanup_temp_files)
        fused_pyramid = self.fuse_pyramids(all_level_counts, n)
        stacked_image = self.collapse(fused_pyramid)
        self.cleanup_temp_files()
        return stacked_image.astype(self.dtype)
