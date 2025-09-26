import pytest
from shinestacker.config.app_config import AppConfig
from shinestacker.config.settings import Settings


def test_singleton_instance():
    AppConfig._instance = None
    first = AppConfig.instance()
    second = AppConfig.instance()
    assert first is second


def test_direct_instantiation_raises_error():
    AppConfig._instance = None
    AppConfig.instance()
    with pytest.raises(RuntimeError):
        AppConfig()


def test_get_with_default():
    AppConfig._instance = None
    result = AppConfig.get("nonexistent_key", "default_value")
    assert result == "default_value"


def test_set_and_get():
    AppConfig._instance = None
    AppConfig.set("test_key", "test_value")
    result = AppConfig.get("test_key")
    assert result == "test_value"


def test_loads_defaults():
    AppConfig._instance = None
    instance = AppConfig.instance()
    settings = Settings()
    assert instance.config == settings.settings
