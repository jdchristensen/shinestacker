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
    def __init__(self, **kwargs):
        default_params = DEFAULTS['depth_map_params']
        self.steps_per_frame = 3
        self.energy_smooth_size = kwargs.get(
            'energy_smooth_size', default_params['energy_smooth_size'])
        if self.energy_smooth_size > 0:
            self.steps_per_frame += 1
        self.pyramid_smooth_size = kwargs.get(
            'pyramid_smooth_size', default_params['pyramid_smooth_size'])
        if self.pyramid_smooth_size > 0:
            self.steps_per_frame += 1
        float_type = kwargs.get('float_type', default_params['float_type'])
        super().__init__("depth map", self.steps_per_frame, float_type)
        self.map_type = kwargs.get('map_type', default_params['map_type'])
        self.pyramid_levels = kwargs.get('pyramid_levels', default_params['pyramid_levels'])
        self.energy = kwargs.get('energy', default_params['energy'])
        self.weight_power = kwargs.get('weight_power', default_params['weight_power'])
        self.kernel_size = kwargs.get('kernel_size', default_params['kernel_size'])
        self.blur_size = kwargs.get('blur_size', default_params['blur_size'])
        self.energy_sigma_color = kwargs.get(
            'energy_sigma_color', default_params['energy_sigma_color'])
        self.energy_sigma_space = kwargs.get(
            'energy_sigma_space', default_params['energy_sigma_space'])
        self.temperature = kwargs.get('temperature', default_params['temperature'])
        self.steps_count = 0

    def get_sobel_map(self, gray_img):
        sobel_energy = np.abs(cv2.Sobel(gray_img, cv2.CV_64F, 1, 0, ksize=3)) + \
            np.abs(cv2.Sobel(gray_img, cv2.CV_64F, 0, 1, ksize=3))
        return sobel_energy.astype(self.float_type)

    def get_laplacian_map(self, gray_img):
        blurred = cv2.GaussianBlur(gray_img, (self.blur_size, self.blur_size), 0)
        lap_result = cv2.Laplacian(
            blurred, cv2.CV_32F if self.float_type == np.float32 else cv2.CV_64F,
            ksize=self.kernel_size)
        return np.abs(lap_result)

    def get_modified_laplacian(self, gray_img):
        dx = cv2.Sobel(gray_img, cv2.CV_64F, 1, 0, ksize=3)
        dy = cv2.Sobel(gray_img, cv2.CV_64F, 0, 1, ksize=3)
        mod_laplacian = np.abs(dx) + np.abs(dy)
        return mod_laplacian.astype(self.float_type)

    def get_variance_map(self, gray_img, window_size=5):
        mean = cv2.boxFilter(gray_img, -1, (window_size, window_size))
        mean_sq = cv2.boxFilter(gray_img**2, -1, (window_size, window_size))
        return mean_sq - mean**2

    def get_tenengrad(self, gray_img, threshold=5):
        gx = cv2.Sobel(gray_img, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray_img, cv2.CV_64F, 0, 1, ksize=3)
        tenengrad = gx * gx + gy * gy
        return np.where(tenengrad > threshold, tenengrad, 0)

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
            self.after_step(i + n_images)
            self.check_running()
        return smoothed

    def get_focus_map(self, energies):
        if self.map_type == constants.DM_MAP_AVERAGE:
            sum_energies = np.sum(energies, axis=0)
            sum_energies = np.where(sum_energies == 0, np.finfo(energies.dtype).eps, sum_energies)
            weights = np.divide(energies, sum_energies)
        elif self.map_type == constants.DM_MAP_MAX:
            max_energy = np.max(energies, axis=0)
            temperature_safe = max(self.temperature, np.finfo(energies.dtype).eps)
            relative = np.exp((energies - max_energy) / temperature_safe)
            sum_relative = np.sum(relative, axis=0)
            sum_relative = np.where(sum_relative == 0, np.finfo(energies.dtype).eps, sum_relative)
            weights = relative / sum_relative
        else:
            raise InvalidOptionError("map_type", self.map_type, details=f" valid values are "
                                     f"{constants.DM_MAP_AVERAGE} and {constants.DM_MAP_MAX}.")
        if self.weight_power != 1.0:
            weights = np.power(weights, self.weight_power)
            sum_weights = np.sum(weights, axis=0)
            sum_weights = np.where(sum_weights == 0, np.finfo(weights.dtype).eps, sum_weights)
            weights = np.divide(weights, sum_weights)
        return weights

    def focus_stack(self):
        n_images = len(self.filenames)
        self.process.callback(constants.CALLBACKS_SET_TOTAL_ACTIONS,
                              self.process.output_path, self.output_filename,
                              self.steps_per_frame)
        energies = np.empty((n_images, *self.shape), dtype=self.float_type)
        energy_str = {
            constants.DM_ENERGY_VARIANCE: "variance",
            constants.DM_ENERGY_TENENGRAD: "tenengrad",
            constants.DM_ENERGY_LAPLACIAN: "laplacian",
            constants.DM_ENERGY_MOD_LAPLACIAN: "modified laplacian",
            constants.DM_ENERGY_SOBEL: "sobel"
        }.get(self.energy, '')
        self.print_message(f": computing energy maps, method: {energy_str}")
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": computing energy for {self.image_str(i)}")
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, img_path, 200)
            img = read_and_validate_img(img_path, self.shape, self.dtype)
            gray = img_bw(img).astype(self.float_type)
            if self.energy == constants.DM_ENERGY_SOBEL:
                energy_map = self.get_sobel_map(gray)
            elif self.energy == constants.DM_ENERGY_LAPLACIAN:
                energy_map = self.get_laplacian_map(gray)
            elif self.energy == constants.DM_ENERGY_MOD_LAPLACIAN:
                energy_map = self.get_modified_laplacian(gray)
            elif self.energy == constants.DM_ENERGY_VARIANCE:
                energy_map = self.get_variance_map(gray)
            elif self.energy == constants.DM_ENERGY_TENENGRAD:
                energy_map = self.get_tenengrad(gray)
            else:
                raise InvalidOptionError(
                    'energy', self.energy, details=f" valid values are "
                    f"{constants.DM_ENERGY_SOBEL} and {constants.DM_ENERGY_LAPLACIAN}."
                )
            energies[i] = energy_map
            self.after_step(i)
            self.check_running()
        self.steps_count = 1
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
        self.print_message(": blending images")
        weights = self.get_focus_map(energies)
        result = self._weighted_pyramid_blend(weights, n_images)
        self.steps_count += 1
        self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                              self.process.name, self.output_filename,
                              self.steps_count)
        return result

    def _weighted_pyramid_blend(self, weights, n_images):
        n_steps = 2 if self.energy_smooth_size <= 0 else 3
        if self.pyramid_smooth_size > 0:
            for i in range(weights.shape[0]):
                self.print_message(f": smooth weights for pyramid, {self.image_str(i)}")
                ksize = self.pyramid_smooth_size
                if ksize % 2 == 0:
                    ksize += 1
                weights[i] = cv2.GaussianBlur(weights[i], (ksize, ksize), 0)
                self.after_step(i + n_images * n_steps)
                self.check_running()
            n_steps += 1
            self.steps_count += 1
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.name, self.output_filename,
                                  self.steps_count)
        sum_weights = np.sum(weights, axis=0)
        weights = np.divide(weights, sum_weights, where=sum_weights != 0)
        blended_pyramid = None
        weight_pyramid_accum = None
        for i, img_path in enumerate(self.filenames):
            self.print_message(f": pyramid blending {self.image_str(i)}")
            filename = os.path.basename(img_path)
            img = read_img(img_path)
            if img.dtype == np.uint8:
                img_float = img.astype(self.float_type) / 255.0
            elif img.dtype == np.uint16:
                img_float = img.astype(self.float_type) / 65535.0
            else:
                img_float = img.astype(self.float_type)
                if img_float.max() > 1.0:
                    img_float = img_float / self.num_pixel_values
            weight = weights[i]
            gp_img = [img_float]  # Use normalized float image
            gp_weight = [weight]
            for level in range(self.pyramid_levels - 1):
                gp_img.append(cv2.pyrDown(gp_img[-1]))
                gp_weight.append(cv2.pyrDown(gp_weight[-1]))
            lp_img = [gp_img[-1]]
            for level in range(self.pyramid_levels - 1, 0, -1):
                size = (gp_img[level - 1].shape[1], gp_img[level - 1].shape[0])
                expanded = cv2.pyrUp(gp_img[level], dstsize=size)
                laplacian = gp_img[level - 1] - expanded
                lp_img.append(laplacian)
            current_blend = []
            current_weights = []
            for level in range(self.pyramid_levels):
                weighted_level = lp_img[level] * \
                    gp_weight[self.pyramid_levels - 1 - level][..., np.newaxis]
                current_blend.append(weighted_level)
                current_weights.append(gp_weight[self.pyramid_levels - 1 - level])
            if blended_pyramid is None:
                blended_pyramid = current_blend
                weight_pyramid_accum = current_weights
            else:
                blended_pyramid = [bp + cb for bp, cb in zip(blended_pyramid, current_blend)]
                weight_pyramid_accum = [wp + cw for wp, cw
                                        in zip(weight_pyramid_accum, current_weights)]
            self.after_step(i + n_images * n_steps)
            self.check_running()
            self.process.callback(constants.CALLBACK_UPDATE_FRAME_STATUS,
                                  self.process.input_path, filename, 201)
            self.check_running()
        for level in range(self.pyramid_levels):
            mask = weight_pyramid_accum[level] > 1e-8
            if np.any(mask):
                if len(blended_pyramid[level].shape) == 3:
                    weight_expanded = weight_pyramid_accum[level][:, :, np.newaxis]
                else:
                    weight_expanded = weight_pyramid_accum[level]
                blended_pyramid[level][mask] = blended_pyramid[level][mask] / weight_expanded[mask]
        self.print_message(': reconstructing pyramid')
        result = blended_pyramid[0]
        for level in range(1, self.pyramid_levels):
            size = (blended_pyramid[level].shape[1], blended_pyramid[level].shape[0])
            result = cv2.pyrUp(result, dstsize=size) + blended_pyramid[level]
        if self.dtype == np.uint8:
            result = np.clip(result * 255.0, 0, 255).astype(np.uint8)
        elif self.dtype == np.uint16:
            result = np.clip(result * 65535.0, 0, 65535).astype(np.uint16)
        else:
            result = np.clip(result, 0, 1.0).astype(self.dtype)
        return result
