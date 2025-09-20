# pylint: disable=C0114, C0115, C0116
class FilterManager:
    def __init__(self, editor):
        self.editor = editor
        self.image_viewer = editor.image_viewer
        self.layer_collection = editor.layer_collection
        self.filters = {}

    def register_filter(self, name, filter_class):
        self.filters[name] = filter_class(
            name, self.editor, self.image_viewer, self.layer_collection)

    def apply(self, name, **kwargs):
        if name in self.filters:
            self.filters[name].run_with_preview(**kwargs)
