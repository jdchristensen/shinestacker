import numpy as np
from unittest.mock import Mock
from shinestacker.config.gui_constants import gui_constants
from shinestacker.retouch.undo_manager import UndoManager
from shinestacker.retouch.paint_area_manager import PaintAreaManager


def test_undo_manager_initialization():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    assert undo_manager.undo_stack == []
    assert undo_manager.redo_stack == []
    assert undo_manager.paint_area_manager.x_start == gui_constants.MAX_UNDO_SIZE
    assert undo_manager.paint_area_manager.y_start == gui_constants.MAX_UNDO_SIZE
    assert undo_manager.paint_area_manager.x_end == 0
    assert undo_manager.paint_area_manager.y_end == 0


def test_reset():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    undo_manager.undo_stack = [1, 2, 3]
    undo_manager.redo_stack = [4, 5]
    undo_manager.paint_area_manager.x_start = 10
    undo_manager.paint_area_manager.y_start = 20
    undo_manager.paint_area_manager.x_end = 30
    undo_manager.paint_area_manager.y_end = 40
    undo_manager.reset()
    assert undo_manager.undo_stack == []
    assert undo_manager.redo_stack == []
    assert undo_manager.paint_area_manager.x_start == gui_constants.MAX_UNDO_SIZE
    assert undo_manager.paint_area_manager.y_start == gui_constants.MAX_UNDO_SIZE
    assert undo_manager.paint_area_manager.x_end == 0
    assert undo_manager.paint_area_manager.y_end == 0


def test_reset_undo_area():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    undo_manager.paint_area_manager.x_start = 10
    undo_manager.paint_area_manager.y_start = 20
    undo_manager.paint_area_manager.x_end = 30
    undo_manager.paint_area_manager.y_end = 40
    undo_manager.reset_undo_area()
    assert undo_manager.paint_area_manager.x_end == 0
    assert undo_manager.paint_area_manager.y_end == 0
    assert undo_manager.paint_area_manager.x_start == gui_constants.MAX_UNDO_SIZE
    assert undo_manager.paint_area_manager.y_start == gui_constants.MAX_UNDO_SIZE


def test_save_undo_state_with_none_layer():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    undo_manager.save_undo_state(None, "test")
    assert len(undo_manager.undo_stack) == 0
    assert len(undo_manager.redo_stack) == 0


def test_save_undo_state_normal():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_layer = np.zeros((20, 20))
    undo_manager.paint_area_manager.x_start = 5
    undo_manager.paint_area_manager.y_start = 5
    undo_manager.paint_area_manager.x_end = 10
    undo_manager.paint_area_manager.y_end = 10
    undo_manager.save_undo_state(mock_layer, "test operation")
    assert len(undo_manager.undo_stack) == 1
    assert undo_manager.undo_stack[0]['description'] == "test operation"
    assert undo_manager.redo_stack == []


def test_save_undo_state_overflow():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_layer = np.zeros((20, 20))
    undo_manager.paint_area_manager.x_start = 5
    undo_manager.paint_area_manager.y_start = 5
    undo_manager.paint_area_manager.x_end = 10
    undo_manager.paint_area_manager.y_end = 10
    for i in range(gui_constants.MAX_UNDO_SIZE + 5):
        undo_manager.save_undo_state(mock_layer, f"op{i}")
    assert len(undo_manager.undo_stack) == gui_constants.MAX_UNDO_SIZE


def test_undo_with_no_stack():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    result = undo_manager.undo(np.zeros((10, 10)))
    assert not result


def test_undo_normal_operation():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_layer = np.zeros((20, 20))
    mock_layer[5:10, 5:10] = 1
    original_state = mock_layer[5:10, 5:10].copy()
    undo_manager.paint_area_manager.x_start = 5
    undo_manager.paint_area_manager.y_start = 5
    undo_manager.paint_area_manager.x_end = 10
    undo_manager.paint_area_manager.y_end = 10
    undo_manager.save_undo_state(mock_layer, "test")
    mock_layer[5:10, 5:10] = 2
    undo_manager.undo(mock_layer)
    assert np.array_equal(mock_layer[5:10, 5:10], original_state)
    assert len(undo_manager.undo_stack) == 0
    assert len(undo_manager.redo_stack) == 1


def test_undo_rotate_operations():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_layer = np.zeros((20, 20))
    undo_manager.undo_stack = [
        {'description': gui_constants.ROTATE_90_CW_LABEL, 'area': (0, 0, 0, 0)}]
    undo_manager.undo(mock_layer)
    mock_transformation_manager.rotate_90_ccw.assert_called_once_with(False)
    mock_transformation_manager.reset_mock()
    undo_manager.undo_stack = [
        {'description': gui_constants.ROTATE_90_CCW_LABEL, 'area': (0, 0, 0, 0)}]
    undo_manager.undo(mock_layer)
    mock_transformation_manager.rotate_90_cw.assert_called_once_with(False)
    mock_transformation_manager.reset_mock()
    undo_manager.undo_stack = [
        {'description': gui_constants.ROTATE_180_LABEL, 'area': (0, 0, 0, 0)}]
    undo_manager.undo(mock_layer)
    mock_transformation_manager.rotate_180.assert_called_once_with(False)


def test_redo_with_no_stack():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    result = undo_manager.redo(np.zeros((10, 10)))
    assert not result


def test_redo_normal_operation():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_layer = np.zeros((20, 20))
    mock_layer[5:10, 5:10] = 1
    undo_manager.paint_area_manager.x_start = 5
    undo_manager.paint_area_manager.y_start = 5
    undo_manager.paint_area_manager.x_end = 10
    undo_manager.paint_area_manager.y_end = 10
    undo_manager.save_undo_state(mock_layer, "test")
    mock_layer[5:10, 5:10] = 2
    undo_manager.undo(mock_layer)
    undo_manager.redo(mock_layer)
    assert np.array_equal(mock_layer[5:10, 5:10], 2 * np.ones((5, 5)))
    assert len(undo_manager.undo_stack) == 1
    assert len(undo_manager.redo_stack) == 0


def test_redo_rotate_operations():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_layer = np.zeros((20, 20))
    undo_manager.redo_stack = [
        {'description': gui_constants.ROTATE_90_CW_LABEL, 'area': (0, 0, 0, 0)}]
    undo_manager.redo(mock_layer)
    mock_transformation_manager.rotate_90_cw.assert_called_once_with(False)
    mock_transformation_manager.reset_mock()
    undo_manager.redo_stack = [
        {'description': gui_constants.ROTATE_90_CCW_LABEL, 'area': (0, 0, 0, 0)}]
    undo_manager.redo(mock_layer)
    mock_transformation_manager.rotate_90_ccw.assert_called_once_with(False)
    mock_transformation_manager.reset_mock()
    undo_manager.redo_stack = [
        {'description': gui_constants.ROTATE_180_LABEL, 'area': (0, 0, 0, 0)}]
    undo_manager.redo(mock_layer)
    mock_transformation_manager.rotate_180.assert_called_once_with(False)


def test_signal_emission_on_save():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_slot = Mock()
    undo_manager.stack_changed.connect(mock_slot)
    mock_layer = np.zeros((20, 20))
    undo_manager.paint_area_manager.x_start = 5
    undo_manager.paint_area_manager.y_start = 5
    undo_manager.paint_area_manager.x_end = 10
    undo_manager.paint_area_manager.y_end = 10
    undo_manager.save_undo_state(mock_layer, "test")
    mock_slot.assert_called_once_with(True, "test", False, "")


def test_signal_emission_on_undo():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_slot = Mock()
    undo_manager.stack_changed.connect(mock_slot)
    mock_layer = np.zeros((20, 20))
    undo_manager.paint_area_manager.x_start = 5
    undo_manager.paint_area_manager.y_start = 5
    undo_manager.paint_area_manager.x_end = 10
    undo_manager.paint_area_manager.y_end = 10
    undo_manager.save_undo_state(mock_layer, "test")
    mock_slot.reset_mock()
    undo_manager.undo(mock_layer)
    mock_slot.assert_called_once_with(False, "", True, "test")


def test_signal_emission_on_redo():
    mock_transformation_manager = Mock()
    mock_paint_area_manager = PaintAreaManager()
    undo_manager = UndoManager(mock_transformation_manager, mock_paint_area_manager)
    mock_slot = Mock()
    undo_manager.stack_changed.connect(mock_slot)
    mock_layer = np.zeros((20, 20))
    undo_manager.paint_area_manager.x_start = 5
    undo_manager.paint_area_manager.y_start = 5
    undo_manager.paint_area_manager.x_end = 10
    undo_manager.paint_area_manager.y_end = 10
    undo_manager.save_undo_state(mock_layer, "test")
    undo_manager.undo(mock_layer)
    mock_slot.reset_mock()
    undo_manager.redo(mock_layer)
    mock_slot.assert_called_once_with(True, "test", False, "")


if __name__ == "__main__":
    pytest_main = __import__('pytest')
    pytest_main.main([__file__, "-v"])
