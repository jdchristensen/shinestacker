# pylint: disable=C0114, C0115, C0116, E0611, R0903
from .base_widget import BaseWidget
from ..gui.project_model import get_action_input_path, get_action_output_path


class ActionWidget(BaseWidget):
    def __init__(self, action, dark_theme=False, parent=None):
        action_name = action.params['name']
        super().__init__(action_name, 40, dark_theme, parent)
        in_path = get_action_input_path(action)[0]
        out_path = get_action_output_path(action)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i> → " \
            f"📂 <i>{self._format_path(out_path)}</i>"
        self._add_path_label(path_text)

    def widget_type(self):
        return 'ActionWidget'
