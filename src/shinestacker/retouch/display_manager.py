# pylint: disable=C0114, C0115, C0116, E0611, R0903, R0913, R0917, E1121, R0902
import numpy as np
from PySide6.QtWidgets import (QWidget, QListWidgetItem, QVBoxLayout, QLabel, QInputDialog,
                               QAbstractItemView)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QObject, QTimer, QSize, Signal
from .. config.gui_constants import gui_constants
from .layer_collection import LayerCollectionHandler


class ClickableLabel(QLabel):
    double_clicked = Signal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)

    # pylint: disable=C0103
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
    # pylint: enable=C0103


class DisplayManager(QObject, LayerCollectionHandler):
    status_message_requested = Signal(str)

    def __init__(self, layer_collection, image_viewer, master_thumbnail_label,
                 thumbnail_list, parent=None):
        QObject.__init__(self, parent)
        LayerCollectionHandler.__init__(self, layer_collection)
        self.image_viewer = image_viewer
        self.master_thumbnail_label = master_thumbnail_label
        self.thumbnail_list = thumbnail_list
        self.view_mode = 'master'
        self.needs_update = False
        self.update_timer = QTimer()
        self.update_timer.setInterval(gui_constants.PAINT_REFRESH_TIMER)
        self.update_timer.timeout.connect(self.process_pending_updates)
        self.thumbnail_highlight = gui_constants.THUMB_LO_COLOR

    def process_pending_updates(self):
        if self.needs_update:
            self.refresh_master_view()
            self.needs_update = False

    def create_thumbnail(self, layer):
        source_layer = (layer // 256).astype(np.uint8) if layer.dtype == np.uint16 else layer
        if not source_layer.flags.c_contiguous:
            source_layer = np.ascontiguousarray(source_layer)
        height, width = source_layer.shape[:2]
        if layer.ndim == 3 and source_layer.shape[-1] == 3:
            qimg = QImage(source_layer.data, width, height, 3 * width, QImage.Format_RGB888)
        else:
            qimg = QImage(source_layer.data, width, height, width, QImage.Format_Grayscale8)
        return QPixmap.fromImage(
            qimg.scaledToWidth(
                gui_constants.UI_SIZES['thumbnail_width'], Qt.SmoothTransformation))

    def update_thumbnails(self):
        self.update_master_thumbnail()
        thumbnails = []
        if self.layer_stack() is None:
            return
        for i, (layer, label) in enumerate(zip(self.layer_stack(), self.layer_labels())):
            thumbnail = self.create_thumbnail(layer)
            thumbnails.append((thumbnail, label, i, i == self.current_layer_idx()))
        self._update_thumbnail_list(thumbnails)

    def _update_thumbnail_list(self, thumbnails):
        self.thumbnail_list.clear()
        for thumb_data in thumbnails:
            thumbnail, label, index, is_current = thumb_data
            self.add_thumbnail_item(thumbnail, label, index, is_current)

    def update_master_thumbnail(self):
        if self.has_no_master_layer():
            self._clear_master_thumbnail()
        else:
            self._set_master_thumbnail(self.create_thumbnail(self.master_layer()))

    def _clear_master_thumbnail(self):
        self.master_thumbnail_label.clear()

    def _set_master_thumbnail(self, pixmap):
        self.master_thumbnail_label.setPixmap(pixmap)

    def add_thumbnail_item(self, thumbnail, label, i, is_current):
        container = QWidget()
        container.setFixedWidth(gui_constants.UI_SIZES['thumbnail_width'] + 4)
        container.setObjectName("thumbnailContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(2, 2, 2, 2)
        container_layout.setSpacing(0)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        thumbnail_label = QLabel()
        thumbnail_label.setPixmap(thumbnail)
        thumbnail_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(thumbnail_label)
        label_widget = ClickableLabel(label)
        label_widget.setFixedHeight(gui_constants.UI_SIZES['label_height'])
        label_widget.setAlignment(Qt.AlignCenter)

        def rename_label(label_widget, old_label, i):
            new_label, ok = QInputDialog.getText(
                self.thumbnail_list, "Rename Label", "New label name:", text=old_label)
            if ok and new_label and new_label != old_label:
                label_widget.setText(new_label)
                self.set_layer_labels(i, new_label)

        label_widget.double_clicked.connect(lambda: rename_label(label_widget, label, i))
        content_layout.addWidget(label_widget)
        container_layout.addWidget(content_widget)
        if is_current:
            container.setStyleSheet(
                f"#thumbnailContainer{{ border: 2px solid {self.thumbnail_highlight}; }}")
        else:
            container.setStyleSheet("#thumbnailContainer{ border: 2px solid transparent; }")
        item = QListWidgetItem()
        item.setSizeHint(QSize(gui_constants.UI_SIZES['thumbnail_width'] + 4,
                               thumbnail.height() + label_widget.height() + 4))
        self.thumbnail_list.addItem(item)
        self.thumbnail_list.setItemWidget(item, container)
        if is_current:
            self.thumbnail_list.setCurrentItem(item)

    def highlight_thumbnail(self, index):
        for i in range(self.thumbnail_list.count()):
            item = self.thumbnail_list.item(i)
            widget = self.thumbnail_list.itemWidget(item)
            if widget:
                widget.setStyleSheet("#thumbnailContainer{ border: 2px solid transparent; }")
        current_item = self.thumbnail_list.item(index)
        if current_item:
            widget = self.thumbnail_list.itemWidget(current_item)
            if widget:
                widget.setStyleSheet(
                    f"#thumbnailContainer{{ border: 2px solid {self.thumbnail_highlight}; }}")
        self.thumbnail_list.setCurrentRow(index)
        self.thumbnail_list.scrollToItem(
            self.thumbnail_list.item(index), QAbstractItemView.PositionAtCenter)

    def _master_refresh_and_thumb(self):
        self.image_viewer.show_master()
        self.refresh_master_view()
        self.thumbnail_highlight = gui_constants.THUMB_LO_COLOR
        self.highlight_thumbnail(self.current_layer_idx())

    def _current_refresh_and_thumb(self):
        self.image_viewer.show_current()
        self.refresh_current_view()
        self.thumbnail_highlight = gui_constants.THUMB_HI_COLOR
        self.highlight_thumbnail(self.current_layer_idx())

    def set_view_master(self):
        if self.has_no_master_layer():
            return
        self.view_mode = 'master'
        self._master_refresh_and_thumb()
        self.status_message_requested.emit("View mode: Master")

    def set_view_individual(self):
        if self.has_no_master_layer():
            return
        self.view_mode = 'individual'
        self._current_refresh_and_thumb()
        self.status_message_requested.emit("View mode: Individual layers")

    def refresh_master_view(self):
        if self.has_no_master_layer():
            return
        self.image_viewer.update_master_display()
        self.image_viewer.refresh_display()
        self.update_master_thumbnail()

    def refresh_current_view(self):
        if self.number_of_layers() == 0:
            return
        self.image_viewer.update_current_display()
        self.image_viewer.refresh_display()

    def start_temp_view(self):
        if self.view_mode == 'master':
            self._current_refresh_and_thumb()
            self.status_message_requested.emit("Temporary view: Individual layer")
        else:
            self._master_refresh_and_thumb()
            self.image_viewer.strategy.brush_preview.hide()
            self.status_message_requested.emit("Temporary view: Master")

    def end_temp_view(self):
        if self.view_mode == 'master':
            self._master_refresh_and_thumb()
            self.status_message_requested.emit("View mode: Master")
        else:
            self._current_refresh_and_thumb()
            self.status_message_requested.emit("View: Individual layer")

    def allow_cursor_preview(self):
        return self.view_mode == 'master'
