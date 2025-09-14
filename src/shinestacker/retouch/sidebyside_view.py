# pylint: disable=C0114, C0115, C0116, R0904, R0915, E0611, R0902, R0911
import math
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFrame, QGraphicsEllipseItem)
from PySide6.QtGui import QPixmap, QColor, QBrush, QPen, QCursor
from PySide6.QtCore import Qt, Signal, QPoint, QPointF, QEvent, QTime, QRectF
from .. config.gui_constants import gui_constants
from .view_strategy import ViewStrategy, ImageGraphicsViewBase


class ImageGraphicsView(ImageGraphicsViewBase):
    mouse_pressed = Signal(QEvent)
    mouse_moved = Signal(QEvent)
    mouse_released = Signal(QEvent)
    gesture_event = Signal(QEvent)

    def event(self, event):
        if event.type() == QEvent.Gesture:
            self.gesture_event.emit(event)
            return True
        return super().event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed.emit(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(event)
        event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_released.emit(event)
        super().mouseReleaseEvent(event)


class SideBySideView(ViewStrategy, QWidget):
    temp_view_requested = Signal(bool)
    brush_operation_started = Signal(QPoint)
    brush_operation_continued = Signal(QPoint)
    brush_operation_ended = Signal()
    brush_size_change_requested = Signal(int)

    def __init__(self, layer_collection, status, parent):
        ViewStrategy.__init__(self, layer_collection, status)
        QWidget.__init__(self, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.left_view = ImageGraphicsView(parent)
        self.right_view = ImageGraphicsView(parent)
        self.left_scene = self.create_scene(self.left_view)
        self.right_scene = self.create_scene(self.right_view)
        self.create_pixmaps()
        self.right_scene.addItem(self.brush_preview)
        layout.addWidget(self.left_view, 1)
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(2)
        layout.addWidget(separator, 0)
        layout.addWidget(self.right_view, 1)
        self._connect_signals()
        self.space_pressed = False
        self.control_pressed = False
        self.dragging = False
        self.scrolling = False
        self.panning_left = False
        self.last_brush_pos = None
        self.last_mouse_pos = None
        self.last_update_time = QTime.currentTime()
        self.brush_cursor = None
        self.right_view.setCursor(Qt.BlankCursor)
        self.setup_brush_cursor()
        self.setFocusPolicy(Qt.StrongFocus)

    def create_pixmaps(self):
        self.left_pixmap_item = self.create_pixmap(self.left_scene)
        self.right_pixmap_item = self.create_pixmap(self.right_scene)

    def _connect_signals(self):
        self.left_view.mouse_pressed.connect(self.handle_left_mouse_press)
        self.left_view.mouse_moved.connect(self.handle_left_mouse_move)
        self.left_view.mouse_released.connect(self.handle_left_mouse_release)
        self.left_view.gesture_event.connect(self.handle_gesture_event)
        self.right_view.mouse_pressed.connect(self.handle_right_mouse_press)
        self.right_view.mouse_moved.connect(self.handle_right_mouse_move)
        self.right_view.mouse_released.connect(self.handle_right_mouse_release)
        self.right_view.gesture_event.connect(self.handle_gesture_event)
        self.left_view.horizontalScrollBar().valueChanged.connect(
            self.right_view.horizontalScrollBar().setValue)
        self.left_view.verticalScrollBar().valueChanged.connect(
            self.right_view.verticalScrollBar().setValue)
        self.right_view.horizontalScrollBar().valueChanged.connect(
            self.left_view.horizontalScrollBar().setValue)
        self.right_view.verticalScrollBar().valueChanged.connect(
            self.left_view.verticalScrollBar().setValue)

    def get_master_view(self):
        return self.right_view

    def get_master_scene(self):
        return self.right_scene

    def get_master_pixmap(self):
        return self.right_pixmap_item

    def get_views(self):
        return [self.right_view, self.left_view]

    def get_scenes(self):
        return [self.right_scene, self.left_scene]

    def get_pixmaps(self):
        return {
            self.right_pixmap_item: self.right_view,
            self.left_pixmap_item: self.left_view
        }

    def showEvent(self, event):
        super().showEvent(event)
        self.update_brush_cursor()

    def enterEvent(self, event):
        self.activateWindow()
        self.setFocus()
        if not self.empty():
            if self.space_pressed:
                self.right_view.setCursor(Qt.OpenHandCursor)
            else:
                self.right_view.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.empty():
            self.right_view.setCursor(Qt.ArrowCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        super().leaveEvent(event)

    def handle_right_mouse_press(self, event):
        position = event.position()
        if self.has_master_layer():
            if self.space_pressed:
                self.scrolling = True
                self.last_mouse_pos = event.position()
                self.right_view.setCursor(Qt.ClosedHandCursor)
            else:
                self.last_brush_pos = position
                self.brush_operation_started.emit(position.toPoint())
                self.dragging = True
            if self.brush_cursor:
                self.brush_cursor.show()

    def handle_right_mouse_move(self, event):
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
            if self.space_pressed:
                self.right_view.setCursor(Qt.ClosedHandCursor)
                if self.brush_cursor:
                    self.brush_cursor.hide()
            delta = position - self.last_mouse_pos
            self.last_mouse_pos = position
            self.right_view.horizontalScrollBar().setValue(
                self.right_view.horizontalScrollBar().value() - delta.x())
            self.right_view.verticalScrollBar().setValue(
                self.right_view.verticalScrollBar().value() - delta.y())

    def handle_right_mouse_release(self, event):
        if self.space_pressed:
            self.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        else:
            self.setCursor(Qt.BlankCursor)
            if self.brush_cursor:
                self.brush_cursor.show()
        if event.button() == Qt.LeftButton:
            if self.scrolling:
                self.scrolling = False
                self.last_mouse_pos = None
            elif hasattr(self, 'dragging') and self.dragging:
                self.dragging = False
                self.brush_operation_ended.emit()

    def handle_left_mouse_press(self, event):
        position = event.position()
        if self.space_pressed:
            self.pan_start = position
            self.panning_left = True

    def handle_left_mouse_move(self, event):
        position = event.position()
        if self.panning_left and self.space_pressed:
            delta = position - self.pan_start
            self.pan_start = position
            self.left_view.horizontalScrollBar().setValue(
                self.left_view.horizontalScrollBar().value() - delta.x())
            self.left_view.verticalScrollBar().setValue(
                self.left_view.verticalScrollBar().value() - delta.y())

    def handle_left_mouse_release(self, event):
        if self.panning_left:
            self.panning_left = False

    def handle_gesture_event(self, event):
        if self.empty():
            return
        pinch_gesture = event.gesture(Qt.PinchGesture)
        if pinch_gesture:
            self.handle_pinch_gesture(pinch_gesture)
            event.accept()

    def handle_pinch_gesture(self, pinch):
        if pinch.state() == Qt.GestureStarted:
            self.pinch_start_scale = self.zoom_factor()
            self.pinch_center_view = pinch.centerPoint()
            self.pinch_center_scene = self.right_view.mapToScene(self.pinch_center_view.toPoint())
        elif pinch.state() == Qt.GestureUpdated:
            new_scale = self.pinch_start_scale * pinch.totalScaleFactor()
            new_scale = max(self.min_scale(), min(new_scale, self.max_scale()))
            if abs(new_scale - self.zoom_factor()) > 0.01:
                self.set_zoom_factor(new_scale)
                self._apply_zoom()
                new_center = self.right_view.mapToScene(self.pinch_center_view.toPoint())
                delta = self.pinch_center_scene - new_center
                h_scroll = self.right_view.horizontalScrollBar().value()
                v_scroll = self.right_view.verticalScrollBar().value()
                self.right_view.horizontalScrollBar().setValue(
                    h_scroll + int(delta.x() * self.zoom_factor()))
                self.right_view.verticalScrollBar().setValue(
                    v_scroll + int(delta.y() * self.zoom_factor()))

    def set_master_image(self, qimage):
        self.status.set_master_image(qimage)
        pixmap = self.status.pixmap_master
        img_width, img_height = pixmap.width(), pixmap.height()
        self.set_min_scale(min(gui_constants.MIN_ZOOMED_IMG_WIDTH / img_width,
                               gui_constants.MIN_ZOOMED_IMG_HEIGHT / img_height))
        self.set_max_scale(gui_constants.MAX_ZOOMED_IMG_PX_SIZE)
        self.set_zoom_factor(self.get_current_scale())
        self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), self.zoom_factor())))
        self.righ_scene.setSceneRect(QRectF(pixmap.rect()))
        self.righ_scene.fitInView(self.right_pixmap_item, Qt.KeepAspectRatio)
        self.righ_scene.resetTransform()
        self.righ_scene.scale(self.zoom_factor(), self.zoom_factor())

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        pixmap = self.status.pixmap_current
        self.left_scene.setSceneRect(QRectF(pixmap.rect()))
        self.left_scene.fitInView(self.right_pixmap_item, Qt.KeepAspectRatio)
        self.left_scene.resetTransform()
        self.left_scene.scale(self.zoom_factor(), self.zoom_factor())

    def _arrange_images(self):
        if self.status.empty():
            return
        if self.right_pixmap_item.pixmap().height() == 0:
            self.right_scene.addItem(self.brush_preview)
            self.update_master_display()
            self.update_current_display()
            self.reset_zoom()
        self._apply_zoom()

    def update_master_display(self):
        if not self.status.empty():
            master_qimage = self.numpy_to_qimage(self.master_layer())
            if master_qimage:
                self.right_pixmap_item.setPixmap(QPixmap.fromImage(master_qimage))
                self._arrange_images()

    def update_current_display(self):
        if not self.status.empty() and self.number_of_layers() > 0:
            current_qimage = self.numpy_to_qimage(self.current_layer())
            if current_qimage:
                self.left_pixmap_item.setPixmap(QPixmap.fromImage(current_qimage))
                self._arrange_images()

    def _apply_zoom(self):
        if not self.left_pixmap_item.pixmap().isNull():
            self.left_view.resetTransform()
            self.left_view.scale(self.zoom_factor(), self.zoom_factor())
        if not self.right_pixmap_item.pixmap().isNull():
            self.right_view.resetTransform()
            self.right_view.scale(self.zoom_factor(), self.zoom_factor())

    def update_brush_cursor(self):
        if self.empty():
            return
        if not self.brush_cursor or not self.isVisible():
            return
        mouse_pos = self.right_view.mapFromGlobal(QCursor.pos())
        if not self.right_view.rect().contains(mouse_pos):
            self.brush_cursor.hide()
            return
        scene_pos = self.right_view.mapToScene(mouse_pos)
        size = self.brush.size
        radius = size / 2
        self.brush_cursor.setRect(scene_pos.x() - radius, scene_pos.y() - radius, size, size)
        allow_cursor_preview = self.display_manager.allow_cursor_preview()
        if self.cursor_style == 'preview' and allow_cursor_preview:
            self.setup_outline_style()
            self.brush_cursor.hide()
            pos = QCursor.pos()
            if isinstance(pos, QPointF):
                scene_pos = pos
            else:
                cursor_pos = self.right_view.mapFromGlobal(pos)
                scene_pos = self.right_view.mapToScene(cursor_pos)
            self.brush_preview.update(scene_pos, int(size))
        else:
            self.brush_preview.hide()
            if self.cursor_style == 'outline' or not allow_cursor_preview:
                self.setup_outline_style()
            else:
                self.setup_simple_brush_style(scene_pos.x(), scene_pos.y(), radius)
        if not self.brush_cursor.isVisible():
            self.brush_cursor.show()

    def set_cursor_style(self, style):
        self.cursor_style = style
        if self.brush_cursor:
            self.update_brush_cursor()

    def set_brush(self, brush):
        super().set_brush(brush)
        if self.brush_cursor:
            self.right_scene.removeItem(self.brush_cursor)
        self.setup_brush_cursor()

    def setup_brush_cursor(self):
        if not self.brush:
            return
        for item in self.right_scene.items():
            if isinstance(item, QGraphicsEllipseItem) and item != self.brush_preview:
                self.right_scene.removeItem(item)
        pen = QPen(QColor(*gui_constants.BRUSH_COLORS['pen']), 1)
        brush = QBrush(QColor(*gui_constants.BRUSH_COLORS['cursor_inner']))
        self.brush_cursor = self.right_scene.addEllipse(
            0, 0, self.brush.size, self.brush.size, pen, brush)
        self.brush_cursor.setZValue(1000)
        self.brush_cursor.hide()
