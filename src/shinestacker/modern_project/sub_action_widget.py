# pylint: disable=C0114, C0115, C0116, E0611, R0903
from .base_widget import BaseWidget


class SubActionWidget(BaseWidget):
    def __init__(self, sub_action, dark_theme=False, parent=None):
        sub_action_name = sub_action.params['name']
        super().__init__(sub_action_name, 35, dark_theme, parent)

    def widget_type(self):
        return 'SubActionWidget'
