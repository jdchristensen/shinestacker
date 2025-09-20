# pylint: disable=C0114, C0115, C0116, R0904, R0915, E0611, R0902, R0911, R0914, E1003
from PySide6.QtCore import Qt, Signal, QEvent, QRectF
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame
from .view_strategy import ViewStrategy, ImageGraphicsViewBase, ViewSignals


class ImageGraphicsView(ImageGraphicsViewBase):
    mouse_pressed = Signal(QEvent)
    mouse_moved = Signal(QEvent)
    mouse_released = Signal(QEvent)
    gesture_event = Signal(QEvent)
    wheel_event = Signal(QEvent)

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

    def wheelEvent(self, event):
        self.wheel_event.emit(event)
        event.accept()
    # pylint: enable=C0103


class DoubleViewBase(ViewStrategy, QWidget, ViewSignals):
    def __init__(self, layer_collection, status, parent):
        ViewStrategy.__init__(self, layer_collection, status)
        QWidget.__init__(self, parent)
        self.current_view = ImageGraphicsView(parent)
        self.master_view = ImageGraphicsView(parent)
        self.current_scene = self.create_scene(self.current_view)
        self.master_scene = self.create_scene(self.master_view)
        self.create_pixmaps()
        self.master_scene.addItem(self.brush_preview)
        self.setup_layout()
        self._connect_signals()
        self.panning_current = False
        self.brush_cursor = None
        self.setFocusPolicy(Qt.StrongFocus)
        self.pan_start = None
        self.pinch_start_scale = None
        self.current_view.installEventFilter(self)
        self.master_view.installEventFilter(self)
        self.current_view.setFocusPolicy(Qt.NoFocus)
        self.master_view.setFocusPolicy(Qt.NoFocus)
        self.current_brush_cursor = None

    def setup_layout(self):
        raise NotImplementedError("Subclasses must implement setup_layout")

    def create_pixmaps(self):
        self.pixmap_item_current = self.create_pixmap(self.current_scene)
        self.pixmap_item_master = self.create_pixmap(self.master_scene)

    def _connect_signals(self):
        self.current_view.mouse_pressed.connect(self.handle_current_mouse_press)
        self.current_view.mouse_moved.connect(self.handle_current_mouse_move)
        self.current_view.mouse_released.connect(self.handle_current_mouse_release)
        self.current_view.gesture_event.connect(self.handle_gesture_event)
        self.master_view.mouse_pressed.connect(self.handle_master_mouse_press)
        self.master_view.mouse_moved.connect(self.handle_master_mouse_move)
        self.master_view.mouse_released.connect(self.handle_master_mouse_release)
        self.master_view.gesture_event.connect(self.handle_gesture_event)
        self.current_view.horizontalScrollBar().valueChanged.connect(
            self.master_view.horizontalScrollBar().setValue)
        self.current_view.verticalScrollBar().valueChanged.connect(
            self.master_view.verticalScrollBar().setValue)
        self.master_view.horizontalScrollBar().valueChanged.connect(
            self.current_view.horizontalScrollBar().setValue)
        self.master_view.verticalScrollBar().valueChanged.connect(
            self.current_view.verticalScrollBar().setValue)
        self.current_view.wheel_event.connect(self.handle_wheel_event)
        self.master_view.wheel_event.connect(self.handle_wheel_event)
        # pylint: disable=C0103, W0201
        self.current_view.enterEvent = self.current_view_enter_event
        self.current_view.leaveEvent = self.current_view_leave_event
        self.master_view.enterEvent = self.master_view_enter_event
        self.master_view.leaveEvent = self.master_view_leave_event
        # pylint: enable=C0103, W0201

    def current_view_enter_event(self, event):
        self.activateWindow()
        self.setFocus()
        if not self.empty():
            self.update_brush_cursor()
        super(ImageGraphicsView, self.current_view).enterEvent(event)

    def current_view_leave_event(self, event):
        if not self.empty():
            self.update_brush_cursor()
        super(ImageGraphicsView, self.current_view).leaveEvent(event)

    def master_view_enter_event(self, event):
        self.activateWindow()
        self.setFocus()
        if not self.empty():
            self.update_brush_cursor()
        super(ImageGraphicsView, self.master_view).enterEvent(event)

    def master_view_leave_event(self, event):
        if not self.empty():
            self.update_brush_cursor()
        super(ImageGraphicsView, self.master_view).leaveEvent(event)

    def get_master_view(self):
        return self.master_view

    def get_current_view(self):
        return self.current_view

    def get_master_scene(self):
        return self.master_scene

    def get_current_scene(self):
        return self.current_scene

    def get_master_pixmap(self):
        return self.pixmap_item_master

    def get_current_pixmap(self):
        return self.pixmap_item_current

    def get_views(self):
        return [self.master_view, self.current_view]

    def get_scenes(self):
        return [self.master_scene, self.current_scene]

    def get_pixmaps(self):
        return {
            self.pixmap_item_master: self.master_view,
            self.pixmap_item_current: self.current_view
        }

    # pylint: disable=C0103
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.activateWindow()
        self.setFocus()

    def eventFilter(self, obj, event):
        if obj in [self.current_view, self.master_view]:
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
        if self.empty():
            self.setCursor(Qt.ArrowCursor)
            self.master_view.setCursor(Qt.ArrowCursor)
            self.current_view.setCursor(Qt.ArrowCursor)
        else:
            if self.space_pressed:
                self.master_view.setCursor(Qt.OpenHandCursor)
                self.current_view.setCursor(Qt.OpenHandCursor)
            else:
                if self.brush_cursor is None or self.current_brush_cursor is None:
                    self.setup_brush_cursor()
                self.master_view.setCursor(Qt.BlankCursor)
                self.current_view.setCursor(Qt.BlankCursor)
                self.brush_cursor.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.empty():
            self.setCursor(Qt.ArrowCursor)
            self.master_view.setCursor(Qt.ArrowCursor)
            self.current_view.setCursor(Qt.ArrowCursor)
        else:
            if self.brush_cursor is None or self.current_brush_cursor is None:
                self.setup_brush_cursor()
            self.brush_cursor.hide()
            self.current_brush_cursor.hide()
            self.master_view.setCursor(Qt.ArrowCursor)
            self.current_view.setCursor(Qt.ArrowCursor)
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

    # pylint: enable=R0801
    def handle_wheel_event(self, event):
        if self.empty() or self.gesture_active:
            return
        if event.source() == Qt.MouseEventNotSynthesized:  # Physical mouse
            if self.control_pressed:
                self.brush_size_change_requested.emit(1 if event.angleDelta().y() > 0 else -1)
            else:
                if event.angleDelta().y() > 0:  # Zoom in
                    self.zoom_in()
                else:  # Zoom out
                    self.zoom_out()
        else:  # Touchpad event - handle scrolling
            if not self.control_pressed:
                delta = event.pixelDelta() or event.angleDelta() / 8
                if delta:
                    self.scroll_view(self.master_view, delta.x(), delta.y())
                    self.scroll_view(self.current_view, delta.x(), delta.y())
    # pylint: disable=R0801

    def _apply_zoom_to_view(self, view, factor):
        view.scale(factor, factor)
        other_view = self.current_view if view == self.master_view else self.master_view
        other_view.resetTransform()
        other_view.scale(self.zoom_factor(), self.zoom_factor())

    def show_master(self):
        self.pixmap_item_master.setVisible(True)
        self.pixmap_item_current.setVisible(True)

    def show_current(self):
        self.pixmap_item_master.setVisible(True)
        self.pixmap_item_current.setVisible(True)

    def setup_brush_cursor(self):
        super().setup_brush_cursor()
        self.setup_current_brush_cursor()

    def setup_current_brush_cursor(self):
        if not self.brush:
            return
        self.current_brush_cursor = self.create_alt_circle(
            self.get_current_scene(), line_style=Qt.SolidLine)

    def update_cursor_pen_width(self):
        pen_width = super().update_cursor_pen_width()
        if self.current_brush_cursor:
            current_pen = self.current_brush_cursor.pen()
            current_pen.setWidthF(pen_width)
            self.current_brush_cursor.setPen(current_pen)
        return pen_width

    def update_brush_cursor(self):
        if self.empty():
            return
        if self.brush_cursor is None or self.current_brush_cursor is None:
            self.setup_brush_cursor()
        self.update_cursor_pen_width()
        if self.space_pressed:
            cursor_style = Qt.OpenHandCursor if not self.scrolling else Qt.ClosedHandCursor
            self.master_view.setCursor(cursor_style)
            self.current_view.setCursor(cursor_style)
            self.brush_cursor.hide()
            self.current_brush_cursor.hide()
            return
        self.master_view.setCursor(Qt.BlankCursor)
        self.current_view.setCursor(Qt.BlankCursor)
        mouse_pos_global = QCursor.pos()
        mouse_pos_current = self.current_view.mapFromGlobal(mouse_pos_global)
        mouse_pos_master = self.master_view.mapFromGlobal(mouse_pos_global)
        current_has_mouse = self.current_view.rect().contains(mouse_pos_current)
        master_has_mouse = self.master_view.rect().contains(mouse_pos_master)
        self.current_brush_cursor.hide()
        if master_has_mouse:
            if self.cursor_style == 'preview':
                self.brush_preview.show()
            super().update_brush_cursor()
            self.sync_current_cursor_with_master()
        elif current_has_mouse:
            self.brush_preview.hide()
            scene_pos = self.current_view.mapToScene(mouse_pos_current)
            size = self.brush.size
            radius = size / 2
            self.current_brush_cursor.setRect(
                scene_pos.x() - radius, scene_pos.y() - radius, size, size)
            self.current_brush_cursor.show()
            self.brush_cursor.setRect(
                scene_pos.x() - radius, scene_pos.y() - radius, size, size)
            self.brush_cursor.show()
        else:
            self.brush_cursor.hide()
            self.current_brush_cursor.hide()
            self.master_view.setCursor(Qt.ArrowCursor)
            self.current_view.setCursor(Qt.ArrowCursor)

    def handle_master_mouse_press(self, event):
        self.setFocus()
        self.mouse_press_event(event)

    def handle_master_mouse_move(self, event):
        self.mouse_move_event(event)
        self.update_brush_cursor()

    def handle_master_mouse_release(self, event):
        self.mouse_release_event(event)

    def handle_current_mouse_press(self, event):
        position = event.position()
        if self.space_pressed:
            self.pan_start = position
            self.panning_current = True
            self.update_brush_cursor()

    def handle_current_mouse_move(self, event):
        position = event.position()
        if self.panning_current and self.space_pressed:
            delta = position - self.pan_start
            self.pan_start = position
            self.scroll_view(self.current_view, delta.x(), delta.y())
        else:
            self.update_brush_cursor()

    def handle_current_mouse_release(self, _event):
        if self.panning_current:
            self.panning_current = False
            self.update_brush_cursor()

    def handle_gesture_event(self, event):
        if self.empty():
            return
        pinch_gesture = event.gesture(Qt.PinchGesture)
        if pinch_gesture:
            self.handle_pinch_gesture(pinch_gesture)
            event.accept()

    def set_master_image(self, qimage):
        self.status.set_master_image(qimage)
        pixmap = self.status.pixmap_master
        self.master_view.setSceneRect(QRectF(pixmap.rect()))
        self.pixmap_item_master.setPixmap(pixmap)
        img_width, img_height = pixmap.width(), pixmap.height()
        self.set_max_min_scales(img_width, img_height)
        view_rect = self.master_view.viewport().rect()
        scale_x = view_rect.width() / img_width
        scale_y = view_rect.height() / img_height
        scale_factor = min(scale_x, scale_y)
        scale_factor = max(self.min_scale(), min(scale_factor, self.max_scale()))
        self.set_zoom_factor(scale_factor)
        self.master_view.resetTransform()
        self.master_view.scale(scale_factor, scale_factor)
        self.master_view.centerOn(self.pixmap_item_master)
        center = self.master_scene.sceneRect().center()
        self.brush_preview.setPos(max(0, min(center.x(), img_width)),
                                  max(0, min(center.y(), img_height)))
        self.master_scene.setSceneRect(QRectF(self.pixmap_item_master.boundingRect()))
        self.center_image(self.master_view)
        self.update_cursor_pen_width()

    def set_current_image(self, qimage):
        self.status.set_current_image(qimage)
        pixmap = self.status.pixmap_current
        self.current_scene.setSceneRect(QRectF(pixmap.rect()))
        self.pixmap_item_current.setPixmap(pixmap)
        self.current_view.resetTransform()
        self.master_view.scale(self.zoom_factor(), self.zoom_factor())
        self.current_scene.setSceneRect(QRectF(self.pixmap_item_current.boundingRect()))
        self.center_image(self.current_view)

    def arrange_images(self):
        if self.status.empty():
            return
        if self.pixmap_item_master.pixmap().height() == 0:
            self.update_master_display()
            self.update_current_display()
            self.reset_zoom()
        else:
            self.center_image(self.master_view)
        self.apply_zoom()

    def clear_image(self):
        super().clear_image()
        self.setCursor(Qt.ArrowCursor)
        self.master_view.setCursor(Qt.ArrowCursor)
        self.current_view.setCursor(Qt.ArrowCursor)
        if self.current_brush_cursor:
            self.current_scene.removeItem(self.current_brush_cursor)
            self.current_brush_cursor = None

    def sync_current_cursor_with_master(self):
        if not self.brush_cursor or not self.current_brush_cursor:
            return
        master_rect = self.brush_cursor.rect()
        scene_pos = master_rect.center()
        size = self.brush.size
        radius = size / 2
        self.current_brush_cursor.setRect(
            scene_pos.x() - radius, scene_pos.y() - radius,
            size, size)
        if self.brush_cursor.isVisible():
            self.current_brush_cursor.show()
        else:
            self.current_brush_cursor.hide()


class SideBySideView(DoubleViewBase):
    def setup_layout(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.current_view, 1)
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(2)
        layout.addWidget(separator, 0)
        layout.addWidget(self.master_view, 1)


class TopBottomView(DoubleViewBase):
    def setup_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.current_view, 1)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(2)
        layout.addWidget(separator, 0)
        layout.addWidget(self.master_view, 1)
