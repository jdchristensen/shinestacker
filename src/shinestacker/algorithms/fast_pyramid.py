# pylint: disable=C0114, C0115, C0116, E1101
import numpy as np
import cv2
import tempfile
import os
from .. config.constants import constants
from .. core.exceptions import RunStopException
from .utils import read_img
from .base_stack_algo import BaseStackAlgo

TILE_SIZE = 512


class FastPyramidBase(BaseStackAlgo):
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE,
                 kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL,
                 float_type=constants.DEFAULT_PY_FLOAT):
        super().__init__("pyramid", 2, float_type)
        self.min_size = min_size
        self.kernel_size = kernel_size
        self.pad_amount = (kernel_size - 1) // 2
        self.do_step_callback = False
        kernel = np.array([0.25 - gen_kernel / 2.0, 0.25,
                           gen_kernel, 0.25, 0.25 - gen_kernel / 2.0])
        self.gen_kernel = np.outer(kernel, kernel)

    def convolve(self, image):
        return cv2.filter2D(image, -1, self.gen_kernel, borderType=cv2.BORDER_REFLECT101)

    def reduce_layer(self, layer):
        if len(layer.shape) == 2:
            return self.convolve(layer)[::2, ::2]
        reduced_channels = [self.reduce_layer(layer[:, :, channel])
                            for channel in range(layer.shape[2])]
        return np.stack(reduced_channels, axis=-1)

    def expand_layer(self, layer):
        if len(layer.shape) == 2:
            expand = np.empty((2 * layer.shape[0], 2 * layer.shape[1]), dtype=layer.dtype)
            expand[::2, ::2] = layer
            expand[1::2, :] = 0
            expand[:, 1::2] = 0
            return 4. * self.convolve(expand)
        ch_layer = self.expand_layer(layer[:, :, 0])
        next_layer = np.zeros(list(ch_layer.shape) + [layer.shape[2]], dtype=layer.dtype)
        next_layer[:, :, 0] = ch_layer
        for channel in range(1, layer.shape[2]):
            next_layer[:, :, channel] = self.expand_layer(layer[:, :, channel])
        return next_layer

    def fuse_laplacian(self, laplacians):
        gray_laps = [cv2.cvtColor(lap.astype(np.float32), cv2.COLOR_BGR2GRAY) for lap in laplacians]
        energies = [self.convolve(np.square(gray_lap)) for gray_lap in gray_laps]
        best = np.argmax(energies, axis=0)
        fused = np.zeros_like(laplacians[0])
        for i, lap in enumerate(laplacians):
            fused += np.where(best[:, :, np.newaxis] == i, lap, 0)
        return fused

    def collapse(self, pyramid):
        self.print_message(": collapse pyramid")
        img = pyramid[-1]
        for layer in pyramid[-2::-1]:
            expanded = self.expand_layer(img)
            if expanded.shape != layer.shape:
                expanded = expanded[:layer.shape[0], :layer.shape[1]]
            img = expanded + layer
        return np.clip(np.abs(img), 0, self.max_pixel_value)

    def entropy(self, image):
        levels, counts = np.unique(image.astype(self.dtype), return_counts=True)
        probabilities = np.zeros((self.num_pixel_values), dtype=self.float_type)
        probabilities[levels] = counts.astype(self.float_type) / counts.sum()
        padded_image = cv2.copyMakeBorder(image, self.pad_amount, self.pad_amount, self.pad_amount,
                                          self.pad_amount, cv2.BORDER_REFLECT101)
        return np.fromfunction(np.vectorize(lambda row, column: self.area_entropy(
            self.get_pad(padded_image, row, column), probabilities)), image.shape[:2], dtype=int)

    def area_entropy(self, area, probabilities):
        levels = area.flatten()
        return self.float_type(-1. * (levels * np.log(probabilities[levels])).sum())

    def get_pad(self, padded_image, row, column):
        return padded_image[row + self.pad_amount +
                            self.offset[:, np.newaxis], column +
                            self.pad_amount + self.offset]

    def area_deviation(self, area):
        return np.square(area - np.average(area).astype(self.float_type)).sum() / area.size

    def deviation(self, image):
        padded_image = cv2.copyMakeBorder(image, self.pad_amount, self.pad_amount, self.pad_amount,
                                          self.pad_amount, cv2.BORDER_REFLECT101)
        return np.fromfunction(
            np.vectorize(lambda row, column:
                         self.area_deviation(self.get_pad(padded_image, row, column))),
            image.shape[:2], dtype=int)

    def get_fused_base(self, images):
        layers = images.shape[0]
        entropies = np.zeros(images.shape[:3], dtype=self.float_type)
        deviations = np.copy(entropies)
        gray_images = np.array([cv2.cvtColor(
            images[layer].astype(np.float32),
            cv2.COLOR_BGR2GRAY).astype(self.dtype) for layer in range(layers)])
        entropies = np.array([self.entropy(img) for img in gray_images])
        deviations = np.array([self.deviation(img) for img in gray_images])
        best_e = np.argmax(entropies, axis=0)
        best_d = np.argmax(deviations, axis=0)
        fused = np.zeros(images.shape[1:], dtype=self.float_type)
        for layer in range(layers):
            img = images[layer]
            fused += np.where(best_e[:, :, np.newaxis] == layer, img, 0)
            fused += np.where(best_d[:, :, np.newaxis] == layer, img, 0)
        return (fused / 2).astype(images.dtype)


class FastPyramidStack(FastPyramidBase):
    def __init__(self, min_size=constants.DEFAULT_PY_MIN_SIZE,
                 kernel_size=constants.DEFAULT_PY_KERNEL_SIZE,
                 gen_kernel=constants.DEFAULT_PY_GEN_KERNEL,
                 float_type=constants.DEFAULT_PY_FLOAT):
        super().__init__(min_size, kernel_size, gen_kernel, float_type)
        self.offset = np.arange(-self.pad_amount, self.pad_amount + 1)
        self.dtype = None
        self.num_pixel_values = None
        self.max_pixel_value = None
        self.temp_dir = tempfile.TemporaryDirectory()

    def process_single_image(self, img, levels, img_index):
        pyramid = [img.astype(self.float_type)]
        for _ in range(levels):
            next_layer = self.reduce_layer(pyramid[-1])
            if min(next_layer.shape[:2]) < 4:
                break
            pyramid.append(next_layer)
        laplacian = [pyramid[-1]]
        for level in range(len(pyramid) - 1, 0, -1):
            expanded = self.expand_layer(pyramid[level])
            pyr = pyramid[level - 1]
            h, w = pyr.shape[:2]
            expanded = expanded[:h, :w]
            laplacian.append(pyr - expanded)        
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
        for level in range(max_levels-1, -1, -1):
            self.print_message(f': fusing pyramids, layer: {level + 1}')            
            if level == 0:
                sample_level = self.load_level(0, 0)
                h, w = sample_level.shape[:2]
                del sample_level                
                fused_level = np.zeros((h, w, 3), dtype=self.float_type)
                
                for y in range(0, h, TILE_SIZE):
                    for x in range(0, w, TILE_SIZE):
                        y_end = min(y + TILE_SIZE, h)
                        x_end = min(x + TILE_SIZE, w)
                        self.print_message(f': fusing tile [{x}, {x_end}]×[{y}, {y_end}]')
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
            fused.append(fused_level)
        self.print_message(': pyramids fusion completed')
        return fused[::-1]

    def focus_stack(self, filenames):
        metadata = None
        all_level_counts = []
        levels = None
        n = len(filenames)        
        for i, img_path in enumerate(filenames):
            self.print_message(f": validating file {img_path.split('/')[-1]}")
            img, metadata, updated = self.read_image_and_update_metadata(img_path, metadata)
            if updated:
                self.dtype = metadata[1]
                self.num_pixel_values = constants.NUM_UINT8 \
                    if self.dtype == np.uint8 else constants.NUM_UINT16
                self.max_pixel_value = constants.MAX_UINT8 \
                    if self.dtype == np.uint8 else constants.MAX_UINT16
                levels = int(np.log2(min(img.shape[:2]) / self.min_size))
            if self.do_step_callback:
                self.process.callback('after_step', self.process.id, self.process.name, i)
            if self.process.callback('check_running', self.process.id, self.process.name) is False:
                self.cleanup_temp_files()
                raise RunStopException(self.name)        
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
