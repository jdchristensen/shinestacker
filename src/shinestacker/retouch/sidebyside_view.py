# pylint: disable=C0114, C0115, C0116, R0904, R0915, E0611, R0902
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFrame, QGraphicsView, QGraphicsScene,
                               QGraphicsPixmapItem)
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QWheelEvent, QMouseEvent
from PySide6.QtCore import Qt, Signal, QPoint, QPointF, QEvent
from .view_strategy import ViewStrategy


class SideBySideView(ViewStrategy, QWidget):
    temp_view_requested = Signal(bool)
    brush_operation_started = Signal(QPoint)
    brush_operation_continued = Signal(QPoint)
    brush_operation_ended = Signal()
    brush_size_change_requested = Signal(int)  # +1 or -1

    def __init__(self, brush_preview, status, parent):
        ViewStrategy.__init__(self, brush_preview, status)
        QWidget.__init__(self, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.left_view = QGraphicsView()
        self.left_scene = QGraphicsScene()
        self.left_view.setScene(self.left_scene)
        self.left_view.setRenderHint(QPainter.Antialiasing)
        self.left_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.left_pixmap_item = QGraphicsPixmapItem()
        self.left_scene.addItem(self.left_pixmap_item)
        self.left_scene.setBackgroundBrush(QBrush(QColor(120, 120, 120)))
        layout.addWidget(self.left_view)
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(2)
        layout.addWidget(separator)
        self.right_view = QGraphicsView()
        self.right_scene = QGraphicsScene()
        self.right_view.setScene(self.right_scene)
        self.right_view.setRenderHint(QPainter.Antialiasing)
        self.right_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.right_pixmap_item = QGraphicsPixmapItem()
        self.right_scene.addItem(self.right_pixmap_item)
        self.right_scene.setBackgroundBrush(QBrush(QColor(120, 120, 120)))
        layout.addWidget(self.right_view)
        self.zoom_factor = -1
        self.min_scale = 0.1
        self.max_scale = 10.0
        self.pan_start = QPointF()
        self.panning = False
        self.left_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.right_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.left_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.right_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.left_view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.right_view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.left_view.horizontalScrollBar().valueChanged.connect(
            self.right_view.horizontalScrollBar().setValue)
        self.left_view.verticalScrollBar().valueChanged.connect(
            self.right_view.verticalScrollBar().setValue)
        self.right_view.horizontalScrollBar().valueChanged.connect(
            self.left_view.horizontalScrollBar().setValue)
        self.right_view.verticalScrollBar().valueChanged.connect(
            self.left_view.verticalScrollBar().setValue)
        self.left_view.viewport().installEventFilter(self)
        self.right_view.viewport().installEventFilter(self)
        self.pinch_start_scale = 1.0
        self.pinch_center_view = None
        self.pinch_center_scene = None
        self.gesture_active = False
        self.left_view.grabGesture(Qt.PinchGesture)
        self.right_view.grabGesture(Qt.PinchGesture)
        self.left_view.installEventFilter(self)
        self.right_view.installEventFilter(self)

    # pylint: disable=C0103
    def eventFilter(self, obj, event):
        if obj in [self.left_view, self.right_view] and event.type() == QEvent.Gesture:
            return self.handle_gesture_event(event)
        if (obj == self.left_view.viewport() or obj == self.right_view.viewport()) and \
           event.type() == QWheelEvent.Type:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            return True
        if (obj == self.left_view.viewport() or obj == self.right_view.viewport()) and \
                event.type() == QMouseEvent.Type:
            if event.button() == Qt.LeftButton:
                if event.type() == QMouseEvent.MouseButtonPress:
                    self.pan_start = event.pos()
                    self.panning = True
                    return True
                if event.type() == QMouseEvent.MouseMove and self.panning:
                    delta = event.pos() - self.pan_start
                    self.pan_start = event.pos()
                    self.left_view.horizontalScrollBar().setValue(
                        self.left_view.horizontalScrollBar().value() - delta.x())
                    self.left_view.verticalScrollBar().setValue(
                        self.left_view.verticalScrollBar().value() - delta.y())
                    return True
                if event.type() == QMouseEvent.MouseButtonRelease and self.panning:
                    self.panning = False
                    return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_images()

    def showEvent(self, event):
        super().showEvent(event)
        self._arrange_images()
    # pylint: enable=C0103

    def handle_gesture_event(self, event):
        if self.empty():
            return False
        handled = False
        pinch_gesture = event.gesture(Qt.PinchGesture)
        if pinch_gesture:
            self.handle_pinch_gesture(pinch_gesture)
            handled = True
        if handled:
            event.accept()
            return True
        return False

    def handle_pinch_gesture(self, pinch):
        if pinch.state() == Qt.GestureStarted:
            self.pinch_start_scale = self.zoom_factor
            self.pinch_center_view = pinch.centerPoint()
            self.pinch_center_scene = self.right_view.mapToScene(self.pinch_center_view.toPoint())
            self.gesture_active = True
        elif pinch.state() == Qt.GestureUpdated:
            new_scale = self.pinch_start_scale * pinch.totalScaleFactor()
            new_scale = max(self.min_scale, min(new_scale, self.max_scale))
            if abs(new_scale - self.zoom_factor) > 0.01:
                self.zoom_factor = new_scale
                self._apply_zoom()
                new_center = self.right_view.mapToScene(self.pinch_center_view.toPoint())
                delta = self.pinch_center_scene - new_center
                h_scroll = self.right_view.horizontalScrollBar().value()
                v_scroll = self.right_view.verticalScrollBar().value()
                self.right_view.horizontalScrollBar().setValue(
                    h_scroll + int(delta.x() * self.zoom_factor))
                self.right_view.verticalScrollBar().setValue(
                    v_scroll + int(delta.y() * self.zoom_factor))
        elif pinch.state() in (Qt.GestureFinished, Qt.GestureCanceled):
            self.gesture_active = False

    def set_master_image(self, qimage):
        self.status.set_master_image(qimage)
        self.right_pixmap_item.setPixmap(QPixmap.fromImage(qimage))
        self._arrange_images()

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        self.left_pixmap_item.setPixmap(QPixmap.fromImage(qimage))
        self._arrange_images()

    def _arrange_images(self):
        if self.status.empty():
            return
        if self.right_pixmap_item.pixmap().height() == 0:
            self.update_master_display()
            self.update_current_display()
            self.reset_zoom()
        self._apply_zoom()

    def clear_image(self):
        self.left_scene.clear()
        self.right_scene.clear()
        self.left_pixmap_item = QGraphicsPixmapItem()
        self.right_pixmap_item = QGraphicsPixmapItem()
        self.left_scene.addItem(self.left_pixmap_item)
        self.right_scene.addItem(self.right_pixmap_item)
        self.status.clear()

    def update_master_display(self):
        if not self.status.empty():
            master_qimage = self.numpy_to_qimage(self.master_layer())
            self.right_pixmap_item.setPixmap(QPixmap.fromImage(master_qimage))
            self._arrange_images()

    def update_current_display(self):
        if not self.status.empty() and self.number_of_layers() > 0:
            current_qimage = self.numpy_to_qimage(self.current_layer())
            self.left_pixmap_item.setPixmap(QPixmap.fromImage(current_qimage))
            self._arrange_images()

    def refresh_display(self):
        self.left_scene.update()
        self.right_scene.update()

    def zoom_in(self):
        if self.status.empty():
            return
        new_zoom = min(self.zoom_factor * 1.1, self.max_scale)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self._apply_zoom()

    def zoom_out(self):
        if self.status.empty():
            return
        new_zoom = max(self.zoom_factor / 1.1, self.min_scale)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self._apply_zoom()

    def reset_zoom(self):
        pixmap_height = self.right_pixmap_item.pixmap().height()
        view_height = self.right_view.height()
        if pixmap_height > 0:
            self.zoom_factor = view_height / pixmap_height
        else:
            self._arrange_images()

    def actual_size(self):
        self.zoom_factor = 1.0
        self._apply_zoom()

    def _apply_zoom(self):
        if not self.left_pixmap_item.pixmap().isNull():
            self.left_view.resetTransform()
            self.left_view.scale(self.zoom_factor, self.zoom_factor)
        if not self.right_pixmap_item.pixmap().isNull():
            self.right_view.resetTransform()
            self.right_view.scale(self.zoom_factor, self.zoom_factor)

    def get_current_scale(self):
        return self.zoom_factor

    def update_brush_cursor(self):
        pass

    def set_allow_cursor_preview(self, state):
        pass

    def setup_brush_cursor(self):
        pass

    def position_on_image(self, pos):
        return self.right_view.mapToScene(pos)

    def get_visible_image_region(self):
        if self.empty():
            return None
        view_rect = self.right_view.viewport().rect()
        return self.right_view.mapToScene(view_rect).boundingRect()
