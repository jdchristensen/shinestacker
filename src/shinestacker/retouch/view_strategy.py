# pylint: disable=C0114, C0115, C0116, E0611, R0904, R0903, R0902, E1101, R0914, R0913, R0917
import math
from abc import abstractmethod
import numpy as np
from PySide6.QtCore import Qt, QPointF, QTime, QPoint, Signal, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QBrush, QPen, QCursor, QPixmap, QPainterPath
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsItemGroup, QGraphicsPathItem)
from .. config.gui_constants import gui_constants
from .layer_collection import LayerCollectionHandler
from .brush_gradient import create_default_brush_gradient
from .brush_preview import BrushPreviewItem


class BrushCursor(QGraphicsItemGroup):
    def __init__(self, x0, y0, size, pen, brush):
        super().__init__()
        self._pen = pen
        self._radius = size / 2
        self._brush = brush
        self._rect = QRectF(x0 - self._radius, y0 - self._radius, size, size)
        self._arc_items = []
        self._create_arcs()

    def _point_on_circle(self, phi_deg):
        phi = phi_deg / 180.0 * math.pi
        x0 = self._rect.x() + self._radius
        y0 = self._rect.y() + self._radius
        return x0 + self._radius * math.cos(phi), y0 - self._radius * math.sin(phi)

    def _create_arcs(self):
        for item in self._arc_items:
            self.removeFromGroup(item)
            if item.scene():
                item.scene().removeItem(item)
        self._arc_items = []
        half_gap = 20
        arcs = [half_gap, 90 + half_gap, 180 + half_gap, 270 + half_gap]
        span_angle = 90 - 2 * half_gap
        for start_angle in arcs:
            path = QPainterPath()
            path.moveTo(*self._point_on_circle(start_angle))
            path.arcTo(self._rect, start_angle, span_angle)
            arc_item = QGraphicsPathItem(path)
            arc_item.setPen(self._pen)
            arc_item.setBrush(Qt.NoBrush)
            self.addToGroup(arc_item)
            self._arc_items.append(arc_item)

    # pylint: disable=C0103
    def setPen(self, pen):
        self._pen = pen
        for item in self._arc_items:
            item.setPen(pen)

    def pen(self):
        return self._pen

    def setBrush(self, brush):
        self._brush = brush
        for item in self._arc_items:
            item.setBrush(Qt.NoBrush)

    def brush(self):
        return self._brush

    def setRect(self, x, y, w, h):
        self._rect = QRectF(x, y, w, h)
        self._create_arcs()

    def rect(self):
        return self._rect
    # pylint: enable=C0103


class ViewSignals:
    temp_view_requested = Signal(bool)
    brush_operation_started = Signal(QPoint)
    brush_operation_continued = Signal(QPoint)
    brush_operation_ended = Signal()
    brush_size_change_requested = Signal(int)  # +1 or -1


class ImageGraphicsViewBase(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setInteractive(False)
        self.grabGesture(Qt.PinchGesture)
        self.grabGesture(Qt.PanGesture)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setCursor(Qt.BlankCursor)


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
        self.control_pressed = False
        self.space_pressed = False
        self.gesture_active = False
        self.pinch_center_view = None
        self.pinch_center_scene = None
        self.pinch_start_scale = None
        self.scrolling = False
        self.dragging = False
        self.last_brush_pos = None
        self.last_mouse_pos = None
        self.last_update_time = QTime.currentTime()

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
    def get_master_view(self):
        pass

    @abstractmethod
    def get_current_view(self):
        pass

    @abstractmethod
    def get_master_scene(self):
        pass

    @abstractmethod
    def get_current_scene(self):
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

    @abstractmethod
    def get_current_pixmap(self):
        pass

    @abstractmethod
    def show_master(self):
        pass

    @abstractmethod
    def show_current(self):
        pass

    @abstractmethod
    def arrange_images(self):
        pass

    def update_master_display(self):
        if not self.empty():
            master_qimage = self.numpy_to_qimage(self.master_layer())
            if master_qimage:
                pixmap = QPixmap.fromImage(master_qimage)
                self.get_master_pixmap().setPixmap(pixmap)
                self.get_master_scene().setSceneRect(QRectF(pixmap.rect()))
                self.get_master_view().horizontalScrollBar().setValue(self.status.h_scroll)
                self.get_master_view().verticalScrollBar().setValue(self.status.v_scroll)
                self.arrange_images()

    def update_current_display(self):
        if not self.empty() and self.number_of_layers() > 0:
            current_qimage = self.numpy_to_qimage(self.current_layer())
            if current_qimage:
                pixmap = QPixmap.fromImage(current_qimage)
                self.get_current_pixmap().setPixmap(pixmap)
                self.get_current_scene().setSceneRect(QRectF(pixmap.rect()))
                self.get_current_view().horizontalScrollBar().setValue(self.status.h_scroll)
                self.get_current_view().verticalScrollBar().setValue(self.status.v_scroll)
                self.arrange_images()

    def update_cursor_pen_width(self):
        width = gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()
        if self.brush_cursor is not None:
            pen = self.brush_cursor.pen()
            pen.setWidthF(width)
            self.brush_cursor.setPen(pen)
        return width

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

    def handle_key_press_event(self, _event):
        return True

    def handle_key_release_event(self, _event):
        return True

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

    def cleanup_brush_preview(self):
        if self.brush_cursor:
            self.brush_cursor.hide()
        self.brush_preview.hide()

    def set_master_image_np(self, img):
        self.set_master_image(self.numpy_to_qimage(img))
        if self.brush_cursor is None:
            self.setup_brush_cursor()
        self.show_master()

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
        for scene in self.get_scenes():
            scene.update()
        self.update_brush_cursor()

    def set_max_min_scales(self, img_width, img_height):
        self.set_min_scale(min(gui_constants.MIN_ZOOMED_IMG_WIDTH / img_width,
                               gui_constants.MIN_ZOOMED_IMG_HEIGHT / img_height))
        self.set_max_scale(gui_constants.MAX_ZOOMED_IMG_PX_SIZE)

    def zoom_in(self):
        if self.empty():
            return
        master_view = self.get_master_view()
        old_center = master_view.mapToScene(master_view.viewport().rect().center())
        current_scale = self.get_current_scale()
        new_scale = current_scale * gui_constants.ZOOM_IN_FACTOR
        if new_scale <= self.max_scale():
            for view in self.get_views():
                view.scale(gui_constants.ZOOM_IN_FACTOR, gui_constants.ZOOM_IN_FACTOR)
            self.set_zoom_factor(new_scale)
            master_view.centerOn(old_center)
            self.update_brush_cursor()
            self.update_cursor_pen_width()

    def apply_zoom(self):
        if self.empty():
            return
        for view in self.get_views():
            current_scale = view.transform().m11()
            scale_factor = self.zoom_factor() / current_scale
            view.scale(scale_factor, scale_factor)

    def zoom_out(self):
        if self.empty():
            return
        master_view = self.get_master_view()
        old_center = master_view.mapToScene(master_view.viewport().rect().center())
        current_scale = self.get_current_scale()
        new_scale = current_scale * gui_constants.ZOOM_OUT_FACTOR
        if new_scale >= self.min_scale():
            for view in self.get_views():
                view.scale(gui_constants.ZOOM_OUT_FACTOR, gui_constants.ZOOM_OUT_FACTOR)
            self.set_zoom_factor(new_scale)
            master_view.centerOn(old_center)
            self.update_brush_cursor()
            self.update_cursor_pen_width()

    def reset_zoom(self):
        if self.empty():
            return
        self.pinch_start_scale = 1.0
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
        self.update_cursor_pen_width()

    def actual_size(self):
        if self.empty():
            return
        self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), 1.0)))
        for view in self.get_views():
            view.resetTransform()
            view.scale(self.zoom_factor(), self.zoom_factor())
        self.update_brush_cursor()
        self.update_cursor_pen_width()

    def setup_simple_brush_style(self, center_x, center_y, radius):
        gradient = create_default_brush_gradient(center_x, center_y, radius, self.brush)
        self.brush_cursor.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                                      gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()))
        self.brush_cursor.setBrush(QBrush(gradient))

    def create_circle(self, scene, line_style=Qt.SolidLine):
        for item in scene.items():
            if isinstance(item, QGraphicsEllipseItem) and item != self.brush_preview:
                scene.removeItem(item)
        pen_width = gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()
        pen = QPen(QColor(*gui_constants.BRUSH_COLORS['pen']), pen_width, line_style)
        brush = Qt.NoBrush
        scene_center = scene.sceneRect().center()
        brush_cursor = scene.addEllipse(
            scene_center.x(), scene_center.y(),
            self.brush.size, self.brush.size, pen, brush)
        brush_cursor.setZValue(1000)
        brush_cursor.hide()
        return brush_cursor

    def create_alt_circle(self, scene, line_style=Qt.SolidLine):
        for item in scene.items():
            if isinstance(item, BrushCursor) and item != self.brush_preview:
                scene.removeItem(item)
        pen_width = gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()
        pen = QPen(QColor(*gui_constants.BRUSH_COLORS['pen']), pen_width, line_style)
        brush = Qt.NoBrush
        scene_center = scene.sceneRect().center()
        brush_cursor = BrushCursor(
            scene_center.x(), scene_center.y(),
            self.brush.size, pen, brush
        )
        brush_cursor.setZValue(1000)
        brush_cursor.hide()
        scene.addItem(brush_cursor)
        return brush_cursor

    def setup_brush_cursor(self):
        if not self.brush:
            return
        self.brush_cursor = self.create_circle(self.get_master_scene())

    def update_brush_cursor(self):
        if self.empty() or self.brush_cursor is None or not self.isVisible():
            return
        self.update_cursor_pen_width()
        master_view = self.get_master_view()
        mouse_pos = master_view.mapFromGlobal(QCursor.pos())
        if not master_view.rect().contains(mouse_pos):
            self.brush_cursor.hide()
            return
        scene_pos = master_view.mapToScene(mouse_pos)
        size = self.brush.size
        radius = size / 2
        self.brush_cursor.setRect(scene_pos.x() - radius, scene_pos.y() - radius, size, size)
        allow_cursor_preview = self.display_manager.allow_cursor_preview()
        if self.cursor_style == 'preview':
            if allow_cursor_preview:
                self.brush_cursor.hide()
                pos = QCursor.pos()
                if isinstance(pos, QPointF):
                    scene_pos = pos
                else:
                    cursor_pos = master_view.mapFromGlobal(pos)
                    scene_pos = master_view.mapToScene(cursor_pos)
                self.brush_preview.update(scene_pos, int(size))
        else:
            self.brush_preview.hide()
            if self.cursor_style != 'outline':
                self.setup_simple_brush_style(scene_pos.x(), scene_pos.y(), radius)
        if not self.brush_cursor.isVisible():
            self.brush_cursor.show()

    def position_on_image(self, pos):
        master_view = self.get_master_view()
        pixmap = self.get_master_pixmap()
        scene_pos = master_view.mapToScene(pos)
        item_pos = pixmap.mapFromScene(scene_pos)
        return item_pos

    def get_visible_image_region(self):
        if self.empty():
            return None
        master_view = self.get_master_view()
        master_pixmap = self.get_master_pixmap()
        pixmap = self.get_master_pixmap()
        view_rect = master_view.viewport().rect()
        scene_rect = master_view.mapToScene(view_rect).boundingRect()
        image_rect = master_pixmap.mapFromScene(scene_rect).boundingRect().toRect()
        return image_rect.intersected(pixmap.boundingRect().toRect())

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
            self.get_master_view().setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        if self.handle_key_press_event(event):
            if event.key() == Qt.Key_Control and not self.scrolling:
                self.control_pressed = True
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.empty():
            return
        if event.key() == Qt.Key_Space:
            self.space_pressed = False
            if not self.scrolling:
                self.get_master_view().setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
        if self.handle_key_release_event(event):
            if event.key() == Qt.Key_Control:
                self.control_pressed = False
            super().keyReleaseEvent(event)

    def leaveEvent(self, event):
        if self.empty():
            self.setCursor(Qt.ArrowCursor)
        else:
            self.get_master_view().setCursor(Qt.ArrowCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        super().leaveEvent(event)
    # pylint: enable=C0103

    def scroll_view(self, view, delta_x, delta_y):
        view.horizontalScrollBar().setValue(
            view.horizontalScrollBar().value() - delta_x)
        view.verticalScrollBar().setValue(
            view.verticalScrollBar().value() - delta_y)
        self.status.set_scroll(view.horizontalScrollBar().value(),
                               view.verticalScrollBar().value())

    def center_image(self, view):
        view.horizontalScrollBar().setValue(self.status.h_scroll)
        view.verticalScrollBar().setValue(self.status.v_scroll)

    def mouse_move_event(self, event):
        if self.empty():
            return
        position = event.position()
        brush_size = self.brush.size
        if not self.space_pressed:
            self.update_brush_cursor()
        if self.dragging and event.buttons() & Qt.LeftButton:
            current_time = QTime.currentTime()
            if self.last_update_time.msecsTo(current_time) >= gui_constants.PAINT_REFRESH_TIMER:
                min_step = brush_size * \
                    gui_constants.MIN_MOUSE_STEP_BRUSH_FRACTION * self.zoom_factor()
                x, y = position.x(), position.y()
                xp, yp = self.last_brush_pos.x(), self.last_brush_pos.y()
                distance = math.sqrt((x - xp)**2 + (y - yp)**2)
                n_steps = int(float(distance) / min_step)
                if n_steps > 0:
                    delta_x = (position.x() - self.last_brush_pos.x()) / n_steps
                    delta_y = (position.y() - self.last_brush_pos.y()) / n_steps
                    for i in range(0, n_steps + 1):
                        pos = QPoint(self.last_brush_pos.x() + i * delta_x,
                                     self.last_brush_pos.y() + i * delta_y)
                        self.brush_operation_continued.emit(pos)
                    self.last_brush_pos = position
                self.last_update_time = current_time
        if self.scrolling and event.buttons() & Qt.LeftButton:
            master_view = self.get_master_view()
            if self.space_pressed:
                master_view.setCursor(Qt.ClosedHandCursor)
                if self.brush_cursor:
                    self.brush_cursor.hide()
            delta = position - self.last_mouse_pos
            self.last_mouse_pos = position
            self.scroll_view(master_view, delta.x(), delta.y())

    def mouse_press_event(self, event):
        if self.empty():
            return
        if event.button() == Qt.LeftButton and self.has_master_layer():
            if self.space_pressed:
                self.scrolling = True
                self.last_mouse_pos = event.position()
                self.setCursor(Qt.ClosedHandCursor)
            else:
                self.last_brush_pos = event.position()
                self.brush_operation_started.emit(event.position().toPoint())
                self.dragging = True
            if self.brush_cursor:
                self.brush_cursor.show()

    def mouse_release_event(self, event):
        if self.empty():
            return
        master_view = self.get_master_view()
        if self.space_pressed:
            master_view.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        else:
            master_view.setCursor(Qt.BlankCursor)
            if self.brush_cursor:
                self.brush_cursor.show()
        if event.button() == Qt.LeftButton:
            if self.scrolling:
                self.scrolling = False
                self.last_mouse_pos = None
            elif self.dragging:
                self.dragging = False
                self.brush_operation_ended.emit()

    def handle_pinch_gesture(self, pinch):
        master_view = self.get_master_view()
        if pinch.state() == Qt.GestureStarted:
            self.pinch_start_scale = self.zoom_factor()
            self.pinch_center_view = pinch.centerPoint()
            self.pinch_center_scene = master_view.mapToScene(self.pinch_center_view.toPoint())
            self.gesture_active = True
        elif pinch.state() == Qt.GestureUpdated:
            new_scale = self.pinch_start_scale * pinch.totalScaleFactor()
            new_scale = max(self.min_scale(), min(new_scale, self.max_scale()))
            if abs(new_scale - self.zoom_factor()) > 0.01:
                self.set_zoom_factor(new_scale)
                self.apply_zoom()
                new_center = master_view.mapToScene(self.pinch_center_view.toPoint())
                delta = self.pinch_center_scene - new_center
                h_scroll = master_view.horizontalScrollBar().value() + \
                    int(delta.x() * self.zoom_factor())
                v_scroll = master_view.verticalScrollBar().value() + \
                    int(delta.y() * self.zoom_factor())
                self.status.set_scroll(h_scroll, v_scroll)
                self.center_image(master_view)
        elif pinch.state() in (Qt.GestureFinished, Qt.GestureCanceled):
            self.gesture_active = False
        self.update_cursor_pen_width()
