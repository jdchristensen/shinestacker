# pylint: disable=C0114, C0115, R0903
from .. config.defaults import DEFAULTS


class Brush:
    def __init__(self):
        self.size = DEFAULTS['brush_size']
        self.hardness = DEFAULTS['brush_hardness']
        self.opacity = DEFAULTS['brush_opacity']
        self.flow = DEFAULTS['brush_flow']
