# pylint: disable=C0114, C0115, C0116, E0611, R0903
from .base_widget import BaseWidget


class SubActionWidget(BaseWidget):
    def __init__(self, data_object, dark_theme=False, parent=None):
        super().__init__(data_object, 35, dark_theme, parent)

    def widget_type(self):
        return 'SubActionWidget'

    def update(self, data_object):
        name = f"<b>{data_object.params['name']}</b> [{data_object.type_name}]"
        self.set_name(name)
