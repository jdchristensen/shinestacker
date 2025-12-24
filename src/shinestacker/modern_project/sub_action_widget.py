# pylint: disable=C0114, C0115, C0116, E0611, R0903
from .base_widget import BaseWidget


class SubActionWidget(BaseWidget):
    def __init__(self, data_object, dark_theme=False, parent=None):
        super().__init__(data_object, 35, dark_theme, parent)

    def widget_type(self):
        return 'SubActionWidget'
