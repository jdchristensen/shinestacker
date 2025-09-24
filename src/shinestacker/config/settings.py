# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903, E0611
import os
import json
import traceback
import jsonpickle
from PySide6.QtCore import QStandardPaths


class StdPathFile:
    def __init__(self, filename):
        self._config_dir = None
        self.filename = filename

    def get_config_dir(self):
        if self._config_dir is None:
            config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
            if not config_dir:
                if os.name == 'nt':  # Windows
                    config_dir = os.path.join(os.environ.get('APPDATA', ''), 'ShineStacker')
                elif os.name == 'posix':  # macOS and Linux
                    config_dir = os.path.expanduser('~/.config/shinestacker')
                else:
                    config_dir = os.path.join(os.path.expanduser('~'), '.shinestacker')
            os.makedirs(config_dir, exist_ok=True)
            self._config_dir = config_dir
        return self._config_dir

    def get_file_path(self):
        return os.path.join(self.get_config_dir(), self.filename)


class Settings(StdPathFile):
    def __init__(self, filename="shinestacker-settings.txt"):
        super().__init__(filename)
        file_path = self.get_file_path()
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding="utf-8") as file:
                    json_obj = json.load(file)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                raise RuntimeError(f"Can't read file from path {file_path}") from e
            self.settings = json_obj
        else:
            self.settings = {}

    def save(self):
        try:
            json_obj = jsonpickle.encode(self.settings)
            with open(self.get_file_path(), 'w', encoding="utf-8") as f:
                f.write(json_obj)
        except IOError as e:
            raise e
