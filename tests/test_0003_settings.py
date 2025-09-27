import tempfile
import os
from unittest.mock import patch
from shinestacker.config.settings import Settings


def test_settings_basic_functionality():
    with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths:
        MockQStandardPaths.writableLocation.return_value = tempfile.gettempdir()
        with patch('shinestacker.config.constants.constants') as mock_constants, \
             patch('shinestacker.config.gui_constants.gui_constants') as mock_gui_constants:
            mock_constants.DEFAULT_EXPERT_OPTIONS = True
            mock_constants.DEFAULT_VIEW_STRATEGY = "default_view"
            mock_constants.DEFAULT_MAX_FWK_THREADS = 4
            mock_constants.DEFAULT_ALIGN_MAX_THREADS = 2
            mock_constants.DEFAULT_PY_MAX_THREADS = 1
            mock_gui_constants.DEFAULT_PAINT_REFRESH_TIME = 100
            mock_gui_constants.DEFAULT_DISPLAY_REFRESH_TIME = 200
            mock_gui_constants.DEFAULT_CURSOR_UPDATE_TIME = 50
            mock_gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION = 0.1
            settings = Settings("test-settings.txt")
            settings.set('test_key', 'test_value')
            assert settings.get('test_key') == 'test_value'
            file_path = settings.get_file_path()
            assert file_path.endswith("test-settings.txt")
            config_dir = settings.get_config_dir()
            assert config_dir == tempfile.gettempdir()


def test_settings_file_operations():
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths, \
             patch('shinestacker.config.constants.constants') as mock_constants, \
             patch('shinestacker.config.gui_constants.gui_constants') as mock_gui_constants:
            MockQStandardPaths.writableLocation.return_value = temp_dir
            mock_constants.DEFAULT_EXPERT_OPTIONS = True
            mock_constants.DEFAULT_VIEW_STRATEGY = "default"
            mock_constants.DEFAULT_MAX_FWK_THREADS = 4
            mock_constants.DEFAULT_ALIGN_MAX_THREADS = 2
            mock_constants.DEFAULT_PY_MAX_THREADS = 1
            mock_gui_constants.DEFAULT_PAINT_REFRESH_TIME = 100
            mock_gui_constants.DEFAULT_DISPLAY_REFRESH_TIME = 200
            mock_gui_constants.DEFAULT_CURSOR_UPDATE_TIME = 50
            mock_gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION = 0.1
            from shinestacker.config.settings import Settings
            settings = Settings.instance("test-settings.txt")
            settings.set('custom_setting', 'custom_value')
            settings.update()
            file_path = settings.get_file_path()
            assert os.path.exists(file_path)


def test_settings_with_actual_constants():
    with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths:
        MockQStandardPaths.writableLocation.return_value = tempfile.gettempdir()
        settings = Settings.instance("test-settings.txt")
        original_value = settings.get('expert_options')
        settings.set('expert_options', not original_value)
        assert settings.get('expert_options') == (not original_value)
        max_threads = settings.get('combined_actions_params')['max_threads']
        assert isinstance(max_threads, int)


def test_settings_persistence():
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths:
            MockQStandardPaths.writableLocation.return_value = temp_dir
            from shinestacker.config.settings import Settings
            settings1 = Settings.instance("test-settings.txt")
            settings1.set('custom_key', 'custom_value')
            settings1.update()
            Settings.reset_instance_only_for_testing()
            settings2 = Settings.instance("test-settings.txt")
            assert settings2.get('custom_key') == 'custom_value'
