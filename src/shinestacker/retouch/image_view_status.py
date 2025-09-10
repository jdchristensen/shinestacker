# image_view_status.py
from PySide6.QtCore import QObject, QRectF
from PySide6.QtGui import QPixmap


class ImageViewStatus(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.zoom_factor = 1.0
        self.min_scale = 0.0
        self.max_scale = 0.0
        self.h_scroll = 0
        self.v_scroll = 0
        self.empty = True
        self.scene_rect = QRectF()

    def set_image(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        self.pixmap = pixmap
        self.empty = pixmap.isNull()
        self.scene_rect = QRectF(pixmap.rect())

    def clear(self):
        self.pixmap = QPixmap()
        self.empty = True
        self.zoom_factor = 1.0
        self.min_scale = 0.0
        self.max_scale = 0.0
        self.h_scroll = 0
        self.v_scroll = 0
        self.scene_rect = QRectF()

    def get_state(self):
        return {
            'zoom': self.zoom_factor,
            'h_scroll': self.h_scroll,
            'v_scroll': self.v_scroll
        }

    def set_state(self, state):
        if state:
            self.zoom_factor = state['zoom']
            self.h_scroll = state['h_scroll']
            self.v_scroll = state['v_scroll']

    def set_zoom_factor(self, zoom_factor):
        self.zoom_factor = zoom_factor

    def set_min_scale(self, min_scale):
        self.min_scale = min_scale

    def set_max_scale(self, min_scale):
        self.max_scale = min_scale
