# pylint: disable=C0114, C0115, C0116, E1101, R0913, R0902, R0914, R0917
import os
import numpy as np
from .. config.constants import constants
from .utils import extension_tif_jpg
from .base_stack_algo import BaseStackAlgo
from .pyramid import PyramidStack
from .pyramid_tiles import PyramidTilesStack


class PyramidAutoStack(BaseStackAlgo):
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE,
                 kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL,
                 float_type=constants.DEFAULT_PY_FLOAT,
                 tile_size=2048,
                 n_tiled_layers=2,
                 memory_limit=constants.DEFAULT_PY_MEMORY_LIMIT_GB,
                 mode='auto'):
        super().__init__("auto_pyramid", 2, float_type)
        self.min_size = min_size
        self.kernel_size = kernel_size
        self.gen_kernel = gen_kernel
        self.float_type = float_type
        self.tile_size = tile_size
        self.n_tiled_layers = n_tiled_layers
        self.memory_limit = memory_limit * 1024**3
        self.mode = mode
        self._implementation = None
        self.dtype = None
        self.shape = None
        self.n_levels = None
        self.n_frames = 0
        self.channels = 3
        dtype = np.float32 if self.float_type == constants.FLOAT_32 else np.float64
        self.bytes_per_pixel = self.channels * np.dtype(dtype).itemsize
        self.overhead = 1.2

    def init(self, filenames):
        first_img_file = None
        for filename in filenames:
            if os.path.isfile(filename) and extension_tif_jpg(filename):
                first_img_file = filename
                break
        if first_img_file is None:
            raise ValueError("No valid image files found")
        _img, metadata, _ = self.read_image_and_update_metadata(first_img_file, None)
        self.shape, self.dtype = metadata
        self.n_levels = int(np.log2(min(self.shape) / self.min_size))
        self.n_frames = len(filenames)
        memory_required_memory = self._estimate_memory_memory()
        if self.mode == 'memory' or (self.mode == 'auto' and
                                     memory_required_memory <= self.memory_limit):
            self._implementation = PyramidStack(
                min_size=self.min_size,
                kernel_size=self.kernel_size,
                gen_kernel=self.gen_kernel,
                float_type=self.float_type
            )
            self.print_message(": using memory-based pyramid stacking")
        else:
            optimal_params = self._find_optimal_tile_params()
            self._implementation = PyramidTilesStack(
                min_size=self.min_size,
                kernel_size=self.kernel_size,
                gen_kernel=self.gen_kernel,
                float_type=self.float_type,
                tile_size=optimal_params['tile_size'],
                n_tiled_layers=optimal_params['n_tiled_layers']
            )
            self.print_message(f": using tile-based pyramid stacking "
                               f"(tile_size: {optimal_params['tile_size']}, "
                               f"n_tiled_layers: {optimal_params['n_tiled_layers']})")
        self._implementation.init(filenames)
        self._implementation.set_do_step_callback(self.do_step_callback)
        if self.process is not None:
            self._implementation.set_process(self.process)
        else:
            raise RuntimeError("self.process must be initialized.")

    def _estimate_memory_memory(self):
        h, w = self.shape[:2]
        total_memory = 0
        for _ in range(self.n_levels):
            total_memory += h * w * self.bytes_per_pixel
            h, w = max(1, h // 2), max(1, w // 2)
        return self.overhead * total_memory * self.n_frames

    def _estimate_memory_tiles_with_params(self, tile_size, n_tiled_layers):
        tile_memory = tile_size * tile_size * self.bytes_per_pixel * self.n_frames
        h, w = self.shape[:2]
        for _ in range(n_tiled_layers):
            h, w = max(1, h // 2), max(1, w // 2)
        layer_memory = h * w * self.bytes_per_pixel * self.n_frames
        return self.overhead * max(tile_memory, layer_memory)

    def _find_optimal_tile_params(self):
        tile_size_max = int(np.sqrt(self.memory_limit /
                            (self.n_frames * self.bytes_per_pixel * self.overhead)))
        tile_size = min(self.tile_size, tile_size_max, self.shape[0], self.shape[1])
        best_params = {'tile_size': tile_size, 'n_tiled_layers': 1}
        best_memory = self._estimate_memory_tiles_with_params(tile_size, 1)
        for n_layers in range(2, self.n_levels):
            memory_estimate = self._estimate_memory_tiles_with_params(tile_size, n_layers)
            if memory_estimate < best_memory and memory_estimate <= self.memory_limit:
                best_params = {'tile_size': tile_size, 'n_tiled_layers': n_layers}
                best_memory = memory_estimate
            if memory_estimate > self.memory_limit:
                break
        return best_params

    def set_process(self, process):
        super().set_process(process)
        if self._implementation is not None:
            self._implementation.set_process(process)

    def total_steps(self, n_frames):
        if self._implementation is None:
            return super().total_steps(n_frames)
        return self._implementation.total_steps(n_frames)

    def focus_stack(self):
        if self._implementation is None:
            raise RuntimeError("PyramidAutoStack not initialized")
        return self._implementation.focus_stack()

    def after_step(self, step):
        if self._implementation is not None:
            self._implementation.after_step(step)
        else:
            super().after_step(step)

    def check_running(self, cleanup_callback=None):
        if self._implementation is not None:
            self._implementation.check_running(cleanup_callback)
        else:
            super().check_running(cleanup_callback)
