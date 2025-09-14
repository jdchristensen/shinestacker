# pylint: disable=C0114, C0115, C0116, R0904, R0915, E0611, R0902, R0911, R0914, E1003
from PySide6.QtCore import Qt, Signal, QEvent, QRectF
from PySide6.QtGui import QPixmap, QPen, QColor, QCursor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QFrame, QGraphicsEllipseItem
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
        self.mouse_pressed.emit(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(event)

    def mouseReleaseEvent(self, event):
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

        self.left_view.installEventFilter(self)
        self.right_view.installEventFilter(self)
        self.left_view.setFocusPolicy(Qt.NoFocus)
        self.right_view.setFocusPolicy(Qt.NoFocus)

        self.left_brush_cursor = None
        self.setup_left_brush_cursor()

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
        # pylint: disable=C0103, W0201
        self.left_view.enterEvent = self.left_view_enter_event
        self.left_view.leaveEvent = self.left_view_leave_event
        self.right_view.enterEvent = self.right_view_enter_event
        self.right_view.leaveEvent = self.right_view_leave_event
        # pylint: enable=C0103, W0201

    def left_view_enter_event(self, event):
        self.activateWindow()
        self.setFocus()
        self.update_brush_cursor()
        super(ImageGraphicsView, self.left_view).enterEvent(event)

    def left_view_leave_event(self, event):
        self.update_brush_cursor()
        super(ImageGraphicsView, self.left_view).leaveEvent(event)

    def right_view_enter_event(self, event):
        self.activateWindow()
        self.setFocus()
        self.update_brush_cursor()
        super(ImageGraphicsView, self.right_view).enterEvent(event)

    def right_view_leave_event(self, event):
        self.update_brush_cursor()
        super(ImageGraphicsView, self.right_view).leaveEvent(event)

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
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.activateWindow()
        self.setFocus()

    def eventFilter(self, obj, event):
        if obj in [self.left_view, self.right_view]:
            if event.type() == QEvent.KeyPress:
                self.keyPressEvent(event)
                return True
            if event.type() == QEvent.KeyRelease:
                self.keyReleaseEvent(event)
                return True
        return super().eventFilter(obj, event)

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
        if self.brush_cursor:
            self.brush_cursor.hide()
        if self.left_brush_cursor:
            self.left_brush_cursor.hide()
        self.right_view.setCursor(Qt.ArrowCursor)
        self.left_view.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Space:
            self.update_brush_cursor()

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        if event.key() == Qt.Key_Space:
            self.update_brush_cursor()
    # pylint: enable=C0103

    def setup_brush_cursor(self):
        super().setup_brush_cursor()
        self.setup_left_brush_cursor()
        self.update_cursor_pen_width()

    def setup_left_brush_cursor(self):
        if not self.brush:
            return
        for item in self.left_scene.items():
            if isinstance(item, QGraphicsEllipseItem) and item != self.brush_preview:
                self.left_scene.removeItem(item)
        pen_width = gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()
        pen = QPen(QColor(255, 0, 0), pen_width)
        brush = Qt.NoBrush
        self.left_brush_cursor = self.left_scene.addEllipse(
            0, 0, self.brush.size, self.brush.size, pen, brush)
        self.left_brush_cursor.setZValue(1000)
        self.left_brush_cursor.hide()

    def update_left_brush_cursor(self, scene_pos):
        if not self.left_brush_cursor or not self.isVisible():
            return
        size = self.brush.size
        radius = size / 2
        self.left_brush_cursor.setRect(
            scene_pos.x() - radius, scene_pos.y() - radius, size, size)
        if self.brush_cursor and self.brush_cursor.isVisible():
            self.left_brush_cursor.show()
        else:
            self.left_brush_cursor.hide()

    def update_cursor_pen_width(self):
        if not self.brush_cursor or not self.left_brush_cursor:
            return
        pen_width = gui_constants.BRUSH_LINE_WIDTH / self.zoom_factor()
        right_pen = self.brush_cursor.pen()
        right_pen.setWidthF(pen_width)
        self.brush_cursor.setPen(right_pen)
        left_pen = self.left_brush_cursor.pen()
        left_pen.setWidthF(pen_width)
        self.left_brush_cursor.setPen(left_pen)

    def update_brush_cursor(self):
        if self.empty():
            return
        self.update_cursor_pen_width()
        mouse_pos_global = QCursor.pos()
        mouse_pos_left = self.left_view.mapFromGlobal(mouse_pos_global)
        mouse_pos_right = self.right_view.mapFromGlobal(mouse_pos_global)
        left_has_mouse = self.left_view.rect().contains(mouse_pos_left)
        right_has_mouse = self.right_view.rect().contains(mouse_pos_right)
        if right_has_mouse:
            super().update_brush_cursor()
            self.sync_left_cursor_with_right()
            if self.space_pressed:
                cursor_style = Qt.OpenHandCursor if not self.scrolling else Qt.ClosedHandCursor
                self.right_view.setCursor(cursor_style)
                self.left_view.setCursor(cursor_style)
            else:
                self.right_view.setCursor(Qt.BlankCursor)
                self.left_view.setCursor(Qt.BlankCursor)
        elif left_has_mouse:
            scene_pos = self.left_view.mapToScene(mouse_pos_left)
            size = self.brush.size
            radius = size / 2
            self.left_brush_cursor.setRect(
                scene_pos.x() - radius,
                scene_pos.y() - radius,
                size, size
            )
            self.left_brush_cursor.show()
            if self.brush_cursor:
                self.brush_cursor.setRect(
                    scene_pos.x() - radius,
                    scene_pos.y() - radius,
                    size, size
                )
                self.brush_cursor.show()
            if self.space_pressed:
                cursor_style = Qt.OpenHandCursor if not self.panning_left else Qt.ClosedHandCursor
                self.left_view.setCursor(cursor_style)
                self.right_view.setCursor(cursor_style)
            else:
                self.left_view.setCursor(Qt.BlankCursor)
                self.right_view.setCursor(Qt.BlankCursor)
        else:
            if self.brush_cursor:
                self.brush_cursor.hide()
            if self.left_brush_cursor:
                self.left_brush_cursor.hide()
            self.right_view.setCursor(Qt.ArrowCursor)
            self.left_view.setCursor(Qt.ArrowCursor)

    def handle_right_mouse_press(self, event):
        self.setFocus()
        self.mouse_press_event(event)

    def handle_right_mouse_move(self, event):
        self.mouse_move_event(event)
        self.update_brush_cursor()

    def handle_right_mouse_release(self, event):
        self.mouse_release_event(event)

    def handle_left_mouse_press(self, event):
        position = event.position()
        if self.space_pressed:
            self.pan_start = position
            self.panning_left = True
            self.update_brush_cursor()

    def handle_left_mouse_move(self, event):
        position = event.position()
        if self.panning_left and self.space_pressed:
            delta = position - self.pan_start
            self.pan_start = position
            self.scroll_view(self.left_view, delta.x(), delta.y())
        else:
            self.update_brush_cursor()

    def handle_left_mouse_release(self, _event):
        if self.panning_left:
            self.panning_left = False
            self.update_brush_cursor()

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
        self.right_pixmap_item.setPixmap(pixmap)
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
        self.brush_preview.setPos(max(0, min(center.x(), img_width)),
                                  max(0, min(center.y(), img_height)))
        self.right_scene.setSceneRect(QRectF(self.right_pixmap_item.boundingRect()))

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        pixmap = self.status.pixmap_current
        self.left_scene.setSceneRect(QRectF(pixmap.rect()))
        self.left_pixmap_item.setPixmap(pixmap)
        self.left_view.resetTransform()
        self.left_scene.scale(self.zoom_factor(), self.zoom_factor())
        # self.left_view.centerOn(self.left_pixmap_item)
        self.left_scene.setSceneRect(QRectF(self.left_pixmap_item.boundingRect()))

    def _arrange_images(self):
        if self.status.empty():
            return
        if self.right_pixmap_item.pixmap().height() == 0:
            self.update_master_display()
            self.update_current_display()
            self.reset_zoom()
        self._apply_zoom()

    def update_master_display(self):
        if not self.status.empty():
            master_qimage = self.numpy_to_qimage(self.master_layer())
            if master_qimage:
                pixmap = QPixmap.fromImage(master_qimage)
                self.right_pixmap_item.setPixmap(pixmap)
                self.right_scene.setSceneRect(QRectF(pixmap.rect()))
                self._arrange_images()

    def update_current_display(self):
        if not self.status.empty() and self.number_of_layers() > 0:
            current_qimage = self.numpy_to_qimage(self.current_layer())
            if current_qimage:
                pixmap = QPixmap.fromImage(current_qimage)
                self.left_pixmap_item.setPixmap(pixmap)
                self.left_scene.setSceneRect(QRectF(pixmap.rect()))
                self._arrange_images()

    def _apply_zoom(self):
        if not self.left_pixmap_item.pixmap().isNull():
            self.left_view.resetTransform()
            self.left_view.scale(self.zoom_factor(), self.zoom_factor())
            # self.left_view.centerOn(self.left_pixmap_item)
        if not self.right_pixmap_item.pixmap().isNull():
            self.right_view.resetTransform()
            self.right_view.scale(self.zoom_factor(), self.zoom_factor())
            # self.right_view.centerOn(self.right_pixmap_item)

    def set_brush(self, brush):
        super().set_brush(brush)
        if self.brush_cursor:
            self.right_scene.removeItem(self.brush_cursor)
        self.setup_brush_cursor()
        self.setup_left_brush_cursor()

    def clear_image(self):
        super().clear_image()
        if self.left_brush_cursor:
            self.left_scene.removeItem(self.left_brush_cursor)
            self.left_brush_cursor = None

    def sync_left_cursor_with_right(self):
        if not self.brush_cursor or not self.left_brush_cursor:
            return
        right_rect = self.brush_cursor.rect()
        scene_pos = right_rect.center()
        size = self.brush.size
        radius = size / 2
        self.left_brush_cursor.setRect(
            scene_pos.x() - radius,
            scene_pos.y() - radius,
            size, size
        )
        if self.brush_cursor.isVisible():
            self.left_brush_cursor.show()
        else:
            self.left_brush_cursor.hide()

    def zoom_in(self):
        super().zoom_in()
        self.update_cursor_pen_width()

    def zoom_out(self):
        super().zoom_out()
        self.update_cursor_pen_width()

    def reset_zoom(self):
        super().reset_zoom()
        self.update_cursor_pen_width()

    def actual_size(self):
        super().actual_size()
        self.update_cursor_pen_width()
