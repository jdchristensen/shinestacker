# pylint: disable=C0114, C0115, C0116, R0903, R0903, E0611
from PySide6.QtCore import Signal, QObject


class QtPlotManager(QObject):
    save_plot_signal = Signal(str, object)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)

    def save_plot(self, filename, fig):
        self.save_plot_signal.emit(filename, fig)
