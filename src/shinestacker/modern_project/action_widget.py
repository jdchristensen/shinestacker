# pylint: disable=C0114, C0115, C0116, E0611, R0903
from PySide6.QtWidgets import QWidget, QHBoxLayout
from .base_widget import BaseWidget
from .sub_action_widget import SubActionWidget
from ..gui.project_model import get_action_input_path, get_action_output_path


class ActionWidget(BaseWidget):
    def __init__(self, action, dark_theme=False, parent=None):
        action_name = action.params['name']
        super().__init__(action_name, 50, dark_theme, parent)
        in_path = get_action_input_path(action)[0]
        out_path = get_action_output_path(action)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i> → " \
            f"📂 <i>{self._format_path(out_path)}</i>"
        self._add_path_label(path_text)
        if hasattr(action, 'sub_actions') and action.sub_actions:
            subactions_container = QWidget()
            horizontal_layout = QHBoxLayout(subactions_container)
            horizontal_layout.setContentsMargins(0, 4, 0, 0)
            horizontal_layout.setSpacing(2)
        for sub_action in action.sub_actions:
            sub_action_widget = SubActionWidget(sub_action, dark_theme)
            horizontal_layout.addWidget(sub_action_widget)
            self.add_child_widget(sub_action_widget, add_to_layout=False)
            self.layout().addWidget(subactions_container)

    def widget_type(self):
        return 'ActionWidget'
