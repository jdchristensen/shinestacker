# pylint: disable=C0114, C0115, C0116, R0904, R0915, E0611, R0902, R0911, R0914
from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QEvent, QRectF
from .. config.gui_constants import gui_constants
from .view_strategy import ViewStrategy, ImageGraphicsViewBase, ViewSignals


class ImageGraphicsView(ImageGraphicsViewBase):
    mouse_pressed = Signal(QEvent)
    mouse_moved = Signal(QEvent)
    mouse_released = Signal(QEvent)
    gesture_event = Signal(QEvent)

    # pylint: disable=C0103
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
    # pylint: enable=C0103


class SideBySideView(ViewStrategy, QWidget, ViewSignals):
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
        self.panning_left = False
        self.brush_cursor = None
        self.right_view.setCursor(Qt.BlankCursor)
        self.setup_brush_cursor()
        self.setFocusPolicy(Qt.StrongFocus)
        self.pan_start = None
        self.pinch_start_scale = None

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

    # pylint: disable=C0103
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
    # pylint: enable=C0103

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
        self.mouse_move_event(event)

    def handle_right_mouse_release(self, event):
        self.mouse_release_event(event)

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

    def handle_left_mouse_release(self, _event):
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
        self.right_view.setSceneRect(QRectF(pixmap.rect()))
        self.set_min_scale(min(gui_constants.MIN_ZOOMED_IMG_WIDTH / img_width,
                               gui_constants.MIN_ZOOMED_IMG_HEIGHT / img_height))
        self.set_max_scale(gui_constants.MAX_ZOOMED_IMG_PX_SIZE)
        self.set_zoom_factor(1.0)
        self.right_view.fitInView(self.right_pixmap_item, Qt.KeepAspectRatio)
        self.set_zoom_factor(self.get_current_scale())
        self.set_zoom_factor(max(self.min_scale(), min(self.max_scale(), self.zoom_factor())))
        self.right_view.resetTransform()
        self.right_scene.scale(self.zoom_factor(), self.zoom_factor())
        self.right_view.centerOn(self.right_pixmap_item)
        center = self.right_scene.sceneRect().center()
        self.brush_preview.setPos(center)
        self.brush_cursor.setPos(center)

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        pixmap = self.status.pixmap_current
        self.left_scene.setSceneRect(QRectF(pixmap.rect()))
        self.right_view.fitInView(self.left_pixmap_item, Qt.KeepAspectRatio)
        self.left_view.resetTransform()
        self.left_scene.scale(self.zoom_factor(), self.zoom_factor())
        self.left_view.centerOn(self.left_pixmap_item)

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
            self.left_view.centerOn(self.left_pixmap_item)
        if not self.right_pixmap_item.pixmap().isNull():
            self.right_view.resetTransform()
            self.right_view.scale(self.zoom_factor(), self.zoom_factor())
            self.right_view.centerOn(self.right_pixmap_item)

    def set_brush(self, brush):
        super().set_brush(brush)
        if self.brush_cursor:
            self.right_scene.removeItem(self.brush_cursor)
        self.setup_brush_cursor()
