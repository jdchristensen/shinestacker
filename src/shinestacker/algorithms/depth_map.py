# pylint: disable=C0114, C0115, C0116, E1101, R0902, R0913, R0917, R0914, R0912, R0915
import os
import numpy as np
import cv2
from .. config.constants import constants
from .. config.defaults import DEFAULTS
from .. core.exceptions import InvalidOptionError
from .utils import read_img, read_and_validate_img, img_bw
from .base_stack_algo import BaseStackAlgo


class DepthMapStack(BaseStackAlgo):
    def __init__(self, map_type=DEFAULTS['depth_map_params']['map_type'],
                 energy=DEFAULTS['depth_map_params']['energy'],
                 blend_mode=DEFAULTS['depth_map_params']['blend_mode'],
                 weight_power=DEFAULTS['depth_map_params']['weight_power'],
                 kernel_size=DEFAULTS['depth_map_params']['kernel_size'],
                 blur_size=DEFAULTS['depth_map_params']['blur_size'],
                 energy_smooth_size=DEFAULTS['depth_map_params']['energy_smooth_size'],
                 energy_sigma_color=DEFAULTS['depth_map_params']['energy_sigma_color'],
                 energy_sigma_space=DEFAULTS['depth_map_params']['energy_sigma_space'],
                 weights_smooth_size=DEFAULTS['depth_map_params']['weights_smooth_size'],
                 weights_sigma_color=DEFAULTS['depth_map_params']['weights_sigma_color'],
                 weights_sigma_space=DEFAULTS['depth_map_params']['weights_sigma_space'],
                 temperature=DEFAULTS['depth_map_params']['temperature'],
                 float_type=DEFAULTS['depth_map_params']['float_type']):
        self.steps_per_frame = 3
        if energy_smooth_size > 0:
            self.steps_per_frame += 1
        if weights_smooth_size > 0:
            self.steps_per_frame += 1
        super().__init__("depth map", self.steps_per_frame, float_type)
        self.map_type = map_type
        self.energy = energy
        self.blend_mode = blend_mode
        self.weight_power = weight_power
        self.kernel_size = kernel_size
        self.blur_size = blur_size
        self.energy_smooth_size = energy_smooth_size
        self.energy_sigma_color = energy_sigma_color
        self.energy_sigma_space = energy_sigma_space
        self.weights_smooth_size = weights_smooth_size
        self.weights_sigma_color = weights_sigma_color
        self.weights_sigma_space = weights_sigma_space
        self.temperature = temperature
        self.steps_count = 0

    def _with_energy_progress(self, energy_func, message_template):
        def wrapper(gray_images, *args, **kwargs):
            n = gray_images.shape[0]
            result = np.zeros(gray_images.shape, dtype=self.float_type)
            n_images = len(self.filenames)
            for i in range(n):
                self.print_message(f": {message_template} {i + 1}/{n}")
                if args or kwargs:
                    result[i] = energy_func(gray_images[i], *args, **kwargs)
                else:
                    result[i] = energy_func(gray_images[i])
                self.after_step(i + n_images)
                self.check_running()
            return result
        return wrapper

    def get_sobel_map(self, gray_images):
        def sobel_energy(img):
            return np.abs(cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)) + \
                np.abs(cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3))
        return self._with_energy_progress(
            sobel_energy, "create sobel energy map")(gray_images)

    def get_laplacian_map(self, gray_images):
        def laplacian_energy(img):
            blurred = cv2.GaussianBlur(img, (self.blur_size, self.blur_size), 0)
            lap_result = cv2.Laplacian(
                blurred, cv2.CV_32F if self.float_type == np.float32 else cv2.CV_64F,
                ksize=self.kernel_size)
            return np.abs(lap_result)
        return self._with_energy_progress(
            laplacian_energy, "create laplacian energy map")(gray_images)

    def get_modified_laplacian(self, gray_images):
        def mod_laplacian_energy(img):
            dx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
            dy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
            return np.abs(dx) + np.abs(dy)
        return self._with_energy_progress(
            mod_laplacian_energy, "create modified laplacian energy map")(gray_images)

    def get_variance_map(self, gray_images, window_size=5):
        def variance_energy(img, window_size=window_size):
            mean = cv2.boxFilter(img, -1, (window_size, window_size))
            mean_sq = cv2.boxFilter(img**2, -1, (window_size, window_size))
            return mean_sq - mean**2
        return self._with_energy_progress(
            variance_energy, "create variance energy map")(gray_images)

    def get_tenengrad(self, gray_images, threshold=5):
        def tenengrad_energy(img, threshold=threshold):
            gx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
            tenengrad = gx * gx + gy * gy
            return np.where(tenengrad > threshold, tenengrad, 0)
        return self._with_energy_progress(
            tenengrad_energy, "create tenengrad energy map")(gray_images)

    def smooth_energy(self, energy_map):
        n_images = len(self.filenames)
        if self.energy_smooth_size <= 0:
            return energy_map
        smoothed = np.zeros(energy_map.shape, dtype=np.float32)
        n = energy_map.shape[0]
        for i in range(n):
            self.print_message(f": smooth energy map,  {i + 1}/{n}")
            energy_32f = energy_map[i].astype(np.float32)
            smoothed_32f = cv2.bilateralFilter(
                energy_32f, self.energy_smooth_size,
                self.energy_sigma_color, self.energy_sigma_space)
            smoothed[i] = smoothed_32f.astype(energy_map.dtype)
            self.after_step(i + n_images * 2)
            self.check_running()
        return smoothed

    def get_focus_map(self, energies):
        if self.map_type == constants.DM_MAP_AVERAGE:
            sum_energies = np.sum(energies, axis=0)
            weights = np.divide(energies, sum_energies, where=sum_energies != 0)
        elif self.map_type == constants.DM_MAP_MAX:
            max_energy = np.max(energies, axis=0)
            relative = np.exp((energies - max_energy) / max(self.temperature, 0.1))
            weights = relative / np.sum(relative, axis=0)
        else:
            raise InvalidOptionError("map_type", self.map_type, details=f" valid values are "
                                     f"{constants.DM_MAP_AVERAGE} and {constants.DM_MAP_MAX}.")
        if self.weight_power != 1.0:
            weights = np.power(weights, self.weight_power)
            sum_weights = np.sum(weights, axis=0)
            weights = np.divide(weights, sum_weights, where=sum_weights != 0)
        return weights

    def focus_stack(self):
        n_images = len(self.filenames)
        self.process.callback(constants.CALLBACKS_SET_TOTAL_ACTIONS,
                              self.process.output_path, self.output_filename,
                              self.steps_per_frame)
        gray_images = np.empty((n_images, *self.shape), dtype=self.float_type)
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": preprocessing {self.image_str(i)}")
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, img_path, 200)
            img = read_and_validate_img(img_path, self.shape, self.dtype)
            gray = img_bw(img)
            gray_images[i] = gray.astype(self.float_type)
            self.after_step(i)
            self.check_running()
        self.steps_count = 1
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.name, self.output_filename,
                              self.steps_count)
        energy_str = {
            constants.DM_ENERGY_VARIANCE: "variance",
            constants.DM_ENERGY_TENENGRAD: "tenengrad",
            constants.DM_ENERGY_LAPLACIAN: "laplacian",
            constants.DM_ENERGY_MOD_LAPLACIAN: "modified laplacian",
            constants.DM_ENERGY_SOBEL: "sobel"
        }[self.energy]
        self.print_message(f": computing energy map, method: {energy_str}")
        if self.energy == constants.DM_ENERGY_SOBEL:
            energies = self.get_sobel_map(gray_images)
        elif self.energy == constants.DM_ENERGY_LAPLACIAN:
            energies = self.get_laplacian_map(gray_images)
        elif self.energy == constants.DM_ENERGY_MOD_LAPLACIAN:
            energies = self.get_modified_laplacian(gray_images)
        elif self.energy == constants.DM_ENERGY_VARIANCE:
            energies = self.get_variance_map(gray_images)
        elif self.energy == constants.DM_ENERGY_TENENGRAD:
            energies = self.get_tenengrad(gray_images)
        else:
            raise InvalidOptionError(
                'energy', self.energy, details=f" valid values are "
                f"{constants.DM_ENERGY_SOBEL} and {constants.DM_ENERGY_LAPLACIAN}."
            )
        self.steps_count += 1
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.name, self.output_filename,
                              self.steps_count)
        self.print_message(": normalize energy maps")
        global_max = np.max(energies)
        if global_max > 0:
            energies = energies / global_max
        if self.energy_smooth_size > 0:
            energies = self.smooth_energy(energies)
            self.steps_count += 1
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.name, self.output_filename,
                                  self.steps_count)
        mode_str = {
            constants.DM_MODE_BEST: 'best frame',
            constants.DM_MODE_WEIGHTED: 'weighted frames'
        }[self.blend_mode]
        self.print_message(f": blending images, mode: {mode_str}")
        if self.blend_mode == constants.DM_MODE_WEIGHTED:
            weights = self.get_focus_map(energies)
            result = self._weighted_pyramid_blend(weights, n_images)
        elif self.blend_mode == constants.DM_MODE_BEST:
            result = self._best_pixel_selection(energies, n_images)
        else:
            raise InvalidOptionError(
                "blend_mode", self.blend_mode,
                details=f"Valid values are {constants.DM_MODE_WEIGHTED} "
                        "and {constants.DM_MODE_BEST}")
        self.steps_count += 1
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.name, self.output_filename,
                              self.steps_count)
        return result

    def _best_pixel_selection(self, energies, n_images):
        best_indices = np.argmax(energies, axis=0)
        color_images = []
        n_steps = 2 if self.energy_smooth_size <= 0 else 3
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": reading image {self.image_str(i)}")
            img = read_img(img_path).astype(self.float_type)
            color_images.append(img)
            self.after_step(i + n_images * n_steps)
            self.check_running()
        result = np.zeros_like(color_images[0])
        n_steps += 1
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": blending {self.image_str(i)}")
            filename = os.path.basename(img_path)
            mask = best_indices == i
            result[mask] = color_images[i][mask]
            self.after_step(i + n_images * n_steps)
            self.check_running()
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, filename, 201)
            self.check_running()
        return np.clip(np.absolute(result), 0, self.num_pixel_values).astype(self.dtype)

    def _weighted_pyramid_blend(self, weights, n_images):
        n_steps = 2 if self.energy_smooth_size <= 0 else 3
        if self.weights_smooth_size > 0:
            for i in range(weights.shape[0]):
                self.print_message(f": filter weights, {self.image_str(i)}")
                weights[i] = cv2.bilateralFilter(
                    weights[i].astype(np.float32),
                    d=self.weights_smooth_size,
                    sigmaColor=self.weights_sigma_color,
                    sigmaSpace=self.weights_sigma_space).astype(weights.dtype)
                self.after_step(i + n_images * n_steps)
                self.check_running()
            n_steps += 1
            self.steps_count += 1
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.name, self.output_filename,
                                  self.steps_count)
        sum_weights = np.sum(weights, axis=0)
        weights = np.divide(weights, sum_weights, where=sum_weights != 0)
        result = np.zeros((self.shape[0], self.shape[1], 3), dtype=self.float_type)
        total_weight = np.zeros((self.shape[0], self.shape[1]), dtype=self.float_type)
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": blending {self.image_str(i)}")
            filename = os.path.basename(img_path)
            img = read_img(img_path).astype(self.float_type)
            weight = weights[i]
            result += img * weight[:, :, np.newaxis]
            total_weight += weight
            self.after_step(i + n_images * n_steps)
            self.check_running()
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, filename, 201)
            self.check_running()
        total_weight_3d = np.maximum(total_weight[:, :, np.newaxis], 1e-8)
        result = result / total_weight_3d
        return np.clip(result, 0, self.num_pixel_values).astype(self.dtype)
