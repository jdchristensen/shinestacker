# pylint: disable=C0114, C0115, C0116, E0611, W0718, R0903, E0611
import os
import json
import traceback
import jsonpickle
from PySide6.QtCore import QStandardPaths
from .. config.constants import constants
from .. config.gui_constants import gui_constants


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


DEFAULT_SETTINGS = {
    'expert_options': constants.DEFAULT_EXPERT_OPTIONS,
    'view_strategy': constants.DEFAULT_VIEW_STRATEGY,
    'paint_refresh_time': gui_constants.DEFAULT_PAINT_REFRESH_TIME,
    'display_refresh_time': gui_constants.DEFAULT_DISPLAY_REFRESH_TIME,
    'cursor_update_time': gui_constants.DEFAULT_CURSOR_UPDATE_TIME,
    'min_mouse_step_brush_fraction': gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION,
    'combined_actions_params': {
        'max_threads': constants.DEFAULT_MAX_FWK_THREADS
    },
    'align_frames_params': {
        'max_threads': constants.DEFAULT_ALIGN_MAX_THREADS
    },
    'focus_stack_params': {
        'max_threads': constants.DEFAULT_PY_MAX_THREADS
    },
    'focus_stack_bunch_params': {
        'max_threads': constants.DEFAULT_PY_MAX_THREADS
    }
}

CURRENT_VERSION = 1


class Settings(StdPathFile):
    _instance = None
    _observers = []

    def __init__(self, filename):
        if Settings._instance is not None:
            raise RuntimeError("Settings is a singleton.")
        super().__init__(filename)
        self.settings = DEFAULT_SETTINGS
        file_path = self.get_file_path()
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding="utf-8") as file:
                    json_data = json.load(file)
                    settings = json_data['settings']
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                print(f"Can't read file from path {file_path}. Default settings ignored.")
                settings = {}
            self.settings = {**self.settings, **settings}

    @classmethod
    def instance(cls, filename="shinestacker-settings.txt"):
        if cls._instance is None:
            cls._instance = cls(filename)
        return cls._instance

    @classmethod
    def add_observer(cls, observer):
        cls._observers.append(observer)

    def set(self, key, value):
        self.settings[key] = value

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def update(self):
        try:
            config_dir = self.get_config_dir()
            os.makedirs(config_dir, exist_ok=True)
            json_data = {'version': CURRENT_VERSION, 'settings': self.settings}
            json_obj = jsonpickle.encode(json_data)
            with open(self.get_file_path(), 'w', encoding="utf-8") as f:
                f.write(json_obj)
        except IOError as e:
            raise e
        for observer in Settings._observers:
            observer.update(self.settings)

    @classmethod
    def reset_instance_only_for_testing(cls):
        cls._instance = None
