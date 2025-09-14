# pylint: disable=C0114, C0115, C0116, E0611, R0904
from abc import abstractmethod
import numpy as np
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QImage, QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from .. config.gui_constants import gui_constants
from .layer_collection import LayerCollectionHandler
from .brush_gradient import create_default_brush_gradient
from .brush_preview import BrushPreviewItem


class ImageGraphicsViewBase(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setInteractive(False)
        self.grabGesture(Qt.PinchGesture)
        self.grabGesture(Qt.PanGesture)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)


class ViewStrategy(LayerCollectionHandler):
    def __init__(self, layer_collection, status):
        LayerCollectionHandler.__init__(self, layer_collection)
        self.display_manager = None
        self.status = status
        self.brush = None
        self.brush_cursor = None
        self.display_manager = None
        self.brush_preview = BrushPreviewItem(layer_collection)
        self.cursor_style = gui_constants.DEFAULT_CURSOR_STYLE
        self.allow_cursor_preview = True

    @abstractmethod
    def create_pixmaps(self):
        pass

    @abstractmethod
    def set_master_image(self, qimage):
        pass

    @abstractmethod
    def set_current_image(self, qimage):
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
    def setup_brush_cursor(self):
        pass

    @abstractmethod
    def get_master_view(self):
        pass

    @abstractmethod
    def get_master_scene(self):
        pass

    @abstractmethod
    def get_views(self):
        pass

    @abstractmethod
    def get_scenes(self):
        pass

    @abstractmethod
    def get_pixmaps(self):
        pass

    @abstractmethod
    def get_master_pixmap(self):
        pass

    def show_master(self):
        pass

    def show_current(self):
        pass

    def set_allow_cursor_preview(self, state):
        self.allow_cursor_preview = state

    def zoom_factor(self):
        return self.status.zoom_factor

    def set_zoom_factor(self, zoom_factor):
        self.status.set_zoom_factor(zoom_factor)

    def get_current_scale(self):
        return self.get_master_view().transform().m11()

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

    def handle_key_press_event(self, event):
        return

    def handle_key_release_event(self, event):
        return

    def clear_image(self):
        for scene in self.get_scenes():
            scene.clear()
        self.create_pixmaps()
        self.status.clear()
        self.setup_brush_cursor()
        self.brush_preview = BrushPreviewItem(self.layer_collection)
        self.get_master_scene().addItem(self.brush_preview)
        self.setCursor(Qt.ArrowCursor)
        if self.brush_cursor:
            self.brush_cursor.hide()

    def set_master_image_np(self, img):
        self.set_master_image(self.numpy_to_qimage(img))

    def numpy_to_qimage(self, array):
        if array is None:
            return None
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

    def create_scene(self, view):
        scene = QGraphicsScene()
        view.setScene(scene)
        scene.setBackgroundBrush(QBrush(QColor(120, 120, 120)))
        return scene

    def create_pixmap(self, scene):
        pixmap_item = QGraphicsPixmapItem()
        scene.addItem(pixmap_item)
        return pixmap_item

    def refresh_display(self):
        self.update_brush_cursor()
        for scene in self.get_scenes():
            scene.update()

    def zoom_in(self):
        if self.empty():
            return
        current_scale = self.get_current_scale()
        new_scale = current_scale * gui_constants.ZOOM_IN_FACTOR
        if new_scale <= self.max_scale():
            for view in self.get_views():
                view.scale(gui_constants.ZOOM_IN_FACTOR, gui_constants.ZOOM_IN_FACTOR)
            self.set_zoom_factor(new_scale)
            self.update_brush_cursor()

    def zoom_out(self):
        if self.empty():
            return
        current_scale = self.get_current_scale()
        new_scale = current_scale * gui_constants.ZOOM_OUT_FACTOR
        if new_scale >= self.min_scale():
            for view in self.get_views():
                view.scale(gui_constants.ZOOM_OUT_FACTOR, gui_constants.ZOOM_OUT_FACTOR)
            self.set_zoom_factor(new_scale)
            self.update_brush_cursor()

    def reset_zoom(self):
        if self.empty():
            return
        self.pinch_start_scale = 1.0
        self.last_scroll_pos = QPointF()
        self.gesture_active = False
        self.pinch_center_view = None
        self.pinch_center_scene = None
        for pixmap, view in self.get_pixmaps().items():
            view.fitInView(pixmap, Qt.KeepAspectRatio)
        self.set_zoom_factor(self.get_current_scale())
        self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), self.zoom_factor())))
        for view in self.get_views():
            view.resetTransform()
            view.scale(self.zoom_factor(), self.zoom_factor())
        self.update_brush_cursor()

    def actual_size(self):
        if self.empty():
            return
        self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), 1.0)))
        for view in self.get_views():
            view.resetTransform()
            view.scale(self.zoom_factor(), self.zoom_factor())
        self.update_brush_cursor()

    def setup_outline_style(self):
        self.brush_cursor.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                                      gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()))
        self.brush_cursor.setBrush(Qt.NoBrush)

    def setup_simple_brush_style(self, center_x, center_y, radius):
        gradient = create_default_brush_gradient(center_x, center_y, radius, self.brush)
        self.brush_cursor.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                                      gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()))
        self.brush_cursor.setBrush(QBrush(gradient))

    def position_on_image(self, pos):
        view = self.get_master_view()
        pixmap = self.get_master_pixmap()
        scene_pos = view.mapToScene(pos)
        item_pos = pixmap.mapFromScene(scene_pos)
        return item_pos

    def get_visible_image_region(self):
        if self.empty():
            return None
        view = self.get_master_view()
        pixmap = self.get_master_pixmap()
        view_rect = view.viewport().rect()
        scene_rect = view.mapToScene(view_rect).boundingRect()
        image_rect = view.mapFromScene(scene_rect).boundingRect()
        image_rect = image_rect.intersected(pixmap.boundingRect().toRect())
        return image_rect

    def get_visible_image_portion(self):
        if self.has_no_master_layer():
            return None
        visible_rect = self.get_visible_image_region()
        if not visible_rect:
            return self.master_layer()
        x, y = int(visible_rect.x()), int(visible_rect.y())
        w, h = int(visible_rect.width()), int(visible_rect.height())
        master_img = self.master_layer()
        return master_img[y:y + h, x:x + w], (x, y, w, h)

    def map_to_scene(self, pos):
        return self.get_master_view().mapToScene(pos)

    # pylint: disable=C0103
    def keyPressEvent(self, event):
        if self.empty():
            return
        if event.key() == Qt.Key_Space and not self.scrolling:
            self.space_pressed = True
            self.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        self.handle_key_press_event(event)
        if event.key() == Qt.Key_Control and not self.scrolling:
            self.control_pressed = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.empty():
            return
        self.update_brush_cursor()
        if event.key() == Qt.Key_Space:
            self.space_pressed = False
            if not self.scrolling:
                self.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
        self.handle_key_release_event(event)
        if event.key() == Qt.Key_Control:
            self.control_pressed = False
        super().keyReleaseEvent(event)
    # pylint: enable=C0103
