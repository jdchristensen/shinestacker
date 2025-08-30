
# pylint: disable=C0114, C0115, C0116, E1101, R0914, R1702, R1732, R0913
# pylint: disable=R0917, R0912, R0915, R0902, W0718
import os
import time
import shutil
import tempfile
import concurrent.futures
import numpy as np
from .. config.constants import constants
from .. core.exceptions import RunStopException
from .utils import read_img
from .pyramid import PyramidBase


class PyramidTilesStack(PyramidBase):
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE,
                 kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL,
                 float_type=constants.DEFAULT_PY_FLOAT,
                 tile_size=constants.DEFAULT_PY_TILE_SIZE,
                 n_tiled_layers=constants.DEFAULT_PY_N_TILED_LAYERS,
                 max_threads=constants.DEFAULT_PY_MAX_THREADS):
        super().__init__("fast_pyramid", min_size, kernel_size, gen_kernel, float_type)
        self.offset = np.arange(-self.pad_amount, self.pad_amount + 1)
        self.dtype = None
        self.num_pixel_values = None
        self.max_pixel_value = None
        self.tile_size = tile_size
        self.n_tiled_layers = n_tiled_layers
        self.temp_dir = tempfile.TemporaryDirectory()
        self.n_tiles = 0
        self.level_shapes = {}
        available_cores = os.cpu_count() or 1
        self.num_threads = max(1, min(max_threads, available_cores))

    def init(self, filenames):
        super().init(filenames)
        self.n_tiles = 0
        for layer in range(self.n_tiled_layers):
            h, w = max(1, self.shape[0] // (2 ** layer)), max(1, self.shape[1] // (2 ** layer))
            self.n_tiles += (h // self.tile_size + 1) * (w // self.tile_size + 1)

    def total_steps(self, n_frames):
        n_steps = super().total_steps(n_frames)
        return n_steps + self.n_tiles

    def _process_single_image_wrapper(self, args):
        img_path, img_index, _n = args
        # self.print_message(f": processing file {img_path.split('/')[-1]}, {img_index + 1}/{n}")
        img = read_img(img_path)
        level_count = self.process_single_image(img, self.n_levels, img_index)
        return img_index, level_count

    def process_single_image(self, img, levels, img_index):
        laplacian = self.single_image_laplacian(img, levels)
        self.level_shapes[img_index] = [level.shape for level in laplacian[::-1]]
        for level_idx, level_data in enumerate(laplacian[::-1]):
            h, w = level_data.shape[:2]
            if level_idx < self.n_tiled_layers:
                for y in range(0, h, self.tile_size):
                    for x in range(0, w, self.tile_size):
                        y_end, x_end = min(y + self.tile_size, h), min(x + self.tile_size, w)
                        tile = level_data[y:y_end, x:x_end]
                        np.save(
                            os.path.join(
                                self.temp_dir.name,
                                f'img_{img_index}_level_{level_idx}_tile_{y}_{x}.npy'),
                            tile
                        )
            else:
                np.save(
                    os.path.join(self.temp_dir.name,
                                 f'img_{img_index}_level_{level_idx}.npy'), level_data)
        return len(laplacian)

    def load_level_tile(self, img_index, level, y, x):
        return np.load(
            os.path.join(self.temp_dir.name,
                         f'img_{img_index}_level_{level}_tile_{y}_{x}.npy'))

    def load_level(self, img_index, level):
        return np.load(os.path.join(self.temp_dir.name, f'img_{img_index}_level_{level}.npy'))

    def cleanup_temp_files(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            try:
                shutil.rmtree(self.temp_dir.name, ignore_errors=True)
            except Exception:
                pass

    def _fuse_level_tiles_serial(self, level, num_images, all_level_counts, h, w, count):
        fused_level = np.zeros((h, w, 3), dtype=self.float_type)
        for y in range(0, h, self.tile_size):
            for x in range(0, w, self.tile_size):
                y_end, x_end = min(y + self.tile_size, h), min(x + self.tile_size, w)
                self.print_message(f': fusing tile [{x}, {x_end - 1}]×[{y}, {y_end - 1}]')
                laplacians = []
                for img_index in range(num_images):
                    if level < all_level_counts[img_index]:
                        try:
                            tile = self.load_level_tile(img_index, level, y, x)
                            laplacians.append(tile)
                        except FileNotFoundError:
                            continue
                if laplacians:
                    stacked = np.stack(laplacians, axis=0)
                    fused_tile = self.fuse_laplacian(stacked)
                    fused_level[y:y_end, x:x_end] = fused_tile
                self.after_step(count)
                self.check_running(self.cleanup_temp_files)
                count += 1
        return fused_level, count

    def _fuse_level_tiles_parallel(self, level, num_images, all_level_counts, h, w, count):
        fused_level = np.zeros((h, w, 3), dtype=self.float_type)
        tiles = []
        for y in range(0, h, self.tile_size):
            for x in range(0, w, self.tile_size):
                tiles.append((y, x))
        self.print_message(f': starting parallel propcessging on {self.num_threads} cores')
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            future_to_tile = {
                executor.submit(
                    self._process_tile, level, num_images, all_level_counts, y, x, h, w): (y, x)
                for y, x in tiles
            }
            for future in concurrent.futures.as_completed(future_to_tile):
                y, x = future_to_tile[future]
                try:
                    fused_tile = future.result()
                    if fused_tile is not None:
                        y_end, x_end = min(y + self.tile_size, h), min(x + self.tile_size, w)
                        fused_level[y:y_end, x:x_end] = fused_tile
                        self.print_message(f': fused tile [{x}, {x_end - 1}]×[{y}, {y_end - 1}]')
                except Exception as e:
                    self.print_message(f"Error processing tile ({y}, {x}): {str(e)}")
                self.after_step(count)
                self.check_running(self.cleanup_temp_files)
                count += 1
        return fused_level, count

    def _process_tile(self, level, num_images, all_level_counts, y, x, h, w):
        laplacians = []
        for img_index in range(num_images):
            if level < all_level_counts[img_index]:
                try:
                    tile = self.load_level_tile(img_index, level, y, x)
                    laplacians.append(tile)
                except FileNotFoundError:
                    continue
        if laplacians:
            stacked = np.stack(laplacians, axis=0)
            return self.fuse_laplacian(stacked)
        y_end, x_end = min(y + self.tile_size, h), min(x + self.tile_size, w)
        return np.zeros((y_end - y, x_end - x, 3), dtype=self.float_type)

    def fuse_pyramids(self, all_level_counts, num_images):
        max_levels = max(all_level_counts)
        fused = []
        count = self._steps_per_frame * self.n_frames
        for level in range(max_levels - 1, -1, -1):
            self.print_message(f': fusing pyramids, layer: {level + 1}')
            if level < self.n_tiled_layers:
                h, w = None, None
                for img_index in range(num_images):
                    if level < all_level_counts[img_index]:
                        h, w = self.level_shapes[img_index][level][:2]
                        break
                if h is None or w is None:
                    continue
                if self.num_threads > 1:
                    fused_level, count = self._fuse_level_tiles_parallel(
                        level, num_images, all_level_counts, h, w, count)
                else:
                    fused_level, count = self._fuse_level_tiles_serial(
                        level, num_images, all_level_counts, h, w, count)
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
                self.check_running(lambda: None)
            fused.append(fused_level)
            count += 1
            self.after_step(count)
            self.check_running(lambda: None)
        self.print_message(': pyramids fusion completed')
        return fused[::-1]

    def focus_stack(self):
        n = len(self.filenames)
        self.focus_stack_validate(self.cleanup_temp_files)
        all_level_counts = [0] * n
        if self.num_threads > 1:
            self.print_message(f': starting parallel image processing on {self.num_threads} cores')
            args_list = [(file_path, i, n) for i, file_path in enumerate(self.filenames)]
            executor = None
            try:
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.num_threads)
                future_to_index = {
                    executor.submit(self._process_single_image_wrapper, args): i
                    for i, args in enumerate(args_list)
                }
                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_index):
                    i = future_to_index[future]
                    try:
                        img_index, level_count = future.result()
                        all_level_counts[img_index] = level_count
                        completed_count += 1
                        self.print_message(f': completed processing image {completed_count}/{n}')
                    except Exception as e:
                        self.print_message(f"Error processing image {i + 1}: {str(e)}")
                    self.after_step(i + n + 1)
                    self.check_running(lambda: None)
            except RunStopException:
                self.print_message(": stopping image processing...")
                if executor:
                    executor.shutdown(wait=False, cancel_futures=True)
                    time.sleep(0.5)
                    self._safe_cleanup()
                raise
            finally:
                if executor:
                    executor.shutdown(wait=True)
        else:
            for i, file_path in enumerate(self.filenames):
                self.print_message(f": processing file {file_path.split('/')[-1]}, {i + 1}/{n}")
                img = read_img(file_path)
                level_count = self.process_single_image(img, self.n_levels, i)
                all_level_counts[i] = level_count
                self.after_step(i + n + 1)
                self.check_running(lambda: None)
        try:
            self.check_running(lambda: None)
            fused_pyramid = self.fuse_pyramids(all_level_counts, n)
            stacked_image = self.collapse(fused_pyramid)
            return stacked_image.astype(self.dtype)
        except RunStopException:
            self.print_message(": stopping pyramid fusion...")
            raise
        finally:
            self._safe_cleanup()

    def _safe_cleanup(self):
        try:
            self.cleanup_temp_files()
        except Exception as e:
            self.print_message(f": warning during cleanup: {str(e)}")
            time.sleep(1)
            try:
                self.cleanup_temp_files()
            except Exception:
                self.print_message(": could not fully clean up temporary files")
