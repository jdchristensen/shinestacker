# pylint: disable=C0114, C0115, C0116, E0611, R0903
from .base_widget import BaseWidget


class SubActionWidget(BaseWidget):
    def __init__(self, sub_action, dark_theme=False, parent=None):
        super().__init__(sub_action, 35, dark_theme, parent)

    def widget_type(self):
        return 'SubActionWidget'

    def update(self, sub_action):
        name = f"<b>{sub_action.params['name']}</b> [{sub_action.type_name}]"
        self.set_name(name)
