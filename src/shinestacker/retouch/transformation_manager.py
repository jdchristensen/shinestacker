# pylint: disable=C0114, C0115, C0116, E1101, W0718
from .. algorithms.utils import rotate_90_cw, rotate_90_ccw, rotate_180
from .layer_collection import LayerCollectionHandler


class TransfromationManager(LayerCollectionHandler):
    def __init__(self, editor):
        super().__init__(editor.layer_collection)
        self.editor = editor

    def transform(self, transf_func, label):
        if self.has_no_master_layer():
            return
        try:
            self.editor.undo_manager.extend_undo_area(0, 0, 1, 1)  # dummy for the moment
            self.editor.undo_manager.save_undo_state(self.editor.master_layer_copy(), label)
        except Exception:
            pass
        self.set_master_layer(transf_func(self.master_layer()))
        self.set_layer_stack([transf_func(layer) for layer in self.layer_stack()])
        self.copy_master_layer()
        self.editor.image_viewer.update_master_display()
        self.editor.image_viewer.refresh_display()
        self.editor.display_manager.update_thumbnails()
        self.editor.mark_as_modified()

    def rotate_90_cw(self):
        self.transform(rotate_90_cw, "Rotate 90° CW")

    def rotate_90_ccw(self):
        self.transform(rotate_90_ccw, "Rotate 90° CCW")

    def rotate_180(self):
        self.transform(rotate_180, "Rotate 180°")
