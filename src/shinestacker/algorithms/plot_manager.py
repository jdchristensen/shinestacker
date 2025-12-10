# pylint: disable=C0114, C0115, C0116, R0903, R0903
from abc import ABC, abstractmethod
from .utils import save_plot


class PlotManager(ABC):
    @abstractmethod
    def save_plot(self, filename: str, fig):
        pass


class DirectPlotManager(PlotManager):
    def save_plot(self, filename, fig):
        save_plot(filename, fig)
