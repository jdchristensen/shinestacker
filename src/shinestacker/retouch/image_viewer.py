# pylint: disable=C0114, C0115, C0116, E0611, R0904, R0902, R0914, R0912
from .image_view_status import ImageViewStatus
from .overlaid_view import OverlaidView


class ImageViewer:
    def __init__(self, layer_collection, parent=None):
        self.status = ImageViewStatus()
        self.strategy = OverlaidView(layer_collection, self.status, parent)
        self._strategies = [self.strategy]

    def empty(self):
        return self.strategy.empty()

    def set_master_image_np(self, img):
        self.strategy.set_master_image_np(img)

    def clear_image(self):
        self.strategy.clear_image()

    def show_master(self):
        self.strategy.show_master()

    def show_current(self):
        self.strategy.show_current()

    def update_master_display(self):
        self.strategy.update_master_display()

    def update_current_display(self):
        self.strategy.update_current_display()

    def update_brush_cursor(self):
        self.strategy.update_brush_cursor()

    def refresh_display(self):
        self.strategy.refresh_display()

    def set_brush(self, brush):
        for s in self._strategies:
            s.set_brush(brush)

    def set_preview_brush(self, brush):
        for s in self._strategies:
            s.set_preview_brush(brush)

    def set_display_manager(self, dm):
        for s in self._strategies:
            s.set_display_manager(dm)

    def set_allow_cursor_preview(self, state):
        self.strategy.set_allow_cursor_preview(state)

    def setup_brush_cursor(self):
        self.strategy.setup_brush_cursor()

    def zoom_in(self):
        self.strategy.zoom_in()

    def zoom_out(self):
        self.strategy.zoom_out()

    def reset_zoom(self):
        self.strategy.reset_zoom()

    def actual_size(self):
        self.strategy.actual_size()

    def get_current_scale(self):
        return self.strategy.get_current_scale()

    def get_cursor_style(self):
        return self.strategy.get_cursor_style()

    def set_cursor_style(self, style):
        self.strategy.set_cursor_style(style)

    def position_on_image(self, pos):
        return self.strategy.position_on_image(pos)

    def get_visible_image_portion(self):
        return self.strategy.get_visible_image_portion()
