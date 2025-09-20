# pylint: disable=C0114, C0115, C0116, E0611, E1101, R0904, R0912, R0914, R0902
from PySide6.QtCore import Qt, QPointF, QEvent, QRectF
from .. config.gui_constants import gui_constants
from .view_strategy import ViewStrategy, ImageGraphicsViewBase, ViewSignals


class OverlaidView(ViewStrategy, ImageGraphicsViewBase, ViewSignals):
    def __init__(self, layer_collection, status, parent):
        ViewStrategy.__init__(self, layer_collection, status)
        ImageGraphicsViewBase.__init__(self, parent)
        self.scene = self.create_scene(self)
        self.create_pixmaps()
        self.scene.addItem(self.brush_preview)
        self.brush_cursor = None
        self.pinch_start_scale = 1.0
        self.last_scroll_pos = QPointF()

    def create_pixmaps(self):
        self.pixmap_item_master = self.create_pixmap(self.scene)
        self.pixmap_item_current = self.create_pixmap(self.scene)

    def get_master_view(self):
        return self

    def get_current_view(self):
        return self

    def get_master_scene(self):
        return self.scene

    def get_current_scene(self):
        return self.scene

    def get_master_pixmap(self):
        return self.pixmap_item_master

    def get_current_pixmap(self):
        return self.pixmap_item_current

    def get_views(self):
        return [self]

    def get_scenes(self):
        return [self.scene]

    def get_pixmaps(self):
        return {
            self.pixmap_item_master: self,
            self.pixmap_item_current: self
        }

    # pylint: disable=C0103
    def mousePressEvent(self, event):
        self.mouse_press_event(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_move_event(event)

    def mouseReleaseEvent(self, event):
        self.mouse_release_event(event)
        super().mouseReleaseEvent(event)

    # pylint: enable=R0801
    def wheelEvent(self, event):
        if self.empty() or self.gesture_active:
            return
        if event.source() == Qt.MouseEventNotSynthesized:  # Physical mouse
            if self.control_pressed:
                self.brush_size_change_requested.emit(1 if event.angleDelta().y() > 0 else -1)
            else:
                zoom_in_factor = gui_constants.ZOOM_IN_FACTOR
                zoom_out_factor = gui_constants.ZOOM_OUT_FACTOR
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
                    self.scroll_view(self, delta.x(), delta.y())
            else:  # Control + touchpad scroll for zoom
                zoom_in = event.angleDelta().y() > 0
                if zoom_in:
                    self.zoom_in()
                else:
                    self.zoom_out()
        event.accept()
        # pylint: disable=R0801

    def enterEvent(self, event):
        self.activateWindow()
        self.setFocus()
        if self.empty():
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.BlankCursor)
            if self.brush_cursor:
                self.brush_cursor.show()
        super().enterEvent(event)
    # pylint: enable=C0103

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.handle_gesture_event(event)
        return super().event(event)

    def setup_scene_image(self, pixmap, pixmap_item):
        self.setSceneRect(QRectF(pixmap.rect()))
        img_width, img_height = pixmap.width(), pixmap.height()
        self.set_max_min_scales(img_width, img_height)
        view_rect = self.viewport().rect()
        scale_x = view_rect.width() / img_width
        scale_y = view_rect.height() / img_height
        scale_factor = min(scale_x, scale_y)
        scale_factor = max(self.min_scale(), min(scale_factor, self.max_scale()))
        self.set_zoom_factor(scale_factor)
        self.resetTransform()
        self.scale(scale_factor, scale_factor)
        self.centerOn(pixmap_item)
        self.center_image(self)
        self.update_cursor_pen_width()

    def set_master_image(self, qimage):
        self.status.set_master_image(qimage)
        self.setup_scene_image(self.status.pixmap_master, self.pixmap_item_master)
        self.update_master_display()

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        if self.empty():
            self.setup_scene_image(self.status.pixmap_current, self.pixmap_item_current)

    def setup_brush_cursor(self):
        super().setup_brush_cursor()
        self.update_cursor_pen_width()

    def show_master(self):
        self.pixmap_item_master.setVisible(True)
        self.pixmap_item_current.setVisible(False)
        self.brush_preview.show()
        if self.brush_cursor:
            self.scene.removeItem(self.brush_cursor)
            self.brush_cursor = self.create_circle(self.scene)
            self.update_brush_cursor()

    def show_current(self):
        self.pixmap_item_master.setVisible(False)
        self.pixmap_item_current.setVisible(True)
        self.brush_preview.hide()
        if self.brush_cursor:
            self.scene.removeItem(self.brush_cursor)
            self.brush_cursor = self.create_alt_circle(self.scene)
            self.update_brush_cursor()

    def arrange_images(self):
        if self.empty():
            return
        if self.pixmap_item_master.isVisible():
            pixmap = self.pixmap_item_master.pixmap()
            if not pixmap.isNull():
                self.setSceneRect(QRectF(pixmap.rect()))
                self.centerOn(self.pixmap_item_master)
                self.center_image(self)
        elif self.pixmap_item_current.isVisible():
            pixmap = self.pixmap_item_current.pixmap()
            if not pixmap.isNull():
                self.setSceneRect(QRectF(pixmap.rect()))
                self.centerOn(self.pixmap_item_current)
                self.center_image(self)
        current_scale = self.get_current_scale()
        scale_factor = self.zoom_factor() / current_scale
        self.scale(scale_factor, scale_factor)

    def handle_key_press_event(self, event):
        if event.key() in [Qt.Key_Up, Qt.Key_Down]:
            return False
        if event.key() == Qt.Key_X:
            self.temp_view_requested.emit(True)
            return False
        return True

    def handle_key_release_event(self, event):
        if event.key() in [Qt.Key_Up, Qt.Key_Down]:
            return False
        if event.key() == Qt.Key_X:
            self.temp_view_requested.emit(False)
            return False
        return True

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
            self.scroll_view(self, int(scaled_delta.x()), int(scaled_delta.y()))
        elif pan_gesture.state() == Qt.GestureFinished:
            self.gesture_active = False
