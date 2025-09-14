# pylint: disable=C0114, C0115, C0116, E0611, E1101, R0904, R0912, R0914, R0902
import math
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QTime, QPoint, QPointF, QEvent, QRectF, Signal
from .. config.gui_constants import gui_constants
from .view_strategy import ViewStrategy, ImageGraphicsViewBase


class OverlaidView(ViewStrategy, ImageGraphicsViewBase):
    temp_view_requested = Signal(bool)
    brush_operation_started = Signal(QPoint)
    brush_operation_continued = Signal(QPoint)
    brush_operation_ended = Signal()
    brush_size_change_requested = Signal(int)  # +1 or -1

    def __init__(self, layer_collection, status, parent):
        ViewStrategy.__init__(self, layer_collection, status)
        ImageGraphicsViewBase.__init__(self, parent)
        self.scene = self.create_scene(self)
        self.create_pixmaps()
        self.scene.addItem(self.brush_preview)
        self.last_mouse_pos = None
        self.brush_cursor = None
        self.scrolling = False
        self.dragging = False
        self.last_update_time = QTime.currentTime()
        self.last_brush_pos = None
        self.pinch_start_scale = 1.0
        self.last_scroll_pos = QPointF()

    def create_pixmaps(self):
        self.pixmap_item_master = self.create_pixmap(self.scene)
        self.pixmap_item_current = self.create_pixmap(self.scene)

    def get_master_view(self):
        return self

    def get_master_scene(self):
        return self.scene

    def get_master_pixmap(self):
        return self.pixmap_item_master

    def get_views(self):
        return [self]

    def get_scenes(self):
        return [self.scene]

    def get_pixmaps(self):
        return {
            self.pixmap_item_master: self,
            self.pixmap_item_current: self
        }

    def set_master_image(self, qimage):
        self.status.set_master_image(qimage)
        pixmap = self.status.pixmap_master
        self.setSceneRect(QRectF(pixmap.rect()))

        img_width, img_height = pixmap.width(), pixmap.height()
        self.set_min_scale(min(gui_constants.MIN_ZOOMED_IMG_WIDTH / img_width,
                               gui_constants.MIN_ZOOMED_IMG_HEIGHT / img_height))
        self.set_max_scale(gui_constants.MAX_ZOOMED_IMG_PX_SIZE)
        if self.set_zoom_factor(1.0):
            self.fitInView(self.pixmap_item_master, Qt.KeepAspectRatio)
            self.set_zoom_factor(self.get_current_scale())
            self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), self.zoom_factor())))
            self.resetTransform()
            self.scale(self.zoom_factor(), self.zoom_factor())

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        if self.empty():
            self.setSceneRect(QRectF(self.status.pixmap_current.rect()))

    def show_master(self):
        self.pixmap_item_master.setVisible(True)
        self.pixmap_item_current.setVisible(False)

    def show_current(self):
        self.pixmap_item_master.setVisible(False)
        self.pixmap_item_current.setVisible(True)

    def update_master_display(self):
        if not self.empty():
            master_qimage = self.numpy_to_qimage(
                self.master_layer())
            if master_qimage:
                self.pixmap_item_master.setPixmap(QPixmap.fromImage(master_qimage))

    def update_current_display(self):
        if not self.empty() and self.number_of_layers() > 0:
            current_qimage = self.numpy_to_qimage(
                self.current_layer())
            if current_qimage:
                self.pixmap_item_current.setPixmap(QPixmap.fromImage(current_qimage))

    def set_view_state(self, state):
        self.status.set_state(state)
        if state:
            self.resetTransform()
            self.scale(state['zoom'], state['zoom'])
            self.horizontalScrollBar().setValue(state['h_scroll'])
            self.verticalScrollBar().setValue(state['v_scroll'])
            self.set_zoom_factor(state['zoom'])

    def handle_key_press_event(self, event):
        if event.key() == Qt.Key_X:
            self.temp_view_requested.emit(True)
            self.update_brush_cursor()

    def handle_key_release_event(self, event):
        if event.key() == Qt.Key_X:
            self.temp_view_requested.emit(False)

    # pylint: disable=C0103
    def mousePressEvent(self, event):
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
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
                self.setCursor(Qt.ClosedHandCursor)
                if self.brush_cursor:
                    self.brush_cursor.hide()
            delta = position - self.last_mouse_pos
            self.last_mouse_pos = position
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.empty():
            return
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
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self.empty() or self.gesture_active:
            return
        if event.source() == Qt.MouseEventNotSynthesized:  # Physical mouse
            if self.control_pressed:
                self.brush_size_change_requested.emit(1 if event.angleDelta().y() > 0 else -1)
            else:
                zoom_in_factor = 1.10
                zoom_out_factor = 1 / zoom_in_factor
                current_scale = self.get_current_scale()
                if event.angleDelta().y() > 0:  # Zoom in
                    new_scale = current_scale * zoom_in_factor
                    if new_scale <= self.max_scale():
                        self.scale(zoom_in_factor, zoom_in_factor)
                        self.set_zoom_factor(new_scale)
                else:  # Zoom out
                    new_scale = current_scale * zoom_out_factor
                    if new_scale >= self.min_scale():
                        self.scale(zoom_out_factor, zoom_out_factor)
                        self.set_zoom_factor(new_scale)
            self.update_brush_cursor()
        else:  # Touchpad event - fallback for systems without gesture recognition
            if not self.control_pressed:
                delta = event.pixelDelta() or event.angleDelta() / 8
                if delta:
                    self.horizontalScrollBar().setValue(
                        self.horizontalScrollBar().value() - delta.x()
                    )
                    self.verticalScrollBar().setValue(
                        self.verticalScrollBar().value() - delta.y()
                    )
            else:  # Control + touchpad scroll for zoom
                zoom_in = event.angleDelta().y() > 0
                if zoom_in:
                    self.zoom_in()
                else:
                    self.zoom_out()
        event.accept()

    def enterEvent(self, event):
        self.activateWindow()
        self.setFocus()
        if not self.empty():
            self.setCursor(Qt.BlankCursor)
            if self.brush_cursor:
                self.brush_cursor.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.empty():
            self.setCursor(Qt.ArrowCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
        super().leaveEvent(event)
    # pylint: enable=C0103

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.handle_gesture_event(event)
        return super().event(event)

    def handle_gesture_event(self, event):
        if self.empty():
            return False
        handled = False
        pan_gesture = event.gesture(Qt.PanGesture)
        if pan_gesture:
            self.handle_pan_gesture(pan_gesture)
            handled = True
        pinch_gesture = event.gesture(Qt.PinchGesture)
        if pinch_gesture:
            self.handle_pinch_gesture(pinch_gesture)
            handled = True
        if handled:
            event.accept()
            return True
        return False

    def handle_pan_gesture(self, pan_gesture):
        if pan_gesture.state() == Qt.GestureStarted:
            self.last_scroll_pos = pan_gesture.delta()
            self.gesture_active = True
        elif pan_gesture.state() == Qt.GestureUpdated:
            delta = pan_gesture.delta() - self.last_scroll_pos
            self.last_scroll_pos = pan_gesture.delta()
            scaled_delta = delta * (1.0 / self.get_current_scale())
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(scaled_delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(scaled_delta.y())
            )
        elif pan_gesture.state() == Qt.GestureFinished:
            self.gesture_active = False

    def handle_pinch_gesture(self, pinch):
        if pinch.state() == Qt.GestureStarted:
            self.pinch_start_scale = self.get_current_scale()
            self.pinch_center_view = pinch.centerPoint()
            self.pinch_center_scene = self.mapToScene(self.pinch_center_view.toPoint())
            self.gesture_active = True
        elif pinch.state() == Qt.GestureUpdated:
            new_scale = self.pinch_start_scale * pinch.totalScaleFactor()
            new_scale = max(self.min_scale(), min(new_scale, self.max_scale()))
            if abs(new_scale - self.get_current_scale()) > 0.01:
                self.resetTransform()
                self.scale(new_scale, new_scale)
                self.set_zoom_factor(new_scale)
                new_center = self.mapToScene(self.pinch_center_view.toPoint())
                delta = self.pinch_center_scene - new_center
                self.translate(delta.x(), delta.y())
                self.update_brush_cursor()
        elif pinch.state() in (Qt.GestureFinished, Qt.GestureCanceled):
            self.gesture_active = False
