# pylint: disable=C0114, C0115, C0116
from .settings import Settings


class AppConfig:
    _instance = None

    def __init__(self):
        if AppConfig._instance is not None:
            raise RuntimeError("AppConfig is a singleton.")
        self.config = {}
        self.load_defaults()

    def load_defaults(self):
        settings = Settings()
        self.config = {**self.config, **settings.settings}

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls, key):
        return cls.instance().config.get(key, None)

    @classmethod
    def set(cls, key, value):
        cls.instance().config[key] = value
