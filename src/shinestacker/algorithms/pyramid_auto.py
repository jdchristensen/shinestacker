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
                 tile_size=constants.DEFAULT_PY_TILE_SIZE,
                 n_tiled_layers=constants.DEFAULT_PY_N_TILED_LAYERS,
                 memory_limit=constants.DEFAULT_PY_MEMORY_LIMIT_GB,
                 max_threads=constants.DEFAULT_PY_MAX_THREADS,
                 max_tile_size=2048,
                 min_n_tiled_layers=1,
                 mode='auto'):
        super().__init__("auto_pyramid", 2, float_type)
        self.min_size = min_size
        self.kernel_size = kernel_size
        self.gen_kernel = gen_kernel
        self.float_type = float_type
        self.tile_size = tile_size
        self.n_tiled_layers = n_tiled_layers
        self.memory_limit = memory_limit * constants.ONE_GIGA
        self.max_threads = max_threads
        available_cores = os.cpu_count() or 1
        self.num_threads = min(max_threads, available_cores)
        self.max_tile_size = max_tile_size
        self.min_n_tiled_layers = min_n_tiled_layers
        self.mode = mode
        self._implementation = None
        self.dtype = None
        self.shape = None
        self.n_levels = None
        self.n_frames = 0
        self.channels = 3
        dtype = np.float32 if self.float_type == constants.FLOAT_32 else np.float64
        self.bytes_per_pixel = self.channels * np.dtype(dtype).itemsize
        self.overhead = 1.5

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
                n_tiled_layers=optimal_params['n_tiled_layers'],
                max_threads=self.num_threads
            )
            self.print_message(f": using tile-based pyramid stacking "
                               f"(tile_size: {optimal_params['tile_size']}, "
                               f"n_tiled_layers: {optimal_params['n_tiled_layers']}), "
                               f"{self.num_threads} cores.")
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

    def _find_optimal_tile_params(self):
        tile_size_max = int(np.sqrt(self.memory_limit /
                            (self.num_threads * self.n_frames *
                             self.bytes_per_pixel * self.overhead)))
        tile_size = min(self.max_tile_size, tile_size_max, self.shape[0], self.shape[1])
        n_tiled_layers = 0
        for layer in range(self.n_levels):
            h = max(1, self.shape[0] // (2 ** layer))
            w = max(1, self.shape[1] // (2 ** layer))
            if h > tile_size or w > tile_size:
                n_tiled_layers = layer + 1
            else:
                break
        n_tiled_layers = max(n_tiled_layers, self.min_n_tiled_layers)
        n_tiled_layers = min(n_tiled_layers, self.n_levels)
        return {'tile_size': tile_size, 'n_tiled_layers': n_tiled_layers}

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
