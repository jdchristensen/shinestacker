# pylint: disable=C0114, C0115, C0116, E0611, W0221, R0913, R0917, R0902, R0914
import math
from .base_filter import BaseFilter
from .. algorithms.corrections import gamma_correction, contrast_correction


class GammaSCurveFilter(BaseFilter):
    def __init__(self, name, parent, image_viewer, layer_collection, undo_manager):
        super().__init__(name, parent, image_viewer, layer_collection, undo_manager,
                         preview_at_startup=True)
        self.min_lumi = -1
        self.max_lumi = +1
        self.initial_lumi = 0
        self.min_contrast = -1
        self.max_contrast = 1
        self.initial_contrast = 0
        self.lumi_slider = None
        self.contrast_slider = None

    def setup_ui(self, dlg, layout, do_preview, restore_original, **kwargs):
        dlg.setWindowTitle("Unsharp Mask")
        dlg.setMinimumWidth(600)
        params = {
            "Luminosity": (self.min_lumi, self.max_lumi, self.initial_lumi, "{:.1%}"),
            "Contrast": (self.min_contrast, self.max_contrast, self.initial_contrast, "{:.1%}"),
        }

        def set_slider(name, slider):
            if name == "Luminosity":
                self.lumi_slider = slider
            elif name == "Contrast":
                self.contrast_slider = slider

        value_labels = self.create_sliders(params, dlg, layout, set_slider)

        def update_value(name, slider_value, min_val, max_val, fmt):
            value = self.value_from_slider(slider_value, min_val, max_val)
            value_labels[name].setText(fmt.format(value))
            if self.preview_check.isChecked():
                self.preview_timer.start()

        self.lumi_slider.valueChanged.connect(
            lambda v: update_value(
                "Luminosity", v, self.min_lumi, self.max_lumi, params["Luminosity"][3]))
        self.contrast_slider.valueChanged.connect(
            lambda v: update_value(
                "Contrast", v, self.min_contrast, self.max_contrast, params["Contrast"][3]))
        self.set_timer(do_preview, restore_original, dlg)

    def get_params(self):
        return (
            self.value_from_slider(
                self.lumi_slider.value(), self.min_lumi, self.max_lumi),
            self.value_from_slider(
                self.contrast_slider.value(), self.min_contrast, self.max_contrast)
        )

    def apply(self, image, lumi, contrast):
        img_corr = contrast_correction(image, 0.5 * contrast)
        img_corr = gamma_correction(img_corr, math.exp(0.5 * lumi))
        return img_corr


class LumiContrastFilter(GammaSCurveFilter):
    pass