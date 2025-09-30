# pylint: disable=C0114, C0115, C0116, E0611, R0902, W0718, R0904, E1101
import os
import traceback
import numpy as np
import cv2
from PySide6.QtWidgets import (QFileDialog, QMessageBox, QVBoxLayout, QLabel, QDialog,
                               QApplication, QProgressBar)
from PySide6.QtGui import QGuiApplication, QCursor
from PySide6.QtCore import Qt, QObject, QTimer, Signal
from .. algorithms.exif import get_exif, write_image_with_exif_data
from .file_loader import FileLoader
from .exif_data import ExifData
from .io_threads import FileMultilayerSaver, FrameImporter
from .layer_collection import LayerCollectionHandler


class IOGuiHandler(QObject, LayerCollectionHandler):
    status_message_requested = Signal(str)
    update_title_requested = Signal()
    mark_as_modified_requested = Signal(bool)
    change_layer_requested = Signal(int)
    add_recent_file_requested = Signal(str)
    set_enabled_file_open_close_actions_requested = Signal(bool)

    def __init__(self, layer_collection, undo_manager, parent):
        QObject.__init__(self, parent)
        LayerCollectionHandler.__init__(self)
        self.undo_manager = undo_manager
        self.set_layer_collection(layer_collection)
        self.loader_thread = None
        self.display_manager = None
        self.image_viewer = None
        self.loading_dialog = None
        self.loading_timer = None
        self.exif_dialog = None
        self.saver_thread = None
        self.saving_dialog = None
        self.saving_timer = None
        self.current_file_path_master = ''
        self.current_file_path_multi = ''
        self.frame_importer_thread = None
        self.frame_loading_dialog = None
        self.frame_loading_timer = None
        self.progress_label = None
        self.progress_bar = None
        self.exif_data = None
        self.exif_path = ''

    def current_file_path(self):
        return self.current_file_path_master if self.save_master_only.isChecked() \
            else self.current_file_path_multi

    def setup_ui(self, display_manager, image_viewer):
        self.display_manager = display_manager
        self.image_viewer = image_viewer

    def on_file_loaded(self, stack, labels, master_layer):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.hide()
        self.set_layer_stack(stack)
        if labels is None:
            self.set_layer_labels([f'Layer {i:03d}' for i in range(len(stack))])
        else:
            self.set_layer_labels(labels)
        self.set_master_layer(master_layer)
        self.image_viewer.set_master_image_np(master_layer)
        self.set_blank_layer()
        self.undo_manager.reset()
        self.finish_loading_setup(f"Loaded: {self.current_file_path()}")
        self.image_viewer.reset_zoom()

    def on_file_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.loading_timer.stop()
        self.loading_dialog.accept()
        self.loading_dialog.deleteLater()
        QMessageBox.critical(self.parent(), "Error", error_msg)
        self.current_file_path_master = ''
        self.current_file_path_multi = ''
        self.status_message_requested.emit(f"Error loading: {self.current_file_path()}")

    def on_frames_imported(self, stack, labels, master):
        QApplication.restoreOverrideCursor()
        self.frame_loading_timer.stop()
        self.frame_loading_dialog.hide()
        self.frame_loading_dialog.deleteLater()
        empty_viewer = self.image_viewer.empty()
        self.image_viewer.set_master_image_np(master)
        if self.layer_stack() is None and len(stack) > 0:
            self.set_layer_stack(np.array(stack))
            if labels is None:
                labels = self.layer_labels()
            else:
                self.set_layer_labels(labels)
            self.set_master_layer(master)
            self.set_blank_layer()
        else:
            if labels is None:
                labels = self.layer_labels()
            for img, label in zip(stack, labels):
                self.add_layer_label(label)
                self.add_layer(img)
        self.finish_loading_setup("Selected frames imported")
        if empty_viewer:
            self.image_viewer.update_master_display()

    def on_frames_import_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.frame_loading_timer.stop()
        self.frame_loading_dialog.hide()
        self.frame_loading_dialog.deleteLater()
        QMessageBox.critical(self.parent(), "Import Error", error_msg)
        self.status_message_requested.emit("Error importing frames")

    def on_multilayer_saved(self):
        QApplication.restoreOverrideCursor()
        self.saving_timer.stop()
        self.saving_dialog.hide()
        self.saving_dialog.deleteLater()
        self.mark_as_modified_requested.emit(False)
        self.update_title_requested.emit()
        self.add_recent_file_requested.emit(self.current_file_path_multi)
        self.status_message_requested.emit(f"Saved multilayer to: {self.current_file_path_multi}")

    def on_multilayer_save_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        self.saving_timer.stop()
        self.saving_dialog.hide()
        self.saving_dialog.deleteLater()
        QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {error_msg}")

    def open_file(self, file_paths=None):
        self.cleanup_old_threads()
        if file_paths is None:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self.parent(), "Open Image", "",
                "Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
        if not file_paths:
            return
        if self.loader_thread and self.loader_thread.isRunning():
            if not self.loader_thread.wait(10000):
                raise RuntimeError("Loading timeout error.")
        if isinstance(file_paths, list) and len(file_paths) > 1:
            self.import_frames_from_files(file_paths)
            return
        path = file_paths[0] if isinstance(file_paths, list) else file_paths
        self.current_file_path_master = os.path.abspath(path)
        self.current_file_path_multi = os.path.abspath(path)
        QGuiApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        self.loading_dialog = QDialog(self.parent())
        self.loading_dialog.setWindowTitle("Loading")
        self.loading_dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.loading_dialog.setModal(True)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("File loading..."))
        self.loading_dialog.setLayout(layout)
        self.loading_timer = QTimer()
        self.loading_timer.setSingleShot(True)
        self.loading_timer.timeout.connect(self.loading_dialog.show)
        self.loading_timer.start(100)
        self.loader_thread = FileLoader(path)
        self.loader_thread.finished.connect(self.on_file_loaded)
        self.loader_thread.error.connect(self.on_file_error)
        self.loader_thread.start()

    def import_frames(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.parent(), "Select frames", "",
            "Images Images (*.tif *.tiff *.jpg *.jpeg);;All Files (*)")
        if file_paths:
            self.import_frames_from_files(file_paths)

    def import_frames_from_files(self, file_paths):
        self.cleanup_old_threads()
        QGuiApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
        self.frame_loading_dialog = QDialog(self.parent())
        self.frame_loading_dialog.setWindowTitle("Loading Frames")
        self.frame_loading_dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.frame_loading_dialog.setModal(True)
        layout = QVBoxLayout()
        self.progress_label = QLabel("Frames loading...")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        self.frame_loading_dialog.setLayout(layout)
        self.frame_loading_timer = QTimer()
        self.frame_loading_timer.setSingleShot(True)
        self.frame_loading_timer.timeout.connect(self.frame_loading_dialog.show)
        self.frame_loading_timer.start(100)
        self.frame_importer_thread = FrameImporter(file_paths, self.master_layer())
        self.frame_importer_thread.finished.connect(self.on_frames_imported)
        self.frame_importer_thread.error.connect(self.on_frames_import_error)
        self.frame_importer_thread.progress.connect(self.update_import_progress)
        self.frame_importer_thread.start()

    def update_import_progress(self, percent, filename):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(percent)
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(f"Loading: {filename} ({percent}%)")

    def finish_loading_setup(self, message):
        self.display_manager.update_thumbnails()
        self.mark_as_modified_requested.emit(True)
        self.change_layer_requested.emit(0)
        self.status_message_requested.emit(message)
        self.update_title_requested.emit()
        self.set_enabled_file_open_close_actions_requested.emit(True)
        self.add_recent_file_requested.emit(self.current_file_path_master)

    def save_file(self):
        if self.save_master_only.isChecked():
            self.save_master()
        else:
            self.save_multilayer()

    def save_file_as(self):
        if self.save_master_only.isChecked():
            self.save_master_as()
        else:
            self.save_multilayer_as()

    def save_multilayer(self):
        if self.layer_stack() is None:
            return
        if self.current_file_path_multi != '':
            extension = self.current_file_path_multi.split('.')[-1]
            if extension in ['tif', 'tiff']:
                self.save_multilayer_to_path(self.current_file_path_multi)
                return
        else:
            self.save_multilayer_as()

    def save_multilayer_as(self):
        if self.layer_stack() is None:
            return
        path, _ = QFileDialog.getSaveFileName(self.parent(), "Save Image", "",
                                              "TIFF Files (*.tif *.tiff);;All Files (*)")
        if path:
            if not path.lower().endswith(('.tif', '.tiff')):
                path += '.tif'
            self.save_multilayer_to_path(path)

    def save_multilayer_to_path(self, path):
        self.cleanup_old_threads()
        try:
            master_layer = {'Master': self.master_layer().copy()}
            individual_layers = dict(zip(
                self.layer_labels(),
                [layer.copy() for layer in self.layer_stack()]
            ))
            images_dict = {**master_layer, **individual_layers}
            self.saver_thread = FileMultilayerSaver(
                images_dict, path, exif_path=self.exif_path)
            self.saver_thread.finished.connect(self.on_multilayer_saved)
            self.saver_thread.error.connect(self.on_multilayer_save_error)
            QGuiApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            self.saving_dialog = QDialog(self.parent())
            self.saving_dialog.setWindowTitle("Saving")
            self.saving_dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self.saving_dialog.setModal(True)
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Saving file..."))
            self.saving_dialog.setLayout(layout)
            self.saving_timer = QTimer()
            self.saving_timer.setSingleShot(True)
            self.saving_timer.timeout.connect(self.saving_dialog.show)
            self.saving_timer.start(100)
            self.saver_thread.start()
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {str(e)}")

    def save_master(self):
        if self.master_layer() is None:
            return
        if self.current_file_path_master != '':
            self.save_master_to_path(self.current_file_path_master)
            return
        self.save_master_as()

    def save_master_as(self):
        if self.layer_stack() is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self.parent(), "Save Image", "",
            "TIFF Files (*.tif *.tiff);;JPEG Files (*.jpg *.jpeg);;All Files (*)")
        if path:
            self.save_master_to_path(path)

    def save_master_to_path(self, path):
        try:
            img = cv2.cvtColor(self.master_layer(), cv2.COLOR_RGB2BGR)
            write_image_with_exif_data(self.exif_data, img, path)
            self.current_file_path_master = os.path.abspath(path)
            # self.mark_as_modified_requested.emit(False)
            self.update_title_requested.emit()
            self.add_recent_file_requested.emit(self.current_file_path_master)
            self.status_message_requested.emit(f"Saved master layer to: {path}")
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            QMessageBox.critical(self.parent(), "Save Error", f"Could not save file: {str(e)}")

    def select_exif_path(self):
        path, _ = QFileDialog.getOpenFileName(None, "Select file with exif data")
        if path:
            self.exif_path = path
            self.exif_data = get_exif(path)
            self.status_message_requested.emit(f"EXIF data extracted from {path}.")
        self.exif_dialog = ExifData(self.exif_data, self.parent())
        self.exif_dialog.exec()

    def close_file(self):
        self.mark_as_modified_requested.emit(False)
        self.layer_collection.reset()
        self.current_file_path_master = ''
        self.current_file_path_multi = ''
        self.undo_manager.reset()
        self.image_viewer.clear_image()
        self.display_manager.thumbnail_list.clear()
        self.display_manager.update_thumbnails()
        self.update_title_requested.emit()
        self.set_enabled_file_open_close_actions_requested.emit(False)
        self.status_message_requested.emit("File closed")

    def cleanup_old_threads(self):
        if self.loader_thread and self.loader_thread.isFinished():
            self.loader_thread = None
        if self.frame_importer_thread and self.frame_importer_thread.isFinished():
            self.frame_importer_thread = None
        if self.saver_thread and self.saver_thread.isFinished():
            self.saver_thread = None
