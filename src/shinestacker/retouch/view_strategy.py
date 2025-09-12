# pylint: disable=C0114, C0115, C0116, E0611
from abc import abstractmethod
import numpy as np
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Signal, QPoint
from PySide6.QtGui import QImage
from .. config.gui_constants import gui_constants
from .layer_collection import LayerCollectionHandler


class ViewStrategy(QGraphicsView, LayerCollectionHandler):
    temp_view_requested = Signal(bool)
    brush_operation_started = Signal(QPoint)
    brush_operation_continued = Signal(QPoint)
    brush_operation_ended = Signal()
    brush_size_change_requested = Signal(int)  # +1 or -1

    def __init__(self, layer_collection, status, parent=None):
        QGraphicsView.__init__(self, parent)
        LayerCollectionHandler.__init__(self, layer_collection)
        self.status = status
        self.brush = None
        self.brush_cursor = None
        self.display_manager = None
        self.cursor_style = gui_constants.DEFAULT_CURSOR_STYLE

    @abstractmethod
    def set_master_image(self, qimage):
        pass

    @abstractmethod
    def set_current_image(self, qimage):
        pass

    @abstractmethod
    def clear_image(self):
        pass

    @abstractmethod
    def show_master(self):
        pass

    @abstractmethod
    def show_current(self):
        pass

    @abstractmethod
    def update_master_display(self):
        pass

    @abstractmethod
    def update_current_display(self):
        pass

    @abstractmethod
    def update_brush_cursor(self):
        pass

    @abstractmethod
    def refresh_display(self):
        pass

    @abstractmethod
    def set_allow_cursor_preview(self, state):
        pass

    @abstractmethod
    def setup_brush_cursor(self):
        pass

    @abstractmethod
    def zoom_in(self):
        pass

    @abstractmethod
    def zoom_out(self):
        pass

    @abstractmethod
    def reset_zoom(self):
        pass

    @abstractmethod
    def actual_size(self):
        pass

    @abstractmethod
    def get_current_scale(self):
        pass

    @abstractmethod
    def position_on_image(self, pos):
        pass

    @abstractmethod
    def get_visible_image_region(self):
        pass

    def zoom_factor(self):
        return self.status.zoom_factor

    def set_zoom_factor(self, zoom_factor):
        self.status.set_zoom_factor(zoom_factor)

    def min_scale(self):
        return self.status.min_scale

    def max_scale(self):
        return self.status.max_scale

    def set_min_scale(self, scale):
        self.status.set_min_scale(scale)

    def set_max_scale(self, scale):
        self.status.set_max_scale(scale)

    def empty(self):
        return self.status.empty()

    def set_brush(self, brush):
        self.brush = brush

    def set_preview_brush(self, brush):
        self.brush_preview.brush = brush

    def set_display_manager(self, dm):
        self.display_manager = dm

    def set_cursor_style(self, style):
        self.cursor_style = style
        if self.brush_cursor:
            self.update_brush_cursor()

    def get_cursor_style(self):
        return self.cursor_style

    def set_master_image_np(self, img):
        self.set_master_image(self.numpy_to_qimage(img))

    def numpy_to_qimage(self, array):
        if array.dtype == np.uint16:
            array = np.right_shift(array, 8).astype(np.uint8)
        if array.ndim == 2:
            height, width = array.shape
            return QImage(memoryview(array), width, height, width, QImage.Format_Grayscale8)
        if array.ndim == 3:
            height, width, _ = array.shape
            if not array.flags['C_CONTIGUOUS']:
                array = np.ascontiguousarray(array)
            return QImage(memoryview(array), width, height, 3 * width, QImage.Format_RGB888)
        return QImage()
