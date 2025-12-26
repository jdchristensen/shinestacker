# pylint: disable=C0114, C0115, C0116, E0611, R0903
from PySide6.QtWidgets import QPushButton
from ..gui.project_model import get_action_input_path
from ..config.constants import constants
from ..gui.colors import ColorPalette
from .base_widget import BaseWidget
from .action_widget import ActionWidget


class JobWidget(BaseWidget):
    def __init__(self, job, dark_theme=False, parent=None):
        super().__init__(job, 50, dark_theme, parent)
        in_path = get_action_input_path(job)[0]
        self._add_path_label(f"📁 {self._format_path(in_path)}")
        if hasattr(job, 'sub_actions') and job.sub_actions:
            for action in job.sub_actions:
                action_widget = ActionWidget(action, dark_theme)
                self.add_child_widget(action_widget, add_to_layout=True)
        self.retouch_button = QPushButton("🖌️")
        self.retouch_button.setToolTip("Retouch outputs")
        self.retouch_button.clicked.connect(self._on_retouch_clicked)
        header_layout = self.layout().itemAt(0).layout()
        header_layout.insertWidget(1, self.retouch_button)
        header_layout.insertSpacing(2, 4)
        self._update_button_style()
        self.retouch_button.setVisible(self._should_show_retouch_button())

    def widget_type(self):
        return 'JobWidget'

    def update(self, data_object):
        super().update(data_object)
        in_path = get_action_input_path(data_object)[0]
        path_text = f"📁 <i>{self._format_path(in_path)}</i></i>"
        self._add_path_label(path_text)
        if hasattr(self, 'retouch_button'):
            self.retouch_button.setVisible(self._should_show_retouch_button())
            self._update_button_style()

    def _update_button_style(self):
        if self._dark_theme:
            color = ColorPalette.LIGHT_BLUE.hex()
        else:
            color = ColorPalette.DARK_BLUE.hex()
        style = f"""
            QPushButton {{
                color: #{color};
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: #{ColorPalette.MEDIUM_BLUE.hex()};
            }}
        """
        self.retouch_button.setStyleSheet(style)

    def _should_show_retouch_button(self):
        job = self.data_object
        if not hasattr(job, 'sub_actions'):
            return False
        for action in job.sub_actions:
            if action.type_name in [constants.ACTION_COMBO,
                                    constants.ACTION_FOCUSSTACK,
                                    constants.ACTION_FOCUSSTACKBUNCH]:
                return True
        return False

    def _on_retouch_clicked(self):
        parent = self.parent()
        while parent and not hasattr(parent, 'run_retouch_path'):
            parent = parent.parent()
        if parent:
            retouch_paths = parent.get_retouch_path(self.data_object)
            if retouch_paths:
                parent.run_retouch_path(self.data_object, retouch_paths)

    def set_dark_theme(self, dark_theme):
        super().set_dark_theme(dark_theme)
        if hasattr(self, 'retouch_button'):
            self._update_button_style()
