import os
import tempfile
import threading
import shutil
import unittest
from unittest.mock import patch, MagicMock
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import logging
from shinestacker.algorithms.plot_manager import DirectPlotManager


class TestDirectPlotManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DirectPlotManager()
        logging.getLogger().setLevel(logging.CRITICAL)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        plt.close('all')

    def test_save_plot_success(self):
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        result = self.manager.save_plot(filename, fig)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filename))

    def test_save_plot_creates_directory(self):
        filename = os.path.join(self.temp_dir, 'subdir', 'test_plot.png')
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        result = self.manager.save_plot(filename, fig)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filename))

    def test_save_plot_with_none_fig(self):
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        plt.plot([1, 2, 3], [1, 2, 3])
        result = self.manager.save_plot(filename, None)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filename))

    @patch('shinestacker.algorithms.plot_manager.config')
    @patch('matplotlib.pyplot.show')
    def test_save_plot_jupyter_mode(self, mock_show, mock_config):
        mock_config.JUPYTER_NOTEBOOK = True
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        result = self.manager.save_plot(filename, fig)
        self.assertTrue(result)
        mock_show.assert_called_once()

    @patch('shinestacker.algorithms.plot_manager.config')
    @patch('matplotlib.pyplot.show')
    def test_save_plot_jupyter_mode_exception(self, mock_show, mock_config):
        mock_config.JUPYTER_NOTEBOOK = True
        mock_show.side_effect = Exception("Display error")
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        result = self.manager.save_plot(filename, fig)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filename))

    @patch('matplotlib.figure.Figure.savefig')
    def test_save_plot_savefig_exception(self, mock_savefig):
        mock_savefig.side_effect = Exception("Save error")
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        with self.assertRaises(Exception):
            self.manager.save_plot(filename, fig)
        self.assertFalse(os.path.exists(filename))

    @patch('matplotlib.pyplot.close')
    @patch('matplotlib.figure.Figure.savefig')
    def test_save_plot_close_after_exception(self, mock_savefig, mock_close):
        mock_savefig.side_effect = Exception("Save error")
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        with self.assertRaises(Exception) as context:
            self.manager.save_plot(filename, fig)
        self.assertIn("Save error", str(context.exception))
        mock_close.assert_called_with(fig)

    @patch('matplotlib.pyplot.close')
    @patch('matplotlib.figure.Figure.savefig')
    def test_save_plot_close_exception_handled(self, mock_savefig, mock_close):
        mock_savefig.side_effect = Exception("Save error")
        mock_close.side_effect = Exception("Close error")
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        fig = MagicMock(spec=plt.Figure)
        with self.assertRaises(Exception):
            self.manager.save_plot(filename, fig)

    def test_save_plot_thread_safety(self):
        filename_base = os.path.join(self.temp_dir, 'plot_{}.png')
        results = []

        def save_one(index):
            fig, ax = plt.subplots()
            ax.plot([index, index + 1, index + 2], [1, 2, 3])
            filename = filename_base.format(index)
            results.append(self.manager.save_plot(filename, fig))

        threads = []
        for i in range(5):
            t = threading.Thread(target=save_one, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        self.assertTrue(all(results))
        for i in range(5):
            self.assertTrue(os.path.exists(filename_base.format(i)))

    @patch('shinestacker.algorithms.plot_manager.logging.getLogger')
    def test_logging_level_restoration(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_logger.level = logging.DEBUG
        filename = os.path.join(self.temp_dir, 'test_plot.png')
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        result = self.manager.save_plot(filename, fig)
        self.assertTrue(result)
        self.assertEqual(mock_logger.setLevel.call_count, 2)
        mock_logger.setLevel.assert_any_call(logging.WARNING)
        mock_logger.setLevel.assert_any_call(logging.DEBUG)


if __name__ == '__main__':
    unittest.main()
