import tempfile
import os
import json
import numpy as np
from unittest.mock import patch
from shinestacker.config.settings import Settings


def test_settings_basic_functionality():
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths:
            MockQStandardPaths.writableLocation.return_value = temp_dir
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
                Settings._instance = None
                settings = Settings.instance("test-settings.txt")
                settings.set('test_key', 'test_value')
                assert settings.get('test_key') == 'test_value'
                file_path = settings.get_file_path()
                expected_path = os.path.join(temp_dir, "test-settings.txt")
                assert file_path == expected_path, f"Expected {expected_path}, got {file_path}"
                config_dir = settings.get_config_dir()
                assert config_dir == temp_dir


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
            Settings._instance = None
            settings = Settings.instance("test-settings.txt")
            settings.set('custom_setting', 'custom_value')
            settings.update()  # This should not crash
            file_path = settings.get_file_path()
            assert os.path.exists(file_path)


def test_settings_with_actual_constants():
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths:
            MockQStandardPaths.writableLocation.return_value = temp_dir
            Settings._instance = None
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
            Settings._instance = None
            settings1 = Settings.instance("test-settings.txt")
            original_value = settings1.get('expert_options')
            settings1.set('expert_options', not original_value)
            settings1.update()  # Save to file
            Settings._instance = None
            settings2 = Settings.instance("test-settings.txt")
            assert settings2.get('expert_options') == (not original_value)


def test_settings_extra_keys_filtered():
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths, \
             patch('shinestacker.config.constants.constants') as mock_constants, \
             patch('shinestacker.config.gui_constants.gui_constants') as mock_gui_constants:
            MockQStandardPaths.writableLocation.return_value = temp_dir
            mock_constants.DEFAULT_EXPERT_OPTIONS = True
            mock_constants.DEFAULT_VIEW_STRATEGY = "default"
            mock_constants.DEFAULT_FWK_MAX_THREADS = 4
            mock_constants.DEFAULT_ALIGN_MAX_THREADS = 2
            mock_constants.DEFAULT_PY_MAX_THREADS = 1
            mock_constants.DEFAULT_ALIGN_MEMORY_LIMIT_GB = 8
            mock_constants.DEFAULT_DETECTOR = 'ORB'
            mock_constants.DEFAULT_DESCRIPTOR = 'ORB'
            mock_constants.DEFAULT_MATCHING_METHOD = 'BF'
            mock_constants.DEFAULT_PY_MEMORY_LIMIT_GB = 4
            mock_gui_constants.DEFAULT_PAINT_REFRESH_TIME = 100
            mock_gui_constants.DEFAULT_DISPLAY_REFRESH_TIME = 200
            mock_gui_constants.DEFAULT_CURSOR_UPDATE_TIME = 50
            mock_gui_constants.DEFAULT_MIN_MOUSE_STEP_BRUSH_FRACTION = 0.1
            extra_settings = {
                'expert_options': False,
                'retouch_view_strategy': 'new_strategy',
                'extra_top_level_key': 'should_be_removed',
                'combined_actions_params': {
                    'max_threads': 10,
                    'extra_nested_key': 'should_be_removed'
                }
            }
            file_path = os.path.join(temp_dir, "test-settings.txt")
            with open(file_path, 'w', encoding="utf-8") as f:
                json.dump({'version': 1, 'settings': extra_settings}, f)
            Settings._instance = None
            settings = Settings.instance("test-settings.txt")
            assert 'extra_top_level_key' not in settings.settings
            assert 'extra_nested_key' not in settings.settings['combined_actions_params']
            assert not settings.get('expert_options')
            assert settings.get('retouch_view_strategy') == 'new_strategy'
            assert settings.get('combined_actions_params')['max_threads'] == 10


def test_settings_numpy_type_protection():
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('shinestacker.config.settings.QStandardPaths') as MockQStandardPaths:
            MockQStandardPaths.writableLocation.return_value = temp_dir
            problematic_defaults = {
                'expert_options': np.bool_(False),
                'view_strategy': 'overlaid',
                'test_numpy_int64': np.int64(1),
                'test_numpy_int32': np.int32(2),
                'test_numpy_float64': np.float64(1.5),
                'test_numpy_float32': np.float32(2.5),
                'test_numpy_bool': np.bool_(True),
                'nested_structure': {
                    'numpy_val': np.int64(99),
                    'regular_val': 'test'
                }
            }
            with patch('shinestacker.config.settings.DEFAULTS', problematic_defaults):
                Settings._instance = None
                settings = Settings.instance("test-numpy-settings.txt")
                assert settings.get('test_numpy_int64') == 1
                assert isinstance(settings.get('test_numpy_int64'), int)
                assert settings.get('test_numpy_int32') == 2
                assert isinstance(settings.get('test_numpy_int32'), int)
                assert settings.get('test_numpy_float64') == 1.5
                assert isinstance(settings.get('test_numpy_float64'), float)
                assert settings.get('test_numpy_float32') == 2.5
                assert isinstance(settings.get('test_numpy_float32'), float)
                assert settings.get('test_numpy_bool')
                assert isinstance(settings.get('test_numpy_bool'), bool)
                assert settings.get('nested_structure')['numpy_val'] == 99
                assert isinstance(settings.get('nested_structure')['numpy_val'], int)
                settings.update()
                file_path = settings.get_file_path()
                assert os.path.exists(file_path)
