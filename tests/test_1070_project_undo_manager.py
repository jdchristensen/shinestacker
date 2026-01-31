import unittest
from PySide6.QtCore import QCoreApplication
from shinestacker.common_project.project_undo_manager import ProjectUndoManager

class TestProjectUndoManager(unittest.TestCase):
    def setUp(self):
        self.app = QCoreApplication.instance() or QCoreApplication()
        self.manager = ProjectUndoManager()

    def test_initial_state(self):
        self.assertEqual(len(self.manager._undo_buffer), 0)
        self.assertEqual(len(self.manager._redo_buffer), 0)

    def test_add_entry(self):
        self.manager.add(item="test", description="Test Action")
        self.assertEqual(len(self.manager._undo_buffer), 1)
        self.assertEqual(self.manager._undo_buffer[0]['item'], "test")
        self.assertEqual(self.manager._undo_buffer[0]['description'], "Test Action")

    def test_pop_entry(self):
        self.manager.add(item="test1", description="Action1")
        self.manager.add(item="test2", description="Action2")
        entry = self.manager.pop()
        self.assertEqual(entry['item'], "test2")
        self.assertEqual(len(self.manager._undo_buffer), 1)
        self.assertEqual(self.manager._undo_buffer[0]['item'], "test1")

    def test_peek_and_last_entry(self):
        self.assertIsNone(self.manager.peek())
        self.assertIsNone(self.manager.last_entry())
        self.manager.add(item="test", description="Action")
        self.assertEqual(self.manager.peek()['item'], "test")
        self.assertEqual(self.manager.last_entry()['item'], "test")

    def test_filled(self):
        self.assertFalse(self.manager.filled())
        self.manager.add(item="test", description="Action")
        self.assertTrue(self.manager.filled())

    def test_reset(self):
        self.manager.add(item="test1", description="Action1")
        self.manager.add(item="test2", description="Action2")
        self.manager.add_to_redo({'item':'redo', 'description':'RedoAction'})
        self.manager.reset()
        self.assertEqual(len(self.manager._undo_buffer), 0)
        self.assertEqual(len(self.manager._redo_buffer), 0)

    def test_add_extra_data_to_last_entry(self):
        self.manager.add(item="test", description="Action")
        self.manager.add_extra_data_to_last_entry("extra", "data")
        self.assertEqual(self.manager.peek()['extra'], "data")

    def test_clear_redo(self):
        self.manager.add_to_redo({'item':'redo', 'description':'RedoAction'})
        self.manager.clear_redo()
        self.assertEqual(len(self.manager._redo_buffer), 0)

    def test_add_to_undo_and_redo(self):
        entry = {'item':'test', 'description':'Test'}
        self.manager.add_to_undo(entry)
        self.assertEqual(self.manager.peek()['item'], 'test')
        self.manager.add_to_redo(entry)
        self.assertEqual(self.manager.peek_redo()['item'], 'test')

    def test_pop_redo(self):
        self.manager.add_to_redo({'item':'redo1', 'description':'Redo1'})
        self.manager.add_to_redo({'item':'redo2', 'description':'Redo2'})
        entry = self.manager.pop_redo()
        self.assertEqual(entry['item'], 'redo2')
        self.assertEqual(len(self.manager._redo_buffer), 1)

    def test_peek_redo(self):
        self.assertIsNone(self.manager.peek_redo())
        self.manager.add_to_redo({'item':'redo', 'description':'Redo'})
        self.assertEqual(self.manager.peek_redo()['item'], 'redo')

    def test_filled_redo(self):
        self.assertFalse(self.manager.filled_redo())
        self.manager.add_to_redo({'item':'redo', 'description':'Redo'})
        self.assertTrue(self.manager.filled_redo())

if __name__ == 'main':
    unittest.main()
