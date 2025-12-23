# pylint: disable=C0114, C0115, C0116, E0611, R0903
from .base_widget import BaseWidget
from .action_widget import ActionWidget
from ..gui.project_model import get_action_input_path


class JobWidget(BaseWidget):
    def __init__(self, job, dark_theme=False, parent=None):
        job_name = job.params['name']
        super().__init__(job_name, 50, dark_theme, parent)
        in_path = get_action_input_path(job)[0]
        self._add_path_label(f"📁 {self._format_path(in_path)}")
        if hasattr(job, 'sub_actions') and job.sub_actions:
            for action in job.sub_actions:
                action_widget = ActionWidget(action, dark_theme)
                self.add_child_widget(action_widget)

    def widget_type(self):
        return 'JobWidget'
