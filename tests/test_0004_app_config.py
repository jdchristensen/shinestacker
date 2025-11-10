import pytest
from unittest.mock import patch
import tempfile
from shinestacker.config.app_config import AppConfig
from shinestacker.config.settings import Settings


def test_singleton_instance():
    AppConfig._instance = None
    Settings._instance = None
    first = AppConfig.instance()
    second = AppConfig.instance()
    assert first is second


def test_direct_instantiation_raises_error():
    AppConfig._instance = None
    Settings._instance = None
    AppConfig.instance()
    with pytest.raises(RuntimeError):
        AppConfig()


def test_get_with_default():
    AppConfig._instance = None
    Settings._instance = None
    result = AppConfig.get("nonexistent_key", "default_value")
    assert result == "default_value"


def test_set_and_get():
    AppConfig._instance = None
    Settings._instance = None
    AppConfig.set("test_key", "test_value")
    result = AppConfig.get("test_key")
    assert result == "test_value"


def test_loads_defaults():
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths, \
             patch('shinestacker.config.constants.constants') as mock_constants, \
             patch('shinestacker.config.gui_constants.gui_constants') as mock_gui_constants:
            MockQStandardPaths.writableLocation.return_value = temp_dir
            mock_constants.DEFAULT_EXPERT_OPTIONS = True
            mock_constants.DEFAULT_VIEW_STRATEGY = "default_view"
            mock_constants.DEFAULT_MAX_FWK_THREADS = 4
            mock_constants.DEFAULT_ALIGN_MAX_THREADS = 2
            mock_constants.DEFAULT_PY_MAX_THREADS = 1
            mock_gui_constants.DEFAULT_PAINT_REFRESH_TIME = 100
            mock_gui_constants.DEFAULT_DISPLAY_REFRESH_TIME = 200
            mock_gui_constants.DEFAULT_CURSOR_UPDATE_TIME = 50
            mock_gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION = 0.1
            AppConfig._instance = None
            Settings._instance = None
            instance = AppConfig.instance()
            settings = Settings.instance()
            assert instance.config == settings.settings
