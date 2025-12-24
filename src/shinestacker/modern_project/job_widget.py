# pylint: disable=C0114, C0115, C0116, E0611, R0903
from .base_widget import BaseWidget
from .action_widget import ActionWidget
from ..gui.project_model import get_action_input_path


class JobWidget(BaseWidget):
    def __init__(self, job, dark_theme=False, parent=None):
        super().__init__(job, 50, dark_theme, parent)
        in_path = get_action_input_path(job)[0]
        self._add_path_label(f"📁 {self._format_path(in_path)}")
        if hasattr(job, 'sub_actions') and job.sub_actions:
            for action in job.sub_actions:
                action_widget = ActionWidget(action, dark_theme)
                self.add_child_widget(action_widget, add_to_layout=True)

    def widget_type(self):
        return 'JobWidget'

    def update(self, data_object):
        name = f"<b>{data_object.params['name']}</b> [{data_object.type_name}]"
        self.set_name(name)
        in_path = get_action_input_path(data_object)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i></i>"
        self._add_path_label(path_text)
