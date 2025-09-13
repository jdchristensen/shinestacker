# pylint: disable=C0114, C0115, C0116, R0904, R0915, E0611, R0902, R0911
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QFrame, QGraphicsView, QGraphicsScene,
                               QGraphicsPixmapItem, QGraphicsEllipseItem)
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QCursor
from PySide6.QtCore import Qt, Signal, QPoint, QPointF, QEvent, QTime
from .. config.gui_constants import gui_constants
from .view_strategy import ViewStrategy
from .brush_preview import BrushPreviewItem
from .brush_gradient import create_default_brush_gradient

class ImageGraphicsView(QGraphicsView):
    mouse_pressed = Signal(QPointF)
    mouse_moved = Signal(QPointF)
    mouse_released = Signal(QPointF)
    gesture_event = Signal(QEvent)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setInteractive(False)
        self.grabGesture(Qt.PinchGesture)

    def event(self, event):
        if event.type() == QEvent.Gesture:
            self.gesture_event.emit(event)
            return True
        return super().event(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed.emit(event.position())
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(event.position())
        super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_released.emit(event.position())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class SideBySideView(ViewStrategy, QWidget):
    temp_view_requested = Signal(bool)
    brush_operation_started = Signal(QPoint)
    brush_operation_continued = Signal(QPoint)
    brush_operation_ended = Signal()
    brush_size_change_requested = Signal(int)

    def __init__(self, brush_preview, status, parent):
        ViewStrategy.__init__(self, brush_preview, status)
        QWidget.__init__(self, parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.left_view, self.left_scene, self.left_pixmap_item = self._create_view()
        self.right_view, self.right_scene, self.right_pixmap_item = self._create_view()
        
        layout.addWidget(self.left_view)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(2)
        layout.addWidget(separator)
        
        layout.addWidget(self.right_view)
        
        self._connect_signals()
        
        self.zoom_factor = 1.0
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
        self.allow_cursor_preview = True
        self.setup_brush_cursor()
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def _create_view(self):
        view = ImageGraphicsView()
        scene = QGraphicsScene()
        view.setScene(scene)
        view.setRenderHint(QPainter.Antialiasing)
        view.setRenderHint(QPainter.SmoothPixmapTransform)
        
        pixmap_item = QGraphicsPixmapItem()
        scene.addItem(pixmap_item)
        scene.setBackgroundBrush(QBrush(QColor(120, 120, 120)))
        
        return view, scene, pixmap_item

    def _connect_signals(self):
        self.left_view.mouse_pressed.connect(self.handle_left_mouse_press)
        self.left_view.mouse_moved.connect(self.handle_left_mouse_move)
        self.left_view.mouse_released.connect(self.handle_left_mouse_release)
        self.left_view.gesture_event.connect(self.handle_gesture_event)
        
        self.right_view.mouse_pressed.connect(self.handle_right_mouse_press)
        self.right_view.mouse_moved.connect(self.handle_right_mouse_move)
        self.right_view.mouse_released.connect(self.handle_right_mouse_release)
        self.right_view.gesture_event.connect(self.handle_gesture_event)
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

    def keyPressEvent(self, event):
        if self.empty():
            return
        if event.key() == Qt.Key_Space and not self.scrolling:
            self.space_pressed = True
            self.right_view.setCursor(Qt.OpenHandCursor)
            if self.brush_cursor:
                self.brush_cursor.hide()
            event.accept()
        elif event.key() == Qt.Key_Control and not self.scrolling:
            self.control_pressed = True
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.empty():
            return
        if event.key() == Qt.Key_Space:
            self.space_pressed = False
            if not self.scrolling:
                self.right_view.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
            event.accept()
        elif event.key() == Qt.Key_Control:
            self.control_pressed = False
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_images()

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

    def handle_right_mouse_press(self, position):
        if self.has_master_layer():
            if self.space_pressed:
                self.scrolling = True
                self.last_mouse_pos = position
                self.right_view.setCursor(Qt.ClosedHandCursor)
            else:
                self.last_brush_pos = position
                self.brush_operation_started.emit(position.toPoint())
                self.dragging = True
            if self.brush_cursor:
                self.brush_cursor.show()

    def handle_right_mouse_move(self, position):
        self.update_brush_cursor()            
        if self.dragging:
            current_time = QTime.currentTime()
            if self.last_update_time.msecsTo(current_time) >= gui_constants.PAINT_REFRESH_TIMER:
                self.brush_operation_continued.emit(position.toPoint())
                self.last_brush_pos = position
                self.last_update_time = current_time
        elif self.scrolling:
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

    def handle_right_mouse_release(self, position):
        if self.scrolling:
            self.scrolling = False
            if self.space_pressed:
                self.right_view.setCursor(Qt.OpenHandCursor)
            else:
                self.right_view.setCursor(Qt.BlankCursor)
                if self.brush_cursor:
                    self.brush_cursor.show()
        elif self.dragging:
            self.brush_operation_ended.emit()
            self.dragging = False

    def handle_left_mouse_press(self, position):
        if self.space_pressed:
            self.pan_start = position
            self.panning_left = True

    def handle_left_mouse_move(self, position):
        if self.panning_left and self.space_pressed:
            delta = position - self.pan_start
            self.pan_start = position
            self.left_view.horizontalScrollBar().setValue(
                self.left_view.horizontalScrollBar().value() - delta.x())
            self.left_view.verticalScrollBar().setValue(
                self.left_view.verticalScrollBar().value() - delta.y())

    def handle_left_mouse_release(self, position):
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
            self.pinch_start_scale = self.zoom_factor
            self.pinch_center_view = pinch.centerPoint()
            self.pinch_center_scene = self.right_view.mapToScene(self.pinch_center_view.toPoint())
        elif pinch.state() == Qt.GestureUpdated:
            new_scale = self.pinch_start_scale * pinch.totalScaleFactor()
            new_scale = max(self.min_scale(), min(new_scale, self.max_scale()))
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
            self.right_scene.addItem(self.brush_preview)
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
        self.setup_brush_cursor()
        self.brush_preview = BrushPreviewItem(self.layer_collection)
        self.right_scene.addItem(self.brush_preview)
        self.setCursor(Qt.ArrowCursor)
        if self.brush_cursor:
            self.brush_cursor.hide()

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
        new_zoom = min(self.zoom_factor * gui_constants.ZOOM_IN_FACTOR, self.max_scale())
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self._apply_zoom()
            self.update_brush_cursor()

    def zoom_out(self):
        if self.status.empty():
            return
        new_zoom = max(self.zoom_factor * gui_constants.ZOOM_OUT_FACTOR, self.min_scale())
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self._apply_zoom()
            self.update_brush_cursor()

    def reset_zoom(self):
        pixmap_height = self.right_pixmap_item.pixmap().height()
        view_height = self.right_view.height()
        if pixmap_height > 0:
            self.zoom_factor = view_height / pixmap_height
        else:
            self._arrange_images()
        self.update_brush_cursor()

    def actual_size(self):
        self.zoom_factor = 1.0
        self._apply_zoom()
        self.update_brush_cursor()

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
        if self.empty():
            return
        if not self.brush_cursor or not self.isVisible():
            return         
        mouse_pos = self.right_view.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(mouse_pos):
            self.brush_cursor.hide()
            return
        scene_pos = self.right_view.mapToScene(mouse_pos)
        size = self.brush.size
        radius = size / 2
        self.brush_cursor.setRect(scene_pos.x() - radius, scene_pos.y() - radius, size, size)
        allow_cursor_preview = self.display_manager.allow_cursor_preview()
        if self.cursor_style == 'preview' and allow_cursor_preview:
            self._setup_outline_style()
            self.brush_cursor.hide()
            pos = QCursor.pos()
            if isinstance(pos, QPointF):
                scene_pos = pos
            else:
                cursor_pos = self.mapFromGlobal(pos)
                scene_pos = self.mapToScene(cursor_pos)
            self.brush_preview.update(scene_pos, int(size))
        else:
            self.brush_preview.hide()
            if self.cursor_style == 'outline' or not allow_cursor_preview:
                self._setup_outline_style()
            else:
                self._setup_simple_brush_style(scene_pos.x(), scene_pos.y(), radius)
        if not self.brush_cursor.isVisible():
            self.brush_cursor.show()

    def _setup_outline_style(self):
        self.brush_cursor.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                                      gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor))
        self.brush_cursor.setBrush(Qt.NoBrush)

    def _setup_simple_brush_style(self, center_x, center_y, radius):
        gradient = create_default_brush_gradient(center_x, center_y, radius, self.brush)
        self.brush_cursor.setPen(QPen(QColor(*gui_constants.BRUSH_COLORS['pen']),
                                      gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor))
        self.brush_cursor.setBrush(QBrush(gradient))

    def set_allow_cursor_preview(self, state):
        self.allow_cursor_preview = state

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

    def position_on_image(self, pos):
        return self.right_view.mapToScene(pos)

    def get_visible_image_region(self):
        if self.empty():
            return None
        view_rect = self.right_view.viewport().rect()
        scene_rect = self.right_view.mapToScene(view_rect).boundingRect()
        image_rect = self.right_view.mapFromScene(scene_rect).boundingRect()
        image_rect = image_rect.intersected(self.right_pixmap_item.boundingRect().toRect())
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

    def mapToScene(self, pos):
        return self.right_view.mapToScene(pos)
